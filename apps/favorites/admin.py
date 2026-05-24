"""
收藏管理模块 - Django Admin 配置

提供 Favorite 模型的管理界面，支持按用户和书籍搜索、按创建时间过滤，
便于管理用户收藏记录。
"""
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Favorite


@admin.register(Favorite)
class FavoriteAdmin(ModelAdmin):
    """
    收藏管理界面

    管理用户书籍收藏记录，支持按用户名和书名搜索、按创建时间过滤，
    便于查看和分析用户收藏行为。
    """
    list_display = ['user', 'book', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'book__title']
