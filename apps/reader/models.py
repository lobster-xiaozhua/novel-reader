from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book
from apps.chapters.models import Chapter


class ReadingProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='书籍')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name='章节')
    position = models.PositiveIntegerField(default=0, verbose_name='阅读位置')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '阅读进度'
        verbose_name_plural = '阅读进度'
        unique_together = ['user', 'book']

    def __str__(self):
        return f'{self.user.username} - {self.book.title}'
