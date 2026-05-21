from django.contrib import admin
from .models import Book, Tag

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'created_at']
    search_fields = ['name']

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'total_chapters', 'created_at']
    search_fields = ['title', 'author']
    list_filter = ['category', 'created_at', 'tags']
    filter_horizontal = ['tags']
