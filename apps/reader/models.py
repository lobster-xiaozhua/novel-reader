from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book
from apps.chapters.models import Chapter


class ReadingProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, db_index=True, verbose_name='书籍')
    chapter = models.ForeignKey(Chapter, on_delete=models.SET_NULL, null=True, verbose_name='章节')
    position = models.PositiveIntegerField(default=0, verbose_name='阅读位置')
    updated_at = models.DateTimeField(auto_now=True, db_index=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '阅读进度'
        verbose_name_plural = '阅读进度'
        unique_together = ['user', 'book']

    def __str__(self):
        return f'{self.user.username} - {self.book.title}'


class ReadingStats(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True, verbose_name='用户')
    date = models.DateField(db_index=True, verbose_name='日期')
    read_seconds = models.PositiveIntegerField(default=0, verbose_name='阅读秒数')
    chapters_read = models.PositiveIntegerField(default=0, verbose_name='阅读章节数')
    words_read = models.PositiveIntegerField(default=0, verbose_name='阅读字数')

    class Meta:
        verbose_name = '阅读统计'
        verbose_name_plural = '阅读统计'
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f'{self.user.username} - {self.date}'
