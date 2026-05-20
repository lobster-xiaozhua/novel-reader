from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book


class BookRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户", related_name="book_ratings")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="书籍", related_name="ratings")
    rating = models.PositiveSmallIntegerField(verbose_name="评分", help_text="1-5星")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "书籍评分"
        verbose_name_plural = "书籍评分"
        unique_together = ["user", "book"]

    def __str__(self):
        return f"{self.user.username} - {self.book.title} - {self.rating}星"

    def save(self, *args, **kwargs):
        if not 1 <= self.rating <= 5:
            raise ValueError("评分必须在1-5之间")
        super().save(*args, **kwargs)


class BookReview(models.Model):
    REVIEW_STATUS = [
        ("pending", "待审核"),
        ("approved", "已通过"),
        ("rejected", "已拒绝"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户", related_name="book_reviews")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="书籍", related_name="reviews")
    title = models.CharField(max_length=200, blank=True, verbose_name="评论标题")
    content = models.TextField(verbose_name="评论内容")
    rating = models.PositiveSmallIntegerField(verbose_name="评分", help_text="1-5星")
    likes_count = models.PositiveIntegerField(default=0, verbose_name="点赞数")
    status = models.CharField(max_length=10, choices=REVIEW_STATUS, default="approved", verbose_name="状态")
    is_spoiler = models.BooleanField(default=False, verbose_name="包含剧透")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "书籍评论"
        verbose_name_plural = "书籍评论"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["book", "status", "created_at"], name="review_book_status_idx"),
            models.Index(fields=["user", "book"], name="review_user_book_idx"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.book.title} - 评论 {self.id}"

    def add_like(self):
        self.likes_count += 1
        self.save(update_fields=["likes_count"])

    def remove_like(self):
        if self.likes_count > 0:
            self.likes_count -= 1
            self.save(update_fields=["likes_count"])


class ReviewComment(models.Model):
    review = models.ForeignKey(BookReview, on_delete=models.CASCADE, verbose_name="评论", related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户", related_name="review_comments")
    content = models.TextField(verbose_name="评论内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "评论回复"
        verbose_name_plural = "评论回复"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username} - 回复 {self.id}"
