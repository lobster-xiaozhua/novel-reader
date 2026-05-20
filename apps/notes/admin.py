from django.contrib import admin
from .models import Bookmark, Note, NoteComment


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "chapter", "bookmark_type", "title", "created_at"]
    list_filter = ["bookmark_type", "created_at"]
    search_fields = ["user__username", "book__title", "title"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "chapter", "content_preview", "is_public", "likes_count", "created_at"]
    list_filter = ["is_public", "created_at"]
    search_fields = ["user__username", "book__title", "content"]
    readonly_fields = ["created_at", "updated_at", "likes_count"]

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_preview.short_description = "内容预览"


@admin.register(NoteComment)
class NoteCommentAdmin(admin.ModelAdmin):
    list_display = ["note", "user", "content_preview", "created_at"]
    search_fields = ["user__username", "content"]
    readonly_fields = ["created_at", "updated_at"]

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_preview.short_description = "内容预览"
