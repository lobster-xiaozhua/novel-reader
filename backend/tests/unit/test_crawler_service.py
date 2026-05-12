import pytest
from unittest.mock import MagicMock, patch

from app.services.crawler_service import (
    validate_crawl_url, IntelligentParser, DynamicConcurrencyController
)


class TestSSRFProtection:
    def test_validate_crawl_url_valid_http(self):
        assert validate_crawl_url("http://example.com/novel") is True

    def test_validate_crawl_url_valid_https(self):
        assert validate_crawl_url("https://example.com/novel") is True

    def test_validate_crawl_url_blocked_localhost(self):
        assert validate_crawl_url("http://localhost:8080") is False

    def test_validate_crawl_url_blocked_127(self):
        assert validate_crawl_url("http://127.0.0.1:8080") is False

    def test_validate_crawl_url_blocked_metadata(self):
        assert validate_crawl_url("http://169.254.169.254/latest/meta-data") is False

    def test_validate_crawl_url_blocked_google_metadata(self):
        assert validate_crawl_url("http://metadata.google.internal/computeMetadata") is False

    def test_validate_crawl_url_blocked_private_ip(self):
        assert validate_crawl_url("http://192.168.1.100:8080") is False

    def test_validate_crawl_url_blocked_localhost_hostname(self):
        assert validate_crawl_url("https://localhost/api") is False

    def test_validate_crawl_url_invalid_scheme(self):
        assert validate_crawl_url("ftp://example.com/file") is False

    def test_validate_crawl_url_invalid_url(self):
        assert validate_crawl_url("not a url") is False

    def test_validate_crawl_url_empty(self):
        assert validate_crawl_url("") is False


class TestIntelligentParser:
    @pytest.fixture
    def parser(self):
        return IntelligentParser()

    def test_parse_chapter_list_with_valid_html(self, parser):
        html = """
        <div class="chapter-list">
            <a href="/chapter/1">第一章 开始</a>
            <a href="/chapter/2">第二章 发展</a>
        </div>
        """
        chapters = parser.parse_chapter_list(html, "http://example.com")
        assert len(chapters) == 2
        assert chapters[0]["title"] == "第一章 开始"
        assert chapters[0]["url"] == "http://example.com/chapter/1"

    def test_parse_chapter_list_filters_navigation(self, parser):
        html = """
        <div class="chapter-list">
            <a href="/">首页</a>
            <a href="/chapter/1">第一章 开始</a>
            <a href="/prev">上一页</a>
            <a href="/chapter/2">第二章 发展</a>
            <a href="/next">下一页</a>
        </div>
        """
        chapters = parser.parse_chapter_list(html, "http://example.com")
        assert len(chapters) == 2

    def test_parse_chapter_list_empty_when_no_links(self, parser):
        html = "<html><body><div></div></body></html>"
        chapters = parser.parse_chapter_list(html, "http://example.com")
        assert len(chapters) == 0

    def test_parse_chapter_list_with_chapter_patterns(self, parser):
        html = """
        <html>
            <body>
                <a href="/1.html">第1章 序章</a>
                <a href="/2.html">Chapter 2</a>
                <a href="/3.html">1. 第三章</a>
            </body>
        </html>
        """
        chapters = parser.parse_chapter_list(html, "http://example.com")
        assert len(chapters) == 3

    def test_parse_chapter_content_with_id_selector(self, parser):
        html = """
        <div id="content">
            <p>这是第一段内容，包含足够多的文字以满足解析器对内容长度的要求。</p>
            <p>这是第二段内容，同样包含足够多的文字来确保解析器能够正确提取内容。</p>
        </div>
        """
        result = parser.parse_chapter_content(html)
        assert "第一段内容" in result["content"]
        assert "第二段内容" in result["content"]

    def test_parse_chapter_content_with_class_selector(self, parser):
        html = """
        <div class="chapter-content">
            <p>这是一个内容段落，包含足够多的文字来满足解析器的内容长度要求。</p>
            <p>第二个段落确保内容长度超过50字符。</p>
        </div>
        """
        result = parser.parse_chapter_content(html)
        assert "内容段落" in result["content"]

    def test_parse_chapter_content_with_p_tags(self, parser):
        html = """
        <html>
            <body>
                <p>这是段落1，包含足够多的文字以满足解析器的要求。</p>
                <p>这是段落2，同样包含足够多的文字。</p>
                <p>这是段落3，确保段落数量满足要求。</p>
                <p>这是段落4，满足段落数>3的条件。</p>
                <p>这是段落5，确保content_parts超过3个。</p>
            </body>
        </html>
        """
        result = parser.parse_chapter_content(html)
        assert "段落1" in result["content"]

    def test_parse_chapter_content_empty_when_no_content(self, parser):
        html = "<html><body><div></div></body></html>"
        result = parser.parse_chapter_content(html)
        assert result["content"] == ""

    def test_parse_book_info_extracts_title(self, parser):
        html = "<html><head></head><body><h1>书名：测试小说</h1></body></html>"
        info = parser.parse_book_info(html)
        assert info["title"] == "书名：测试小说"

    def test_parse_book_info_extracts_author(self, parser):
        html = """
        <html>
            <body>
                <span class="author">作者：测试作者</span>
            </body>
        </html>
        """
        info = parser.parse_book_info(html)
        assert info["author"] == "测试作者"

    def test_parse_book_info_with_meta_author(self, parser):
        html = """
        <html>
            <head>
                <meta name="author" content="元数据作者">
            </head>
        </html>
        """
        info = parser.parse_book_info(html)
        assert info["author"] == "元数据作者"

    def test_clean_content_removes_scripts(self, parser):
        html = """
        <div id="content">
            <script>alert('test');</script>
            <p>这是正文内容，包含足够多的文字以满足解析器对内容长度的要求。</p>
            <style>.hidden { display: none; }</style>
            <p>第二个段落确保内容总长度超过50字符。</p>
        </div>
        """
        result = parser.parse_chapter_content(html)
        assert "alert" not in result["content"]
        assert "正文内容" in result["content"]


class TestDynamicConcurrencyController:
    @pytest.fixture
    def controller(self):
        return DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)

    def test_initial_concurrency(self, controller):
        assert controller._current_concurrent == 1

    def test_record_response_success(self, controller):
        controller.record_response(0.5, True)
        assert controller._success_count == 1
        assert controller._error_count == 0

    def test_record_response_failure(self, controller):
        controller.record_response(0.5, False)
        assert controller._error_count == 1

    def test_get_delay_normal(self, controller):
        delay = controller.get_delay()
        assert delay == 1.0

    def test_get_delay_increased_on_errors(self, controller):
        for _ in range(2):
            controller.record_response(0.5, False)
        delay = controller.get_delay()
        assert delay == 2.0

    def test_get_delay_high_on_many_errors(self, controller):
        for _ in range(4):
            controller.record_response(0.5, False)
        delay = controller.get_delay()
        assert delay == 3.0

    def test_concurrency_decreases_on_errors(self, controller):
        controller._current_concurrent = 3
        for _ in range(6):
            controller.record_response(0.5, False)
        assert controller._current_concurrent == 2

    def test_concurrency_increases_on_success(self, controller):
        controller._current_concurrent = 1
        for _ in range(11):
            controller.record_response(0.5, True)
        assert controller._current_concurrent == 2

    def test_concurrency_cannot_go_below_1(self, controller):
        controller._current_concurrent = 1
        for _ in range(10):
            controller.record_response(0.5, False)
        assert controller._current_concurrent == 1

    def test_concurrency_cannot_exceed_max(self, controller):
        controller._current_concurrent = 5
        for _ in range(20):
            controller.record_response(0.5, True)
        assert controller._current_concurrent == 5