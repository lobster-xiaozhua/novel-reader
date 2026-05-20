import logging
from datetime import date, timedelta
from django.db.models import Sum, Avg
from django.core.cache import cache
from apps.reader.models import ReadingSession, ReadingStatistics, ReadingGoal

logger = logging.getLogger(__name__)


class ReadingStatisticsService:
    CACHE_TIMEOUT = 300

    def __init__(self, user):
        self.user = user
        self.cache_prefix = f"reading_stats_{user.id}"

    def _get_cache(self, key):
        return cache.get(f"{self.cache_prefix}_{key}")

    def _set_cache(self, key, value, timeout=None):
        timeout = timeout or self.CACHE_TIMEOUT
        cache.set(f"{self.cache_prefix}_{key}", value, timeout)

    def _invalidate_cache(self):
        try:
            cache.clear()
        except Exception:
            pass

    def track_reading_session(self, book, chapter, words_read, duration_seconds, start_position=0, end_position=0):
        try:
            session = ReadingSession.objects.create(
                user=self.user,
                book=book,
                chapter=chapter,
                start_position=start_position,
                end_position=end_position,
                words_read=words_read,
                duration_seconds=duration_seconds,
            )
            self._invalidate_cache()
            self.update_daily_statistics()
            self.update_goals(words_read, duration_seconds)
            logger.info(f"阅读会话已记录: 用户={self.user.username}, 书籍={book.title}, 字数={words_read}")
            return session
        except Exception as e:
            logger.error(f"记录阅读会话失败: {e}")
            raise

    def update_daily_statistics(self):
        try:
            today = date.today()
            sessions_today = ReadingSession.objects.filter(user=self.user, date=today)
            if not sessions_today.exists():
                return None

            daily_stats, created = ReadingStatistics.objects.get_or_create(
                user=self.user,
                stats_type="daily",
                date=today,
                defaults={
                    "total_words_read": 0,
                    "total_reading_time": 0,
                },
            )
            daily_stats.update_from_sessions(sessions_today)

            week_start = today - timedelta(days=today.weekday())
            week_sessions = ReadingSession.objects.filter(user=self.user, date__gte=week_start, date__lte=today)
            weekly_stats, _ = ReadingStatistics.objects.get_or_create(
                user=self.user,
                stats_type="weekly",
                date=week_start,
                defaults={
                    "total_words_read": 0,
                    "total_reading_time": 0,
                },
            )
            weekly_stats.update_from_sessions(week_sessions)

            month_start = today.replace(day=1)
            month_sessions = ReadingSession.objects.filter(user=self.user, date__gte=month_start, date__lte=today)
            monthly_stats, _ = ReadingStatistics.objects.get_or_create(
                user=self.user,
                stats_type="monthly",
                date=month_start,
                defaults={
                    "total_words_read": 0,
                    "total_reading_time": 0,
                },
            )
            monthly_stats.update_from_sessions(month_sessions)

            self._invalidate_cache()
            return daily_stats
        except Exception as e:
            logger.error(f"更新日统计失败: {e}")
            raise

    def get_today_summary(self):
        cache_key = "today_summary"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        today = date.today()
        sessions = ReadingSession.objects.filter(user=self.user, date=today)
        summary = {
            "total_words": sessions.aggregate(Sum("words_read"))["words_read__sum"] or 0,
            "total_time": sessions.aggregate(Sum("duration_seconds"))["duration_seconds__sum"] or 0,
            "total_sessions": sessions.count(),
            "avg_speed": sessions.aggregate(Avg("reading_speed"))["reading_speed__avg"] or 0.0,
            "books_read": sessions.values("book").distinct().count(),
        }
        self._set_cache(cache_key, summary)
        return summary

    def get_weekly_report(self):
        cache_key = "weekly_report"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        today = date.today()
        week_ago = today - timedelta(days=7)
        sessions = ReadingSession.objects.filter(user=self.user, date__gte=week_ago, date__lte=today)
        daily_stats = []
        for i in range(7):
            day = week_ago + timedelta(days=i)
            day_sessions = sessions.filter(date=day)
            daily_stats.append(
                {
                    "date": day,
                    "words": day_sessions.aggregate(Sum("words_read"))["words_read__sum"] or 0,
                    "time": day_sessions.aggregate(Sum("duration_seconds"))["duration_seconds__sum"] or 0,
                }
            )

        report = {
            "total_words": sessions.aggregate(Sum("words_read"))["words_read__sum"] or 0,
            "total_time": sessions.aggregate(Sum("duration_seconds"))["duration_seconds__sum"] or 0,
            "avg_speed": sessions.aggregate(Avg("reading_speed"))["reading_speed__avg"] or 0.0,
            "days_active": sessions.values("date").distinct().count(),
            "daily_breakdown": daily_stats,
        }
        self._set_cache(cache_key, report, timeout=600)
        return report

    def get_monthly_report(self):
        cache_key = "monthly_report"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        today = date.today()
        month_start = today.replace(day=1)
        sessions = ReadingSession.objects.filter(user=self.user, date__gte=month_start, date__lte=today)

        report = {
            "total_words": sessions.aggregate(Sum("words_read"))["words_read__sum"] or 0,
            "total_time": sessions.aggregate(Sum("duration_seconds"))["duration_seconds__sum"] or 0,
            "avg_speed": sessions.aggregate(Avg("reading_speed"))["reading_speed__avg"] or 0.0,
            "total_sessions": sessions.count(),
            "books_started": sessions.values("book").distinct().count(),
        }
        self._set_cache(cache_key, report, timeout=600)
        return report

    def update_goals(self, words_read=0, duration_seconds=0):
        active_goals = ReadingGoal.objects.filter(
            user=self.user, is_active=True, is_completed=False, start_date__lte=date.today(), end_date__gte=date.today()
        )
        for goal in active_goals:
            if goal.goal_type == "words":
                goal.update_progress(words_read)
            elif goal.goal_type == "time":
                goal.update_progress(duration_seconds)
        self._invalidate_cache()

    def create_goal(self, goal_type, target_value, start_date=None, end_date=None):
        if not start_date:
            start_date = date.today()
        if not end_date:
            end_date = date.today() + timedelta(days=30)
        goal = ReadingGoal.objects.create(
            user=self.user,
            goal_type=goal_type,
            target_value=target_value,
            start_date=start_date,
            end_date=end_date,
        )
        logger.info(f"阅读目标已创建: 用户={self.user.username}, 类型={goal_type}, 目标={target_value}")
        return goal

    def get_active_goals(self):
        return ReadingGoal.objects.filter(
            user=self.user, is_active=True, is_completed=False, start_date__lte=date.today(), end_date__gte=date.today()
        )

    def get_streak_info(self):
        cache_key = "streak_info"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        today = date.today()
        current_streak = 0
        longest_streak = 0
        temp_streak = 0
        check_date = today

        while True:
            has_sessions = ReadingSession.objects.filter(user=self.user, date=check_date).exists()
            if has_sessions:
                temp_streak += 1
                if check_date <= today:
                    current_streak = temp_streak
            else:
                if temp_streak > longest_streak:
                    longest_streak = temp_streak
                temp_streak = 0
                if check_date < today - timedelta(days=1):
                    break
            check_date -= timedelta(days=1)
            if temp_streak == 0 and check_date < today - timedelta(days=1):
                break

        streak_info = {
            "current_streak": current_streak,
            "longest_streak": max(longest_streak, temp_streak),
        }
        self._set_cache(cache_key, streak_info, timeout=3600)
        return streak_info
