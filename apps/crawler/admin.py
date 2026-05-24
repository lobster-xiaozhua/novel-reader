"""
爬虫管理模块 - Django Admin 配置

提供 CrawlerTask 模型的管理界面，包含爬虫任务状态监控、进度展示、
URL 缩略显示、状态标签映射等功能，便于管理员追踪和管理爬虫任务。
"""
from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import CrawlerTask


@admin.register(CrawlerTask)
class CrawlerTaskAdmin(ModelAdmin):
    """
    爬虫任务管理界面

    管理所有爬虫任务，提供 URL 缩略展示（长链接截断）、状态中文标签映射、
    下载进度百分比计算等功能。支持按状态、用户、创建时间过滤和搜索。
    """
    list_display = ['url_short', 'status_badge', 'progress_display', 'user', 'created_at']
    list_filter = ['status', 'created_at', 'user']
    search_fields = ['url', 'error_message']
    date_hierarchy = 'created_at'

    @display(description='URL')
    def url_short(self, obj):
        """
        URL 缩略展示

        将长 URL 截断为前 60 个字符并添加省略号，避免列表列宽过大。

        参数:
            obj: CrawlerTask 实例

        返回:
            str: 截断后的 URL 文本
        """
        return obj.url[:60] + '...' if len(obj.url) > 60 else obj.url

    @display(description='状态')
    def status_badge(self, obj):
        """
        爬虫状态中文标签

        将英文状态码映射为中文标签（如 pending→等待中），便于管理员快速识别。

        参数:
            obj: CrawlerTask 实例

        返回:
            str: 状态中文描述
        """
        labels = {
            'pending': '等待中',
            'running': '运行中',
            'completed': '已完成',
            'failed': '失败',
            'cancelled': '已取消',
        }
        return labels.get(obj.status, obj.status)

    @display(description='进度')
    def progress_display(self, obj):
        """
        下载进度展示

        计算并展示已下载章节数/总章节数及完成百分比。
        当总章节数为 0 时显示 "0/0"。

        参数:
            obj: CrawlerTask 实例

        返回:
            str: 进度文本，格式为 "已下载/总数 (百分比%)"
        """
        if obj.total_chapters > 0:
            pct = int(obj.downloaded_chapters / obj.total_chapters * 100)
            return f'{obj.downloaded_chapters}/{obj.total_chapters} ({pct}%)'
        return '0/0'
