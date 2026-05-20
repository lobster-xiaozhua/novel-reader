import socket
from unittest.mock import patch, MagicMock

import pytest

from utils.crawler_engine import (
    IntelligentParser,
    validate_crawl_url,
    CrawlerEngine,
    SSRF_BLOCKED_HOSTS,
)


class TestValidateCrawlUrl:
    def test_valid_http_url(self):
        assert validate_crawl_url('http://example.com/novel') is True

    def test_valid_https_url(self):
        assert validate_crawl_url('https://example.com/novel') is True

    def test_ftp_scheme_rejected(self):
        assert validate_crawl_url('ftp://example.com/file') is False

    def test_javascript_scheme_rejected(self):
        assert validate_crawl_url('javascript:alert(1)') is False

    def test_file_scheme_rejected(self):
        assert validate_crawl_url('file:///etc/passwd') is False

    def test_empty_scheme_rejected(self):
        assert validate_crawl_url('example.com/novel') is False

    def test_localhost_blocked(self):
        assert validate_crawl_url('http://localhost/admin') is False

    def test_127_0_0_1_blocked(self):
        assert validate_crawl_url('http://127.0.0.1/admin') is False

    def test_0_0_0_0_blocked(self):
        assert validate_crawl_url('http://0.0.0.0/admin') is False

    def test_ipv6_loopback_blocked(self):
        assert validate_crawl_url('http://[::1]/admin') is False

    def test_aws_metadata_blocked(self):
        assert validate_crawl_url('http://169.254.169.254/latest/meta-data/') is False

    def test_gcp_metadata_blocked(self):
        assert validate_crawl_url('http://metadata.google.internal/') is False

    @patch('utils.crawler_engine.socket.getaddrinfo')
    def test_private_ip_10_range_blocked(self, mock_dns):
        mock_dns.return_value = [(socket.AF_INET, 1, 6, '', ('10.0.0.1', 0))]
        assert validate_crawl_url('http://internal.corp.com/') is False

    @patch('utils.crawler_engine.socket.getaddrinfo')
    def test_private_ip_172_range_blocked(self, mock_dns):
        mock_dns.return_value = [(socket.AF_INET, 1, 6, '', ('172.16.0.1', 0))]
        assert validate_crawl_url('http://intranet.corp.com/') is False

    @patch('utils.crawler_engine.socket.getaddrinfo')
    def test_private_ip_192_range_blocked(self, mock_dns):
        mock_dns.return_value = [(socket.AF_INET, 1, 6, '', ('192.168.1.1', 0))]
        assert validate_crawl_url('http://lan.corp.com/') is False

    @patch('utils.crawler_engine.socket.getaddrinfo')
    def test_public_ip_allowed(self, mock_dns):
        mock_dns.return_value = [(socket.AF_INET, 1, 6, '', ('93.184.216.34', 0))]
        assert validate_crawl_url('http://example.com/') is True

    @patch('utils.crawler_engine.socket.getaddrinfo', side_effect=socket.gaierror)
    def test_dns_failure_rejected(self, mock_dns):
        assert validate_crawl_url('http://nonexistent.invalid/') is False

    def test_no_hostname_rejected(self):
        assert validate_crawl_url('http:///path') is False

    def test_all_ssrf_blocked_hosts(self):
        for host in SSRF_BLOCKED_HOSTS:
            assert validate_crawl_url(f'http://{host}/') is False, f'{host} 未被阻止'


class TestIntelligentParser:
    def setup_method(self):
        self.parser = IntelligentParser()

    def test_parse_chapter_list_basic(self):
        html = '''
        <html><body>
        <div class="chapter-list">
            <a href="/chapter/1">第一章 起始</a>
            <a href="/chapter/2">第二章 发展</a>
            <a href="/chapter/3">第三章 高潮</a>
        </div>
        </body></html>'''
        result = self.parser.parse_chapter_list(html, 'http://example.com/book/')
        assert len(result) == 3
        assert result[0]['title'] == '第一章 起始'
        assert result[0]['url'] == 'http://example.com/chapter/1'

    def test_parse_chapter_list_dedup(self):
        html = '''
        <html><body>
        <div class="list">
            <a href="/ch1">第一章</a>
            <a href="/ch1">第一章</a>
        </div>
        </body></html>'''
        result = self.parser.parse_chapter_list(html, 'http://example.com/')
        assert len(result) == 1

    def test_parse_chapter_list_skip_pagination(self):
        html = '''
        <html><body>
        <div class="chapter-list">
            <a href="/ch1">第一章</a>
            <a href="?page=2">下一页</a>
            <a href="?page=1">首页</a>
            <a href="?page=last">末页</a>
            <a href="/">返回</a>
            <a href="/catalog">目录</a>
        </div>
        </body></html>'''
        result = self.parser.parse_chapter_list(html, 'http://example.com/')
        assert len(result) == 1
        assert result[0]['title'] == '第一章'

    def test_parse_chapter_list_empty_href_skipped(self):
        html = '''
        <html><body>
        <div class="list">
            <a href="">空链接</a>
            <a>无href</a>
            <a href="/ch1">有效章节</a>
        </div>
        </body></html>'''
        result = self.parser.parse_chapter_list(html, 'http://example.com/')
        assert len(result) == 1

    def test_parse_chapter_list_empty_title_skipped(self):
        html = '''
        <html><body>
        <div class="list">
            <a href="/ch1">   </a>
            <a href="/ch2">有效标题</a>
        </div>
        </body></html>'''
        result = self.parser.parse_chapter_list(html, 'http://example.com/')
        assert len(result) == 1

    def test_parse_chapter_list_no_container(self):
        html = '<html><body><p>无章节列表</p></body></html>'
        result = self.parser.parse_chapter_list(html, 'http://example.com/')
        assert result == []

    def test_parse_chapter_content_by_id(self):
        html = '''
        <html><body>
        <div id="content"><p>这是章节内容，足够长以满足最低长度要求，需要超过五十字才能被正确返回给调用方使用，确保解析逻辑正常工作无误。</p></div>
        </body></html>'''
        result = self.parser.parse_chapter_content(html)
        assert '这是章节内容' in result['content']

    def test_parse_chapter_content_by_class(self):
        html = '''
        <html><body>
        <div class="chapter-content"><p>这是通过class选择器提取的章节内容，需要足够长以满足最低长度要求，超过五十字才能被正确返回给调用方。</p></div>
        </body></html>'''
        result = self.parser.parse_chapter_content(html)
        assert '通过class选择器' in result['content']

    def test_parse_chapter_content_too_short(self):
        html = '''
        <html><body>
        <div id="content"><p>短</p></div>
        </body></html>'''
        result = self.parser.parse_chapter_content(html)
        assert result['content'] == ''

    def test_parse_chapter_content_no_match(self):
        html = '<html><body><p>无内容容器</p></body></html>'
        result = self.parser.parse_chapter_content(html)
        assert result['content'] == ''

    def test_clean_content_removes_scripts(self):
        html = '''
        <html><body>
        <div id="content">
            <script>alert('xss')</script>
            <style>.hidden{display:none}</style>
            <p>正文内容需要足够长来通过长度检查，确保脚本和样式已被移除，这段文字必须超过五十字才能被返回给调用方使用。</p>
        </div>
        </body></html>'''
        result = self.parser.parse_chapter_content(html)
        assert 'alert' not in result['content']
        assert 'hidden' not in result['content']
        assert '正文内容' in result['content']

    def test_clean_content_no_paragraphs(self):
        html = '''
        <html><body>
        <div id="content">纯文本内容没有段落标签但足够长来通过最低长度检查要求返回给调用方使用确保正确提取文本内容无误通过验证。</div>
        </body></html>'''
        result = self.parser.parse_chapter_content(html)
        assert '纯文本内容' in result['content']

    def test_parse_book_info(self):
        html = '<html><body><h1>我的小说</h1></body></html>'
        result = self.parser.parse_book_info(html)
        assert result['title'] == '我的小说'

    def test_parse_book_info_no_h1(self):
        html = '<html><body><p>无标题</p></body></html>'
        result = self.parser.parse_book_info(html)
        assert result['title'] == ''


class TestCrawlerEngine:
    def test_safe_filename_normal(self):
        engine = CrawlerEngine(1, '/tmp/books')
        assert engine._safe_filename('正常书名') == '正常书名'

    def test_safe_filename_special_chars(self):
        engine = CrawlerEngine(1, '/tmp/books')
        result = engine._safe_filename('书名/包含\\特殊:字符*?<>|')
        assert '/' not in result
        assert '\\' not in result
        assert ':' not in result

    def test_safe_filename_truncation(self):
        engine = CrawlerEngine(1, '/tmp/books')
        long_name = '很长的书名' * 50
        result = engine._safe_filename(long_name)
        assert len(result) <= 100

    def test_safe_filename_empty(self):
        engine = CrawlerEngine(1, '/tmp/books')
        assert engine._safe_filename('') == 'unnamed'

    def test_safe_filename_dots_only(self):
        engine = CrawlerEngine(1, '/tmp/books')
        assert engine._safe_filename('...') == 'unnamed'

    def test_get_ua_rotation(self):
        engine = CrawlerEngine(1, '/tmp/books')
        ua1 = engine._get_ua()
        ua2 = engine._get_ua()
        assert ua1 != ua2

    def test_stop_flag(self):
        engine = CrawlerEngine(1, '/tmp/books')
        assert engine._stop is False
        engine.stop()
        assert engine._stop is True

    @patch('utils.crawler_engine.validate_crawl_url', return_value=False)
    def test_run_rejects_invalid_url(self, mock_validate):
        engine = CrawlerEngine(1, '/tmp/books')
        task = MagicMock()
        task.url = 'http://evil.internal/'
        task.id = 1
        engine.run(task)
        task.save.assert_called()
        assert task.status == 'failed'
        assert '禁止访问' in task.error_message
