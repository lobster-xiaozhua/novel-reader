import logging
import time
from functools import wraps
from django.core.cache import cache
from django.db import connection

logger = logging.getLogger(__name__)


class QueryOptimizer:
    @staticmethod
    def get_optimized_books(user=None):
        from apps.books.models import Book
        from django.db.models import Count, Prefetch

        queryset = Book.objects.annotate(favorite_count=Count("favorites"), chapter_count=Count("chapters"))

        if user:
            from apps.favorites.models import Favorite

            favorites = Favorite.objects.filter(user=user).values_list("book_id", flat=True)
            queryset = queryset.prefetch_related(
                Prefetch("favorites", queryset=Favorite.objects.filter(user=user), to_attr="user_favorite")
            )

        return queryset.select_related().order_by("-favorite_count", "-created_at")

    @staticmethod
    def get_book_with_details(book_id, user=None):
        from apps.books.models import Book
        from apps.chapters.models import Chapter
        from django.db.models import Count, Prefetch

        try:
            book = Book.objects.annotate(favorite_count=Count("favorite"), rating_count=Count("ratings")).get(
                id=book_id
            )

            chapters = Chapter.objects.filter(book=book).order_by("chapter_number")

            book.chapters_list = list(chapters)

            if user:
                from apps.favorites.models import Favorite
                from apps.reader.models import ReadingProgress
                from apps.reviews.models import BookRating

                book.is_favorited = Favorite.objects.filter(user=user, book=book).exists()
                try:
                    progress = ReadingProgress.objects.get(user=user, book=book)
                    book.user_progress = progress
                except ReadingProgress.DoesNotExist:
                    book.user_progress = None

                try:
                    rating = BookRating.objects.get(user=user, book=book)
                    book.user_rating = rating.rating
                except BookRating.DoesNotExist:
                    book.user_rating = None
            else:
                book.is_favorited = False
                book.user_progress = None
                book.user_rating = None

            return book
        except Book.DoesNotExist:
            return None

    @staticmethod
    def get_user_dashboard_data(user):
        from apps.favorites.models import Favorite
        from apps.reader.models import ReadingSession, ReadingGoal
        from django.db.models import Sum, Count
        from datetime import date

        today = date.today()
        week_ago = today - timedelta(days=7)

        favorites_count = Favorite.objects.filter(user=user).count()

        recent_sessions = ReadingSession.objects.filter(user=user, date__gte=week_ago).aggregate(
            total_words=Sum("words_read"), total_time=Sum("duration_seconds")
        )

        active_goals = ReadingGoal.objects.filter(user=user, is_active=True).values(
            "goal_type", "target_value", "current_value"
        )

        return {
            "favorites_count": favorites_count,
            "weekly_words": recent_sessions["total_words"] or 0,
            "weekly_time": recent_sessions["total_time"] or 0,
            "active_goals": list(active_goals),
        }


class CacheManager:
    CACHE_VERSIONS = {}

    @classmethod
    def get(cls, key, default=None, version=None):
        cache_key = cls._make_cache_key(key, version)
        return cache.get(cache_key, default)

    @classmethod
    def set(cls, key, value, timeout=None, version=None):
        cache_key = cls._make_cache_key(key, version)
        cache.set(cache_key, value, timeout)

    @classmethod
    def delete(cls, key, version=None):
        cache_key = cls._make_cache_key(key, version)
        cache.delete(cache_key)

    @classmethod
    def invalidate_pattern(cls, pattern):
        from django.core.cache import cache

        cache.delete_pattern(pattern)

    @classmethod
    def _make_cache_key(cls, key, version=None):
        if version is None:
            version = cls.CACHE_VERSIONS.get(key, 1)
        return f"{key}_v{version}"

    @classmethod
    def increment_version(cls, key):
        if key in cls.CACHE_VERSIONS:
            cls.CACHE_VERSIONS[key] += 1
        else:
            cls.CACHE_VERSIONS[key] = 1
        cls.invalidate_pattern(f"{key}_*")


def measure_query_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        query_time = end_time - start_time
        logger.debug(f"{func.__name__} 执行时间: {query_time:.3f}秒")
        return result

    return wrapper


def log_database_queries(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        initial_queries = len(connection.queries)
        result = func(*args, **kwargs)
        final_queries = len(connection.queries)
        query_count = final_queries - initial_queries
        logger.debug(f"{func.__name__} 执行了 {query_count} 个数据库查询")
        return result

    return wrapper


class PerformanceMonitor:
    @staticmethod
    def log_slow_queries(threshold=0.1):
        slow_queries = [q for q in connection.queries if float(q["time"]) > threshold]
        if slow_queries:
            logger.warning(f"发现 {len(slow_queries)} 个慢查询 (> {threshold}秒):")
            for query in slow_queries:
                logger.warning(f"  SQL: {query['sql'][:200]}... Time: {query['time']}s")

    @staticmethod
    def get_query_stats():
        if not connection.queries:
            return {"count": 0, "total_time": 0, "avg_time": 0}

        total_time = sum(float(q["time"]) for q in connection.queries)
        return {
            "count": len(connection.queries),
            "total_time": round(total_time, 3),
            "avg_time": round(total_time / len(connection.queries), 3) if connection.queries else 0,
        }


from datetime import timedelta
