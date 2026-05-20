from django.contrib import admin
from .models import Chapter


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ["book", "chapter_number", "title", "word_count"]
    list_filter = ["book"]
