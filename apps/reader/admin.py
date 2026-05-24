"""
阅读管理模块 - Django Admin 配置

提供 ReadingProgress（阅读进度）和 ReadingStats（阅读统计）模型的管理界面。
支持阅读进度的用户/书籍/章节追踪，以及阅读数据的时长格式化、字数展示等功能。
"""
from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import ReadingProgress, ReadingStats


@admin.register(ReadingProgress)
class ReadingProgressAdmin(ModelAdmin):
    """
    阅读进度管理界面

    追踪和管理用户的阅读进度记录，支持按用户和书籍搜索、按更新时间过滤、
    列表内编辑阅读位置。提供时间层级导航，便于按日期查看进度数据。
    """
    list_display = ['user', 'book', 'chapter', 'position', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['user__username', 'book__title']
    list_editable = ['position']
    date_hierarchy = 'updated_at'


@admin.register(ReadingStats)
class ReadingStatsAdmin(ModelAdmin):
    """
    阅读统计管理界面

    管理用户每日阅读统计数据，包括阅读时长、章节数、字数等核心指标。
    支持按用户搜索、按日期和用户过滤、列表内编辑章节数。
    提供时长和字数的格式化展示，提升数据可读性。
    """
    list_display = ['user', 'date', 'read_time_display', 'chapters_read', 'words_read_display']
    list_filter = ['date', 'user']
    search_fields = ['user__username']
    date_hierarchy = 'date'
    list_editable = ['chapters_read']

    @display(description='阅读时长')
    def read_time_display(self, obj):
        """
        阅读时长格式化展示

        将秒数转换为分钟单位的可读文本（如 "45 分钟"），便于管理员快速查看。

        参数:
            obj: ReadingStats 实例

        返回:
            str: 阅读时长文本
        """
        minutes = obj.read_seconds // 60
        return f'{minutes} 分钟'

    @display(description='阅读字数')
    def words_read_display(self, obj):
        """
        阅读字数格式化展示

        将阅读字数以千位分隔符格式显示（如 12,345），提升大数字的可读性。

        参数:
            obj: ReadingStats 实例

        返回:
            str: 带千位分隔符的字数文本
        """
        return f'{obj.words_read:,}'
