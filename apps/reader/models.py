from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book
from apps.chapters.models import Chapter


class ReadingProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="书籍")
    chapter = models.ForeignKey(Chapter, on_delete=models.SET_NULL, null=True, verbose_name="章节")
    position = models.PositiveIntegerField(default=0, verbose_name="阅读位置")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "阅读进度"
        verbose_name_plural = "阅读进度"
        unique_together = ["user", "book"]

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"


class ReadingSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户", related_name="reading_sessions")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="书籍", related_name="reading_sessions")
    chapter = models.ForeignKey(
        Chapter, on_delete=models.SET_NULL, null=True, verbose_name="章节", related_name="reading_sessions"
    )
    start_position = models.PositiveIntegerField(default=0, verbose_name="起始位置")
    end_position = models.PositiveIntegerField(default=0, verbose_name="结束位置")
    words_read = models.PositiveIntegerField(default=0, verbose_name="阅读字数")
    duration_seconds = models.PositiveIntegerField(default=0, verbose_name="阅读时长(秒)")
    reading_speed = models.FloatField(default=0.0, verbose_name="阅读速度(字/分钟)")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="开始时间")
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")
    date = models.DateField(auto_now_add=True, verbose_name="日期")

    class Meta:
        verbose_name = "阅读会话"
        verbose_name_plural = "阅读会话"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "date"], name="session_user_date_idx"),
            models.Index(fields=["user", "book"], name="session_user_book_idx"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.book.title} - {self.started_at}"

    def calculate_reading_speed(self):
        if self.duration_seconds > 0:
            self.reading_speed = (self.words_read / self.duration_seconds) * 60
            return self.reading_speed
        return 0.0

    def save(self, *args, **kwargs):
        self.calculate_reading_speed()
        super().save(*args, **kwargs)


class ReadingStatistics(models.Model):
    STATS_TYPES = [
        ("daily", "每日统计"),
        ("weekly", "每周统计"),
        ("monthly", "每月统计"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户", related_name="reading_statistics")
    stats_type = models.CharField(max_length=10, choices=STATS_TYPES, verbose_name="统计类型")
    date = models.DateField(verbose_name="统计日期")
    total_words_read = models.PositiveIntegerField(default=0, verbose_name="总阅读字数")
    total_reading_time = models.PositiveIntegerField(default=0, verbose_name="总阅读时长(秒)")
    books_started = models.PositiveIntegerField(default=0, verbose_name="开始阅读书籍数")
    books_finished = models.PositiveIntegerField(default=0, verbose_name="完成阅读书籍数")
    avg_reading_speed = models.FloatField(default=0.0, verbose_name="平均阅读速度")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "阅读统计"
        verbose_name_plural = "阅读统计"
        unique_together = ["user", "stats_type", "date"]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["user", "stats_type", "date"], name="stats_user_type_date_idx"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.stats_type} - {self.date}"

    def update_from_sessions(self, sessions):
        if sessions:
            self.total_words_read = sum(s.words_read for s in sessions)
            self.total_reading_time = sum(s.duration_seconds for s in sessions)
            speeds = [s.reading_speed for s in sessions if s.reading_speed > 0]
            self.avg_reading_speed = sum(speeds) / len(speeds) if speeds else 0.0
            self.books_started = len(set(s.book_id for s in sessions))
            self.save()


class ReadingGoal(models.Model):
    GOAL_TYPES = [
        ("words", "字数目标"),
        ("time", "时长目标"),
        ("chapters", "章节目标"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户", related_name="reading_goals")
    goal_type = models.CharField(max_length=10, choices=GOAL_TYPES, verbose_name="目标类型")
    target_value = models.PositiveIntegerField(verbose_name="目标值")
    current_value = models.PositiveIntegerField(default=0, verbose_name="当前值")
    start_date = models.DateField(verbose_name="开始日期")
    end_date = models.DateField(verbose_name="结束日期")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    is_completed = models.BooleanField(default=False, verbose_name="是否完成")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "阅读目标"
        verbose_name_plural = "阅读目标"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.get_goal_type_display()} - {self.target_value}"

    @property
    def progress_percentage(self):
        if self.target_value > 0:
            percentage = (self.current_value / self.target_value) * 100
            return min(percentage, 100.0)
        return 0.0

    def check_completion(self):
        if self.current_value >= self.target_value and not self.is_completed:
            self.is_completed = True
            self.is_active = False
            self.save()
            return True
        return False

    def update_progress(self, value):
        self.current_value += value
        self.save(update_fields=["current_value"])
        self.check_completion()
