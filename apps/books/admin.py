from django.contrib import admin
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from django.contrib.admin import ModelAdmin, display
from .models import Book, Tag
from apps.reader.models import ReadingStats
from apps.crawler.models import CrawlerTask


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ['name', 'color_preview', 'created_at']
    search_fields = ['name']

    @display(description='颜色')
    def color_preview(self, obj):
        return obj.color


@admin.register(Book)
class BookAdmin(ModelAdmin):
    list_display = ['title', 'author', 'category', 'total_chapters', 'chapter_count_badge', 'created_at']
    list_filter = ['category', 'created_at', 'tags']
    search_fields = ['title', 'author', 'description']
    filter_horizontal = ['tags']
    date_hierarchy = 'created_at'
    list_editable = ['author', 'category']

    @display(description='章节数')
    def chapter_count_badge(self, obj):
        count = obj.chapters.count()
        return count


def dashboard_callback(request, context):
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    # 书籍统计
    total_books = Book.objects.count()
    new_books_week = Book.objects.filter(created_at__date__gte=week_start).count()
    new_books_month = Book.objects.filter(created_at__date__gte=month_start).count()

    # 阅读统计
    today_stats = ReadingStats.objects.filter(date=today).aggregate(
        total_seconds=Sum('read_seconds'),
        total_chapters=Sum('chapters_read'),
        total_words=Sum('words_read'),
    )
    week_stats = ReadingStats.objects.filter(date__gte=week_start).aggregate(
        total_seconds=Sum('read_seconds'),
        total_chapters=Sum('chapters_read'),
        total_words=Sum('words_read'),
    )

    # 爬虫任务统计
    crawler_stats = {
        'pending': CrawlerTask.objects.filter(status='pending').count(),
        'running': CrawlerTask.objects.filter(status='running').count(),
        'completed': CrawlerTask.objects.filter(status='completed').count(),
        'failed': CrawlerTask.objects.filter(status='failed').count(),
        'total': CrawlerTask.objects.count(),
    }

    # 分类分布
    category_data = list(Book.objects.values('category').annotate(
        count=Count('id')
    ).order_by('-count')[:8])

    # 最近7天阅读趋势
    last_7_days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_stat = ReadingStats.objects.filter(date=d).aggregate(
            seconds=Sum('read_seconds'),
            chapters=Sum('chapters_read'),
        )
        last_7_days.append({
            'date': d.strftime('%m-%d'),
            'minutes': round((day_stat['seconds'] or 0) / 60, 1),
            'chapters': day_stat['chapters'] or 0,
        })

    context.update({
        'cards': [
            {'title': '总书籍数', 'value': total_books, 'icon': 'menu_book', 'color': 'primary'},
            {'title': '本周新增', 'value': new_books_week, 'icon': 'add_circle', 'color': 'success'},
            {'title': '本月新增', 'value': new_books_month, 'icon': 'trending_up', 'color': 'info'},
            {'title': '今日阅读', 'value': f"{round((today_stats['total_seconds'] or 0) / 60)}分钟", 'icon': 'schedule', 'color': 'warning'},
            {'title': '今日章节', 'value': today_stats['total_chapters'] or 0, 'icon': 'article', 'color': 'primary'},
            {'title': '今日字数', 'value': f"{(today_stats['total_words'] or 0) // 1000}k", 'icon': 'text_snippet', 'color': 'success'},
            {'title': '爬虫等待中', 'value': crawler_stats['pending'], 'icon': 'pending', 'color': 'warning'},
            {'title': '爬虫运行中', 'value': crawler_stats['running'], 'icon': 'sync', 'color': 'info'},
            {'title': '爬虫已完成', 'value': crawler_stats['completed'], 'icon': 'check_circle', 'color': 'success'},
            {'title': '爬虫失败', 'value': crawler_stats['failed'], 'icon': 'error', 'color': 'danger'},
        ],
        'category_data': category_data,
        'last_7_days': last_7_days,
        'crawler_stats': crawler_stats,
        'week_read_minutes': round((week_stats['total_seconds'] or 0) / 60),
        'week_chapters': week_stats['total_chapters'] or 0,
    })
    return context
