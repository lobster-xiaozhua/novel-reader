from django.contrib import admin
from .models import ReadingProgress, ReadingStats

@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'book', 'chapter', 'updated_at']
    list_filter = ['user', 'book']
    search_fields = ['user__username', 'book__title']

@admin.register(ReadingStats)
class ReadingStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'read_seconds', 'chapters_read', 'words_read']
    list_filter = ['date', 'user']
    search_fields = ['user__username']
