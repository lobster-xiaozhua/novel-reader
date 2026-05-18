from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=200, db_index=True, verbose_name='书名')
    author = models.CharField(max_length=100, db_index=True, blank=True, verbose_name='作者')
    folder_path = models.CharField(max_length=500, unique=True, verbose_name='文件夹路径')
    description = models.TextField(blank=True, verbose_name='简介')
    total_chapters = models.PositiveIntegerField(default=0, verbose_name='总章节数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '书籍'
        verbose_name_plural = '书籍'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
