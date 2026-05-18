from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book


class FavoriteFolder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    name = models.CharField(max_length=50, verbose_name='文件夹名')
    description = models.CharField(max_length=200, blank=True, verbose_name='描述')
    color = models.CharField(max_length=7, blank=True, verbose_name='颜色')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '收藏夹'
        verbose_name_plural = '收藏夹'
        ordering = ['sort_order', 'created_at']

    def __str__(self):
        return self.name


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='书籍')
    folder = models.ForeignKey(FavoriteFolder, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='收藏夹')
    notes = models.CharField(max_length=500, blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '收藏'
        verbose_name_plural = '收藏'
        unique_together = ['user', 'book']

    def __str__(self):
        return f'{self.user.username} - {self.book.title}'
