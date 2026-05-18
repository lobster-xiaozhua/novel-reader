from django.contrib import admin
from .models import Favorite, FavoriteFolder

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'book', 'created_at']

@admin.register(FavoriteFolder)
class FavoriteFolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'user']
