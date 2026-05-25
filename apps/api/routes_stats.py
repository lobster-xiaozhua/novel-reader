import logging
from datetime import date, timedelta
from typing import List

from django.contrib.auth.models import User
from django.db.models import Count, Sum
from ninja import Router

from apps.books.models import Book
from apps.chapters.models import Chapter
from apps.favorites.models import Favorite
from apps.reader.models import ReadingProgress, ReadingStats

from .auth import jwt_auth, optional_jwt_auth
from .schemas import DashboardStatsSchema, UserStatsSchema

logger = logging.getLogger(__name__)
router = Router()


@router.get('/stats/', response=UserStatsSchema, auth=jwt_auth)
def get_user_stats(request, days: int = 7) -> dict:
    user = request.user
    today = date.today()
    total_books: int = Book.objects.count()
    reading_count: int = ReadingProgress.objects.filter(user=user).count()
    favorite_count: int = Favorite.objects.filter(user=user).count()
    today_stats = ReadingStats.objects.filter(user=user, date=today).first()
    week_start = today - timedelta(days=today.weekday())
    week_stats = ReadingStats.objects.filter(user=user, date__gte=week_start).aggregate(
        total_chapters=Sum('chapters_read'),
    )
    total_words: int = ReadingStats.objects.filter(user=user).aggregate(
        total=Sum('words_read'),
    )['total'] or 0
    start = today - timedelta(days=days - 1)
    daily_stats = ReadingStats.objects.filter(user=user, date__gte=start)
    stats_map = {s.date: s for s in daily_stats}
    chart: List[dict] = []
    current = start
    while current <= today:
        s = stats_map.get(current)
        chart.append({
            'date': current.isoformat(),
            'minutes': round(s.read_seconds / 60, 1) if s else 0.0,
            'chapters': s.chapters_read if s else 0,
            'words': s.words_read if s else 0,
        })
        current += timedelta(days=1)
    return {
        'total_books': total_books,
        'reading_count': reading_count,
        'favorite_count': favorite_count,
        'today_chapters': today_stats.chapters_read if today_stats else 0,
        'today_minutes': round(today_stats.read_seconds / 60, 1) if today_stats else 0.0,
        'week_chapters': week_stats['total_chapters'] or 0,
        'total_words': total_words,
        'chart': chart,
    }


@router.get('/dashboard/', response=DashboardStatsSchema, auth=optional_jwt_auth)
def get_dashboard_stats(request) -> dict:
    category_stats: list[dict] = list(
        Book.objects.exclude(category='')
        .values('category')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    return {
        'total_books': Book.objects.count(),
        'total_users': User.objects.count(),
        'total_chapters': Chapter.objects.count(),
        'total_words': Chapter.objects.aggregate(total=Sum('word_count'))['total'] or 0,
        'category_stats': category_stats,
    }
