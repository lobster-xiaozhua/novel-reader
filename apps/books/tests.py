import os
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Book, Tag, BookTag
import django.test.client


# Monkey patch store_rendered_templates to be a no-op to prevent copy errors
def no_op_store_rendered_templates(*args, **kwargs):
    pass


django.test.client.store_rendered_templates = no_op_store_rendered_templates


class BookModelTest(TestCase):
    def test_book_creation(self):
        book = Book.objects.create(
            title='Test Book',
            author='Test Author',
            folder_path='data/books/test_book',
            description='This is a test book'
        )
        self.assertEqual(book.title, 'Test Book')
        self.assertEqual(book.author, 'Test Author')
        self.assertEqual(str(book), 'Test Book')


class BookViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        self.book = Book.objects.create(
            title='Test Book',
            author='Test Author',
            folder_path='data/books/test_book'
        )

    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_book_list_view(self):
        response = self.client.get(reverse('book_list'))
        self.assertEqual(response.status_code, 200)

    def test_book_detail_view(self):
        response = self.client.get(reverse('book_detail', args=[self.book.pk]))
        self.assertEqual(response.status_code, 200)

    def test_book_add_view_get(self):
        response = self.client.get(reverse('book_add'))
        self.assertEqual(response.status_code, 200)

    def test_book_add_view_post(self):
        response = self.client.post(reverse('book_add'), {
            'title': 'New Book',
            'author': 'New Author',
            'description': 'New Description'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Book.objects.filter(title='New Book').exists())
        # Clean up created directory
        book = Book.objects.get(title='New Book')
        if os.path.exists(book.folder_path):
            os.rmdir(book.folder_path)

    def test_book_delete_view(self):
        response = self.client.post(reverse('book_delete', args=[self.book.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Book.objects.filter(pk=self.book.pk).exists())
