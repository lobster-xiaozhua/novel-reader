from datetime import date, timedelta
from typing import List, Optional
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema, Field
from ninja.pagination import paginate
from ninja.security import SessionAuth
from ninja.errors import HttpError

from apps.books.models import Book, Tag
from apps.chapters.models import Chapter
from apps.reader.models import ReadingProgress, ReadingStats
from apps.favorites.models import Favorite
from apps.crawler.models import CrawlerTask

api = NinjaAPI(
    title='NovelReader API',
    version='1.0.0',
    description='高性能小说阅读器 API',
    auth=SessionAuth(),
    docs_url='/docs/',
    openapi_url='/openapi.json',
)


# ========== Schemas ==========

class TagSchema(Schema):
    id: int
    name: str
    color: str = '#f59e0b'


class BookListSchema(Schema):
    id: int
    title: str
    author: str = ''
    category: str = ''
    description: str = ''
    total_chapters: int = 0
    chapter_count: int = 0
    tags: List[TagSchema] = []
    gradient: tuple = ('#667eea', '#764ba2')
    created_at: str
    updated_at: str


class BookDetailSchema(Schema):
    id: int
    title: str
    author: str = ''
    category: str = ''
    description: str = ''
    total_chapters: int = 0
    tags: List[TagSchema] = []
    gradient: tuple = ('#667eea', '#764ba2')
    is_favorited: bool = False
    reading_progress: Optional[dict] = None
    created_at: str
    updated_at: str


class ChapterSchema(Schema):
    id: int
    chapter_number: int
    title: str
    word_count: int = 0


class ChapterContentSchema(Schema):
    id: int
    chapter_number: int
    title: str
    word_count: int = 0
    content: str = ''


class ReadingProgressSchema(Schema):
    id: int
    book_id: int
    chapter_id: Optional[int] = None
    position: int = 0
    updated_at: str


class ReadingProgressIn(Schema):
    book_id: int
    chapter_id: Optional[int] = None
    position: int = 0


class CrawlerTaskSchema(Schema):
    id: int
    url: str
    status: str
    total_chapters: int = 0
    downloaded_chapters: int = 0
    error_message: str = ''
    created_at: str
    updated_at: str


class CrawlerTaskIn(Schema):
    url: str


class DailyStat(Schema):
    date: str
    minutes: float = 0.0
    chapters: int = 0
    words: int = 0


class UserStatsSchema(Schema):
    total_books: int
    reading_count: int
    favorite_count: int
    today_chapters: int = 0
    today_minutes: float = 0.0
    week_chapters: int = 0
    total_words: int = 0
    chart: List[DailyStat] = []


class MessageSchema(Schema):
    message: str


# ========== Helpers ==========

def book_gradient(book_id: Optional[int]) -> tuple:
    colors = [
        ('#667eea', '#764ba2'),
        ('#f093fb', '#f5576c'),
        ('#4facfe', '#00f2fe'),
        ('#43e97b', '#38f9d7'),
        ('#fa709a', '#fee140'),
        ('#30cfd0', '#330867'),
        ('#a8edea', '#fed6e3'),
        ('#ff9a9e', '#fecfef'),
    ]
    idx = (book_id or 0) % len(colors)
    return colors[idx]


# ========== Books ==========

@api.get('/books/', response=List[BookListSchema])
@paginate
def list_books(request, tag: Optional[str] = None, category: Optional[str] = None, search: Optional[str] = None):
    qs = Book.objects.prefetch_related('tags').all()
    if tag:
        qs = qs.filter(tags__name=tag)
    if category:
        qs = qs.filter(category=category)
    if search:
        qs = qs.filter(title__icontains=search) | qs.filter(author__icontains=search)
    return qs


@api.get('/books/{book_id}/', response=BookDetailSchema)
def get_book(request, book_id: int):
    book = get_object_or_404(Book.objects.prefetch_related('tags'), id=book_id)
    is_fav = False
    progress = None
    if request.user.is_authenticated:
        is_fav = Favorite.objects.filter(user=request.user, book=book).exists()
        rp = ReadingProgress.objects.filter(user=request.user, book=book).first()
        if rp:
            progress = {'chapter_id': rp.chapter_id, 'position': rp.position}
    return {
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'category': book.category,
        'description': book.description,
        'total_chapters': book.total_chapters,
        'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in book.tags.all()],
        'gradient': book_gradient(book.id),
        'is_favorited': is_fav,
        'reading_progress': progress,
        'created_at': book.created_at.isoformat(),
        'updated_at': book.updated_at.isoformat(),
    }


@api.get('/books/{book_id}/chapters/', response=List[ChapterSchema])
def list_chapters(request, book_id: int):
    book = get_object_or_404(Book, id=book_id)
    return book.chapters.all()


@api.get('/books/{book_id}/chapters/{chapter_id}/', response=ChapterContentSchema)
def get_chapter_content(request, book_id: int, chapter_id: int):
    chapter = get_object_or_404(Chapter, book_id=book_id, id=chapter_id)
    content = ''
    import os
    from django.core.cache import cache
    cache_key = f'chapter_content:{chapter.id}'
    content = cache.get(cache_key)
    if content is None and os.path.exists(chapter.file_path):
        for enc in ('utf-8', 'gbk', 'gb2312', 'utf-16'):
            try:
                with open(chapter.file_path, 'r', encoding=enc) as f:
                    content = f.read()
                cache.set(cache_key, content, 300)
                break
            except (UnicodeDecodeError, Exception):
                continue
    return {
        'id': chapter.id,
        'chapter_number': chapter.chapter_number,
        'title': chapter.title,
        'word_count': chapter.word_count,
        'content': content,
    }


# ========== Progress ==========

@api.get('/progress/', response=List[ReadingProgressSchema])
@paginate
def list_progress(request):
    if not request.user.is_authenticated:
        raise HttpError(401, '未登录')
    qs = ReadingProgress.objects.filter(user=request.user)
    return [{
        'id': p.id,
        'book_id': p.book_id,
        'chapter_id': p.chapter_id,
        'position': p.position,
        'updated_at': p.updated_at.isoformat(),
    } for p in qs]


@api.post('/progress/', response=ReadingProgressSchema)
def create_progress(request, payload: ReadingProgressIn):
    if not request.user.is_authenticated:
        raise HttpError(401, '未登录')
    progress, _ = ReadingProgress.objects.update_or_create(
        user=request.user,
        book_id=payload.book_id,
        defaults={
            'chapter_id': payload.chapter_id,
            'position': payload.position,
        }
    )
    return {
        'id': progress.id,
        'book_id': progress.book_id,
        'chapter_id': progress.chapter_id,
        'position': progress.position,
        'updated_at': progress.updated_at.isoformat(),
    }


# ========== Crawler ==========

@api.get('/crawler/', response=List[CrawlerTaskSchema])
@paginate
def list_crawler_tasks(request):
    if not request.user.is_authenticated:
        raise HttpError(401, '未登录')
    return CrawlerTask.objects.filter(user=request.user)


@api.post('/crawler/', response=CrawlerTaskSchema)
def create_crawler_task(request, payload: CrawlerTaskIn):
    if not request.user.is_authenticated:
        raise HttpError(401, '未登录')
    task = CrawlerTask.objects.create(
        user=request.user,
        url=payload.url,
        status='pending',
    )
    from apps.crawler.tasks import run_crawler_task
    run_crawler_task.delay(task.id)
    return task


# ========== Stats ==========

@api.get('/stats/', response=UserStatsSchema)
def get_user_stats(request, days: int = 7):
    if not request.user.is_authenticated:
        raise HttpError(401, '未登录')
    user = request.user
    today = date.today()
    total_books = Book.objects.count()
    reading_count = ReadingProgress.objects.filter(user=user).count()
    favorite_count = Favorite.objects.filter(user=user).count()

    today_stats = ReadingStats.objects.filter(user=user, date=today).first()
    week_start = today - timedelta(days=today.weekday())
    week_stats = ReadingStats.objects.filter(user=user, date__gte=week_start)
    week_chapters = sum(s.chapters_read for s in week_stats)
    total_words = sum(s.words_read for s in ReadingStats.objects.filter(user=user))

    start = today - timedelta(days=days - 1)
    daily_stats = ReadingStats.objects.filter(user=user, date__gte=start)
    stats_map = {s.date: s for s in daily_stats}

    chart = []
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
        'week_chapters': week_chapters,
        'total_words': total_words,
        'chart': chart,
    }
