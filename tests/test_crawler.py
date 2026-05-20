import pytest
from django.test import TestCase
from utils.crawler_config import SiteConfig, get_config_for_url, DEFAULT_CONFIG
from utils.crawler_engine import validate_crawl_url, IntelligentParser


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
            content_selectors=["#novel-content"],
            chapter_list_selectors=["#chapter-list"],
        )
        self.parser = IntelligentParser(self.config)

    def test_clean_content(self):
        html = """
        <div id="novel-content">
            <p>第一段这是一个比较长的内容</p>
            <p>第二段这也是一个比较长的内容</p>
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
