import unittest
from utils.crawler_engine import IntelligentParser, validate_crawl_url


class CrawlerEngineTests(unittest.TestCase):
    def test_validate_crawl_url_valid_public(self):
        self.assertTrue(validate_crawl_url('https://example.com'))

    def test_validate_crawl_url_blocked_localhost(self):
        self.assertFalse(validate_crawl_url('http://localhost'))
        self.assertFalse(validate_crawl_url('http://127.0.0.1'))

    def test_validate_crawl_url_blocked_metadata(self):
        self.assertFalse(validate_crawl_url('http://169.254.169.254'))

    def test_validate_crawl_url_invalid_scheme(self):
        self.assertFalse(validate_crawl_url('ftp://example.com'))

    def test_intelligent_parser_parse_chapter_list(self):
        parser = IntelligentParser()
        html = '''
        <div class="chapter-list">
            <a href="/chapter1">第1章 开头</a>
            <a href="/chapter2">第2章 发展</a>
        </div>
        '''
        chapters = parser.parse_chapter_list(html, 'https://example.com')
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0]['title'], '第1章 开头')
        self.assertEqual(chapters[0]['url'], 'https://example.com/chapter1')

    def test_intelligent_parser_parse_chapter_content(self):
        parser = IntelligentParser()
        html = '''
        <div id="content">
            <p>这是第一段很长很长的内容，超过50个字符的长度，这样才能满足条件，对吧？让我们继续写一点，确保足够长。</p>
            <p>这是第二段内容，也足够长，超过50个字符的长度，这样才能让测试通过，没问题的。</p>
        </div>
        '''
        result = parser.parse_chapter_content(html)
        self.assertIn('这是第一段很长很长的内容，超过50个字符的长度，这样才能满足条件，对吧？让我们继续写一点，确保足够长。', result['content'])
        self.assertIn('这是第二段内容，也足够长，超过50个字符的长度，这样才能让测试通过，没问题的。', result['content'])

    def test_intelligent_parser_parse_book_info(self):
        parser = IntelligentParser()
        html = '''
        <h1>我的小说</h1>
        '''
        info = parser.parse_book_info(html)
        self.assertEqual(info['title'], '我的小说')


if __name__ == '__main__':
    unittest.main()
