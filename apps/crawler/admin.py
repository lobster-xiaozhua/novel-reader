from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import CrawlerTask


@admin.register(CrawlerTask)
class CrawlerTaskAdmin(ModelAdmin):
    list_display = ['url_short', 'status_badge', 'progress_display', 'user', 'created_at']
    list_filter = ['status', 'created_at', 'user']
    search_fields = ['url', 'error_message']
    date_hierarchy = 'created_at'

    @display(description='URL')
    def url_short(self, obj):
        return obj.url[:60] + '...' if len(obj.url) > 60 else obj.url

    @display(description='状态')
    def status_badge(self, obj):
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
        if obj.total_chapters > 0:
            pct = int(obj.downloaded_chapters / obj.total_chapters * 100)
            return f'{obj.downloaded_chapters}/{obj.total_chapters} ({pct}%)'
        return '0/0'
