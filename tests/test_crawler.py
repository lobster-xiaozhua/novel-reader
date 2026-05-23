from django.test import TestCase
from utils.crawler_config import SiteConfig, get_config_for_url, DEFAULT_CONFIG
from utils.crawler_engine import validate_crawl_url, IntelligentParser
from utils.book_gradient import get_book_gradient


class CrawlerConfigTest(TestCase):
    def test_default_config(self):
        self.assertEqual(DEFAULT_CONFIG.name, "default")
        self.assertEqual(DEFAULT_CONFIG.domain, "*")
        self.assertTrue(len(DEFAULT_CONFIG.content_selectors) > 0)

    def test_get_config_for_url(self):
        config = get_config_for_url("https://example.com/some/path")
        self.assertEqual(config.name, "Example Novel Site")
        config2 = get_config_for_url("https://unknown-site.com")
        self.assertEqual(config2.name, "default")

    def test_validate_crawl_url(self):
        self.assertTrue(validate_crawl_url("https://example.com"))
        self.assertFalse(validate_crawl_url("http://localhost:8000"))
        self.assertFalse(validate_crawl_url("http://127.0.0.1"))
        self.assertFalse(validate_crawl_url("ftp://example.com"))
        self.assertFalse(validate_crawl_url("invalid-url"))


class IntelligentParserTest(TestCase):
    def setUp(self):
        self.config = SiteConfig(
            name="test",
            domain="test.com",
            content_selectors=["#test-content"],
            chapter_list_selectors=["#chapter-list"]
        )
        self.parser = IntelligentParser(self.config)

    def test_clean_content(self):
        html = """
        <div id="test-content">
            <p>第一段内容，这是一段测试文本，用于验证内容解析功能是否正常工作</p>
            <p>第二段内容，这也是一段测试文本，确保多段落内容都能被正确提取</p>
            <script>alert('test')</script>
        </div>
        """
        result = self.parser.parse_chapter_content(html)
        self.assertIn("第一段", result["content"])
        self.assertIn("第二段", result["content"])

    def test_parse_chapter_list(self):
        html = """
        <div id="chapter-list">
            <a href="/chapter/1">第一章</a>
            <a href="/chapter/2">第二章</a>
            <a href="/">首页</a>
        </div>
        """
        chapters = self.parser.parse_chapter_list(html, "https://test.com")
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0]["title"], "第一章")
        self.assertEqual(chapters[1]["url"], "https://test.com/chapter/2")


class BookGradientTest(TestCase):
    def test_gradient_returns_tuple(self):
        result = get_book_gradient(0)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_gradient_deterministic(self):
        self.assertEqual(get_book_gradient(1), get_book_gradient(1))

    def test_gradient_wraps(self):
        self.assertEqual(get_book_gradient(0), get_book_gradient(8))
