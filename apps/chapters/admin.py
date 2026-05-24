"""
章节管理模块 - Django Admin 配置

提供 Chapter 模型的管理界面，支持章节标题搜索、按书籍和创建时间过滤、
列表内编辑标题、字数格式化展示等功能。
"""
from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Chapter


@admin.register(Chapter)
class ChapterAdmin(ModelAdmin):
    """
    章节管理界面

    管理书籍章节数据，支持按标题和所属书籍搜索、按书籍和创建时间过滤、
    列表内直接编辑标题、创建时间层级导航。
    提供格式化字数展示，便于管理员快速浏览章节信息。
    """
    list_display = ['book', 'chapter_number', 'title', 'word_count', 'created_at']
    list_filter = ['book', 'created_at']
    search_fields = ['title', 'book__title']
    list_editable = ['title']
    date_hierarchy = 'created_at'

    @display(description='字数')
    def word_count_display(self, obj):
        """
        章节字数格式化展示

        将章节字数以千位分隔符格式显示（如 12,345），提升可读性。

        参数:
            obj: Chapter 实例

        返回:
            str: 带千位分隔符的字数文本
        """
        return f'{obj.word_count:,}'
