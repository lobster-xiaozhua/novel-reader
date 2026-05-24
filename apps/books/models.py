"""书籍管理模块。

定义 Tag（标签）和 Book（书籍）两个模型，用于管理书籍的元数据、
分类、标签关联以及封面渐变等展示信息。
"""
from django.db import models
from utils.book_gradient import get_book_gradient


class Tag(models.Model):
    """标签模型，用于给书籍打分类标记。

    Attributes:
        name: 标签名称，全局唯一，带索引
        color: 标签颜色，十六进制色值，默认琥珀色
        created_at: 标签创建时间，自动生成
    """
    name = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='标签名')
    color = models.CharField(max_length=7, default='#f59e0b', verbose_name='颜色')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        """标签元数据配置。

        verbose_name: 单数显示名称
        verbose_name_plural: 复数显示名称（中文与单数相同）
        ordering: 默认按标签名升序排列
        """
        verbose_name = '标签'
        verbose_name_plural = '标签'
        ordering = ['name']

    def __str__(self):
        return self.name


class Book(models.Model):
    """书籍模型，存储书籍的核心元数据。

    包含书名、作者、分类、文件夹路径、简介、标签关联、章节数等字段，
    以及按作者和分类的组合索引以加速查询。

    Attributes:
        title: 书名，带索引
        author: 作者名，可空，带索引
        category: 分类名称，可空，带索引
        folder_path: 书籍文件夹路径，全局唯一
        description: 书籍简介
        tags: 多对多关联的标签集合
        total_chapters: 总章节数
        created_at: 书籍创建时间
        updated_at: 书籍最后更新时间，带索引
    """
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
        """书籍元数据配置。

        verbose_name: 单数显示名称
        verbose_name_plural: 复数显示名称
        ordering: 默认按创建时间降序排列
        indexes: 组合索引 (author, created_at) 和 (category, created_at)
        """
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
        """获取本书封面的渐变色配置。

        Returns:
            根据书籍 ID 生成的渐变色字符串
        """
        return get_book_gradient(self.id)

    @property
    def chapter_count(self):
        """获取本书的实际章节数量。

        Returns:
            通过反向关联 chapters 查询到的章节总数
        """
        return self.chapters.count()
