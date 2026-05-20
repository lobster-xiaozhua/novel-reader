import socket
import ipaddress
from unittest.mock import patch, MagicMock
from django.test import TestCase
from .crawler_engine import (
    validate_crawl_url,
    IntelligentParser,
    CrawlerEngine,
    SSRF_BLOCKED_HOSTS
)


class ValidateCrawlUrlTest(TestCase):
    """测试爬虫URL验证 - 防止SSRF攻击"""

    def test_valid_http_url(self):
        """测试有效HTTP URL"""
        self.assertTrue(validate_crawl_url('http://example.com'))

    def test_valid_https_url(self):
        """测试有效HTTPS URL"""
        self.assertTrue(validate_crawl_url('https://example.com'))

    def test_invalid_scheme(self):
        """测试无效协议"""
        self.assertFalse(validate_crawl_url('ftp://example.com'))
        self.assertFalse(validate_crawl_url('file:///etc/passwd'))
        self.assertFalse(validate_crawl_url('javascript:alert(1)'))

    def test_blocked_localhost(self):
        """测试阻止localhost"""
        self.assertFalse(validate_crawl_url('http://localhost'))
        self.assertFalse(validate_crawl_url('http://127.0.0.1'))
        self.assertFalse(validate_crawl_url('http://0.0.0.0'))
        self.assertFalse(validate_crawl_url('http://[::1]'))

    def test_blocked_metadata_endpoints(self):
        """测试阻止云元数据端点"""
        self.assertFalse(validate_crawl_url('http://169.254.169.254'))
        self.assertFalse(validate_crawl_url('http://metadata.google.internal'))

    def test_private_ip_ranges(self):
        """测试阻止私有IP范围"""
        private_ips = [
            'http://10.0.0.1',
            'http://172.16.0.1',
            'http://192.168.1.1',
            'http://169.254.0.1',
        ]
        for url in private_ips:
            with self.subTest(url=url):
                self.assertFalse(validate_crawl_url(url))

    def test_malformed_url(self):
        """测试畸形URL"""
        self.assertFalse(validate_crawl_url('not-a-url'))
        self.assertFalse(validate_crawl_url(''))
        self.assertFalse(validate_crawl_url('http://'))

    def test_url_with_path_and_query(self):
        """测试带路径和参数的URL"""
        self.assertTrue(validate_crawl_url('https://example.com/path?query=value'))


class IntelligentParserTest(TestCase):
    """测试智能解析器"""

    def setUp(self):
        self.parser = IntelligentParser()

    def test_parse_chapter_list(self):
        """测试解析章节列表"""
        html = '''
        <html>
        <div class="chapter-list">
            <a href="/chapter/1">第一章</a>
            <a href="/chapter/2">第二章</a>
        </div>
        </html>
        '''
        chapters = self.parser.parse_chapter_list(html, 'http://example.com')
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0]['title'], '第一章')
        self.assertEqual(chapters[0]['url'], 'http://example.com/chapter/1')

    def test_parse_chapter_list_skips_pagination(self):
        """测试解析章节列表跳过分页链接"""
        html = '''
        <html>
        <div class="chapter-list">
            <a href="/chapter/1">第一章</a>
            <a href="/prev">上一页</a>
            <a href="/next">下一页</a>
            <a href="/">首页</a>
        </div>
        </html>
        '''
        chapters = self.parser.parse_chapter_list(html, 'http://example.com')
        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0]['title'], '第一章')

    def test_parse_chapter_list_deduplication(self):
        """测试章节列表去重"""
        html = '''
        <html>
        <div class="chapter-list">
            <a href="/chapter/1">第一章</a>
            <a href="/chapter/1">第一章重复</a>
        </div>
        </html>
        '''
        chapters = self.parser.parse_chapter_list(html, 'http://example.com')
        self.assertEqual(len(chapters), 1)

    def test_parse_chapter_list_empty_title(self):
        """测试跳过空标题链接"""
        html = '''
        <html>
        <div class="chapter-list">
            <a href="/chapter/1">第一章</a>
            <a href="/chapter/2"></a>
        </div>
        </html>
        '''
        chapters = self.parser.parse_chapter_list(html, 'http://example.com')
        self.assertEqual(len(chapters), 1)

    def test_parse_chapter_content(self):
        """测试解析章节内容"""
        html = '''
        <html>
        <div id="content">
            <p>第一段内容测试文本足够长以满足长度要求</p>
            <p>第二段内容测试文本足够长以满足长度要求</p>
            <p>第三段内容测试文本足够长以满足长度要求</p>
        </div>
        </html>
        '''
        result = self.parser.parse_chapter_content(html)
        self.assertIn('第一段内容', result['content'])
        self.assertIn('第二段内容', result['content'])
        self.assertTrue(len(result['content']) > 50)

    def test_parse_chapter_content_removes_scripts(self):
        """测试解析章节内容移除脚本"""
        html = '''
        <html>
        <div id="content">
            <p>正常内容测试文本足够长以满足长度要求正常内容测试文本足够长以满足长度要求正常内容测试文本足够长</p>
            <p>第二段正常内容测试文本足够长以满足长度要求正常内容测试文本足够长以满足长度要求</p>
            <script>alert('xss')</script>
            <style>.hidden{display:none}</style>
        </div>
        </html>
        '''
        result = self.parser.parse_chapter_content(html)
        self.assertIn('正常内容', result['content'])
        self.assertNotIn('alert', result['content'])
        self.assertNotIn('style', result['content'])

    def test_parse_chapter_content_short_content_fallback(self):
        """测试短内容回退处理"""
        html = '''
        <html>
        <div id="content">
            <p>短</p>
        </div>
        </html>
        '''
        result = self.parser.parse_chapter_content(html)
        self.assertEqual(result['content'], '')

    def test_parse_chapter_content_no_matching_selector(self):
        """测试无匹配选择器"""
        html = '<html><body><p>内容</p></body></html>'
        result = self.parser.parse_chapter_content(html)
        self.assertEqual(result['content'], '')

    def test_parse_book_info(self):
        """测试解析书籍信息"""
        html = '''
        <html>
        <h1>书籍标题</h1>
        </html>
        '''
        info = self.parser.parse_book_info(html)
        self.assertEqual(info['title'], '书籍标题')

    def test_clean_content_with_paragraphs(self):
        """测试清理带段落的内容"""
        html = '''
        <div>
            <p>  段落1  </p>
            <p></p>
            <p>段落2</p>
        </div>
        '''
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find('div')
        content = self.parser._clean_content(div)
        self.assertIn('段落1', content)
        self.assertIn('段落2', content)

    def test_clean_content_without_paragraphs(self):
        """测试清理无段落的内容"""
        html = '<div>行1<br>行2<br><br>行3</div>'
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find('div')
        content = self.parser._clean_content(div)
        self.assertIn('行1', content)
        self.assertIn('行2', content)


class CrawlerEngineUnitTest(TestCase):
    """测试爬虫引擎单元功能"""

    def setUp(self):
        self.engine = CrawlerEngine(1, '/tmp/books')

    def test_safe_filename(self):
        """测试安全文件名处理"""
        self.assertEqual(self.engine._safe_filename('正常文件名'), '正常文件名')
        self.assertEqual(self.engine._safe_filename('文件/名'), '文件_名')
        self.assertEqual(self.engine._safe_filename('文件:名?'), '文件_名_')
        self.assertEqual(self.engine._safe_filename('   .  '), 'unnamed')
        self.assertEqual(len(self.engine._safe_filename('a' * 200)), 100)

    def test_get_ua_rotation(self):
        """测试User-Agent轮询"""
        ua1 = self.engine._get_ua()
        ua2 = self.engine._get_ua()
        self.assertIn(ua1, [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ])

    def test_stop_flag(self):
        """测试停止标志"""
        self.assertFalse(self.engine._stop)
        self.engine.stop()
        self.assertTrue(self.engine._stop)

    @patch('utils.crawler_engine.requests.Session')
    def test_fetch_page_success(self, mock_session_class):
        """测试获取页面成功"""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html>内容</html>'
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        result = self.engine._fetch_page(mock_session, 'http://example.com')
        self.assertEqual(result, '<html>内容</html>')

    @patch('utils.crawler_engine.requests.Session')
    def test_fetch_page_non_200(self, mock_session_class):
        """测试获取页面非200状态码"""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        result = self.engine._fetch_page(mock_session, 'http://example.com')
        self.assertIsNone(result)


class CrawlerEngineIntegrationTest(TestCase):
    """测试爬虫引擎集成（需要Django环境）"""

    def setUp(self):
        from django.contrib.auth.models import User
        from apps.crawler.models import CrawlerTask

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.task = CrawlerTask.objects.create(
            user=self.user,
            url='http://example.com/book',
            status='pending'
        )
        self.engine = CrawlerEngine(self.task.id, '/tmp/books')

    @patch('utils.crawler_engine.validate_crawl_url')
    def test_run_invalid_url(self, mock_validate):
        """测试运行无效URL"""
        mock_validate.return_value = False

        self.engine.run(self.task)

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'failed')
        self.assertIn('不合法', self.task.error_message)

    @patch('utils.crawler_engine.validate_crawl_url')
    @patch.object(CrawlerEngine, '_fetch_page')
    def test_run_fetch_page_failure(self, mock_fetch, mock_validate):
        """测试获取页面失败"""
        mock_validate.return_value = True
        mock_fetch.return_value = None

        self.engine.run(self.task)

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'failed')
        self.assertIn('无法获取', self.task.error_message)

    @patch('utils.crawler_engine.validate_crawl_url')
    @patch.object(CrawlerEngine, '_fetch_page')
    def test_run_empty_chapter_list(self, mock_fetch, mock_validate):
        """测试空章节列表"""
        mock_validate.return_value = True
        mock_fetch.return_value = '<html><body>无章节</body></html>'

        self.engine.run(self.task)

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'failed')
        self.assertIn('无法解析章节列表', self.task.error_message)

    @patch('utils.crawler_engine.validate_crawl_url')
    @patch.object(CrawlerEngine, '_fetch_page')
    def test_run_task_cancelled(self, mock_fetch, mock_validate):
        """测试任务取消"""
        mock_validate.return_value = True
        mock_fetch.return_value = '''
        <html>
        <h1>书籍</h1>
        <div class="chapter-list">
            <a href="/ch1">第一章</a>
        </div>
        </html>
        '''

        self.engine.stop()
        self.engine.run(self.task)

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'cancelled')
