from django.db import models
from apps.books.models import Book


class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chapters', verbose_name='书籍', db_index=True)
    chapter_number = models.PositiveIntegerField(db_index=True, verbose_name='章节号')
    title = models.CharField(max_length=200, db_index=True, verbose_name='章节标题')
    file_path = models.CharField(max_length=500, verbose_name='文件路径')
    word_count = models.PositiveIntegerField(default=0, db_index=True, verbose_name='字数')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '章节'
        verbose_name_plural = '章节'
        ordering = ['chapter_number']
        unique_together = ['book', 'chapter_number']
        indexes = [
            models.Index(fields=['book', 'chapter_number'], name='chapter_book_num_idx'),
        ]

    def __str__(self):
        return f'{self.book.title} - 第{self.chapter_number}章 {self.title}'
