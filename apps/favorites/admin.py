from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Favorite, FavoriteFolder


@admin.register(Favorite)
class FavoriteAdmin(ModelAdmin):
    list_display = ['user', 'book', 'folder', 'created_at']
    list_filter = ['created_at', 'folder']
    search_fields = ['user__username', 'book__title']
    list_editable = ['folder']


@admin.register(FavoriteFolder)
class FavoriteFolderAdmin(ModelAdmin):
    list_display = ['name', 'user', 'color', 'sort_order']
    search_fields = ['name', 'user__username']
    list_editable = ['sort_order']
