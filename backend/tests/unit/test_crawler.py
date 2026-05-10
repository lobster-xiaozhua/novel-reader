import pytest
import asyncio
import re
from unittest.mock import AsyncMock, MagicMock

from app.services.crawler_service import (
    RobotsTxtChecker,
    IntelligentParser,
    DynamicConcurrencyController,
)


class TestRobotsTxtChecker:
    @pytest.fixture
    def checker(self):
        return RobotsTxtChecker()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        return session

    def test_init_has_user_agent(self, checker):
        assert hasattr(checker, '_user_agent')
        assert 'NovelReaderBot' in checker._user_agent

    def test_init_has_empty_cache(self, checker):
        assert checker._cache == {}

    @pytest.mark.asyncio
    async def test_can_fetch_no_robots_txt(self, checker, mock_session):
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_session.get = AsyncMock(return_value=mock_response)

        result = await checker.can_fetch("https://example.com/page", mock_session)
        assert result is True

    @pytest.mark.asyncio
    async def test_can_fetch_robots_allows(self, checker, mock_session):
        robots_content = "User-agent: *\nDisallow: /private/"
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=robots_content)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_response)

        result = await checker.can_fetch("https://example.com/public/page", mock_session)
        assert result is True

    @pytest.mark.asyncio
    async def test_can_fetch_robots_disallows(self, checker, mock_session):
        robots_content = "User-agent: *\nDisallow: /admin/"
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=robots_content)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_response)

        result = await checker.can_fetch("https://example.com/admin/panel", mock_session)
        assert result is False

    @pytest.mark.asyncio
    async def test_can_fetch_caches_result(self, checker, mock_session):
        robots_content = "User-agent: *\nDisallow: /test/"
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=robots_content)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_response)

        await checker.can_fetch("https://example.com/page1", mock_session)
        assert len(checker._cache) == 1

        await checker.can_fetch("https://example.com/page2", mock_session)
        assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_can_fetch_handles_exception(self, checker, mock_session):
        mock_session.get = MagicMock(side_effect=Exception("Network error"))

        result = await checker.can_fetch("https://example.com/page", mock_session)
        assert result is True

    def test_parse_robots_basic(self, checker):
        text = "User-agent: *\nDisallow: /private/"
        result = checker._parse_robots(text)
        assert result["fetched"] is True
        assert "/private/" in result["disallow"]

    def test_parse_robots_with_wildcard_agent(self, checker):
        text = """User-agent: *
Disallow: /all/

User-agent: OtherBot
Disallow: /other/
"""
        result = checker._parse_robots(text)
        assert "/all/" in result["disallow"]

    def test_parse_robots_crawl_delay(self, checker):
        text = """User-agent: *
Crawl-delay: 5
"""
        result = checker._parse_robots(text)
        assert result["crawl_delay"] == 5.0

    def test_parse_robots_ignores_comments(self, checker):
        text = """# This is a comment
User-agent: *
Disallow: /private/
"""
        result = checker._parse_robots(text)
        assert "/private/" in result["disallow"]

    def test_parse_robots_invalid_crawl_delay(self, checker):
        text = "User-agent: *\nCrawl-delay: not-a-number"
        result = checker._parse_robots(text)
        assert result["crawl_delay"] == 0

    def test_parse_robots_empty(self, checker):
        result = checker._parse_robots("")
        assert result["fetched"] is True
        assert result["disallow"] == []

    def test_parse_robots_malformed_lines(self, checker):
        text = "invalid line without colon\nUser-agent: *\nDisallow:"
        result = checker._parse_robots(text)
        assert result["fetched"] is True


class TestIntelligentParser:
    @pytest.fixture
    def parser(self):
        return IntelligentParser()

    def test_parse_chapter_list_with_list_container(self, parser):
        html = """
        <html>
        <div class="chapter-list">
            <a href="/chapter/1">第一章 开篇</a>
            <a href="/chapter/2">第二章 发展</a>
        </div>
        </html>
        """
        chapters = parser.parse_chapter_list(html, "https://example.com")
        assert len(chapters) == 2
        assert chapters[0]["title"] == "第一章 开篇"

    def test_parse_chapter_list_skips_navigation(self, parser):
        html = """
        <div class="chapter-list">
            <a href="/index">首页</a>
            <a href="/prev">上一页</a>
            <a href="/chapter/1">第一章</a>
            <a href="/next">下一页</a>
            <a href="/end">末页</a>
        </div>
        """
        chapters = parser.parse_chapter_list(html, "https://example.com")
        assert len(chapters) == 1
        assert chapters[0]["title"] == "第一章"

    def test_parse_chapter_list_with_patterns(self, parser):
        html = """
        <div>
            <a href="/c1">Chapter 1: Beginning</a>
            <a href="/c2">第5章 转折</a>
        </div>
        """
        chapters = parser.parse_chapter_list(html, "https://example.com")
        assert len(chapters) == 2

    def test_parse_chapter_list_deduplicates_urls(self, parser):
        html = """
        <div>
            <a href="/chapter/1">第一章</a>
            <a href="/chapter/1">第一章 (repeated)</a>
        </div>
        """
        chapters = parser.parse_chapter_list(html, "https://example.com")
        assert len(chapters) == 1

    def test_parse_chapter_list_handles_relative_urls(self, parser):
        html = '<a href="/chapter/1">第一章</a>'
        chapters = parser.parse_chapter_list(html, "https://example.com/novel/")
        assert chapters[0]["url"].startswith("https://example.com")

    def test_parse_chapter_content_with_id_selector(self, parser):
        html = """
        <html>
        <body>
        <div id="content">
            <p>这是第一章内容，详细描述了故事的开始。</p>
            <p>第二段内容，继续讲述精彩的故事情节。</p>
            <p>第三段内容，人物开始登场亮相。</p>
            <p>第四段内容，情节逐渐展开深入。</p>
            <p>第五段内容，故事发展到一个新的阶段。</p>
            <p>第六段内容，悬念与冲突开始显现。</p>
        </div>
        </body>
        </html>
        """
        result = parser.parse_chapter_content(html)
        assert len(result["content"]) > 50

    def test_parse_chapter_content_with_class_selector(self, parser):
        html = """
        <html>
        <body>
        <div class="content">
            <p>章节正文内容，详细描述了故事情节的发展过程。</p>
            <p>第二段继续讲述。</p>
            <p>第三段进一步展开。</p>
            <p>第四段深入描写。</p>
            <p>第五段推向高潮。</p>
        </div>
        </body>
        </html>
        """
        result = parser.parse_chapter_content(html)
        assert len(result["content"]) > 50

    def test_parse_chapter_content_empty_for_novel(self, parser):
        html = "<html><body><p>No content here</p></body></html>"
        result = parser.parse_chapter_content(html)
        assert result["content"] == ""

    def test_parse_chapter_content_removes_scripts(self, parser):
        html = """
        <html>
        <body>
        <div id="content">
            <p>Real content that is long enough to pass the minimum threshold and describe the story.</p>
            <script>alert('xss')</script>
            <style>.hidden { display: none; }</style>
        </div>
        </body>
        </html>
        """
        result = parser.parse_chapter_content(html)
        assert "alert" not in result["content"]
        assert "Real content" in result["content"]

    def test_extract_title_with_h1(self, parser):
        from bs4 import BeautifulSoup
        html = BeautifulSoup("<html><h1>Book Title</h1></html>", "html.parser")
        title = parser._extract_title(html)
        assert title == "Book Title"

    def test_extract_title_with_class(self, parser):
        from bs4 import BeautifulSoup
        html = BeautifulSoup("<html><div class='title'>Chapter Title</div></html>", "html.parser")
        title = parser._extract_title(html)
        assert title == "Chapter Title"

    def test_extract_title_empty_when_none(self, parser):
        from bs4 import BeautifulSoup
        html = BeautifulSoup("<html><body><p>No title</p></body></html>", "html.parser")
        title = parser._extract_title(html)
        assert title == ""

    def test_parse_book_info(self, parser):
        html = """
        <html>
        <body>
        <h1>My Novel Title</h1>
        <span class="author">John Author</span>
        <div class="intro">This is a great novel.</div>
        </body>
        </html>
        """
        info = parser.parse_book_info(html)
        assert info["title"] == "My Novel Title"

    def test_parse_book_info_with_meta_author(self, parser):
        html = """
        <html>
        <body>
        <h1>Book</h1>
        <meta property="og:novel:author" content="Meta Author"/>
        </body>
        </html>
        """
        info = parser.parse_book_info(html)
        assert info["author"] == "Meta Author"

    def test_parse_book_info_truncates_description(self, parser):
        html = """
        <html>
        <body>
        <h1>Book</h1>
        <div class="intro">""" + "x" * 1000 + """</div>
        </body>
        </html>
        """
        info = parser.parse_book_info(html)
        assert len(info["description"]) <= 500

    def test_chapter_patterns_match_chapter_1(self, parser):
        patterns = [
            "第一章 开始",
            "第12章 发展",
            "第123章 高潮",
        ]
        for title in patterns:
            matched = any(p.search(title) for p in parser.CHAPTER_PATTERNS)
            assert matched, f"Should match: {title}"

    def test_chapter_patterns_match_english(self, parser):
        english_patterns = [
            "Chapter 1: Beginning",
            "Chapter 100 End",
        ]
        for title in english_patterns:
            matched = any(p.search(title) for p in parser.CHAPTER_PATTERNS)
            assert matched, f"Should match: {title}"


class TestDynamicConcurrencyController:
    def test_init_defaults(self):
        controller = DynamicConcurrencyController()
        assert controller._current_concurrent == 1
        assert controller._max_concurrent > 1

    def test_init_custom_values(self):
        controller = DynamicConcurrencyController(max_concurrent=10, base_delay=2.0)
        assert controller._max_concurrent == 10
        assert controller._base_delay == 2.0

    @pytest.mark.asyncio
    async def test_acquire_releases(self):
        controller = DynamicConcurrencyController()
        controller._semaphore = asyncio.Semaphore(1)

        await controller.acquire()
        controller.release()

        assert controller._semaphore._value == 1

    def test_record_response_success(self):
        controller = DynamicConcurrencyController()
        controller.record_response(0.5, success=True)
        assert controller._success_count == 1
        assert controller._error_count == 0

    def test_record_response_failure(self):
        controller = DynamicConcurrencyController()
        controller.record_response(0.5, success=False)
        assert controller._error_count == 1

    def test_record_response_limits_history(self):
        controller = DynamicConcurrencyController()
        for i in range(25):
            controller.record_response(0.5, success=True)
        assert len(controller._response_times) <= 20

    def test_get_delay_no_errors(self):
        controller = DynamicConcurrencyController(base_delay=1.0)
        delay = controller.get_delay()
        assert delay == 1.0

    def test_get_delay_one_error(self):
        controller = DynamicConcurrencyController(base_delay=1.0)
        controller._error_count = 2
        delay = controller.get_delay()
        assert delay == 2.0

    def test_get_delay_many_errors(self):
        controller = DynamicConcurrencyController(base_delay=1.0)
        controller._error_count = 4
        delay = controller.get_delay()
        assert delay == 3.0

    def test_get_delay_slow_response(self):
        controller = DynamicConcurrencyController(base_delay=1.0)
        for _ in range(5):
            controller.record_response(3.5, success=True)
        delay = controller.get_delay()
        assert delay == 2.0

    def test_get_delay_very_slow_response(self):
        controller = DynamicConcurrencyController(base_delay=1.0)
        for _ in range(5):
            controller.record_response(1.6, success=True)
        delay = controller.get_delay()
        assert delay == 1.5

    def test_adjust_concurrency_decreases_on_many_errors(self):
        controller = DynamicConcurrencyController(max_concurrent=5)
        controller._current_concurrent = 3
        controller._error_count = 6

        controller._adjust_concurrency()

        assert controller._current_concurrent == 2

    def test_adjust_concurrency_increases_on_success(self):
        controller = DynamicConcurrencyController(max_concurrent=5)
        controller._current_concurrent = 2
        controller._success_count = 11

        controller._adjust_concurrency()

        assert controller._current_concurrent == 3

    def test_adjust_concurrency_stays_at_minimum(self):
        controller = DynamicConcurrencyController()
        controller._current_concurrent = 1
        controller._error_count = 10

        controller._adjust_concurrency()

        assert controller._current_concurrent == 1

    def test_adjust_concurrency_stays_at_maximum(self):
        controller = DynamicConcurrencyController(max_concurrent=5)
        controller._current_concurrent = 5
        controller._success_count = 20

        controller._adjust_concurrency()

        assert controller._current_concurrent == 5

    @pytest.mark.asyncio
    async def test_robots_checker_get_crawl_delay(self):
        checker = RobotsTxtChecker()
        checker._cache = {"https://example.com/robots.txt": {"crawl_delay": 5}}
        delay = await checker.get_crawl_delay("https://example.com/page")
        assert delay == 5.0
