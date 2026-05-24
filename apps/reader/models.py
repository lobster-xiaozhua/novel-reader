"""阅读进度与统计模块。

定义 ReadingProgress（阅读进度）和 ReadingStats（阅读统计）两个模型，
用于记录用户的阅读位置以及每日阅读行为统计数据。
"""
from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book
from apps.chapters.models import Chapter


class ReadingProgress(models.Model):
    """阅读进度模型，记录用户在某本书中的当前位置。

    每个用户在每本书中只有一条进度记录，通过 (user, book) 联合唯一约束保证。
    进度精确到具体章节和阅读位置。

    Attributes:
        user: 关联用户，删除用户时级联删除进度
        book: 关联书籍，删除书籍时级联删除进度
        chapter: 当前所在章节，章节被删除时进度保留但设为 NULL
        position: 阅读位置（如滚动偏移量或字符索引）
        updated_at: 最后更新时间，带索引
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True, verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, db_index=True, verbose_name='书籍')
    chapter = models.ForeignKey(Chapter, on_delete=models.SET_NULL, null=True, verbose_name='章节')
    position = models.PositiveIntegerField(default=0, verbose_name='阅读位置')
    updated_at = models.DateTimeField(auto_now=True, db_index=True, verbose_name='更新时间')

    class Meta:
        """阅读进度元数据配置。

        verbose_name: 单数显示名称
        verbose_name_plural: 复数显示名称
        unique_together: 同一用户对同一本书只保留一条进度记录
        """
        verbose_name = '阅读进度'
        verbose_name_plural = '阅读进度'
        unique_together = ['user', 'book']

    def __str__(self):
        return f'{self.user.username} - {self.book.title}'


class ReadingStats(models.Model):
    """阅读统计模型，按日期记录用户的阅读行为汇总数据。

    每个用户每天只有一条统计记录，涵盖阅读时长、章节数和字数。

    Attributes:
        user: 关联用户，删除用户时级联删除统计
        date: 统计日期，带索引
        read_seconds: 当日累计阅读秒数
        chapters_read: 当日阅读的章节数量
        words_read: 当日阅读的总字数
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True, verbose_name='用户')
    date = models.DateField(db_index=True, verbose_name='日期')
    read_seconds = models.PositiveIntegerField(default=0, verbose_name='阅读秒数')
    chapters_read = models.PositiveIntegerField(default=0, verbose_name='阅读章节数')
    words_read = models.PositiveIntegerField(default=0, verbose_name='阅读字数')

    class Meta:
        """阅读统计元数据配置。

        verbose_name: 单数显示名称
        verbose_name_plural: 复数显示名称
        unique_together: 同一用户同一天只保留一条统计记录
        ordering: 默认按日期降序排列（最近的在前）
        """
        verbose_name = '阅读统计'
        verbose_name_plural = '阅读统计'
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f'{self.user.username} - {self.date}'
