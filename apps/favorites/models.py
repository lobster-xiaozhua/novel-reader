from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, db_index=True, verbose_name='书籍')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '收藏'
        verbose_name_plural = '收藏'
        unique_together = ['user', 'book']

    def __str__(self):
        return f'{self.user.username} - {self.book.title}'
