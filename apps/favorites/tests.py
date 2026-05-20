from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from apps.books.models import Book
from .models import Favorite, FavoriteFolder


class FavoriteModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.book = Book.objects.create(
            title='测试书籍',
            folder_path='data/books/test_book'
        )

    def test_favorite_str(self):
        """测试收藏模型字符串表示"""
        favorite = Favorite.objects.create(user=self.user, book=self.book)
        expected = f'{self.user.username} - {self.book.title}'
        self.assertEqual(str(favorite), expected)

    def test_favorite_unique_together(self):
        """测试收藏唯一约束"""
        Favorite.objects.create(user=self.user, book=self.book)
        with self.assertRaises(Exception):
            Favorite.objects.create(user=self.user, book=self.book)

    def test_favorite_folder_str(self):
        """测试收藏夹模型字符串表示"""
        folder = FavoriteFolder.objects.create(
            user=self.user,
            name='我的收藏夹',
            color='#ff0000'
        )
        self.assertEqual(str(folder), '我的收藏夹')

    def test_favorite_with_folder(self):
        """测试带收藏夹的收藏"""
        folder = FavoriteFolder.objects.create(
            user=self.user,
            name='我的收藏夹'
        )
        favorite = Favorite.objects.create(
            user=self.user,
            book=self.book,
            folder=folder,
            notes='测试备注'
        )
        self.assertEqual(favorite.folder, folder)
        self.assertEqual(favorite.notes, '测试备注')


class FavoriteViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        self.book = Book.objects.create(
            title='测试书籍',
            folder_path='data/books/test_book'
        )

    def test_favorite_list_requires_login(self):
        """测试收藏列表需要登录"""
        response = self.client.get(reverse('favorite_list'))
        self.assertEqual(response.status_code, 302)

    def test_favorite_list_view(self):
        """测试收藏列表视图"""
        self.client.login(username='testuser', password='testpass123')
        Favorite.objects.create(user=self.user, book=self.book)

        response = self.client.get(reverse('favorite_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'favorites/list.html')
        self.assertEqual(len(response.context['favorites']), 1)

    def test_favorite_list_only_show_own(self):
        """测试收藏列表只显示自己的收藏"""
        self.client.login(username='testuser', password='testpass123')
        Favorite.objects.create(user=self.user, book=self.book)
        Favorite.objects.create(user=self.other_user, book=self.book)

        response = self.client.get(reverse('favorite_list'))
        self.assertEqual(len(response.context['favorites']), 1)

    def test_favorite_toggle_requires_login(self):
        """测试收藏切换需要登录"""
        response = self.client.post(reverse('favorite_toggle'), {
            'book_id': self.book.pk
        })
        self.assertEqual(response.status_code, 302)

    def test_favorite_toggle_add(self):
        """测试添加收藏"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('favorite_toggle'), {
            'book_id': self.book.pk
        })
        self.assertRedirects(response, reverse('book_detail', kwargs={'pk': self.book.pk}))
        self.assertTrue(Favorite.objects.filter(user=self.user, book=self.book).exists())

    def test_favorite_toggle_remove(self):
        """测试取消收藏"""
        self.client.login(username='testuser', password='testpass123')
        Favorite.objects.create(user=self.user, book=self.book)

        response = self.client.post(reverse('favorite_toggle'), {
            'book_id': self.book.pk
        })
        self.assertRedirects(response, reverse('book_detail', kwargs={'pk': self.book.pk}))
        self.assertFalse(Favorite.objects.filter(user=self.user, book=self.book).exists())

    def test_favorite_toggle_with_next_url(self):
        """测试收藏切换后重定向到next URL"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('favorite_toggle'), {
            'book_id': self.book.pk,
            'next': '/books/'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/books/')

    def test_favorite_toggle_with_invalid_next(self):
        """测试收藏切换时无效next URL的安全处理"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('favorite_toggle'), {
            'book_id': self.book.pk,
            'next': 'http://evil.com'
        })
        self.assertRedirects(response, reverse('book_detail', kwargs={'pk': self.book.pk}))

    def test_favorite_toggle_requires_post(self):
        """测试收藏切换只接受POST"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('favorite_toggle'))
        self.assertEqual(response.status_code, 405)

    def test_favorite_toggle_book_not_found(self):
        """测试收藏不存在的书籍"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('favorite_toggle'), {
            'book_id': 99999
        })
        self.assertEqual(response.status_code, 404)
