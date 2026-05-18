from django.contrib import admin
from .models import CrawlerTask

@admin.register(CrawlerTask)
class CrawlerTaskAdmin(admin.ModelAdmin):
    list_display = ['url', 'status', 'user', 'created_at']
    list_filter = ['status', 'created_at']
