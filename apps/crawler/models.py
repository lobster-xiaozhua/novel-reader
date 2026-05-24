"""爬虫任务管理模块。

定义 CrawlerTask（爬虫任务）模型，用于追踪从网络抓取小说内容
的全生命周期，包括等待、运行、完成、失败和取消等状态。
"""
from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book


class CrawlerTask(models.Model):
    """爬虫任务模型，记录一次小说抓取任务的完整信息。

    任务创建用户后处于 pending 状态，经过 running 最终变为 completed 或 failed。
    任务完成后会关联到对应的书籍。

    Attributes:
        user: 任务创建者，删除用户时级联删除任务
        url: 目标网页 URL，带索引
        status: 任务状态，枚举值为 pending/running/completed/failed/cancelled
        book: 爬取成功后关联的书籍，可为空
        total_chapters: 目标总章节数
        downloaded_chapters: 已成功下载的章节数
        error_message: 失败时的错误详情
        logs: 任务运行日志
        created_at: 任务创建时间，带索引
        updated_at: 任务最后更新时间
    """
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True, verbose_name='用户')
    url = models.URLField(db_index=True, verbose_name='URL')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True, verbose_name='状态')
    book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='关联书籍')
    total_chapters = models.PositiveIntegerField(default=0, verbose_name='总章节数')
    downloaded_chapters = models.PositiveIntegerField(default=0, verbose_name='已下载章节数')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    logs = models.TextField(blank=True, verbose_name='日志')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        """爬虫任务元数据配置。

        verbose_name: 单数显示名称
        verbose_name_plural: 复数显示名称
        ordering: 默认按创建时间降序排列（最新的任务在前）
        """
        verbose_name = '爬虫任务'
        verbose_name_plural = '爬虫任务'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.url} ({self.get_status_display()})'
