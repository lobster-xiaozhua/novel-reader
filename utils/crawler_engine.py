"""爬虫引擎模块。

提供智能网页解析、URL 安全校验、HTTP 请求管理、
章节内容抓取与持久化等核心爬虫能力。
支持多站点配置、自动重试、请求延迟、代理切换、
UA 轮换等反爬策略。
"""
import re
import time
import json
import socket
import logging
import random
import ipaddress
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests
from apps.books.models import Book
from apps.chapters.models import Chapter
from .crawler_config import get_config_for_url, SiteConfig

logger = logging.getLogger(__name__)


class IntelligentParser:
    """智能 HTML 解析器。

    根据站点配置（SiteConfig）中的 CSS 选择器，
    从 HTML 中提取章节列表、章节内容、书籍信息。
    支持多选择器回退机制，确保在不同站点结构下都能正常解析。
    """

    def __init__(self, config: SiteConfig):
        """初始化解析器。

        Args:
            config: 站点配置对象，包含各类 CSS 选择器和关键词规则。
        """
        self.config = config

    def parse_chapter_list(self, html: str, base_url: str):
        """解析章节列表。

        遍历配置中的章节列表选择器，提取章节标题和 URL。
        自动过滤重复链接和跳过关键词（如"上一页"、"目录"等）。

        Args:
            html: 网页 HTML 源码。
            base_url: 基准 URL，用于拼接相对路径。

        Returns:
            list[dict]: 章节信息列表，每个元素包含 title 和 url。
        """
        soup = BeautifulSoup(html, "html.parser")
        chapters = []
        seen_urls = set()

        for selector in self.config.chapter_list_selectors:
            try:
                containers = soup.select(selector)
                for container in containers:
                    links = container.select(self.config.link_selector)
                    for link in links:
                        href = link.get("href", "")
                        title = link.get_text(strip=True)

                        if not title or not href:
                            continue
                        # 过滤包含跳过关键词的链接（如翻页、返回目录等）
                        if any(skip in title.lower() for skip in self.config.skip_keywords):
                            continue

                        full_url = urljoin(base_url, href)
                        if full_url in seen_urls:
                            continue

                        seen_urls.add(full_url)
                        chapters.append({"title": title, "url": full_url})

                if chapters:
                    break
            except Exception as e:
                logger.warning(f"选择器 {selector} 解析失败: {e}")
                continue

        return chapters

    def parse_chapter_content(self, html: str):
        """解析单个章节的正文内容。

        使用配置中的内容选择器提取章节文本，
        自动清理脚本、样式等无关标签。

        Args:
            html: 章节页 HTML 源码。

        Returns:
            dict: 包含 title 和 content 的字典。
                  content 为空字符串表示解析失败。
        """
        soup = BeautifulSoup(html, "html.parser")

        for selector in self.config.content_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    content = self._clean_content(element)
                    # 内容长度超过 50 字符才视为有效
                    if len(content) > 50:
                        return {"title": "", "content": content}
            except Exception as e:
                logger.warning(f"内容选择器 {selector} 解析失败: {e}")
                continue

        return {"title": "", "content": ""}

    def _clean_content(self, element):
        """清理 HTML 元素，提取纯文本。

        移除 script、style 等干扰标签，
        优先按段落拆分，否则按换行拆分。

        Args:
            element: BeautifulSoup Tag 对象。

        Returns:
            str: 清理后的纯文本，段落之间用双换行分隔。
        """
        for tag in element.find_all(["script", "style", "iframe", "ins", "nav"]):
            tag.decompose()
        paragraphs = element.find_all("p")
        if paragraphs:
            parts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
            return "\n\n".join(parts)
        text = element.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n\n".join(lines)

    def parse_book_info(self, html: str):
        """解析书籍基本信息。

        提取书名、作者、简介等元数据。
        书名选择器未命中时回退到 h1 标签。

        Args:
            html: 书籍详情页 HTML 源码。

        Returns:
            dict: 包含 title、author、description 的字典。
        """
        soup = BeautifulSoup(html, "html.parser")
        info = {"title": "", "author": "", "description": ""}

        if self.config.title_selector:
            title_tag = soup.select_one(self.config.title_selector)
            if title_tag:
                info["title"] = title_tag.get_text(strip=True)

        # 回退策略：如果没有找到标题，尝试 h1 标签
        if not info["title"]:
            title_tag = soup.find("h1")
            if title_tag:
                info["title"] = title_tag.get_text(strip=True)

        if self.config.author_selector:
            author_tag = soup.select_one(self.config.author_selector)
            if author_tag:
                info["author"] = author_tag.get_text(strip=True)

        if self.config.description_selector:
            desc_tag = soup.select_one(self.config.description_selector)
            if desc_tag:
                info["description"] = desc_tag.get_text(strip=True)

        return info


# SSRF 防护：禁止访问的内网和元数据地址
SSRF_BLOCKED_HOSTS = {
    "169.254.169.254", "metadata.google.internal", "localhost", "127.0.0.1", "0.0.0.0", "::1"
}


def validate_crawl_url(url: str) -> bool:
    """校验目标 URL 是否安全可访问。

    防止 SSRF（服务端请求伪造）攻击：
    1. 仅允许 http/https 协议
    2. 禁止访问内网地址和云元数据地址
    3. DNS 解析后检查 IP 是否为私有地址

    Args:
        url: 待校验的 URL 字符串。

    Returns:
        bool: URL 合法且安全返回 True，否则返回 False。
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname or hostname in SSRF_BLOCKED_HOSTS:
        return False
    try:
        resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in resolved_ips:
            ip = sockaddr[0]
            if ipaddress.ip_address(ip).is_private:
                return False
    except socket.gaierror:
        return False
    return True


class CrawlerEngine:
    """爬虫引擎核心类。

    负责管理 HTTP 会话、请求调度、反爬策略（UA 轮换、请求延迟、代理切换）、
    章节抓取与持久化、任务状态追踪等完整爬虫流程。
    """

    def __init__(self, task_id, books_dir):
        """初始化爬虫引擎。

        Args:
            task_id: 爬虫任务 ID。
            books_dir: 书籍存储目录路径。
        """
        self.task_id = task_id
        self.books_dir = Path(books_dir)
        self.config = None
        self.parser = None
        self._ua_index = 0
        self._proxy_index = 0
        self._cookie_index = 0
        self._stop = False

    def _get_ua(self):
        """获取 User-Agent 字符串。

        优先使用站点配置中的 UA 池，
        若未配置则使用全局默认 UA 池。

        Returns:
            str: 随机选取的 User-Agent 字符串。
        """
        pool = self.config.user_agents
        if not pool:
            from .crawler_config import UA_POOL
            pool = UA_POOL
        return random.choice(pool)

    def _get_proxy(self):
        """获取代理配置。

        Returns:
            dict or None: 代理字典 {'http': url, 'https': url}，
                          未启用代理时返回 None。
        """
        if not self.config.use_proxy or not self.config.proxy_url:
            return None
        return {"http": self.config.proxy_url, "https": self.config.proxy_url}

    def _delay(self):
        """根据配置的请求延迟添加随机等待时间。

        实际等待时间 = 配置延迟 × 0.5~1.5 的随机系数。
        """
        wait = self.config.request_delay * random.uniform(0.5, 1.5)
        time.sleep(wait)

    def _fetch_page(self, session, url):
        """发送 HTTP GET 请求获取网页内容。

        支持自动重试、指数退避、UA 轮换、代理切换。

        Args:
            session: requests.Session 实例，保持 Cookie 状态。
            url: 目标 URL。

        Returns:
            str: 网页 HTML 源码。

        Raises:
            requests.RequestException: 所有重试均失败后抛出最后一次异常。
        """
        max_retries = self.config.max_retries
        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                self._delay()
                headers = {
                    "User-Agent": self._get_ua(),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
                proxies = self._get_proxy()
                cookies = self.config.cookies or None
                resp = session.get(
                    url, headers=headers, timeout=30,
                    proxies=proxies, cookies=cookies,
                )
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as e:
                last_exc = e
                # 指数退避 + 随机抖动，避免重试风暴
                jitter = random.uniform(0, 1)
                backoff = self.config.retry_delay * (2 ** (attempt - 1)) + jitter
                logger.warning(
                    f"请求失败 (第{attempt}/{max_retries}次): {url} - {e}, "
                    f"{backoff:.1f}s后重试"
                )
                if attempt < max_retries:
                    time.sleep(backoff)
        raise last_exc

    def _safe_filename(self, name):
        """将书名转为安全的文件名。

        移除非法文件名字符，去除首尾空白和点号，限制长度。

        Args:
            name: 原始书名。

        Returns:
            str: 安全的文件名，最长 100 字符。
        """
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        name = name.strip('. ')
        return name[:100] if name else "unnamed"

    def _append_log(self, task, message):
        """向任务日志追加一条记录。

        Args:
            task: CrawlerTask 模型实例。
            message: 日志消息内容。
        """
        try:
            task.refresh_from_db()
            logs = json.loads(task.logs) if task.logs else []
            logs.append({"time": time.time(), "msg": message})
            task.logs = json.dumps(logs, ensure_ascii=False)
            task.save(update_fields=['logs'])
            logger.info(f"任务 {task.id}: {message}")
        except Exception as e:
            logger.error(f"添加日志失败: {e}")

    def run(self, task):
        """执行完整的爬虫流程。

        包括：URL 校验 → 获取页面 → 解析书籍信息和章节列表 →
        逐章抓取内容 → 保存到本地文件和数据库 → 更新任务状态。

        Args:
            task: CrawlerTask 模型实例。
        """
        # 根据目标 URL 获取对应站点配置
        self.config = get_config_for_url(task.url)
        self.parser = IntelligentParser(self.config)

        logger.info(f"开始执行任务 {task.id}, 站点: {self.config.name}")

        if not validate_crawl_url(task.url):
            task.status = 'failed'
            task.error_message = '目标URL不合法或指向内网/元数据地址，禁止访问'
            task.save()
            logger.error(f"任务 {task.id} URL验证失败")
            return

        task.status = 'running'
        task.save()
        self._append_log(task, '任务开始执行')

        session = requests.Session()

        try:
            html = self._fetch_page(session, task.url)

            book_info = self.parser.parse_book_info(html)
            chapter_list = self.parser.parse_chapter_list(html, task.url)

            if not chapter_list:
                task.status = 'failed'
                task.error_message = '无法解析章节列表'
                task.save()
                self._append_log(task, '无法解析章节列表')
                return

            task.total_chapters = len(chapter_list)
            self._append_log(task, f'解析到 {len(chapter_list)} 个章节')
            task.save()

            title = book_info.get("title") or f"来自 {task.url}"
            book, _ = Book.objects.get_or_create(
                title=title,
                defaults={
                    'author': book_info.get('author', ''),
                    'description': book_info.get('description', ''),
                    'folder_path': str(self.books_dir / self._safe_filename(title)),
                }
            )
            task.book = book
            task.save()

            books_dir = Path(book.folder_path)
            books_dir.mkdir(parents=True, exist_ok=True)

            for i, chapter_info in enumerate(chapter_list):
                if self._stop:
                    task.status = 'cancelled'
                    self._append_log(task, '任务已取消')
                    task.save()
                    return

                try:
                    chapter_html = self._fetch_page(session, chapter_info["url"])
                    if chapter_html:
                        parsed = self.parser.parse_chapter_content(chapter_html)
                        content = parsed.get("content", "")
                        chapter_title = parsed.get("title") or chapter_info["title"]

                        if content:
                            chapter_filename = f"第{i + 1}章.txt"
                            chapter_path = books_dir / chapter_filename
                            with open(chapter_path, 'w', encoding='utf-8') as f:
                                f.write(f"{chapter_title}\n\n{content}")

                            Chapter.objects.update_or_create(
                                book=book,
                                chapter_number=i + 1,
                                defaults={
                                    'title': chapter_title,
                                    'file_path': str(chapter_path),
                                    'word_count': len(content),
                                }
                            )

                            task.downloaded_chapters = i + 1
                            task.save()

                            # 每下载 10 章记录一次进度日志
                            if (i + 1) % 10 == 0:
                                self._append_log(task, f'已下载 {i + 1}/{len(chapter_list)} 章')

                except Exception as e:
                    logger.error(f"第 {i + 1} 章处理异常: {e}")
                    self._append_log(task, f'第 {i + 1} 章处理异常: {e}')

            # 更新书籍总章节数
            book.total_chapters = task.downloaded_chapters
            book.save()
            task.status = 'completed'
            self._append_log(task, f'任务完成，共下载 {task.downloaded_chapters} 章')
            task.save()

        except Exception as e:
            logger.error(f"任务 {task.id} 失败: {e}")
            task.status = 'failed'
            task.error_message = str(e)[:500]
            self._append_log(task, f'任务失败: {e}')
            task.save()

    def stop(self):
        """发送停止信号，中断当前正在执行的任务。"""
        self._stop = True
