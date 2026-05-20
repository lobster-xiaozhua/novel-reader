import os
import tempfile
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.cache import cache
from apps.books.models import Book
from apps.chapters.models import Chapter
from apps.reader.models import ReadingProgress


class ChapterModelTest(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title='测试书籍',
            folder_path='data/books/test_book'
        )
        self.chapter = Chapter.objects.create(
            book=self.book,
            chapter_number=1,
            title='第一章',
            file_path='data/books/test_book/ch1.txt',
            word_count=1000
        )

    def test_chapter_str(self):
        """测试章节模型字符串表示"""
        expected = f'{self.book.title} - 第{self.chapter.chapter_number}章 {self.chapter.title}'
        self.assertEqual(str(self.chapter), expected)

    def test_chapter_unique_together(self):
        """测试章节唯一约束"""
        with self.assertRaises(Exception):
            Chapter.objects.create(
                book=self.book,
                chapter_number=1,
                title='重复章节',
                file_path='data/books/test_book/ch1_dup.txt'
            )

    def test_chapter_ordering(self):
        """测试章节排序"""
        ch2 = Chapter.objects.create(
            book=self.book,
            chapter_number=2,
            title='第二章',
            file_path='data/books/test_book/ch2.txt'
        )
        chapters = list(Chapter.objects.filter(book=self.book))
        self.assertEqual(chapters, [self.chapter, ch2])


class ChapterViewsTest(TestCase):
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
            file_path='data/books/test_book/ch1.txt',
            word_count=1000
        )
        cache.clear()

    def test_chapter_read_view(self):
        """测试章节阅读视图"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write('测试章节内容')
            temp_path = f.name

        self.chapter.file_path = temp_path
        self.chapter.save()

        try:
            response = self.client.get(reverse('chapter_read', kwargs={
                'book_id': self.book.pk,
                'chapter_id': self.chapter.pk
            }))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'chapters/read.html')
            self.assertEqual(response.context['book'], self.book)
            self.assertEqual(response.context['chapter'], self.chapter)
        finally:
            os.unlink(temp_path)

    def test_chapter_read_view_with_cache(self):
        """测试章节内容缓存"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write('缓存测试内容')
            temp_path = f.name

        self.chapter.file_path = temp_path
        self.chapter.save()

        try:
            response1 = self.client.get(reverse('chapter_read', kwargs={
                'book_id': self.book.pk,
                'chapter_id': self.chapter.pk
            }))
            self.assertEqual(response1.status_code, 200)

            cached_content = cache.get(f'chapter_content:{self.chapter.id}')
            self.assertEqual(cached_content, '缓存测试内容')
        finally:
            os.unlink(temp_path)

    def test_chapter_read_view_file_not_found(self):
        """测试章节文件不存在"""
        self.chapter.file_path = '/nonexistent/path/chapter.txt'
        self.chapter.save()

        response = self.client.get(reverse('chapter_read', kwargs={
            'book_id': self.book.pk,
            'chapter_id': self.chapter.pk
        }))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['content'], '章节文件不存在')

    def test_chapter_read_view_different_encodings(self):
        """测试不同编码的章节文件"""
        for encoding in ['utf-8', 'gbk', 'gb2312']:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding=encoding) as f:
                f.write('测试内容')
                temp_path = f.name

            self.chapter.file_path = temp_path
            self.chapter.save()
            cache.clear()

            try:
                response = self.client.get(reverse('chapter_read', kwargs={
                    'book_id': self.book.pk,
                    'chapter_id': self.chapter.pk
                }))
                self.assertEqual(response.status_code, 200)
                self.assertIn('测试内容', response.context['content'])
            finally:
                os.unlink(temp_path)

    def test_chapter_read_view_with_navigation(self):
        """测试章节导航"""
        ch2 = Chapter.objects.create(
            book=self.book,
            chapter_number=2,
            title='第二章',
            file_path='data/books/test_book/ch2.txt'
        )

        response = self.client.get(reverse('chapter_read', kwargs={
            'book_id': self.book.pk,
            'chapter_id': self.chapter.pk
        }))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['prev_chapter'])
        self.assertIsNotNone(response.context['next_chapter'])
        self.assertEqual(response.context['next_chapter']['id'], ch2.id)

    def test_chapter_read_view_with_progress(self):
        """测试章节阅读带阅读进度"""
        self.client.login(username='testuser', password='testpass123')
        ReadingProgress.objects.create(
            user=self.user,
            book=self.book,
            chapter=self.chapter,
            position=100
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write('测试内容')
            temp_path = f.name

        self.chapter.file_path = temp_path
        self.chapter.save()

        try:
            response = self.client.get(reverse('chapter_read', kwargs={
                'book_id': self.book.pk,
                'chapter_id': self.chapter.pk
            }))
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context['progress'])
        finally:
            os.unlink(temp_path)

    def test_chapter_read_view_not_found(self):
        """测试章节不存在404"""
        response = self.client.get(reverse('chapter_read', kwargs={
            'book_id': self.book.pk,
            'chapter_id': 99999
        }))
        self.assertEqual(response.status_code, 404)

    def test_save_progress_requires_login(self):
        """测试保存进度需要登录"""
        response = self.client.post(reverse('save_progress', kwargs={'book_id': self.book.pk}), {
            'chapter_id': self.chapter.pk,
            'position': 100
        })
        self.assertEqual(response.status_code, 302)

    def test_save_progress_valid(self):
        """测试有效保存进度"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('save_progress', kwargs={'book_id': self.book.pk}), {
            'chapter_id': self.chapter.pk,
            'position': 100
        })
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'ok'})

        progress = ReadingProgress.objects.get(user=self.user, book=self.book)
        self.assertEqual(progress.chapter, self.chapter)
        self.assertEqual(progress.position, 100)

    def test_save_progress_update_existing(self):
        """测试更新现有进度"""
        self.client.login(username='testuser', password='testpass123')
        ReadingProgress.objects.create(
            user=self.user,
            book=self.book,
            chapter=self.chapter,
            position=50
        )

        ch2 = Chapter.objects.create(
            book=self.book,
            chapter_number=2,
            title='第二章',
            file_path='data/books/test_book/ch2.txt'
        )

        response = self.client.post(reverse('save_progress', kwargs={'book_id': self.book.pk}), {
            'chapter_id': ch2.pk,
            'position': 200
        })
        self.assertEqual(response.status_code, 200)

        progress = ReadingProgress.objects.get(user=self.user, book=self.book)
        self.assertEqual(progress.chapter, ch2)
        self.assertEqual(progress.position, 200)

    def test_save_progress_invalid_position(self):
        """测试无效位置参数"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('save_progress', kwargs={'book_id': self.book.pk}), {
            'chapter_id': self.chapter.pk,
            'position': 'invalid'
        })
        self.assertEqual(response.status_code, 200)

        progress = ReadingProgress.objects.get(user=self.user, book=self.book)
        self.assertEqual(progress.position, 0)

    def test_save_progress_requires_post(self):
        """测试保存进度只接受POST"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('save_progress', kwargs={'book_id': self.book.pk}))
        self.assertEqual(response.status_code, 405)

    def test_save_progress_wrong_book(self):
        """测试保存进度时章节不属于该书"""
        self.client.login(username='testuser', password='testpass123')
        other_book = Book.objects.create(
            title='其他书籍',
            folder_path='data/books/other_book'
        )

        response = self.client.post(reverse('save_progress', kwargs={'book_id': other_book.pk}), {
            'chapter_id': self.chapter.pk,
            'position': 100
        })
        self.assertEqual(response.status_code, 404)
