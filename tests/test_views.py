import json
from unittest.mock import patch, MagicMock

import pytest
from django.test import Client, TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from apps.books.models import Book
from apps.chapters.models import Chapter
from apps.favorites.models import Favorite
from apps.reader.models import ReadingProgress


class TestAccountsViews:
    def test_login_page_renders(self, client):
        resp = client.get(reverse('login'))
        assert resp.status_code == 200

    def test_login_with_valid_credentials(self, client, user):
        resp = client.post(reverse('login'), {'username': 'testuser', 'password': 'testpass123'})
        assert resp.status_code == 302

    def test_login_with_invalid_credentials(self, client, user):
        resp = client.post(reverse('login'), {'username': 'testuser', 'password': 'wrongpass'})
        assert resp.status_code == 200

    def test_login_redirect_if_authenticated(self, auth_client):
        resp = auth_client.get(reverse('login'))
        assert resp.status_code == 302

    def test_login_with_next_param(self, client, user):
        resp = client.post(reverse('login') + '?next=/books/', {'username': 'testuser', 'password': 'testpass123'})
        assert resp.status_code == 302
        assert '/books/' in resp.url

    def test_login_rejects_invalid_next_url(self, client, user):
        resp = client.post(reverse('login') + '?next=http://evil.com/', {'username': 'testuser', 'password': 'testpass123'})
        assert resp.status_code == 302
        assert 'evil.com' not in resp.url

    def test_register_page_renders(self, client):
        resp = client.get(reverse('register'))
        assert resp.status_code == 200

    def test_register_new_user(self, client, db):
        resp = client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'Str0ng!Pass123',
            'password2': 'Str0ng!Pass123',
        })
        assert resp.status_code == 302
        assert User.objects.filter(username='newuser').exists()

    def test_register_redirect_if_authenticated(self, auth_client):
        resp = auth_client.get(reverse('register'))
        assert resp.status_code == 302

    def test_logout_requires_post(self, auth_client):
        resp = auth_client.get(reverse('logout'))
        assert resp.status_code == 405

    def test_logout_with_post(self, auth_client):
        resp = auth_client.post(reverse('logout'))
        assert resp.status_code == 302


class TestBooksViews:
    def test_home_page(self, client, book):
        resp = client.get(reverse('home'))
        assert resp.status_code == 200

    def test_home_page_with_auth_user(self, auth_client, book):
        resp = auth_client.get(reverse('home'))
        assert resp.status_code == 200

    def test_book_list(self, client, book):
        resp = client.get(reverse('book_list'))
        assert resp.status_code == 200
        assert '测试小说' in resp.content.decode()

    def test_book_list_search(self, client, book):
        resp = client.get(reverse('book_list'), {'q': '测试'})
        assert resp.status_code == 200
        assert '测试小说' in resp.content.decode()

    def test_book_list_search_no_results(self, client, book):
        resp = client.get(reverse('book_list'), {'q': '不存在的书名'})
        assert resp.status_code == 200

    def test_book_detail(self, client, book):
        resp = client.get(reverse('book_detail', kwargs={'pk': book.pk}))
        assert resp.status_code == 200

    def test_book_detail_not_found(self, client, db):
        resp = client.get(reverse('book_detail', kwargs={'pk': 9999}))
        assert resp.status_code == 404

    def test_book_add_requires_login(self, client):
        resp = client.post(reverse('book_add'), {'title': '新书'})
        assert resp.status_code == 302
        assert 'login' in resp.url

    def test_book_add_authenticated(self, auth_client, db):
        resp = auth_client.post(reverse('book_add'), {
            'title': '新增小说',
            'author': '新作者',
            'description': '新描述',
        })
        assert resp.status_code == 302
        assert Book.objects.filter(title='新增小说').exists()

    def test_book_add_invalid_form(self, auth_client, db):
        resp = auth_client.post(reverse('book_add'), {})
        assert resp.status_code == 302

    def test_book_delete_requires_login(self, client, book):
        resp = client.post(reverse('book_delete', kwargs={'pk': book.pk}))
        assert resp.status_code == 302
        assert 'login' in resp.url

    def test_book_delete_with_post(self, auth_client, book):
        resp = auth_client.post(reverse('book_delete', kwargs={'pk': book.pk}))
        assert resp.status_code == 302
        assert not Book.objects.filter(pk=book.pk).exists()

    def test_book_delete_get_redirects(self, auth_client, book):
        resp = auth_client.get(reverse('book_delete', kwargs={'pk': book.pk}))
        assert resp.status_code == 302


class TestChaptersViews:
    def test_chapter_read(self, client, book, chapter):
        resp = client.get(reverse('chapter_read', kwargs={'book_id': book.pk, 'chapter_id': chapter.pk}))
        assert resp.status_code == 200

    def test_chapter_read_shows_content(self, client, book, chapter):
        resp = client.get(reverse('chapter_read', kwargs={'book_id': book.pk, 'chapter_id': chapter.pk}))
        content = resp.content.decode()
        assert '测试章节' in content or '测试内容' in content

    def test_chapter_read_not_found(self, client, book, db):
        resp = client.get(reverse('chapter_read', kwargs={'book_id': book.pk, 'chapter_id': 9999}))
        assert resp.status_code == 404

    def test_save_progress_requires_login(self, client, book, chapter):
        resp = client.post(reverse('save_progress', kwargs={'book_id': book.pk}), {
            'chapter_id': chapter.pk,
            'position': 50,
        })
        assert resp.status_code == 302

    def test_save_progress_requires_post(self, auth_client, book, chapter):
        resp = auth_client.get(reverse('save_progress', kwargs={'book_id': book.pk}))
        assert resp.status_code == 405

    def test_save_progress_authenticated(self, auth_client, book, chapter):
        resp = auth_client.post(reverse('save_progress', kwargs={'book_id': book.pk}), {
            'chapter_id': chapter.pk,
            'position': 50,
        })
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data['status'] == 'ok'
        assert ReadingProgress.objects.filter(user__username='testuser', book=book).exists()

    def test_save_progress_invalid_position(self, auth_client, book, chapter):
        resp = auth_client.post(reverse('save_progress', kwargs={'book_id': book.pk}), {
            'chapter_id': chapter.pk,
            'position': 'not_a_number',
        })
        assert resp.status_code == 200
        progress = ReadingProgress.objects.filter(user__username='testuser', book=book).first()
        assert progress is not None
        assert progress.position == 0

    def test_read_chapter_content_file_not_found(self, client, book, db):
        chapter = Chapter.objects.create(
            book=book, chapter_number=99, title='不存在文件',
            file_path='/nonexistent/path.txt', word_count=0,
        )
        resp = client.get(reverse('chapter_read', kwargs={'book_id': book.pk, 'chapter_id': chapter.pk}))
        assert resp.status_code == 200


class TestFavoritesViews:
    def test_favorite_list_requires_login(self, client):
        resp = client.get(reverse('favorite_list'))
        assert resp.status_code == 302

    def test_favorite_list_authenticated(self, auth_client, book):
        resp = auth_client.get(reverse('favorite_list'))
        assert resp.status_code == 200

    def test_favorite_toggle_add(self, auth_client, book):
        resp = auth_client.post(reverse('favorite_toggle'), {'book_id': book.pk})
        assert resp.status_code == 302
        assert Favorite.objects.filter(user__username='testuser', book=book).exists()

    def test_favorite_toggle_remove(self, auth_client, book):
        Favorite.objects.create(user=User.objects.get(username='testuser'), book=book)
        resp = auth_client.post(reverse('favorite_toggle'), {'book_id': book.pk})
        assert resp.status_code == 302
        assert not Favorite.objects.filter(user__username='testuser', book=book).exists()

    def test_favorite_toggle_requires_login(self, client, book):
        resp = client.post(reverse('favorite_toggle'), {'book_id': book.pk})
        assert resp.status_code == 302

    def test_favorite_toggle_requires_post(self, auth_client, book):
        resp = auth_client.get(reverse('favorite_toggle'), {'book_id': book.pk})
        assert resp.status_code == 405

    def test_favorite_toggle_with_valid_next(self, auth_client, book):
        resp = auth_client.post(reverse('favorite_toggle'), {
            'book_id': book.pk,
            'next': f'/books/{book.pk}/',
        })
        assert resp.status_code == 302

    def test_favorite_toggle_rejects_invalid_next(self, auth_client, book):
        resp = auth_client.post(reverse('favorite_toggle'), {
            'book_id': book.pk,
            'next': 'http://evil.com/',
        })
        assert resp.status_code == 302
        assert 'evil.com' not in resp.url


class TestCrawlerViews:
    def test_crawler_tasks_requires_login(self, client):
        resp = client.get(reverse('crawler_tasks'))
        assert resp.status_code == 302

    def test_crawler_tasks_authenticated(self, auth_client):
        resp = auth_client.get(reverse('crawler_tasks'))
        assert resp.status_code == 200

    def test_create_task_requires_login(self, client):
        resp = client.post(reverse('create_task'), {'url': 'http://example.com'})
        assert resp.status_code == 302

    def test_create_task_requires_post(self, auth_client):
        resp = auth_client.get(reverse('create_task'))
        assert resp.status_code == 405

    def test_create_task_empty_url(self, auth_client):
        resp = auth_client.post(reverse('create_task'), {'url': ''})
        assert resp.status_code == 302

    @patch('utils.crawler_engine.CrawlerEngine.run')
    def test_create_task_valid_url(self, mock_run, auth_client):
        resp = auth_client.post(reverse('create_task'), {'url': 'http://example.com/novel'})
        assert resp.status_code == 302
        from apps.crawler.models import CrawlerTask
        assert CrawlerTask.objects.filter(user__username='testuser').exists()

    def test_task_detail_requires_login(self, client, db):
        resp = client.get(reverse('task_detail', kwargs={'pk': 1}))
        assert resp.status_code == 302

    def test_task_detail_other_user_forbidden(self, db):
        user1 = User.objects.create_user('user1', password='pass123')
        user2 = User.objects.create_user('user2', password='pass123')
        from apps.crawler.models import CrawlerTask
        task = CrawlerTask.objects.create(user=user1, url='http://example.com')
        c = Client()
        c.force_login(user2)
        resp = c.get(reverse('task_detail', kwargs={'pk': task.pk}))
        assert resp.status_code == 404


class TestSearchView:
    def test_search_empty_query(self, client, book):
        resp = client.get(reverse('search'), {'q': ''})
        assert resp.status_code == 200

    def test_search_with_results(self, client, book):
        resp = client.get(reverse('search'), {'q': '测试'})
        assert resp.status_code == 200

    def test_search_no_results(self, client, book):
        resp = client.get(reverse('search'), {'q': '不存在的书'})
        assert resp.status_code == 200

    def test_search_suggestions(self, client, book):
        resp = client.get(reverse('search'), {'q': '测试'})
        assert resp.status_code == 200

    def test_search_short_query_no_suggestions(self, client, book):
        resp = client.get(reverse('search'), {'q': '测'})
        assert resp.status_code == 200
