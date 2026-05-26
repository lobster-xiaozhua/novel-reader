from django.db import models
from utils.book_gradient import get_book_gradient


class Tag(models.Model):
    name = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='标签名')
    color = models.CharField(max_length=7, default='#f59e0b', verbose_name='颜色')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '标签'
        verbose_name_plural = '标签'
        ordering = ['name']

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200, db_index=True, verbose_name='书名')
    author = models.CharField(max_length=100, db_index=True, blank=True, verbose_name='作者')
    category = models.CharField(max_length=50, blank=True, db_index=True, verbose_name='分类')
    folder_path = models.CharField(max_length=500, unique=True, verbose_name='文件夹路径')
    description = models.TextField(blank=True, verbose_name='简介')
    tags = models.ManyToManyField(Tag, blank=True, related_name='books', verbose_name='标签')
    total_chapters = models.PositiveIntegerField(default=0, verbose_name='总章节数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, db_index=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '书籍'
        verbose_name_plural = '书籍'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['author', 'created_at'], name='book_author_created_idx'),
            models.Index(fields=['category', 'created_at'], name='book_category_created_idx'),
        ]

    def __str__(self):
        return self.title

    @property
    def cover_gradient(self):
        return get_book_gradient(self.id)

    @property
    def chapter_count(self):
        if hasattr(self, '_chapter_count'):
            return self._chapter_count
        return self.chapters.count()
