from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import ReadingProgress, ReadingStats


@admin.register(ReadingProgress)
class ReadingProgressAdmin(ModelAdmin):
    list_display = ['user', 'book', 'chapter', 'position', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['user__username', 'book__title']
    list_editable = ['position']
    date_hierarchy = 'updated_at'


@admin.register(ReadingStats)
class ReadingStatsAdmin(ModelAdmin):
    list_display = ['user', 'date', 'read_time_display', 'chapters_read', 'words_read_display']
    list_filter = ['date', 'user']
    search_fields = ['user__username']
    date_hierarchy = 'date'
    list_editable = ['chapters_read']

    @display(description='阅读时长')
    def read_time_display(self, obj):
        minutes = obj.read_seconds // 60
        return f'{minutes} 分钟'

    @display(description='阅读字数')
    def words_read_display(self, obj):
        return f'{obj.words_read:,}'
