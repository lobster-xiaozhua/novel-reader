import os
import json
import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache
from apps.books.models import Book
from apps.reader.models import ReadingProgress, ReadingStats
from .models import Chapter

logger = logging.getLogger(__name__)


def _read_chapter_content(chapter):
    cache_key = f'chapter_content:{chapter.id}'
    content = cache.get(cache_key)
    if content is not None:
        return content

    if not os.path.exists(chapter.file_path):
        return '章节文件不存在'

    for encoding in ('utf-8', 'gbk', 'gb2312', 'utf-16'):
        try:
            with open(chapter.file_path, 'r', encoding=encoding) as f:
                content = f.read()
            cache.set(cache_key, content, 300)
            return content
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f'读取章节文件失败 {chapter.file_path}: {e}')
            break

    return '章节内容读取失败'


def chapter_read(request, book_id, chapter_id):
    book = get_object_or_404(Book, pk=book_id)
    chapter = get_object_or_404(Chapter, pk=chapter_id, book=book)

    all_chapters = list(book.chapters.values('id', 'chapter_number', 'title'))

    prev_chapter = None
    next_chapter = None
    try:
        current_idx = next(i for i, ch in enumerate(all_chapters) if ch['id'] == chapter_id)
        if current_idx > 0:
            prev_chapter = all_chapters[current_idx - 1]
        if current_idx < len(all_chapters) - 1:
            next_chapter = all_chapters[current_idx + 1]
    except StopIteration:
        pass

    progress = None
    if request.user.is_authenticated:
        progress = ReadingProgress.objects.filter(
            user=request.user, book=book
        ).select_related('chapter').first()

    content = _read_chapter_content(chapter)

    return JsonResponse({
        'book': {'id': book.id, 'title': book.title},
        'chapter': {
            'id': chapter.id,
            'chapter_number': chapter.chapter_number,
            'title': chapter.title,
            'word_count': chapter.word_count,
            'content': content,
        },
        'chapters': all_chapters,
        'progress': {'chapter_id': progress.chapter_id, 'position': progress.position} if progress else None,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
    })


@login_required
@require_POST
def save_progress(request, book_id):
    import json
    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    chapter_id = data.get('chapter_id')
    try:
        position = int(data.get('position', 0))
    except (ValueError, TypeError):
        position = 0

    book = get_object_or_404(Book, pk=book_id)
    chapter = get_object_or_404(Chapter, pk=chapter_id, book=book)

    ReadingProgress.objects.update_or_create(
        user=request.user,
        book=book,
        defaults={'chapter': chapter, 'position': position}
    )

    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def track_stats(request):
    import json
    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    try:
        seconds = int(data.get('seconds', 0))
        chapter_id = data.get('chapter_id', '0')
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': '参数错误'}, status=400)

    if seconds < 5:
        return JsonResponse({'status': 'ok'})

    from django.utils import timezone
    today = timezone.now().date()
    words = 0
    try:
        ch = Chapter.objects.get(pk=int(chapter_id))
        words = ch.word_count or 0
    except (Chapter.DoesNotExist, ValueError):
        pass

    stats, _ = ReadingStats.objects.get_or_create(
        user=request.user, date=today,
        defaults={'read_seconds': seconds, 'chapters_read': 1, 'words_read': words}
    )
    if not _:
        stats.read_seconds += seconds
        stats.chapters_read += 1
        stats.words_read += words
        stats.save(update_fields=['read_seconds', 'chapters_read', 'words_read'])

    logger.info(f'[Stats] {request.user.username} 阅读 {seconds}s 章节{chapter_id}')
    return JsonResponse({'status': 'ok'})
