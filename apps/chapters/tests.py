from django.test import TestCase
from apps.books.models import Book
from .models import Chapter


class ChapterModelTest(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title='Test Book',
            author='Test Author',
            folder_path='data/books/test_book'
        )

    def test_chapter_creation(self):
        chapter = Chapter.objects.create(
            book=self.book,
            chapter_number=1,
            title='Chapter 1',
            file_path='data/books/test_book/ch1.txt',
            word_count=1000
        )
        self.assertEqual(chapter.title, 'Chapter 1')
        self.assertEqual(chapter.book, self.book)
        self.assertEqual(str(chapter), 'Test Book - 第1章 Chapter 1')
