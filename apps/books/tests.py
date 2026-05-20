import os
import tempfile
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.cache import cache
from .models import Book
from apps.chapters.models import Chapter


class BookModelTest(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title='测试书籍',
            author='测试作者',
            description='测试简介',
            folder_path='data/books/test_book'
        )

    def test_book_str(self):
        """测试书籍模型字符串表示"""
        self.assertEqual(str(self.book), '测试书籍')

    def test_book_cover_gradient(self):
        """测试书籍封面渐变色属性"""
        gradient = self.book.cover_gradient
        self.assertIsInstance(gradient, tuple)
        self.assertEqual(len(gradient), 2)
        self.assertTrue(all(isinstance(c, str) and c.startswith('#') for c in gradient))

    def test_book_cover_gradient_with_none_id(self):
        """测试未保存书籍的封面渐变色"""
        new_book = Book(title='未保存')
        gradient = new_book.cover_gradient
        self.assertEqual(gradient[0], '#667eea')

    def test_book_chapter_count(self):
        """测试书籍章节计数属性"""
        self.assertEqual(self.book.chapter_count, 0)
        Chapter.objects.create(
            book=self.book,
            chapter_number=1,
            title='第一章',
            file_path='data/books/test_book/ch1.txt'
        )
        self.assertEqual(self.book.chapter_count, 1)

    def test_book_meta_options(self):
        """测试书籍模型元选项"""
        self.assertEqual(Book._meta.verbose_name, '书籍')
        self.assertEqual(Book._meta.ordering, ['-created_at'])


class BookViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.book = Book.objects.create(
            title='测试书籍',
            author='测试作者',
            folder_path='data/books/test_book'
        )
        cache.clear()

    def test_home_view(self):
        """测试首页视图"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertIn('recent_books', response.context)

    def test_home_view_with_authenticated_user(self):
        """测试首页视图（已登录用户）"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('reading_count', response.context)
        self.assertIn('favorite_count', response.context)

    def test_home_view_exception_handling(self):
        """测试首页异常处理"""
        Book.objects.all().delete()
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_books'], 0)

    def test_book_list_view(self):
        """测试书籍列表视图"""
        response = self.client.get(reverse('book_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/list.html')
        self.assertIn('page_obj', response.context)

    def test_book_list_view_with_search(self):
        """测试书籍列表搜索功能"""
        response = self.client.get(reverse('book_list') + '?q=测试')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['search_query'], '测试')

    def test_book_list_view_pagination(self):
        """测试书籍列表分页"""
        for i in range(15):
            Book.objects.create(
                title=f'书籍{i}',
                folder_path=f'data/books/book{i}'
            )
        response = self.client.get(reverse('book_list') + '?page=2')
        self.assertEqual(response.status_code, 200)

    def test_book_detail_view(self):
        """测试书籍详情视图"""
        response = self.client.get(reverse('book_detail', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/detail.html')
        self.assertEqual(response.context['book'], self.book)

    def test_book_detail_view_not_found(self):
        """测试书籍详情404"""
        response = self.client.get(reverse('book_detail', kwargs={'pk': 99999}))
        self.assertEqual(response.status_code, 404)

    def test_book_detail_view_with_favorite_cache(self):
        """测试书籍详情收藏缓存"""
        self.client.login(username='testuser', password='testpass123')
        from apps.favorites.models import Favorite
        Favorite.objects.create(user=self.user, book=self.book)

        response = self.client.get(reverse('book_detail', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_favorited'])

        cached_value = cache.get(f'fav:{self.user.id}:{self.book.id}')
        self.assertTrue(cached_value)

    def test_book_add_view_requires_login(self):
        """测试添加书籍需要登录"""
        response = self.client.get(reverse('book_add'))
        self.assertEqual(response.status_code, 302)

    def test_book_add_view_post_valid(self):
        """测试有效添加书籍"""
        self.client.login(username='testuser', password='testpass123')
        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(BOOKS_DIR=tmpdir):
                response = self.client.post(reverse('book_add'), {
                    'title': '新书籍',
                    'author': '新作者',
                    'description': '新简介'
                })
                self.assertRedirects(response, reverse('book_list'))
                self.assertTrue(Book.objects.filter(title='新书籍').exists())

    def test_book_add_view_post_invalid(self):
        """测试无效表单添加书籍"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('book_add'), {
            'title': '',
            'author': '作者'
        })
        self.assertRedirects(response, reverse('book_list'))

    def test_book_add_view_special_chars_in_title(self):
        """测试书名包含特殊字符处理"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('book_add'), {
            'title': '书籍<测试>/\\:*?"<>|',
            'author': '作者'
        })
        self.assertEqual(response.status_code, 302)
        book = Book.objects.get(title='书籍<测试>/\\:*?"<>|')
        self.assertIn('_', book.folder_path)

    def test_book_delete_view_requires_login(self):
        """测试删除书籍需要登录"""
        response = self.client.post(reverse('book_delete', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.status_code, 302)

    def test_book_delete_view_post(self):
        """测试删除书籍"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('book_delete', kwargs={'pk': self.book.pk}))
        self.assertRedirects(response, reverse('book_list'))
        self.assertFalse(Book.objects.filter(pk=self.book.pk).exists())

    def test_book_delete_view_get_redirects(self):
        """测试GET请求删除重定向到详情页"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('book_delete', kwargs={'pk': self.book.pk}))
        self.assertRedirects(response, reverse('book_detail', kwargs={'pk': self.book.pk}))


class BookFormTest(TestCase):
    def test_book_form_valid(self):
        """测试书籍表单验证"""
        from .forms import BookForm
        form = BookForm(data={
            'title': '测试书籍',
            'author': '测试作者',
            'description': '测试简介'
        })
        self.assertTrue(form.is_valid())

    def test_book_form_empty_title(self):
        """测试空书名表单"""
        from .forms import BookForm
        form = BookForm(data={
            'title': '',
            'author': '作者'
        })
        self.assertFalse(form.is_valid())
