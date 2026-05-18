from django.contrib import admin
from .models import Book, Tag, BookTag

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'total_chapters', 'created_at']
    search_fields = ['title', 'author']
    list_filter = ['created_at']

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name']

admin.site.register(BookTag)
