from django.contrib import admin
from .models import BookRating, BookReview, ReviewComment


@admin.register(BookRating)
class BookRatingAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "rating", "created_at"]
    list_filter = ["rating", "created_at"]
    search_fields = ["user__username", "book__title"]


@admin.register(BookReview)
class BookReviewAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "title", "rating", "likes_count", "status", "is_spoiler", "created_at"]
    list_filter = ["status", "is_spoiler", "rating", "created_at"]
    search_fields = ["user__username", "book__title", "title", "content"]
    readonly_fields = ["likes_count", "created_at", "updated_at"]


@admin.register(ReviewComment)
class ReviewCommentAdmin(admin.ModelAdmin):
    list_display = ["review", "user", "content_preview", "created_at"]
    search_fields = ["user__username", "content"]
    readonly_fields = ["created_at"]

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_preview.short_description = "内容预览"
