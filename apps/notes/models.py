from django.db import models
from django.contrib.auth.models import User
from apps.books.models import Book
from apps.chapters.models import Chapter


class Bookmark(models.Model):
    BOOKMARK_TYPES = [
        ("chapter", "章节书签"),
        ("position", "位置书签"),
        ("temporary", "临时书签"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户", related_name="bookmarks")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="书籍", related_name="bookmarks")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name="章节", related_name="bookmarks")
    bookmark_type = models.CharField(max_length=15, choices=BOOKMARK_TYPES, default="chapter", verbose_name="书签类型")
    title = models.CharField(max_length=100, blank=True, verbose_name="标题")
    position = models.PositiveIntegerField(default=0, verbose_name="位置")
    note = models.TextField(blank=True, verbose_name="备注")
    color = models.CharField(max_length=7, default="#ffd700", verbose_name="颜色")
    is_auto = models.BooleanField(default=False, verbose_name="自动书签")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "书签"
        verbose_name_plural = "书签"
        ordering = ["chapter__chapter_number", "position"]
        unique_together = ["user", "chapter", "position"]
        indexes = [
            models.Index(fields=["user", "book"], name="bookmark_user_book_idx"),
            models.Index(fields=["user", "chapter"], name="bookmark_user_chapter_idx"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.book.title} - {self.chapter.title}"


class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户", related_name="notes")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="书籍", related_name="notes")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name="章节", related_name="notes")
    content = models.TextField(verbose_name="笔记内容")
    start_position = models.PositiveIntegerField(default=0, verbose_name="起始位置")
    end_position = models.PositiveIntegerField(default=0, verbose_name="结束位置")
    highlighted_text = models.TextField(blank=True, verbose_name="高亮文本")
    color = models.CharField(max_length=7, default="#ffeb3b", verbose_name="高亮颜色")
    is_public = models.BooleanField(default=False, verbose_name="是否公开")
    likes_count = models.PositiveIntegerField(default=0, verbose_name="点赞数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "笔记"
        verbose_name_plural = "笔记"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "book"], name="note_user_book_idx"),
            models.Index(fields=["user", "chapter"], name="note_user_chapter_idx"),
            models.Index(fields=["created_at"], name="note_created_at_idx"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.book.title} - 笔记 {self.id}"

    def add_like(self):
        self.likes_count += 1
        self.save(update_fields=["likes_count"])

    def remove_like(self):
        if self.likes_count > 0:
            self.likes_count -= 1
            self.save(update_fields=["likes_count"])


class NoteComment(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE, verbose_name="笔记", related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户", related_name="note_comments")
    content = models.TextField(verbose_name="评论内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "笔记评论"
        verbose_name_plural = "笔记评论"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username} - 评论 {self.id}"
