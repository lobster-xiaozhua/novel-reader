from django.contrib import admin
from .models import ReadingProgress

@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'book', 'chapter', 'updated_at']
