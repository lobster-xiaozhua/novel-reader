from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book


class CrawlerTask(models.Model):
    STATUS_CHOICES = [
        ("pending", "等待中"),
        ("running", "运行中"),
        ("completed", "已完成"),
        ("failed", "失败"),
        ("cancelled", "已取消"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    url = models.URLField(max_length=500, verbose_name="目标URL")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="状态")
    book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="关联书籍")
    total_chapters = models.PositiveIntegerField(default=0, verbose_name="总章节数")
    downloaded_chapters = models.PositiveIntegerField(default=0, verbose_name="已下载章节数")
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    logs = models.TextField(blank=True, verbose_name="日志")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "爬虫任务"
        verbose_name_plural = "爬虫任务"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.url} ({self.get_status_display()})"
