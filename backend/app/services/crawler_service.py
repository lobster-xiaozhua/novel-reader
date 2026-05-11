import asyncio
import ipaddress
import json
import logging
import os
import re
import socket
import time
from pathlib import Path
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse

import aiofiles
import aiohttp
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings
from app.database import AsyncSessionLocal
from app.models import CrawlerTask, Book, Chapter

logger = logging.getLogger(__name__)
settings = get_settings()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class IntelligentParser:
    CHAPTER_PATTERNS = [
        re.compile(r'^第[零一二三四五六七八九十百千万\d]+章', re.MULTILINE),
        re.compile(r'^第\d+章', re.MULTILINE),
        re.compile(r'^Chapter\s+\d+', re.MULTILINE | re.IGNORECASE),
        re.compile(r'^\d+[、.]\s*.+', re.MULTILINE),
    ]

    CONTENT_SELECTORS = [
        {"id": "content"},
        {"id": "bookContent"},
        {"id": "chaptercontent"},
        {"class_": "content"},
        {"class_": "chapter-content"},
        {"class_": "read-content"},
        {"class_": "article-content"},
        {"class_": "text-content"},
        {"class_": "bookreadercontent"},
    ]

    TITLE_SELECTORS = [
        {"class_": "title"},
        {"class_": "chapter-title"},
        {"class_": "bookname"},
        {"tag": "h1"},
        {"tag": "h2"},
    ]

    def parse_chapter_list(self, html: str, base_url: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")

        list_containers = soup.find_all(["div", "dl", "ul", "ol"], class_=re.compile(r'(list|chapter|catalog|menu|directory)', re.I))
        if not list_containers:
            list_containers = soup.find_all("dl")

        chapters = []
        seen_urls: Set[str] = set()

        for container in list_containers:
            links = container.find_all("a", href=True)
            for link in links:
                href = link.get("href", "")
                title = link.get_text(strip=True)
                if not title or not href:
                    continue
                if any(skip in title.lower() for skip in ["首页", "末页", "上一页", "下一页", "返回", "目录"]):
                    continue
                full_url = urljoin(base_url, href)
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                chapters.append({"title": title, "url": full_url})

        if not chapters:
            all_links = soup.find_all("a", href=True)
            for link in all_links:
                href = link.get("href", "")
                title = link.get_text(strip=True)
                if not title or not href:
                    continue
                is_chapter = any(pattern.search(title) for pattern in self.CHAPTER_PATTERNS)
                if is_chapter:
                    full_url = urljoin(base_url, href)
                    if full_url not in seen_urls:
                        seen_urls.add(full_url)
                        chapters.append({"title": title, "url": full_url})

        return chapters

    def parse_chapter_content(self, html: str) -> Dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        for sel in self.CONTENT_SELECTORS:
            tag = "div"
            kwargs = {}
            if "id" in sel:
                kwargs = {"id": sel["id"]}
            elif "class_" in sel:
                kwargs = {"class_": sel["class_"]}
            element = soup.find(tag, **kwargs)
            if element:
                content = self._clean_content(element)
                if len(content) > 50:
                    title = self._extract_title(soup)
                    return {"title": title, "content": content}
        paragraphs = soup.find_all("p")
        if len(paragraphs) > 3:
            content_parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 5:
                    content_parts.append(text)
            if len(content_parts) > 3:
                content = "\n\n".join(content_parts)
                title = self._extract_title(soup)
                return {"title": title, "content": content}
        return {"title": "", "content": ""}
    def _extract_title(self, soup: BeautifulSoup) -> str:
        for sel in self.TITLE_SELECTORS:
            kwargs = {}
            if "class_" in sel:
                kwargs = {"class_": sel["class_"]}
                element = soup.find(["div", "span", "h1", "h2"], **kwargs)
            elif "tag" in sel:
                element = soup.find(sel["tag"])
            else:
                continue
            if element:
                title = element.get_text(strip=True)
                if title:
                    return title
        return ""
    def _clean_content(self, element) -> str:
        for tag in element.find_all(["script", "style", "iframe", "ins", "nav"]):
            tag.decompose()
        paragraphs = element.find_all("p")
        if paragraphs:
            parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text:
                    parts.append(text)
            return "\n\n".join(parts)
        text = element.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n\n".join(lines)
    def parse_book_info(self, html: str) -> Dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        info = {"title": "", "author": "", "description": ""}
        title_tag = soup.find("h1")
        if title_tag:
            info["title"] = title_tag.get_text(strip=True)
        author_patterns = [
            soup.find(string=re.compile(r'作者[：:]')),
            soup.find("span", class_=re.compile(r'author', re.I)),
            soup.find("meta", attrs={"property": "og:novel:author"}),
            soup.find("meta", attrs={"name": "author"}),
        ]
        for match in author_patterns:
            if match:
                if match.name == "meta":
                    info["author"] = match.get("content", "")
                else:
                    text = match.get_text(strip=True) if hasattr(match, 'get_text') else str(match)
                    info["author"] = re.sub(r'作者[：:]\s*', '', text)
                break
        desc_tag = soup.find("div", class_=re.compile(r'(intro|desc|summary)', re.I))
        if desc_tag:
            info["description"] = desc_tag.get_text(strip=True)[:500]
        return info
class DynamicConcurrencyController:
    def __init__(self, max_concurrent: int = None, base_delay: float = None):
        self._max_concurrent = max_concurrent or settings.CRAWLER_MAX_CONCURRENT
        self._base_delay = base_delay or settings.CRAWLER_REQUEST_DELAY
        self._current_concurrent = 1
        self._semaphore = asyncio.Semaphore(1)
        self._response_times: List[float] = []
        self._error_count = 0
        self._success_count = 0
    async def acquire(self):
        await self._semaphore.acquire()
    def release(self):
        self._semaphore.release()
    def record_response(self, response_time: float, success: bool):
        self._response_times.append(response_time)
        if len(self._response_times) > 20:
            self._response_times = self._response_times[-20:]
        if success:
            self._success_count += 1
            self._error_count = max(0, self._error_count - 1)
        else:
            self._error_count += 1
        self._adjust_concurrency()
    def get_delay(self) -> float:
        if self._error_count > 3:
            return self._base_delay * 3
        if self._error_count > 1:
            return self._base_delay * 2
        if self._response_times:
            avg_time = sum(self._response_times[-5:]) / len(self._response_times[-5:])
            if avg_time > 3.0:
                return self._base_delay * 2
            if avg_time > 1.5:
                return self._base_delay * 1.5
        return self._base_delay
    def _adjust_concurrency(self):
        if self._error_count > 5 and self._current_concurrent > 1:
            self._current_concurrent = max(1, self._current_concurrent - 1)
            self._semaphore = asyncio.Semaphore(self._current_concurrent)
            logger.info(f"降低并发数至 {self._current_concurrent}")
        elif self._success_count > 10 and self._current_concurrent < self._max_concurrent:
            self._current_concurrent += 1
            self._semaphore = asyncio.Semaphore(self._current_concurrent)
            self._success_count = 0
            logger.info(f"提升并发数至 {self._current_concurrent}")
SSRF_BLOCKED_HOSTS = {"169.254.169.254", "metadata.google.internal", "localhost", "127.0.0.1", "0.0.0.0", "::1"}

def validate_crawl_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    if hostname in SSRF_BLOCKED_HOSTS:
        return False
    try:
        resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in resolved_ips:
            ip = sockaddr[0]
            if ipaddress.ip_address(ip).is_private:
                return False
            if ip in SSRF_BLOCKED_HOSTS:
                return False
    except socket.gaierror:
        return False
    return True

class CrawlerService:
    def __init__(self):
        self.parser = IntelligentParser()
        self._ua_index = 0
        self._active_tasks: Dict[int, bool] = {}
    def _get_ua(self):
        ua = USER_AGENTS[self._ua_index % len(USER_AGENTS)]
        self._ua_index += 1
        return ua
    async def run_task(self, task_id):
        async with AsyncSessionLocal() as db:
            try:
                from sqlalchemy import select
                result = await db.execute(select(CrawlerTask).where(CrawlerTask.id == task_id))
                task = result.scalar_one_or_none()
                if not task:
                    logger.error(f"Task {task_id} not found")
                    return
                task.status = "running"
                task.logs = json.dumps([{"time": time.time(), "msg": "Started"}])
                await db.commit()
                self._active_tasks[task.id] = True
                await self._execute_crawl(db, task)
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}", exc_info=True)
                try:
                    from sqlalchemy import select
                    result = await db.execute(select(CrawlerTask).where(CrawlerTask.id == task_id))
                    task = result.scalar_one_or_none()
                    if task:
                        task.status = "failed"
                        task.error_message = str(e)[:500]
                        await self._append_log(db, task, f"Failed: {e}")
                        await db.commit()
                except Exception:
                    pass
            finally:
                self._active_tasks.pop(task_id, None)
    async def _execute_crawl(self, db, task):
        if not validate_crawl_url(task.url):
            task.status = "failed"
            task.error_message = "Invalid URL"
            await db.commit()
            return
        timeout = aiohttp.ClientTimeout(total=settings.CRAWLER_TIMEOUT)
        connector = aiohttp.TCPConnector(limit=settings.CRAWLER_MAX_CONCURRENT, ssl=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            base_delay = settings.CRAWLER_REQUEST_DELAY
            concurrency_ctrl = DynamicConcurrencyController(max_concurrent=settings.CRAWLER_MAX_CONCURRENT, base_delay=base_delay)
            await self._append_log(db, task, "Parsing catalog")
            html = await self._fetch_page(session, task.url)
            if not html:
                task.status = "failed"
                task.error_message = "Cannot get catalog page"
                await db.commit()
                return
            book_info = self.parser.parse_book_info(html)
            chapter_list = self.parser.parse_chapter_list(html, task.url)
            if not chapter_list:
                task.status = "failed"
                task.error_message = "Cannot parse chapters"
                await self._append_log(db, task, "Chapter parse failed")
                await db.commit()
                return
            task.total_chapters = len(chapter_list)
            await self._append_log(db, task, f"Found {len(chapter_list)} chapters")
            await db.commit()
            book = await self._ensure_book(db, book_info, task)
            task.book_id = book.id
            start_index = task.downloaded_chapters
            if start_index > 0:
                await self._append_log(db, task, f"Resuming from chapter {start_index+1}")
            books_dir = Path(settings.BOOKS_DIR) / self._safe_filename(book_info.get("title", f"book_{book.id}"))
            books_dir.mkdir(parents=True, exist_ok=True)
            for i in range(start_index, len(chapter_list)):
                if not self._active_tasks.get(task.id, False):
                    task.status = "cancelled"
                    await self._append_log(db, task, "Cancelled")
                    await db.commit()
                    return
                chapter_info = chapter_list[i]
                await asyncio.sleep(concurrency_ctrl.get_delay())
                await concurrency_ctrl.acquire()
                try:
                    start_t = time.time()
                    chapter_html = await self._fetch_page(session, chapter_info["url"])
                    elapsed = time.time() - start_t
                    if chapter_html:
                        parsed = self.parser.parse_chapter_content(chapter_html)
                        content = parsed.get("content", "")
                        title = parsed.get("title") or chapter_info["title"]
                        if content:
                            chapter_path = books_dir / f"chapter_{i+1}.txt"
                            async with aiofiles.open(chapter_path, 'w', encoding='utf-8') as f:
                                await f.write(f"{title}\n\n{content}")
                            await self._save_chapter(db, book.id, i+1, title, str(chapter_path), len(content))
                            task.downloaded_chapters = i + 1
                            concurrency_ctrl.record_response(elapsed, True)
                        else:
                            concurrency_ctrl.record_response(elapsed, False)
                            await self._append_log(db, task, f"Ch{i+1} empty content")
                    else:
                        concurrency_ctrl.record_response(0, False)
                        await self._append_log(db, task, f"Ch{i+1} fetch failed")
                    if (i+1) % 5 == 0:
                        await db.commit()
                except Exception as e:
                    concurrency_ctrl.record_response(0, False)
                    await self._append_log(db, task, f"Ch{i+1} err: {e}")
                finally:
                    concurrency_ctrl.release()
            book.total_chapters = task.downloaded_chapters
            task.status = "completed"
            await self._append_log(db, task, f"Done, {task.downloaded_chapters} chapters")
            await db.commit()
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)), reraise=True)
    async def _fetch_page(self, session, url):
        headers = {"User-Agent": self._get_ua()}
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status_code == 200:
                    return await resp.text(errors="replace")
                logger.warning(f"HTTP {resp.status_code} for {url}")
                return None
        except Exception as e:
            logger.warning(f"Fetch err for {url}: {e}")
            raise
    async def _ensure_book(self, db, book_info, task):
        from sqlalchemy import select
        title = book_info.get("title", f"from_{task.url}")
        result = await db.execute(select(Book).where(Book.title == title))
        book = result.scalar_one_or_none()
        if not book:
            safe_name = self._safe_filename(title)
            book = Book(title=title, author=book_info.get("author", ""), description=book_info.get("description", ""), folder_path=str(Path(settings.BOOKS_DIR) / safe_name), total_chapters=0)
            db.add(book)
            await db.flush()
        return book
    async def _save_chapter(self, db, book_id, chapter_num, title, path, wc):
        from sqlalchemy import select
        result = await db.execute(select(Chapter).where(Chapter.book_id == book_id, Chapter.chapter_number == chapter_num))
        chapter = result.scalar_one_or_none()
        if chapter:
            chapter.title = title
            chapter.file_path = path
            chapter.word_count = wc
        else:
            chapter = Chapter(book_id=book_id, chapter_number=chapter_num, title=title, file_path=path, word_count=wc)
            db.add(chapter)
    async def _append_log(self, db, task, msg):
        try:
            logs = json.loads(task.logs) if task.logs else []
        except Exception:
            logs = []
        logs.append({"time": time.time(), "msg": msg})
        task.logs = json.dumps(logs)
    def _safe_filename(self, name):
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        name = name.strip('. ')
        return name[:100] or "unnamed"
    def cancel_task(self, task_id):
        self._active_tasks[task_id] = False
crawler_service = CrawlerService()