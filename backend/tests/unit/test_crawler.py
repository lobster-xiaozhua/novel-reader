import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import socket

from app.services.crawler_service import (
    IntelligentParser,
    DynamicConcurrencyController,
    validate_crawl_url,
    CrawlerService,
)


class TestIntelligentParser:
    @pytest.fixture
    def parser(self):
        return IntelligentParser()

    def test_parse_chapter_list_with_list_container(self, parser):
        html = """
        <html><body>
            <div class="chapter-list">
                <a href="/chapter/1">第一章 入门</a>
                <a href="/chapter/2">第二章 进阶</a>
            </div>
        </body></html>
        """
        chapters = parser.parse_chapter_list(html, "https://example.com/novel/")
        assert len(chapters) == 2
        assert chapters[0]["title"] == "第一章 入门"
        assert "chapter/1" in chapters[0]["url"]

    def test_parse_chapter_list_skips_navigation_links(self, parser):
        html = """
        <html><body>
            <div class="chapter-list">
                <a href="/chapter/1">第一章</a>
                <a href="/">首页</a>
                <a href="/last">末页</a>
                <a href="/prev">上一页</a>
                <a href="/next">下一页</a>
                <a href="/menu">目录</a>
            </div>
        </body></html>
        """
        chapters = parser.parse_chapter_list(html, "https://example.com/")
        assert len(chapters) == 1
        assert chapters[0]["title"] == "第一章"

    def test_parse_chapter_list_with_pattern_matching(self, parser):
        html = """
        <html><body>
            <a href="/ch/1">Chapter 1: Introduction</a>
            <a href="/ch/2">第3章 基础</a>
            <a href="/ch/3">3、First Steps</a>
        </body></html>
        """
        chapters = parser.parse_chapter_list(html, "https://example.com/")
        assert len(chapters) >= 3

    def test_parse_chapter_list_deduplicates_urls(self, parser):
        html = """
        <html><body>
            <div>
                <a href="/ch1">Chapter 1</a>
            </div>
            <div>
                <a href="/ch1">Chapter 1 duplicate</a>
            </div>
        </body></html>
        """
        chapters = parser.parse_chapter_list(html, "https://example.com/")
        urls = [c["url"] for c in chapters]
        assert len(urls) == len(set(urls))

    def test_parse_chapter_content_returns_dict_structure(self, parser):
        html = """
        <html><body>
            <div id="content">
                <p>第一段内容</p>
                <p>第二段内容</p>
            </div>
        </body></html>
        """
        result = parser.parse_chapter_content(html)
        assert isinstance(result, dict)
        assert "content" in result

    def test_parse_chapter_content_empty_html(self, parser):
        html = "<html><body></body></html>"
        result = parser.parse_chapter_content(html)
        assert result["content"] == ""

    def test_clean_content_removes_scripts(self, parser):
        from bs4 import BeautifulSoup
        html = """
        <div>
            <script>alert('xss')</script>
            <p>正常内容</p>
            <style>.hidden {display:none}</style>
            <p>更多内容</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div")
        cleaned = parser._clean_content(div)
        assert "alert" not in cleaned
        assert "正常内容" in cleaned

    def test_parse_book_info_extracts_title(self, parser):
        html = """
        <html><body>
            <h1>小说标题</h1>
        </body></html>
        """
        info = parser.parse_book_info(html)
        assert info["title"] == "小说标题"

    def test_parse_book_info_extracts_author(self, parser):
        html = """
        <html><body>
            <h1>书名</h1>
            <span>作者：张三</span>
        </body></html>
        """
        info = parser.parse_book_info(html)
        assert "张三" in info["author"]


class TestDynamicConcurrencyController:
    def test_initial_state(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        assert controller._current_concurrent == 1
        assert controller._max_concurrent == 5
        assert controller._base_delay == 1.0

    def test_get_delay_returns_base_for_normal_conditions(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        assert controller.get_delay() == 1.0

    def test_get_delay_increases_with_slow_response(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        for _ in range(5):
            controller.record_response(2.0, success=True)
        delay = controller.get_delay()
        assert delay > 1.0

    def test_get_delay_increases_with_error_count(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        for _ in range(4):
            controller.record_response(0.5, success=False)
        delay = controller.get_delay()
        assert delay >= 2.0

    def test_concurrency_decreases_on_many_errors(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        for _ in range(6):
            controller.record_response(0.5, success=False)
        assert controller._current_concurrent == 1

    def test_response_times_window_limit(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        for i in range(25):
            controller.record_response(float(i), success=True)
        assert len(controller._response_times) <= 20

    def test_semaphore_controls_concurrency(self):
        controller = DynamicConcurrencyController(max_concurrent=3, base_delay=0.1)
        controller._semaphore = controller._semaphore.__class__(2)
        assert controller._semaphore._value == 2


class TestValidateCrawlUrl:
    def test_valid_http_url(self):
        assert validate_crawl_url("http://example.com/novel") is True

    def test_valid_https_url(self):
        assert validate_crawl_url("https://example.com/novel") is True

    def test_invalid_scheme_ftp(self):
        assert validate_crawl_url("ftp://example.com") is False

    def test_invalid_scheme_file(self):
        assert validate_crawl_url("file:///etc/passwd") is False

    def test_localhost_blocked(self):
        assert validate_crawl_url("http://localhost/path") is False
        assert validate_crawl_url("http://127.0.0.1/path") is False

    def test_malformed_url(self):
        assert validate_crawl_url("not a url") is False
        assert validate_crawl_url("") is False

    def test_missing_hostname(self):
        assert validate_crawl_url("http://") is False

    def test_metadata_endpoints_blocked(self):
        assert validate_crawl_url("http://169.254.169.254/latest/meta-data") is False
        assert validate_crawl_url("http://metadata.google.internal") is False

    def test_ipv6_loopback_blocked(self):
        assert validate_crawl_url("http://[::1]/path") is False

    def test_private_ip_blocked(self):
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.1', 80))
            ]
            assert validate_crawl_url("http://10.0.0.1/path") is False

    def test_public_ip_allowed(self):
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 80))
            ]
            assert validate_crawl_url("http://example.com/path") is True

    def test_dns_resolution_failure(self):
        with patch('socket.getaddrinfo', side_effect=socket.gaierror("DNS failed")):
            assert validate_crawl_url("http://invalid.domain.that.does.not.exist.xyz/path") is False


class TestCrawlerService:
    @pytest.fixture
    def crawler_service(self):
        return CrawlerService()

    def test_crawler_service_initialization(self, crawler_service):
        assert crawler_service.parser is not None
        assert crawler_service._ua_index == 0
        assert crawler_service._active_tasks == {}

    def test_get_ua_rotates_user_agents(self, crawler_service):
        ua1 = crawler_service._get_ua()
        ua2 = crawler_service._get_ua()
        ua3 = crawler_service._get_ua()
        assert ua1 != ua2 or ua2 != ua3
        assert "Mozilla" in ua1

    def test_safe_filename_removes_invalid_chars(self, crawler_service):
        unsafe = 'file:with*invalid|chars<>:"?/'
        safe = crawler_service._safe_filename(unsafe)
        assert ":" not in safe
        assert "*" not in safe
        assert "|" not in safe

    def test_safe_filename_strips_dots_and_spaces(self, crawler_service):
        assert crawler_service._safe_filename("  .hidden.  ") == "hidden"

    def test_safe_filename_truncates_long_names(self, crawler_service):
        long_name = "a" * 200
        result = crawler_service._safe_filename(long_name)
        assert len(result) <= 100

    def test_safe_filename_empty_becomes_unnamed(self, crawler_service):
        assert crawler_service._safe_filename("   ") == "unnamed"

    def test_cancel_task(self, crawler_service):
        crawler_service._active_tasks[123] = True
        crawler_service.cancel_task(123)
        assert crawler_service._active_tasks.get(123) is False
