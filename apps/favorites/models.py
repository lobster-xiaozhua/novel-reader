"""收藏管理模块。

定义 Favorite（收藏）模型，用于记录用户收藏的书籍。
每个用户对同一本书只能收藏一次，通过联合唯一约束保证。
"""
from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book


class Favorite(models.Model):
    """收藏模型，表示用户收藏了某本书。

    通过 (user, book) 联合唯一约束确保同一用户不会重复收藏同一本书。
    删除用户或书籍时会级联删除对应的收藏记录。

    Attributes:
        user: 收藏者，删除用户时级联删除收藏
        book: 被收藏的书籍，删除书籍时级联删除收藏
        created_at: 收藏时间，带索引
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, db_index=True, verbose_name='书籍')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')

    class Meta:
        """收藏元数据配置。

        verbose_name: 单数显示名称
        verbose_name_plural: 复数显示名称
        unique_together: 同一用户对同一本书不可重复收藏
        """
        verbose_name = '收藏'
        verbose_name_plural = '收藏'
        unique_together = ['user', 'book']

    def __str__(self):
        return f'{self.user.username} - {self.book.title}'
