import pytest
from unittest.mock import MagicMock, patch

from app.services.crawler_service import (
    IntelligentParser, DynamicConcurrencyController,
    validate_crawl_url, SSRF_BLOCKED_HOSTS
)


class TestSSRFProtection:
    def test_validate_crawl_url_valid(self):
        assert validate_crawl_url("https://example.com/novel") is True
        assert validate_crawl_url("http://example.com/book") is True

    def test_validate_crawl_url_localhost_blocked(self):
        assert validate_crawl_url("http://localhost:8080") is False
        assert validate_crawl_url("http://127.0.0.1:8080") is False
        assert validate_crawl_url("http://0.0.0.0:8080") is False
        assert validate_crawl_url("http://[::1]:8080") is False

    def test_validate_crawl_url_metadata_blocked(self):
        assert validate_crawl_url("http://169.254.169.254/latest/meta-data") is False
        assert validate_crawl_url("http://metadata.google.internal/computeMetadata") is False

    def test_validate_crawl_url_private_ip_blocked(self):
        assert validate_crawl_url("http://192.168.1.100") is False
        assert validate_crawl_url("http://10.0.0.1") is False
        assert validate_crawl_url("http://172.16.0.1") is False

    def test_validate_crawl_url_invalid_scheme(self):
        assert validate_crawl_url("ftp://example.com") is False
        assert validate_crawl_url("file:///etc/passwd") is False
        assert validate_crawl_url("ssh://example.com") is False

    def test_validate_crawl_url_empty(self):
        assert validate_crawl_url("") is False
        assert validate_crawl_url(None) is False

    def test_validate_crawl_url_invalid_format(self):
        assert validate_crawl_url("not_a_url") is False
        assert validate_crawl_url("http://") is False


class TestIntelligentParser:
    @pytest.fixture
    def parser(self):
        return IntelligentParser()

    def test_parse_chapter_list_with_chapter_tags(self, parser):
        html = """
        <div class="chapter-list">
            <a href="/chapter1">第一章 初入江湖</a>
            <a href="/chapter2">第二章 奇遇</a>
            <a href="/chapter3">第三章 修炼</a>
        </div>
        """
        chapters = parser.parse_chapter_list(html, "http://example.com")
        
        assert len(chapters) == 3
        assert chapters[0]["title"] == "第一章 初入江湖"
        assert chapters[0]["url"] == "http://example.com/chapter1"

    def test_parse_chapter_list_skips_navigation_links(self, parser):
        html = """
        <div class="chapter-list">
            <a href="/">首页</a>
            <a href="/chapter1">第一章</a>
            <a href="/prev">上一页</a>
            <a href="/next">下一页</a>
            <a href="/chapter2">第二章</a>
        </div>
        """
        chapters = parser.parse_chapter_list(html, "http://example.com")
        
        assert len(chapters) == 2
        assert chapters[0]["title"] == "第一章"
        assert chapters[1]["title"] == "第二章"

    def test_parse_chapter_list_empty(self, parser):
        html = "<html><body><div></div></body></html>"
        chapters = parser.parse_chapter_list(html, "http://example.com")
        
        assert len(chapters) == 0

    def test_parse_chapter_content_with_id_content(self, parser):
        html = """
        <html>
            <h1>第一章</h1>
            <div id="content">
                <p>这是第一章的内容。这是一段非常长的内容，用于测试内容长度是否大于50个字符的判断条件。</p>
                <p>这是第二段，也是一段比较长的内容，确保总长度超过50字符。</p>
            </div>
        </html>
        """
        result = parser.parse_chapter_content(html)
        
        assert result["title"] == "第一章"
        assert "这是第一章的内容" in result["content"]

    def test_parse_chapter_content_with_class_content(self, parser):
        html = """
        <html>
            <h1>第二章</h1>
            <div class="chapter-content">
                <p>第二章内容。这是一段非常长的内容，用于测试内容长度是否大于50个字符的判断条件。这段内容必须足够长，确保能够触发标题提取逻辑。</p>
            </div>
        </html>
        """
        result = parser.parse_chapter_content(html)
        
        assert result["title"] == "第二章"
        assert "第二章内容" in result["content"]

    def test_parse_chapter_content_fallback_to_p_tags(self, parser):
        html = """
        <html>
            <h1>第三章</h1>
            <p>段落1：这是一段非常长的段落内容，用于测试内容长度判断条件。</p>
            <p>段落2：这也是一段比较长的段落内容，确保满足长度要求。</p>
            <p>段落3：继续添加更多内容来满足测试条件。</p>
            <p>段落4：最后一段内容，确保总长度足够。</p>
        </html>
        """
        result = parser.parse_chapter_content(html)
        
        assert result["title"] == "第三章"
        assert "段落1" in result["content"]
        assert "段落4" in result["content"]

    def test_parse_chapter_content_empty(self, parser):
        html = "<html><body></body></html>"
        result = parser.parse_chapter_content(html)
        
        assert result["title"] == ""
        assert result["content"] == ""

    def test_parse_book_info(self, parser):
        html = """
        <html>
            <h1>测试小说</h1>
            <div class="author">作者：张三</div>
            <div class="intro">这是一本测试小说。</div>
        </html>
        """
        info = parser.parse_book_info(html)
        
        assert info["title"] == "测试小说"
        assert info["author"] == "张三"
        assert info["description"] == "这是一本测试小说。"

    def test_parse_book_info_meta_author(self, parser):
        html = """
        <html>
            <h1>测试小说</h1>
            <meta property="og:novel:author" content="李四">
        </html>
        """
        info = parser.parse_book_info(html)
        
        assert info["author"] == "李四"


class TestDynamicConcurrencyController:
    @pytest.fixture
    def controller(self):
        return DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)

    def test_initial_state(self, controller):
        assert controller._max_concurrent == 5
        assert controller._base_delay == 1.0
        assert controller._current_concurrent == 1

    def test_get_delay_normal(self, controller):
        delay = controller.get_delay()
        assert delay == 1.0

    def test_get_delay_with_errors(self, controller):
        controller._error_count = 2
        delay = controller.get_delay()
        assert delay == 2.0
        
        controller._error_count = 4
        delay = controller.get_delay()
        assert delay == 3.0

    def test_get_delay_with_slow_response(self, controller):
        controller._response_times = [3.5, 4.0, 3.8, 3.2, 3.6]
        delay = controller.get_delay()
        assert delay == 2.0

    def test_record_response_success(self, controller):
        controller._error_count = 2
        controller.record_response(0.5, True)
        
        assert controller._success_count == 1
        assert controller._error_count == 1

    def test_record_response_failure(self, controller):
        controller.record_response(0.0, False)
        
        assert controller._error_count == 1

    def test_adjust_concurrency_on_errors(self, controller):
        controller._current_concurrent = 3
        controller._error_count = 6
        
        controller._adjust_concurrency()
        
        assert controller._current_concurrent == 2

    def test_adjust_concurrency_on_success(self, controller):
        controller._success_count = 15
        
        controller._adjust_concurrency()
        
        assert controller._current_concurrent == 2
        assert controller._success_count == 0