from django.contrib import admin
from .models import Book

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'total_chapters', 'created_at']
    search_fields = ['title', 'author']
    list_filter = ['created_at']
