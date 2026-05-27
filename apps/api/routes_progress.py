import logging

from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.pagination import paginate

from apps.books.models import Book
from apps.chapters.models import Chapter
from apps.reader.models import ReadingProgress, ReadingStats

from .auth import jwt_auth
from .schemas import MessageSchema, ProgressOut, ReadingProgressIn, StatsTrackIn

logger = logging.getLogger(__name__)
router = Router()

TRACK_DEDUP_TTL = 5


@router.get('/progress/', response=list[ProgressOut], auth=jwt_auth)
@paginate
def list_progress(request):
    qs = ReadingProgress.objects.filter(user=request.user).select_related('book', 'chapter')
    return [{
        'id': p.id,
        'book_id': p.book_id,
        'book_title': p.book.title,
        'book_author': p.book.author,
        'chapter_id': p.chapter_id,
        'chapter_title': p.chapter.title if p.chapter else None,
        'position': p.position,
        'total_chapters': p.book.total_chapters,
        'updated_at': p.updated_at.isoformat(),
    } for p in qs]


@router.post('/progress/', response=ProgressOut, auth=jwt_auth)
def create_progress(request, payload: ReadingProgressIn) -> dict:
    book = get_object_or_404(Book, id=payload.book_id)
    progress, _ = ReadingProgress.objects.update_or_create(
        user=request.user,
        book=book,
        defaults={'chapter_id': payload.chapter_id, 'position': payload.position},
    )
    logger.info(f'[Progress] 更新阅读进度: {book.title} - 位置{progress.position}')
    return {
        'id': progress.id,
        'book_id': progress.book_id,
        'book_title': progress.book.title,
        'book_author': progress.book.author,
        'chapter_id': progress.chapter_id,
        'chapter_title': progress.chapter.title if progress.chapter else None,
        'position': progress.position,
        'total_chapters': progress.book.total_chapters,
        'updated_at': progress.updated_at.isoformat(),
    }


@router.post('/progress/track-stats/', response=MessageSchema, auth=jwt_auth)
def track_stats(request, payload: StatsTrackIn) -> dict:
    if payload.seconds < 5 or payload.seconds > 3600:
        return {'message': 'ok'}

    user = request.user
    dedup_key = f'track_stats:{user.id}:{payload.chapter_id or 0}:{payload.seconds}'
    if cache.get(dedup_key):
        return {'message': 'ok'}
    cache.set(dedup_key, True, TRACK_DEDUP_TTL)

    today = timezone.now().date()
    words: int = 0
    if payload.chapter_id:
        try:
            ch = Chapter.objects.get(pk=payload.chapter_id)
            words = ch.word_count or 0
        except Chapter.DoesNotExist:
            pass

    with transaction.atomic():
        stats_obj, created = ReadingStats.objects.select_for_update().get_or_create(
            user=user,
            date=today,
            defaults={'read_seconds': payload.seconds, 'chapters_read': 1, 'words_read': words},
        )
        if not created:
            stats_obj.read_seconds = F('read_seconds') + payload.seconds
            stats_obj.chapters_read = F('chapters_read') + 1
            stats_obj.words_read = F('words_read') + words
            stats_obj.save(update_fields=['read_seconds', 'chapters_read', 'words_read'])
    logger.debug(f'[Stats] 记录阅读: {payload.seconds}s, {words}字')
    return {'message': 'ok'}
