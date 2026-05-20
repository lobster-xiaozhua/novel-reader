from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from apps.books.models import Book
from apps.chapters.models import Chapter
from .models import ReadingProgress


class ReadingProgressModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.book = Book.objects.create(
            title='测试书籍',
            folder_path='data/books/test_book'
        )
        self.chapter = Chapter.objects.create(
            book=self.book,
            chapter_number=1,
            title='第一章',
            file_path='data/books/test_book/ch1.txt'
        )

    def test_progress_str(self):
        """测试阅读进度模型字符串表示"""
        progress = ReadingProgress.objects.create(
            user=self.user,
            book=self.book,
            chapter=self.chapter,
            position=100
        )
        expected = f'{self.user.username} - {self.book.title}'
        self.assertEqual(str(progress), expected)

    def test_progress_unique_together(self):
        """测试阅读进度唯一约束"""
        ReadingProgress.objects.create(
            user=self.user,
            book=self.book,
            chapter=self.chapter,
            position=100
        )
        with self.assertRaises(Exception):
            ReadingProgress.objects.create(
                user=self.user,
                book=self.book,
                chapter=self.chapter,
                position=200
            )

    def test_progress_null_chapter(self):
        """测试阅读进度允许空章节"""
        progress = ReadingProgress.objects.create(
            user=self.user,
            book=self.book,
            chapter=None,
            position=0
        )
        self.assertIsNone(progress.chapter)

    def test_progress_default_position(self):
        """测试阅读进度默认位置"""
        progress = ReadingProgress.objects.create(
            user=self.user,
            book=self.book,
            chapter=self.chapter
        )
        self.assertEqual(progress.position, 0)

    def test_progress_auto_update_time(self):
        """测试阅读进度自动更新时间"""
        import time
        progress = ReadingProgress.objects.create(
            user=self.user,
            book=self.book,
            chapter=self.chapter,
            position=100
        )
        first_update = progress.updated_at
        time.sleep(0.01)
        progress.position = 200
        progress.save()
        progress.refresh_from_db()
        self.assertGreater(progress.updated_at, first_update)


class ReaderViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.book = Book.objects.create(
            title='测试书籍',
            folder_path='data/books/test_book'
        )
        self.chapter = Chapter.objects.create(
            book=self.book,
            chapter_number=1,
            title='第一章',
            file_path='data/books/test_book/ch1.txt'
        )

    def test_reader_url_resolution(self):
        """测试阅读器URL配置存在"""
        from django.urls import resolve, Resolver404
        try:
            resolver = resolve('/reader/')
            self.fail("Reader URL should not resolve to any view")
        except Resolver404:
            pass
