from django.test import TestCase
from django.contrib.auth.models import User
from apps.books.models import Book
from .models import FavoriteFolder, Favorite


class FavoritesModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.book = Book.objects.create(
            title='Test Book',
            author='Test Author',
            folder_path='data/books/test_book'
        )

    def test_favorite_folder_creation(self):
        folder = FavoriteFolder.objects.create(
            user=self.user,
            name='Test Folder'
        )
        self.assertEqual(folder.name, 'Test Folder')
        self.assertEqual(str(folder), 'Test Folder')

    def test_favorite_creation(self):
        folder = FavoriteFolder.objects.create(
            user=self.user,
            name='Test Folder'
        )
        favorite = Favorite.objects.create(
            user=self.user,
            book=self.book,
            folder=folder
        )
        self.assertEqual(favorite.user, self.user)
        self.assertEqual(favorite.book, self.book)
