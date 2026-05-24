"""
书籍管理模块 - Django Admin 配置

提供 Book 和 Tag 模型的管理界面，包含列表展示、搜索过滤、批量编辑等功能。
dashboard_callback 函数为管理后台仪表盘提供统计数据，包括书籍数量、阅读统计、
爬虫任务状态、分类分布和阅读趋势等核心指标。
"""
from django.contrib import admin
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Book, Tag
from apps.reader.models import ReadingStats
from apps.crawler.models import CrawlerTask


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    """
    标签管理界面

    管理书籍标签，支持按名称搜索，以颜色预览方式展示标签视觉效果。
    """
    list_display = ['name', 'color_preview', 'created_at']
    search_fields = ['name']

    @display(description='颜色')
    def color_preview(self, obj):
        """
        标签颜色预览

        在列表中以可视化方式展示标签颜色，便于管理员直观区分不同标签。

        参数:
            obj: Tag 实例

        返回:
            str: 标签颜色值
        """
        return obj.color


@admin.register(Book)
class BookAdmin(ModelAdmin):
    """
    书籍管理界面

    提供书籍的完整管理功能，包括标题/作者/分类展示、章节数统计、
    多维搜索（标题、作者、描述）、分类过滤、标签关联管理等。
    支持列表内直接编辑作者和分类字段。
    """
    list_display = ['title', 'author', 'category', 'total_chapters', 'chapter_count_badge', 'created_at']
    list_filter = ['category', 'created_at', 'tags']
    search_fields = ['title', 'author', 'description']
    filter_horizontal = ['tags']
    date_hierarchy = 'created_at'
    list_editable = ['author', 'category']

    @display(description='章节数', header=True)
    def chapter_count_badge(self, obj):
        """
        书籍章节数量徽章

        实时统计当前书籍关联的章节总数，在列表中直观展示。

        参数:
            obj: Book 实例

        返回:
            int: 章节总数
        """
        count = obj.chapters.count()
        return count


def dashboard_callback(request, context):
    """
    管理后台仪表盘数据回调函数

    收集并汇总平台核心运营数据，填充到仪表盘上下文中展示。
    包含以下统计维度：

    1. 书籍总量统计：总书籍数、本周新增、本月新增
    2. 阅读行为统计：今日/本周阅读时长、章节数、字数
    3. 爬虫任务统计：各状态任务数量（等待中、运行中、已完成、失败）
    4. 分类分布：按书籍数量排序的前8个分类占比
    5. 阅读趋势：最近7天每日阅读分钟数和章节数

    参数:
        request: HTTP 请求对象
        context: 仪表盘上下文字典

    返回:
        dict: 更新后的上下文字典，包含 cards（统计卡片）、
              category_data（分类数据）、last_7_days（7天趋势）、
              crawler_stats（爬虫统计）、week_read_minutes（周阅读分钟）、
              week_chapters（周阅读章节）
    """
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    # 书籍统计：总数、本周新增、本月新增
    total_books = Book.objects.count()
    new_books_week = Book.objects.filter(created_at__date__gte=week_start).count()
    new_books_month = Book.objects.filter(created_at__date__gte=month_start).count()

    # 阅读统计：今日和本周的阅读时长、章节数、字数汇总
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

    # 爬虫任务统计：按状态分组计数（等待中、运行中、已完成、失败、总数）
    crawler_stats = {
        'pending': CrawlerTask.objects.filter(status='pending').count(),
        'running': CrawlerTask.objects.filter(status='running').count(),
        'completed': CrawlerTask.objects.filter(status='completed').count(),
        'failed': CrawlerTask.objects.filter(status='failed').count(),
        'total': CrawlerTask.objects.count(),
    }

    # 分类分布：书籍数量最多的前8个分类
    category_data = list(Book.objects.values('category').annotate(
        count=Count('id')
    ).order_by('-count')[:8])

    # 最近7天阅读趋势：每日阅读分钟数和章节数
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

    # 更新仪表盘上下文：统计卡片、图表数据
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
