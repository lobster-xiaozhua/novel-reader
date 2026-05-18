import os
import logging
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from apps.books.models import Book
from apps.reader.models import ReadingProgress
from .models import Chapter

logger = logging.getLogger(__name__)


@login_required
def chapter_read(request, book_id, chapter_id):
    book = get_object_or_404(Book, pk=book_id)
    chapter = get_object_or_404(Chapter, pk=chapter_id, book=book)

    all_chapters = list(book.chapters.all().values('id', 'chapter_number', 'title'))

    prev_chapter = None
    next_chapter = None
    for i, ch in enumerate(all_chapters):
        if ch['id'] == chapter_id:
            if i > 0:
                prev_chapter = all_chapters[i - 1]
            if i < len(all_chapters) - 1:
                next_chapter = all_chapters[i + 1]
            break

    progress = ReadingProgress.objects.filter(user=request.user, book=book).select_related('chapter').first()

    content = ''
    if os.path.exists(chapter.file_path):
        try:
            with open(chapter.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(chapter.file_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except Exception:
                content = '章节内容读取失败'
        except Exception:
            content = '章节内容读取失败'
    else:
        content = '章节文件不存在'

    context = {
        'book': book,
        'chapter': chapter,
        'chapters': all_chapters,
        'content': content,
        'progress': progress,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
    }
    return render(request, 'chapters/read.html', context)


@login_required
@require_POST
def save_progress(request, book_id):
    chapter_id = request.POST.get('chapter_id')
    try:
        position = int(request.POST.get('position', 0))
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
