import os
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from apps.books.models import Book
from apps.reader.models import ReadingProgress
from .models import Chapter


@login_required
def chapter_read(request, book_id, chapter_id):
    book = get_object_or_404(Book, pk=book_id)
    chapter = get_object_or_404(Chapter, pk=chapter_id, book=book)
    chapters = list(book.chapters.all().values('id', 'chapter_number', 'title'))

    # Get content
    content = ''
    if os.path.exists(chapter.file_path):
        try:
            with open(chapter.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            try:
                with open(chapter.file_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except:
                content = '章节内容读取失败'
    else:
        content = '章节文件不存在'

    # Get reading progress
    progress = ReadingProgress.objects.filter(user=request.user, book=book).first()

    # Find prev/next chapters
    prev_chapter = None
    next_chapter = None
    for i, ch in enumerate(chapters):
        if ch['id'] == chapter.id:
            if i > 0:
                prev_chapter = chapters[i - 1]
            if i < len(chapters) - 1:
                next_chapter = chapters[i + 1]
            break

    context = {
        'book': book,
        'chapter': chapter,
        'chapters': chapters,
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
    position = request.POST.get('position', 0)

    book = get_object_or_404(Book, pk=book_id)
    chapter = get_object_or_404(Chapter, pk=chapter_id, book=book)

    progress, _ = ReadingProgress.objects.update_or_create(
        user=request.user,
        book=book,
        defaults={'chapter': chapter, 'position': position}
    )

    return JsonResponse({'status': 'ok'})
