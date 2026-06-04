import re
import time
import json
import socket
import logging
import random
import ipaddress
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from apps.books.models import Book
from apps.chapters.models import Chapter
from .crawler_config import get_config_for_url, SiteConfig

logger = logging.getLogger(__name__)


class IntelligentParser:
    def __init__(self, config: SiteConfig):
        self.config = config

    def parse_chapter_list(self, html: str, base_url: str):
        soup = BeautifulSoup(html, 'html.parser')
        chapters = []
        seen_urls = set()

        for selector in self.config.chapter_list_selectors:
            try:
                containers = soup.select(selector)
                for container in containers:
                    links = container.select(self.config.link_selector)
                    for link in links:
                        href = link.get('href', '')
                        title = link.get_text(strip=True)

                        if not title or not href:
                            continue
                        if any(skip in title.lower() for skip in self.config.skip_keywords):
                            continue

                        full_url = urljoin(base_url, href)
                        if full_url in seen_urls:
                            continue

                        seen_urls.add(full_url)
                        chapters.append({'title': title, 'url': full_url})

                if chapters:
                    break
            except Exception as e:
                logger.warning(f'选择器 {selector} 解析失败: {e}')
                continue

        return chapters

    def parse_chapter_content(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')

        for selector in self.config.content_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    content = self._clean_content(element)
                    if len(content) > 50:
                        return {'title': '', 'content': content}
            except Exception as e:
                logger.warning(f'内容选择器 {selector} 解析失败: {e}')
                continue

        return {'title': '', 'content': ''}

    def _clean_content(self, element):
        for tag in element.find_all(['script', 'style', 'iframe', 'ins', 'nav']):
            tag.decompose()
        paragraphs = element.find_all('p')
        if paragraphs:
            parts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
            return '\n\n'.join(parts)
        text = element.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n\n'.join(lines)

    def parse_book_info(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')
        info = {'title': '', 'author': '', 'description': ''}

        if self.config.title_selector:
            title_tag = soup.select_one(self.config.title_selector)
            if title_tag:
                info['title'] = title_tag.get_text(strip=True)

        if not info['title']:
            title_tag = soup.find('h1')
            if title_tag:
                info['title'] = title_tag.get_text(strip=True)

        if self.config.author_selector:
            author_tag = soup.select_one(self.config.author_selector)
            if author_tag:
                info['author'] = author_tag.get_text(strip=True)

        if self.config.description_selector:
            desc_tag = soup.select_one(self.config.description_selector)
            if desc_tag:
                info['description'] = desc_tag.get_text(strip=True)

        return info


SSRF_BLOCKED_HOSTS = {
    '169.254.169.254', 'metadata.google.internal', 'localhost', '127.0.0.1', '0.0.0.0', '::1',
}


def validate_crawl_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ('http', 'https'):
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
    def __init__(self, task_id, books_dir):
        self.task_id = task_id
        self.books_dir = Path(books_dir)
        self.config = None
        self.parser = None
        self._stop = False

    def _get_ua(self):
        pool = self.config.user_agents
        if not pool:
            from .crawler_config import UA_POOL
            pool = UA_POOL
        return random.choice(pool)

    def _get_proxy(self):
        if not self.config.use_proxy or not self.config.proxy_url:
            return None
        return self.config.proxy_url

    def _delay(self):
        wait = self.config.request_delay * random.uniform(0.5, 1.5)
        time.sleep(wait)

    def _fetch_page(self, client: httpx.Client, url: str) -> str:
        max_retries = self.config.max_retries
        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                self._delay()
                headers = {
                    'User-Agent': self._get_ua(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                proxy = self._get_proxy()
                cookies = self.config.cookies or None

                resp = client.get(
                    url, headers=headers, timeout=30,
                    cookies=cookies,
                )
                resp.raise_for_status()
                return resp.text
            except httpx.HTTPError as e:
                last_exc = e
                jitter = random.uniform(0, 1)
                backoff = self.config.retry_delay * (2 ** (attempt - 1)) + jitter
                logger.warning(
                    f'请求失败 (第{attempt}/{max_retries}次): {url} - {e}, '
                    f'{backoff:.1f}s后重试'
                )
                if attempt < max_retries:
                    time.sleep(backoff)
        raise last_exc

    def _safe_filename(self, name):
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        name = name.strip('. ')
        return name[:100] if name else 'unnamed'

    def _append_log(self, task, message):
        try:
            task.refresh_from_db()
            logs = json.loads(task.logs) if task.logs else []
            logs.append({'time': time.time(), 'msg': message})
            task.logs = json.dumps(logs, ensure_ascii=False)
            task.save(update_fields=['logs'])
            logger.info(f'任务 {task.id}: {message}')
        except Exception as e:
            logger.error(f'添加日志失败: {e}')

    def run(self, task):
        self.config = get_config_for_url(task.url)
        self.parser = IntelligentParser(self.config)

        logger.info(f'开始执行任务 {task.id}, 站点: {self.config.name}')

        if not validate_crawl_url(task.url):
            task.status = 'failed'
            task.error_message = '目标URL不合法或指向内网/元数据地址，禁止访问'
            task.save()
            logger.error(f'任务 {task.id} URL验证失败')
            return

        task.status = 'running'
        task.save()
        self._append_log(task, '任务开始执行')

        proxy = self._get_proxy()
        transport_kwargs = {'http2': True}
        client_kwargs = {
            'timeout': 30,
            'follow_redirects': True,
            'verify': not getattr(self.config, 'skip_ssl_verify', False),  # 默认启用SSL验证
        }
        if proxy:
            client_kwargs['proxy'] = proxy

        with httpx.Client(**client_kwargs) as client:
            try:
                html = self._fetch_page(client, task.url)

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

                title = book_info.get('title') or f'来自 {task.url}'
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
                        chapter_html = self._fetch_page(client, chapter_info['url'])
                        if chapter_html:
                            parsed = self.parser.parse_chapter_content(chapter_html)
                            content = parsed.get('content', '')
                            chapter_title = parsed.get('title') or chapter_info['title']

                            if content:
                                chapter_filename = f'第{i + 1}章.txt'
                                chapter_path = books_dir / chapter_filename
                                with open(chapter_path, 'w', encoding='utf-8') as f:
                                    f.write(f'{chapter_title}\n\n{content}')

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

                                if (i + 1) % 10 == 0:
                                    self._append_log(task, f'已下载 {i + 1}/{len(chapter_list)} 章')

                    except Exception as e:
                        logger.error(f'第 {i + 1} 章处理异常: {e}')
                        self._append_log(task, f'第 {i + 1} 章处理异常: {e}')

                book.total_chapters = task.downloaded_chapters
                book.save()
                task.status = 'completed'
                self._append_log(task, f'任务完成，共下载 {task.downloaded_chapters} 章')
                task.save()

            except Exception as e:
                logger.error(f'任务 {task.id} 失败: {e}')
                task.status = 'failed'
                task.error_message = str(e)[:500]
                self._append_log(task, f'任务失败: {e}')
                task.save()

    def stop(self):
        self._stop = True
