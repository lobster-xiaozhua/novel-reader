"""章节管理模块。

定义 Chapter（章节）模型，用于关联书籍与其具体章节文件，
记录章节序号、标题、文件路径和字数等信息。
"""
from django.db import models
from apps.books.models import Book


class Chapter(models.Model):
    """章节模型，表示一本书中的一个章节。

    每个章节归属于某一本书，通过 book 外键关联。章节号和书籍联合唯一，
    确保同一本书中不会有重复的章节号。

    Attributes:
        book: 所属书籍的外键，删除书籍时级联删除所有章节
        chapter_number: 章节序号，带索引
        title: 章节标题，带索引
        file_path: 章节文件在文件系统中的路径
        word_count: 章节字数，带索引
        created_at: 章节创建时间，带索引
    """
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chapters', verbose_name='书籍', db_index=True)
    chapter_number = models.PositiveIntegerField(db_index=True, verbose_name='章节号')
    title = models.CharField(max_length=200, db_index=True, verbose_name='章节标题')
    file_path = models.CharField(max_length=500, verbose_name='文件路径')
    word_count = models.PositiveIntegerField(default=0, db_index=True, verbose_name='字数')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')

    class Meta:
        """章节元数据配置。

        verbose_name: 单数显示名称
        verbose_name_plural: 复数显示名称
        ordering: 默认按章节号升序排列
        unique_together: 同一本书的章节号不可重复
        indexes: 组合索引 (book, chapter_number) 用于加速按书查章节
        """
        verbose_name = '章节'
        verbose_name_plural = '章节'
        ordering = ['chapter_number']
        unique_together = ['book', 'chapter_number']
        indexes = [
            models.Index(fields=['book', 'chapter_number'], name='chapter_book_num_idx'),
        ]

    def __str__(self):
        return f'{self.book.title} - 第{self.chapter_number}章 {self.title}'
