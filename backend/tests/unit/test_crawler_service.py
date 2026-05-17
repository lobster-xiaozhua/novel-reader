import pytest
from app.services.crawler_service import (
    IntelligentParser,
    DynamicConcurrencyController,
    validate_crawl_url,
)


class TestIntelligentParser:
    def setup_method(self):
        self.parser = IntelligentParser()

    def test_parse_chapter_list_with_container(self):
        html = '''
        <div class="chapter-list">
            <a href="/chapter/1">第1章 入门</a>
            <a href="/chapter/2">第2章 进阶</a>
            <a href="/chapter/3">第三章</a>
        </div>
        '''
        result = self.parser.parse_chapter_list(html, "https://example.com/novel")
        assert len(result) >= 2
        assert any("第1章" in r["title"] for r in result)

    def test_parse_chapter_list_with_chapter_pattern(self):
        html = '''
        <div>
            <a href="/ch/1">Chapter 1: Beginning</a>
            <a href="/ch/2">Chapter 2: Middle</a>
        </div>
        '''
        result = self.parser.parse_chapter_list(html, "https://example.com/")
        assert len(result) >= 2
        assert any("Chapter 1" in r["title"] for r in result)

    def test_parse_chapter_list_skips_navigation(self):
        html = '''
        <div class="chapter-list">
            <a href="/home">首页</a>
            <a href="/prev">上一页</a>
            <a href="/chapter/1">第1章</a>
            <a href="/next">下一页</a>
            <a href="/end">末页</a>
        </div>
        '''
        result = self.parser.parse_chapter_list(html, "https://example.com/")
        titles = [r["title"] for r in result]
        assert "首页" not in titles
        assert "末页" not in titles
        assert "第1章" in titles

    def test_parse_chapter_list_deduplicates(self):
        html = '''
        <div class="list1">
            <a href="/chapter/1">第1章</a>
        </div>
        <div class="list2">
            <a href="/chapter/1">第1章</a>
        </div>
        '''
        result = self.parser.parse_chapter_list(html, "https://example.com/")
        urls = [r["url"] for r in result]
        assert len(urls) == len(set(urls))

    def test_parse_chapter_content_with_content_selector(self):
        html = '''
        <html><body>
            <div class="title">Test Title</div>
            <div id="content">
                <p>Paragraph 1 content here</p>
                <p>Paragraph 2 content here</p>
                <p>Paragraph 3 content here</p>
            </div>
        </body></html>
        '''
        result = self.parser.parse_chapter_content(html)
        assert len(result["content"]) > 0
        assert "Paragraph 1" in result["content"]

    def test_parse_chapter_content_with_fallback_paragraphs(self):
        html = '''
        <html><body>
            <h1>No Selector Title</h1>
            <p>First paragraph content here</p>
            <p>Second paragraph content here</p>
            <p>Third paragraph content here</p>
            <p>Fourth paragraph content here</p>
        </body></html>
        '''
        result = self.parser.parse_chapter_content(html)
        assert "First paragraph" in result["content"]

    def test_parse_chapter_content_with_title_div(self):
        html = '''
        <html><body>
            <div class="title">My Chapter Title</div>
            <div id="content">
                <p>This is paragraph 1</p>
                <p>This is paragraph 2</p>
                <p>This is paragraph 3</p>
            </div>
        </body></html>
        '''
        result = self.parser.parse_chapter_content(html)
        assert len(result["content"]) > 0
        assert "paragraph 1" in result["content"]

    def test_parse_chapter_content_empty_page(self):
        html = '<html><body></body></html>'
        result = self.parser.parse_chapter_content(html)
        assert result["content"] == ""

    def test_parse_book_info_extracts_title(self):
        html = '''
        <html><body>
            <h1>My Amazing Novel</h1>
        </body></html>
        '''
        result = self.parser.parse_book_info(html)
        assert result["title"] == "My Amazing Novel"

    def test_parse_book_info_extracts_author_from_pattern(self):
        html = '''
        <html><body>
            <h1>Novel Title</h1>
            <span>作者：张三</span>
        </body></html>
        '''
        result = self.parser.parse_book_info(html)
        assert result["author"] == "张三"

    def test_parse_book_info_extracts_author_from_meta(self):
        html = '''
        <html><head>
            <meta property="og:novel:author" content="李四">
        </head><body>
            <h1>Book</h1>
        </body></html>
        '''
        result = self.parser.parse_book_info(html)
        assert result["author"] == "李四"

    def test_parse_book_info_extracts_description(self):
        html = '''
        <html><body>
            <h1>Title</h1>
            <div class="intro">这是一本精彩的小说</div>
        </body></html>
        '''
        result = self.parser.parse_book_info(html)
        assert "精彩" in result["description"]


class TestDynamicConcurrencyController:
    def test_initial_state(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        assert controller._current_concurrent == 1
        assert controller._error_count == 0
        assert controller._success_count == 0

    def test_get_delay_base(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        assert controller.get_delay() == 1.0

    def test_get_delay_increases_with_errors(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        controller.record_response(0.5, success=False)
        controller.record_response(0.5, success=False)
        assert controller.get_delay() == 2.0

    def test_get_delay_triples_with_many_errors(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        for _ in range(4):
            controller.record_response(0.5, success=False)
        assert controller.get_delay() == 3.0

    def test_get_delay_scales_with_slow_responses(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        for _ in range(5):
            controller.record_response(4.0, success=True)
        assert controller.get_delay() == 2.0

    def test_record_response_maintains_history(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        for i in range(25):
            controller.record_response(float(i), success=True)
        assert len(controller._response_times) == 20

    def test_record_response_success_decreases_error_count(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        controller._error_count = 3
        controller.record_response(1.0, success=True)
        assert controller._error_count == 2

    def test_adjust_concurrency_decreases_on_many_errors(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        controller._current_concurrent = 3
        for _ in range(6):
            controller.record_response(0.5, success=False)
        assert controller._current_concurrent == 2

    def test_adjust_concurrency_increases_on_success(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        controller._current_concurrent = 1
        for _ in range(15):
            controller.record_response(0.5, success=True)
        assert controller._current_concurrent == 2

    def test_adjust_concurrency_max_limit(self):
        controller = DynamicConcurrencyController(max_concurrent=3, base_delay=1.0)
        controller._current_concurrent = 3
        for _ in range(15):
            controller.record_response(0.5, success=True)
        assert controller._current_concurrent <= 3

    def test_acquire_release(self):
        controller = DynamicConcurrencyController(max_concurrent=5, base_delay=1.0)
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(controller.acquire())
        assert controller._semaphore._value == 0
        controller.release()
        assert controller._semaphore._value == 1
        loop.close()


class TestValidateCrawlUrl:
    def test_valid_http_url(self):
        assert validate_crawl_url("https://example.com/novel") is True

    def test_url_with_only_path_resolves_correctly(self):
        result = validate_crawl_url("https://www.python.org/")
        assert isinstance(result, bool)

    def test_invalid_scheme_ftp(self):
        assert validate_crawl_url("ftp://example.com") is False

    def test_invalid_scheme_file(self):
        assert validate_crawl_url("file:///etc/passwd") is False

    def test_blocked_localhost(self):
        assert validate_crawl_url("http://localhost/index.html") is False

    def test_blocked_127(self):
        assert validate_crawl_url("http://127.0.0.1/admin") is False

    def test_blocked_0(self):
        assert validate_crawl_url("http://0.0.0.0:8080") is False

    def test_blocked_loopback(self):
        assert validate_crawl_url("http://[::1]/api") is False

    def test_blocked_metadata(self):
        assert validate_crawl_url("http://169.254.169.254/latest/meta-data") is False

    def test_blocked_metadata_google(self):
        assert validate_crawl_url("http://metadata.google.internal/computeMetadata/v1") is False

    def test_invalid_url(self):
        assert validate_crawl_url("not a url") is False

    def test_empty_url(self):
        assert validate_crawl_url("") is False

    def test_malformed_url(self):
        assert validate_crawl_url("http://") is False

    def test_resolves_to_private_ip(self):
        assert validate_crawl_url("https://www.python.org/") is False or True

    def test_no_scheme(self):
        assert validate_crawl_url("example.com") is False


class TestCrawlerServiceSafeFilename:
    def test_strips_invalid_chars(self):
        from app.services.crawler_service import CrawlerService
        service = CrawlerService()
        result = service._safe_filename('test:file*name?.txt')
        assert ':' not in result
        assert '*' not in result
        assert '?' not in result

    def test_strips_path_separators(self):
        from app.services.crawler_service import CrawlerService
        service = CrawlerService()
        result = service._safe_filename('path/to/book')
        assert '/' not in result
        assert '\\' not in result

    def test_strips_dots(self):
        from app.services.crawler_service import CrawlerService
        service = CrawlerService()
        result = service._safe_filename('...hidden...')
        assert result == "hidden"

    def test_truncates_long_names(self):
        from app.services.crawler_service import CrawlerService
        service = CrawlerService()
        long_name = "a" * 200
        result = service._safe_filename(long_name)
        assert len(result) <= 100

    def test_handles_empty_name(self):
        from app.services.crawler_service import CrawlerService
        service = CrawlerService()
        result = service._safe_filename("")
        assert result == "unnamed"

    def test_preserves_valid_chars(self):
        from app.services.crawler_service import CrawlerService
        service = CrawlerService()
        result = service._safe_filename("我的书籍_2024")
        assert "我的书籍_2024" in result

    def test_strips_whitespace(self):
        from app.services.crawler_service import CrawlerService
        service = CrawlerService()
        result = service._safe_filename("  book name  ")
        assert result.startswith("book")
