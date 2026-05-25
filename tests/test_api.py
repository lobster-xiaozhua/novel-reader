import json
from datetime import timedelta
from unittest.mock import patch

import jwt as pyjwt
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.utils import timezone

from apps.api.auth import (
    JWT_ALGORITHM,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_from_token,
    JWTAuth,
    OptionalJWTAuth,
)
from apps.books.models import Book, Tag
from apps.chapters.models import Chapter
from apps.favorites.models import Favorite
from apps.reader.models import ReadingProgress, ReadingStats
from apps.crawler.models import CrawlerTask
from utils.crawler_config import SiteConfig, get_config_for_url, DEFAULT_CONFIG
from utils.crawler_engine import validate_crawl_url, IntelligentParser
from utils.book_gradient import get_book_gradient


class JWTAuthTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_create_access_token(self):
        token = create_access_token(self.user.id)
        self.assertIsInstance(token, str)
        payload = decode_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload['sub'], str(self.user.id))
        self.assertEqual(payload['type'], 'access')

    def test_create_refresh_token(self):
        token = create_refresh_token(self.user.id)
        payload = decode_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload['type'], 'refresh')

    def test_decode_invalid_token(self):
        self.assertIsNone(decode_token('invalid.token.here'))

    def test_get_user_from_access_token(self):
        token = create_access_token(self.user.id)
        user = get_user_from_token(token, 'access')
        self.assertEqual(user.id, self.user.id)

    def test_get_user_from_refresh_token_fails_for_access_type(self):
        token = create_refresh_token(self.user.id)
        user = get_user_from_token(token, 'access')
        self.assertIsNone(user)

    def test_get_user_nonexistent(self):
        token = create_access_token(99999)
        user = get_user_from_token(token, 'access')
        self.assertIsNone(user)

    def test_jwt_auth_class(self):
        auth = JWTAuth()
        token = create_access_token(self.user.id)
        request = type('Request', (), {
            'META': {'HTTP_AUTHORIZATION': f'Bearer {token}'},
            'COOKIES': {},
        })()
        result = auth(request)
        self.assertEqual(result.id, self.user.id)

    def test_jwt_auth_no_token(self):
        auth = JWTAuth()
        request = type('Request', (), {'META': {}, 'COOKIES': {}})()
        result = auth(request)
        self.assertIsNone(result)

    def test_optional_jwt_auth_returns_true_when_no_token(self):
        auth = OptionalJWTAuth()
        request = type('Request', (), {'META': {}, 'COOKIES': {}})()
        result = auth(request)
        self.assertTrue(result)

    def test_token_from_cookie(self):
        auth = JWTAuth()
        token = create_access_token(self.user.id)
        request = type('Request', (), {
            'META': {},
            'COOKIES': {'access_token': token},
        })()
        result = auth(request)
        self.assertEqual(result.id, self.user.id)


class AuthAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_login_success(self):
        res = self.client.post('/api/v1/auth/login/', data=json.dumps({
            'username': 'testuser', 'password': 'testpass123'
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)
        self.assertEqual(data['user']['username'], 'testuser')

    def test_login_wrong_password(self):
        res = self.client.post('/api/v1/auth/login/', data=json.dumps({
            'username': 'testuser', 'password': 'wrongpass'
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data['success'])
        self.assertIn('错误', data['error'])

    def test_register_success(self):
        res = self.client.post('/api/v1/auth/register/', data=json.dumps({
            'username': 'newuser', 'password': 'newpass123'
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertIn('access_token', data)

    def test_register_duplicate(self):
        res = self.client.post('/api/v1/auth/register/', data=json.dumps({
            'username': 'testuser', 'password': 'testpass123'
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data['success'])
        self.assertIn('已存在', data['error'])

    def test_me_authenticated(self):
        token = create_access_token(self.user.id)
        res = self.client.get('/api/v1/auth/me/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['username'], 'testuser')

    def test_me_unauthenticated(self):
        res = self.client.get('/api/v1/auth/me/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data['success'])

    def test_refresh_token(self):
        res = self.client.post('/api/v1/auth/login/', data=json.dumps({
            'username': 'testuser', 'password': 'testpass123'
        }), content_type='application/json')
        refresh_token = res.json()['refresh_token']
        res2 = self.client.post('/api/v1/auth/refresh/', data=json.dumps({
            'refresh_token': refresh_token
        }), content_type='application/json')
        self.assertEqual(res2.status_code, 200)
        data = res2.json()
        self.assertTrue(data['success'])
        self.assertIn('access_token', data)

    def test_refresh_invalid_token(self):
        res = self.client.post('/api/v1/auth/refresh/', data=json.dumps({
            'refresh_token': 'invalid'
        }), content_type='application/json')
        self.assertEqual(res.status_code, 401)

    def test_logout(self):
        token = create_access_token(self.user.id)
        res = self.client.post('/api/v1/auth/logout/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 200)


class HealthAPITest(TestCase):
    def test_health_check(self):
        res = self.client.get('/api/v1/health/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['version'], '2.0.0')


class BooksAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bookuser', password='testpass123')
        self.token = create_access_token(self.user.id)
        self.book = Book.objects.create(
            title='测试书籍', author='测试作者', category='玄幻',
            folder_path='data/books/test_book', total_chapters=2
        )
        self.chapter1 = Chapter.objects.create(
            book=self.book, chapter_number=1, title='第一章',
            file_path='data/books/test_book/第1章.txt', word_count=1000
        )

    def test_list_books(self):
        res = self.client.get('/api/v1/books/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('items', data)

    def test_list_books_search(self):
        res = self.client.get('/api/v1/books/?search=测试')
        self.assertEqual(res.status_code, 200)

    def test_get_book_detail(self):
        res = self.client.get(f'/api/v1/books/{self.book.id}/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['title'], '测试书籍')

    def test_get_book_not_found(self):
        res = self.client.get('/api/v1/books/99999/')
        self.assertEqual(res.status_code, 404)

    def test_list_chapters(self):
        res = self.client.get(f'/api/v1/books/{self.book.id}/chapters/')
        self.assertEqual(res.status_code, 200)

    def test_chapters_not_found_book(self):
        res = self.client.get('/api/v1/books/99999/chapters/')
        self.assertEqual(res.status_code, 404)

    def test_search_books(self):
        res = self.client.get('/api/v1/search/?q=测试')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data['total'], 0)

    def test_search_empty(self):
        res = self.client.get('/api/v1/search/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['total'], 0)


class ProgressAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='progressuser', password='testpass123')
        self.token = create_access_token(self.user.id)
        self.book = Book.objects.create(
            title='进度书', author='作者', folder_path='data/books/progress_book', total_chapters=10
        )
        self.chapter = Chapter.objects.create(
            book=self.book, chapter_number=1, title='第一章',
            file_path='data/books/progress_book/第1章.txt', word_count=500
        )

    def test_list_progress_unauthenticated(self):
        res = self.client.get('/api/v1/progress/')
        self.assertEqual(res.status_code, 401)

    def test_create_progress(self):
        res = self.client.post('/api/v1/progress/', data=json.dumps({
            'book_id': self.book.id, 'chapter_id': self.chapter.id, 'position': 5
        }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['position'], 5)

    def test_list_progress_authenticated(self):
        ReadingProgress.objects.create(user=self.user, book=self.book, chapter=self.chapter, position=3)
        res = self.client.get('/api/v1/progress/', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)

    def test_track_stats(self):
        res = self.client.post('/api/v1/progress/track-stats/', data=json.dumps({
            'seconds': 60, 'chapter_id': self.chapter.id
        }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)

    def test_track_stats_too_short(self):
        res = self.client.post('/api/v1/progress/track-stats/', data=json.dumps({
            'seconds': 2
        }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)


class TagsAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='taguser', password='testpass123')
        self.token = create_access_token(self.user.id)

    def test_list_tags(self):
        res = self.client.get('/api/v1/tags/')
        self.assertEqual(res.status_code, 200)

    def test_create_tag(self):
        res = self.client.post('/api/v1/tags/', data=json.dumps({
            'name': '测试标签', 'color': '#ff0000'
        }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['name'], '测试标签')

    def test_create_tag_unauthenticated(self):
        res = self.client.post('/api/v1/tags/', data=json.dumps({
            'name': '测试', 'color': '#ff0000'
        }), content_type='application/json')
        self.assertEqual(res.status_code, 401)

    def test_delete_tag(self):
        tag = Tag.objects.create(name='删除标签', color='#00ff00')
        res = self.client.delete(f'/api/v1/tags/{tag.id}/', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())


class FavoritesAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='favuser', password='testpass123')
        self.token = create_access_token(self.user.id)
        self.book = Book.objects.create(
            title='收藏书', author='作者', folder_path='data/books/fav_book'
        )

    def test_toggle_favorite_add(self):
        res = self.client.post('/api/v1/favorites/toggle/', data=json.dumps({
            'book_id': self.book.id
        }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Favorite.objects.filter(user=self.user, book=self.book).exists())

    def test_toggle_favorite_remove(self):
        Favorite.objects.create(user=self.user, book=self.book)
        res = self.client.post('/api/v1/favorites/toggle/', data=json.dumps({
            'book_id': self.book.id
        }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Favorite.objects.filter(user=self.user, book=self.book).exists())

    def test_list_favorites(self):
        Favorite.objects.create(user=self.user, book=self.book)
        res = self.client.get('/api/v1/favorites/', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)

    def test_favorites_unauthenticated(self):
        res = self.client.get('/api/v1/favorites/')
        self.assertEqual(res.status_code, 401)


class CrawlerAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='crawleruser', password='testpass123')
        self.token = create_access_token(self.user.id)

    def test_list_crawler_tasks(self):
        res = self.client.get('/api/v1/crawler/', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)

    def test_crawler_unauthenticated(self):
        res = self.client.get('/api/v1/crawler/')
        self.assertEqual(res.status_code, 401)


class UsersAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='adminuser', password='testpass123', is_staff=True)
        self.token = create_access_token(self.user.id)

    def test_list_users(self):
        res = self.client.get('/api/v1/users/', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)

    def test_list_users_unauthenticated(self):
        res = self.client.get('/api/v1/users/')
        self.assertEqual(res.status_code, 401)


class StatsAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='statsuser', password='testpass123')
        self.token = create_access_token(self.user.id)

    def test_get_stats(self):
        res = self.client.get('/api/v1/stats/', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('total_books', data)
        self.assertIn('chart', data)

    def test_stats_unauthenticated(self):
        res = self.client.get('/api/v1/stats/')
        self.assertEqual(res.status_code, 401)

    def test_dashboard(self):
        res = self.client.get('/api/v1/dashboard/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('total_books', data)
        self.assertIn('category_stats', data)


class CrawlerConfigTest(TestCase):
    def test_default_config(self):
        self.assertEqual(DEFAULT_CONFIG.name, 'default')
        self.assertEqual(DEFAULT_CONFIG.domain, '*')
        self.assertTrue(len(DEFAULT_CONFIG.content_selectors) > 0)

    def test_get_config_for_url(self):
        config = get_config_for_url('https://example.com/some/path')
        self.assertEqual(config.name, 'Example Novel Site')
        config2 = get_config_for_url('https://unknown-site.com')
        self.assertEqual(config2.name, 'default')

    def test_validate_crawl_url(self):
        self.assertTrue(validate_crawl_url('https://example.com'))
        self.assertFalse(validate_crawl_url('http://localhost:8000'))
        self.assertFalse(validate_crawl_url('http://127.0.0.1'))
        self.assertFalse(validate_crawl_url('ftp://example.com'))
        self.assertFalse(validate_crawl_url('invalid-url'))


class IntelligentParserTest(TestCase):
    def setUp(self):
        self.config = SiteConfig(
            name='test', domain='test.com',
            content_selectors=['.content', '#test-content', 'article'],
            chapter_list_selectors=['.chapter-list', '#chapter-list']
        )
        self.parser = IntelligentParser(self.config)

    def test_clean_content(self):
        long_text_1 = '第一段内容' * 10
        long_text_2 = '第二段内容' * 10
        html = f'<article><p>{long_text_1}</p><p>{long_text_2}</p><script>alert("x")</script></article>'
        result = self.parser.parse_chapter_content(html)
        self.assertIn('第一段', result['content'])
        self.assertIn('第二段', result['content'])

    def test_parse_chapter_list(self):
        html = '<div class="chapter-list"><a href="/chapter/1">第一章 开始</a><a href="/chapter/2">第二章 发展</a></div>'
        chapters = self.parser.parse_chapter_list(html, 'https://test.com')
        self.assertGreaterEqual(len(chapters), 2)


class BookGradientTest(TestCase):
    def test_gradient_returns_tuple(self):
        result = get_book_gradient(0)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_gradient_deterministic(self):
        self.assertEqual(get_book_gradient(1), get_book_gradient(1))

    def test_gradient_wraps(self):
        self.assertEqual(get_book_gradient(0), get_book_gradient(8))
