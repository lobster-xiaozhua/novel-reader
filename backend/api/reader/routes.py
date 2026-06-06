"""API v2 Reader Routes — 高性能阅读器接口"""
import logging
import os
from datetime import date, timedelta
from typing import List, Optional

from django.core.cache import cache
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Query

from ..auth.auth import jwt_auth
from ..schemas import ApiResponse, Meta, PaginatedData
from .schemas import (
    TagItem, BookListItem, RankingBook, CategoryItem, DiscoverFeed,
    ShelfBook, ShelfData, BookDetail, ChapterItem, ChapterContent,
    ProgressIn, ProgressOut, StatsTrackIn, DailyChart, UserStats,
    SearchBookItem, SearchResult, MessageOut,
)
from apps.books.models import Book, Tag
from apps.chapters.models import Chapter
from apps.favorites.models import Favorite
from apps.reader.models import ReadingProgress, ReadingStats
from apps.recommender.engine import recommend_for_user, recommend_similar_books

logger = logging.getLogger(__name__)
router = Router(tags=['reader'])

STATS_CACHE_TTL = 60
TRACK_DEDUP_TTL = 5
DISCOVER_TTL = 120


# ── Helper Functions ──

def _book_to_listitem(book) -> dict:
    """Convert a Book model instance to a BookListItem dict."""
    tags = [{'id': t.id, 'name': t.name, 'color': t.color} for t in book.tags.all()]
    ch_count = getattr(book, '_ch_count', None) or book.total_chapters or 0
    return {
        'id': book.id,
        'title': book.title,
        'author': book.author or '',
        'category': book.category or '',
        'description': book.description or '',
        'gradient': book.cover_gradient,
        'tags': tags,
        'chapter_count': ch_count,
        'total_chapters': book.total_chapters or 0,
        'created_at': book.created_at.isoformat() if book.created_at else '',
        'updated_at': book.updated_at.isoformat() if book.updated_at else '',
    }


def _book_to_ranking(book, fav_count: int = 0) -> dict:
    """Convert a Book model instance to a RankingBook dict."""
    tags = [{'id': t.id, 'name': t.name, 'color': t.color} for t in book.tags.all()]
    ch_count = getattr(book, '_ch_count', None) or book.total_chapters or 0
    return {
        'id': book.id,
        'title': book.title,
        'author': book.author or '',
        'category': book.category or '',
        'gradient': book.cover_gradient,
        'tags': tags,
        'chapter_count': ch_count,
        'fav_count': fav_count,
    }


def _rank_books(queryset, limit: int = 10) -> list:
    """Rank books by fav count and return a list of RankingBook dicts."""
    qs = queryset.prefetch_related('tags').annotate(
        _ch_count=Count('chapters'),
        _fav_count=Count('favorite'),
    ).order_by('-_fav_count', '-updated_at')[:limit]
    return [_book_to_ranking(b, fav_count=getattr(b, '_fav_count', 0)) for b in qs]


# ── Discover ──

@router.get('/discover', response=ApiResponse[DiscoverFeed])
def discover(request):
    """发现页：推荐 + 今日热门 + 本周热门 + 新书上架 + 分类"""
    user = request.user if request.user.is_authenticated else None
    cache_key = f'v2:discover:{user.id if user else "anon"}'
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug('[ReaderV2] 命中发现页缓存')
        return ApiResponse.ok(data=cached)

    now = timezone.now()
    limit = 10

    # 推荐
    recs = recommend_for_user(user=user, limit=limit, strategy='hybrid')
    recommendations = [
        {
            'id': r['id'], 'title': r['title'], 'author': r.get('author', ''),
            'category': r.get('category', ''), 'description': r.get('description', ''),
            'gradient': r.get('gradient', ('#667eea', '#764ba2')),
            'tags': r.get('tags', []), 'chapter_count': r.get('chapter_count', 0),
            'total_chapters': r.get('chapter_count', 0),
            'created_at': r.get('created_at', ''), 'updated_at': r.get('updated_at', ''),
        }
        for r in recs
    ]

    # 今日热门 (24h favorites)
    today_cutoff = now - timedelta(hours=24)
    hot_today_ids = list(
        Favorite.objects.filter(created_at__gte=today_cutoff)
        .values('book_id').annotate(cnt=Count('id'))
        .order_by('-cnt')[:limit]
        .values_list('book_id', flat=True)
    )
    if hot_today_ids:
        books_map = {
            b.id: b for b in Book.objects.filter(id__in=hot_today_ids)
            .prefetch_related('tags').annotate(_ch_count=Count('chapters'))
        }
        hot_today = [
            _book_to_ranking(books_map[bid], fav_count=0)
            for bid in hot_today_ids if bid in books_map
        ]
    else:
        hot_today = _rank_books(Book.objects.all(), limit)

    # 本周热门 (7d favorites)
    week_cutoff = now - timedelta(days=7)
    hot_week_ids = list(
        Favorite.objects.filter(created_at__gte=week_cutoff)
        .values('book_id').annotate(cnt=Count('id'))
        .order_by('-cnt')[:limit]
        .values_list('book_id', flat=True)
    )
    if hot_week_ids:
        books_map = {
            b.id: b for b in Book.objects.filter(id__in=hot_week_ids)
            .prefetch_related('tags').annotate(_ch_count=Count('chapters'))
        }
        hot_week = [
            _book_to_ranking(books_map[bid], fav_count=0)
            for bid in hot_week_ids if bid in books_map
        ]
    else:
        hot_week = _rank_books(Book.objects.all(), limit)

    # 新书上架
    new_arrivals = _rank_books(Book.objects.order_by('-created_at'), limit)

    # 分类
    categories = list(
        Book.objects.filter(category__isnull=False).exclude(category='')
        .values('category').annotate(count=Count('id'))
        .order_by('-count', 'category')[:20]
    )

    feed = DiscoverFeed(
        recommendations=recommendations,
        hot_today=hot_today,
        hot_week=hot_week,
        new_arrivals=new_arrivals,
        categories=[CategoryItem(**c) for c in categories],
    )
    cache.set(cache_key, feed.dict(), DISCOVER_TTL)
    logger.info(f'[ReaderV2] 发现页: {len(recommendations)}推荐, {len(hot_today)}今日热, {len(hot_week)}本周热, {len(new_arrivals)}新书, {len(categories)}分类')
    return ApiResponse.ok(data=feed.dict())


# ── Shelf ──

@router.get('/shelf', response=ApiResponse[ShelfData], auth=jwt_auth)
def shelf(request):
    """书架：收藏 + 最近阅读"""
    user = request.user

    # 收藏列表
    favs = Favorite.objects.filter(user=user).select_related('book').prefetch_related('book__tags').annotate(
        _ch_count=Count('book__chapters'),
    ).order_by('-created_at')[:50]

    favorites = []
    for f in favs:
        b = f.book
        progress = None
        rp = ReadingProgress.objects.filter(user=user, book=b).first()
        if rp:
            progress = {'chapter_id': rp.chapter_id, 'position': rp.position}
        favorites.append({
            'id': f.id, 'book_id': b.id, 'title': b.title, 'author': b.author or '',
            'category': b.category or '', 'gradient': b.cover_gradient,
            'chapter_count': getattr(b, '_ch_count', None) or b.total_chapters or 0,
            'progress': progress, 'created_at': f.created_at.isoformat(),
        })

    # 最近阅读
    recent = ReadingProgress.objects.filter(user=user).select_related('book').prefetch_related('book__tags').annotate(
        _ch_count=Count('book__chapters'),
    ).order_by('-updated_at')[:20]

    recent_reads = []
    for rp in recent:
        b = rp.book
        progress = {'chapter_id': rp.chapter_id, 'position': rp.position}
        recent_reads.append({
            'id': rp.id, 'book_id': b.id, 'title': b.title, 'author': b.author or '',
            'category': b.category or '', 'gradient': b.cover_gradient,
            'chapter_count': getattr(b, '_ch_count', None) or b.total_chapters or 0,
            'progress': progress, 'created_at': rp.updated_at.isoformat(),
        })

    logger.info(f'[ReaderV2] 书架: {len(favorites)}收藏, {len(recent_reads)}最近阅读')
    return ApiResponse.ok(data={'favorites': favorites, 'recent_reads': recent_reads})


# ── Book Detail ──

@router.get('/books/{book_id}', response=ApiResponse[BookDetail])
def book_detail(request, book_id: int):
    """书籍详情"""
    book = get_object_or_404(Book.objects.prefetch_related('tags'), id=book_id)
    is_fav = False
    progress = None
    if request.user.is_authenticated:
        is_fav = Favorite.objects.filter(user=request.user, book=book).exists()
        rp = ReadingProgress.objects.filter(user=request.user, book=book).first()
        if rp:
            progress = {'chapter_id': rp.chapter_id, 'position': rp.position}

    similar_recs = recommend_similar_books(book_id, limit=6)
    similar_books = [
        {
            'id': r['id'], 'title': r['title'], 'author': r.get('author', ''),
            'category': r.get('category', ''), 'description': r.get('description', ''),
            'gradient': r.get('gradient', ('#667eea', '#764ba2')),
            'tags': r.get('tags', []), 'chapter_count': r.get('chapter_count', 0),
            'total_chapters': r.get('chapter_count', 0),
            'created_at': r.get('created_at', ''), 'updated_at': r.get('updated_at', ''),
        }
        for r in similar_recs
    ]

    detail = {
        'id': book.id, 'title': book.title, 'author': book.author or '',
        'category': book.category or '', 'description': book.description or '',
        'total_chapters': book.total_chapters or 0,
        'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in book.tags.all()],
        'gradient': book.cover_gradient,
        'is_favorited': is_fav, 'reading_progress': progress,
        'similar_books': similar_books,
        'created_at': book.created_at.isoformat() if book.created_at else '',
        'updated_at': book.updated_at.isoformat() if book.updated_at else '',
    }
    logger.info(f'[ReaderV2] 书籍详情: {book.title} (id={book_id})')
    return ApiResponse.ok(data=detail)


# ── Chapters ──

@router.get('/books/{book_id}/chapters', response=ApiResponse[PaginatedData])
def book_chapters(request, book_id: int, page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200)):
    """书籍章节目录（分页）"""
    book = get_object_or_404(Book, id=book_id)
    total = book.chapters.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    chapters = book.chapters.all()[offset:offset + per_page]
    items = [
        {'id': ch.id, 'chapter_number': ch.chapter_number, 'title': ch.title, 'word_count': ch.word_count}
        for ch in chapters
    ]
    logger.info(f'[ReaderV2] 章节目录: book_id={book_id}, page={page}/{total_pages}, items={len(items)}')
    return ApiResponse.ok(
        data={'items': items, 'total': total},
        meta=Meta(page=page, total_pages=total_pages, total_items=total),
    )


# ── Read Chapter ──

@router.get('/books/{book_id}/chapters/{chapter_id}', response=ApiResponse[ChapterContent])
def read_chapter(request, book_id: int, chapter_id: int):
    """阅读章节内容（含前后章节导航）"""
    chapter = get_object_or_404(Chapter.objects.select_related('book'), book_id=book_id, id=chapter_id)
    content = ''
    cache_key = f'chapter_content:{chapter.id}'
    content = cache.get(cache_key)

    if content is None:
        if not chapter.file_path:
            logger.warning(f'[ReaderV2] 章节无文件路径: book_id={book_id}, chapter_id={chapter_id}')
        else:
            raw_path = chapter.file_path
            from django.conf import settings
            if os.path.isabs(raw_path):
                file_path = os.path.normpath(raw_path)
            else:
                file_path = None
                for root in settings.BOOKS_ROOTS:
                    candidate = os.path.normpath(os.path.join(str(root), raw_path))
                    if os.path.exists(candidate):
                        file_path = candidate
                        break
                if not file_path:
                    file_path = os.path.normpath(os.path.join(str(settings.BASE_DIR), raw_path))

            real_path = os.path.realpath(file_path)
            allowed = any(real_path.startswith(os.path.realpath(str(r))) for r in settings.BOOKS_ROOTS)
            if not allowed:
                logger.error(f'[ReaderV2] 文件路径越界: {real_path}')
                from ninja.errors import HttpError
                raise HttpError(403, '文件路径越界，访问被拒绝')
            elif not os.path.exists(file_path):
                logger.error(f'[ReaderV2] 文件不存在: {file_path}')
            else:
                for enc in ('utf-8', 'gbk', 'gb2312', 'utf-16'):
                    try:
                        with open(file_path, 'r', encoding=enc) as f:
                            content = f.read()
                        if content.strip():
                            cache.set(cache_key, content, 3600)
                            break
                    except UnicodeDecodeError:
                        continue
                    except Exception as exc:
                        logger.error(f'[ReaderV2] 读取失败 {file_path}: {exc}')
                        break

    # 前后章节
    prev_ch = Chapter.objects.filter(book_id=book_id, chapter_number__lt=chapter.chapter_number).order_by('-chapter_number').first()
    next_ch = Chapter.objects.filter(book_id=book_id, chapter_number__gt=chapter.chapter_number).order_by('chapter_number').first()

    result = {
        'id': chapter.id, 'chapter_number': chapter.chapter_number,
        'title': chapter.title, 'word_count': chapter.word_count,
        'content': content or '',
        'prev_chapter_id': prev_ch.id if prev_ch else None,
        'next_chapter_id': next_ch.id if next_ch else None,
        'book_id': book_id, 'book_title': chapter.book.title,
    }
    logger.info(f'[ReaderV2] 阅读章节: book_id={book_id}, ch={chapter.chapter_number}, prev={result["prev_chapter_id"]}, next={result["next_chapter_id"]}')
    return ApiResponse.ok(data=result)


# ── Progress ──

@router.post('/books/{book_id}/progress', response=ApiResponse[ProgressOut], auth=jwt_auth)
def save_progress(request, book_id: int, payload: ProgressIn):
    """保存阅读进度"""
    book = get_object_or_404(Book.objects.only('id', 'title', 'author', 'total_chapters'), id=payload.book_id)
    progress, _ = ReadingProgress.objects.update_or_create(
        user=request.user, book=book,
        defaults={'chapter_id': payload.chapter_id, 'position': payload.position},
    )
    chapter_title = None
    if progress.chapter_id:
        try:
            chapter_title = Chapter.objects.only('title').get(id=progress.chapter_id).title
        except Chapter.DoesNotExist:
            pass
    logger.info(f'[ReaderV2] 保存进度: {book.title} ch={progress.chapter_id}, pos={progress.position}')
    return ApiResponse.ok(data={
        'id': progress.id, 'book_id': progress.book_id, 'book_title': book.title,
        'chapter_id': progress.chapter_id, 'chapter_title': chapter_title,
        'position': progress.position, 'total_chapters': book.total_chapters or 0,
        'updated_at': progress.updated_at.isoformat(),
    })


# ── Track Stats ──

@router.post('/track-stats', response=ApiResponse[MessageOut], auth=jwt_auth)
def track_stats(request, payload: StatsTrackIn):
    """记录阅读时长统计"""
    if payload.seconds < 5 or payload.seconds > 3600:
        return ApiResponse.ok(data={'message': 'ok'})

    user = request.user
    dedup_key = f'v2:track_stats:{user.id}:{payload.chapter_id or 0}:{payload.seconds}'
    if cache.get(dedup_key):
        return ApiResponse.ok(data={'message': 'ok'})
    cache.set(dedup_key, True, TRACK_DEDUP_TTL)

    today = timezone.now().date()
    words = 0
    if payload.chapter_id:
        try:
            ch = Chapter.objects.only('word_count').get(pk=payload.chapter_id)
            words = ch.word_count or 0
        except Chapter.DoesNotExist:
            pass

    stats, created = ReadingStats.objects.get_or_create(
        user=user, date=today,
        defaults={'read_seconds': payload.seconds, 'chapters_read': 1, 'words_read': words},
    )
    if not created:
        ReadingStats.objects.filter(pk=stats.pk).update(
            read_seconds=F('read_seconds') + payload.seconds,
            chapters_read=F('chapters_read') + 1,
            words_read=F('words_read') + words,
        )
    logger.debug(f'[ReaderV2] 记录阅读: {payload.seconds}s, {words}字')
    return ApiResponse.ok(data={'message': 'ok'})


# ── User Stats ──

@router.get('/stats', response=ApiResponse[UserStats], auth=jwt_auth)
def user_stats(request, days: int = Query(7, ge=1, le=90)):
    """用户阅读统计（含7日图表）"""
    user = request.user
    cache_key = f'v2:user_stats:{user.id}:{days}'
    cached = cache.get(cache_key)
    if cached is not None:
        return ApiResponse.ok(data=cached)

    today = date.today()
    start = today - timedelta(days=days - 1)
    week_start = today - timedelta(days=today.weekday())

    total_books = Book.objects.count()
    reading_count = ReadingProgress.objects.filter(user=user).count()
    favorite_count = Favorite.objects.filter(user=user).count()

    daily_stats = list(
        ReadingStats.objects.filter(user=user, date__gte=start).values(
            'date', 'read_seconds', 'chapters_read', 'words_read',
        )
    )
    stats_map = {s['date']: s for s in daily_stats}

    today_stats = stats_map.get(today)
    week_chapters = sum(s['chapters_read'] for s in daily_stats if s['date'] >= week_start)
    total_words = sum(s['words_read'] for s in daily_stats)

    chart = []
    current = start
    while current <= today:
        s = stats_map.get(current)
        chart.append({
            'date': current.isoformat(),
            'minutes': round(s['read_seconds'] / 60, 1) if s else 0.0,
            'chapters': s['chapters_read'] if s else 0,
            'words': s['words_read'] if s else 0,
        })
        current += timedelta(days=1)

    result = {
        'total_books': total_books, 'reading_count': reading_count,
        'favorite_count': favorite_count,
        'today_chapters': today_stats['chapters_read'] if today_stats else 0,
        'today_minutes': round(today_stats['read_seconds'] / 60, 1) if today_stats else 0.0,
        'week_chapters': week_chapters, 'total_words': total_words, 'chart': chart,
    }
    cache.set(cache_key, result, STATS_CACHE_TTL)
    logger.info(f'[ReaderV2] 用户统计: user={user.username}, days={days}, today_ch={result["today_chapters"]}, today_min={result["today_minutes"]}')
    return ApiResponse.ok(data=result)


# ── Search ──

@router.get('/search', response=ApiResponse[SearchResult])
def search_books(
    request,
    q: str = Query('', description='搜索关键词'),
    category: str = Query('', description='分类筛选'),
    tag: str = Query('', description='标签筛选'),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """搜索书籍"""
    qs = Book.objects.prefetch_related('tags').annotate(_ch_count=Count('chapters'))

    query = q.strip()
    if query:
        qs = qs.filter(
            Q(title__icontains=query) | Q(author__icontains=query) | Q(description__icontains=query)
        )
    if category:
        qs = qs.filter(category=category)
    if tag:
        qs = qs.filter(tags__name=tag)

    total = qs.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    books = qs.order_by('-updated_at')[offset:offset + per_page]

    items = [
        {
            'id': b.id, 'title': b.title, 'author': b.author or '',
            'category': b.category or '', 'description': b.description or '',
            'gradient': b.cover_gradient,
            'chapter_count': getattr(b, '_ch_count', None) or b.total_chapters or 0,
        }
        for b in books
    ]
    logger.info(f'[ReaderV2] 搜索: q="{query}", cat="{category}", tag="{tag}", total={total}, page={page}/{total_pages}')
    return ApiResponse.ok(
        data={'items': items, 'total': total, 'page': page, 'total_pages': total_pages},
        meta=Meta(page=page, total_pages=total_pages, total_items=total),
    )


# ── Toggle Favorite ──

@router.post('/books/{book_id}/favorite', response=ApiResponse[MessageOut], auth=jwt_auth)
def add_favorite(request, book_id: int):
    """收藏书籍"""
    book = get_object_or_404(Book.objects.only('id', 'title'), id=book_id)
    if Favorite.objects.filter(user=request.user, book=book).exists():
        return ApiResponse.ok(data={'message': '已收藏'})
    Favorite.objects.create(user=request.user, book=book)
    logger.info(f'[ReaderV2] 添加收藏: {book.title}')
    return ApiResponse.ok(data={'message': '已收藏'})


@router.delete('/books/{book_id}/favorite', response=ApiResponse[MessageOut], auth=jwt_auth)
def remove_favorite(request, book_id: int):
    """取消收藏"""
    book = get_object_or_404(Book.objects.only('id', 'title'), id=book_id)
    fav = Favorite.objects.filter(user=request.user, book=book).first()
    if fav:
        fav.delete()
        logger.info(f'[ReaderV2] 取消收藏: {book.title}')
    return ApiResponse.ok(data={'message': '已取消收藏'})