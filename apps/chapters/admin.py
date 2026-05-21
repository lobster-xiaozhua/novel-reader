from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline
from unfold.decorators import display
from .models import Chapter


@admin.register(Chapter)
class ChapterAdmin(ModelAdmin):
    list_display = ['book', 'chapter_number', 'title', 'word_count', 'created_at']
    list_filter = ['book', 'created_at']
    search_fields = ['title', 'book__title']
    list_editable = ['title']
    date_hierarchy = 'created_at'

    @display(description='字数')
    def word_count_display(self, obj):
        return f'{obj.word_count:,}'
