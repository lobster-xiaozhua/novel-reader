"""
用户管理模块 - Django Admin 配置

自定义 Django User 模型的管理界面，集成 Unfold 主题样式。
支持用户名、邮箱、姓名展示，按用户权限状态过滤，列表内编辑员工权限。
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from unfold.admin import ModelAdmin


# 注销默认 User Admin，使用自定义配置
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """
    用户管理界面

    继承 Django 基础 UserAdmin 并集成 Unfold 主题，提供完整的用户管理功能。
    展示用户名、邮箱、姓名、权限状态和注册时间。
    支持按权限状态（员工、超级管理员、活跃状态）和注册时间过滤。
    支持按用户名、姓名、邮箱搜索，列表内可切换员工权限。
    """
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'date_joined']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    list_editable = ['is_staff']
