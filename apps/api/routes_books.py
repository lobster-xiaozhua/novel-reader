import logging
import os
import re

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate

from apps.books.models import Book
from apps.chapters.models import Chapter
from apps.favorites.models import Favorite
from apps.reader.models import ReadingProgress

from .auth import jwt_auth, optional_jwt_auth
from .schemas import (
    BatchImportResult,
    BookDetailSchema,
    BookListSchema,
    ChapterContentSchema,
    ChapterSchema,
    SearchResponse,
)

logger = logging.getLogger(__name__)
router = Router()


@router.get('/books/', response=list[BookListSchema], auth=optional_jwt_auth)
@paginate
def list_books(request, tag: str = None, category: str = None, search: str = None):
    qs = Book.objects.prefetch_related('tags').annotate(
        _chapter_count=Count('chapters', output_field=models.IntegerField())
    ).order_by('-created_at')
    if tag:
        qs = qs.filter(tags__name=tag)
    if category:
        qs = qs.filter(category=category)
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(author__icontains=search))
    return qs


@router.post('/books/import/', response=BatchImportResult, auth=jwt_auth)
def batch_import(request) -> dict:
    files = request.FILES.getlist('files')
    if not files:
        return {'success': False, 'errors': ['未选择文件'], 'total': 0}
    imported: int = 0
    errors: list[str] = []
    for f in files:
        if not f.name.endswith('.txt'):
            errors.append(f'{f.name}: 仅支持txt格式')
            continue
        try:
            raw = f.read()
            text = None
            for enc in ('utf-8', 'gbk', 'gb2312'):
                try:
                    text = raw.decode(enc)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            if text is None:
                errors.append(f'{f.name}: 编码无法识别')
                continue
            title = os.path.splitext(f.name)[0].strip()
            if not title:
                errors.append(f'{f.name}: 无法提取书名')
                continue
            safe_name = re.sub(r'[\\/:*?"<>|]', '_', title)[:100]
            book_dir = os.path.join(str(settings.BOOKS_DIR), safe_name)
            book, created = Book.objects.get_or_create(
                title=title,
                defaults={'author': '', 'folder_path': book_dir},
            )
            if not created and book.chapters.exists():
                errors.append(f'{title}: 已存在')
                continue
            os.makedirs(book_dir, exist_ok=True)
            if not book.folder_path:
                book.folder_path = book_dir
                book.save()
            chapter_pattern = re.compile(
                r'^(第[零一二三四五六七八九十百千万\d]+章|chapter\s*\d+|第\d+章|卷[零一二三四五六七八九十百千万\d]+)',
                re.IGNORECASE | re.MULTILINE,
            )
            parts = chapter_pattern.split(text)
            chapters_data: list[tuple[str, str]] = []
            if len(parts) > 1:
                i = 1
                while i < len(parts):
                    ch_title = parts[i].strip()
                    ch_content = parts[i + 1].strip() if i + 1 < len(parts) else ''
                    if ch_title:
                        chapters_data.append((ch_title, ch_content))
                    i += 2
            else:
                paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
                chunk_size = max(1, len(paragraphs) // max(1, len(paragraphs) // 50))
                for idx in range(0, len(paragraphs), chunk_size):
                    chunk = paragraphs[idx:idx + chunk_size]
                    ch_num = idx // chunk_size + 1
                    chapters_data.append((f'第{ch_num}章', '\n'.join(chunk)))
            for idx, (ch_title, ch_content) in enumerate(chapters_data, 1):
                ch_path = os.path.join(book_dir, f'第{idx}章.txt')
                with open(ch_path, 'w', encoding='utf-8') as wf:
                    wf.write(f'{ch_title}\n\n{ch_content}')
                Chapter.objects.update_or_create(
                    book=book, chapter_number=idx,
                    defaults={'title': ch_title, 'file_path': ch_path, 'word_count': len(ch_content)},
                )
            book.total_chapters = len(chapters_data)
            book.save()
            imported += 1
            logger.info(f'[Import] 导入成功: {title} ({len(chapters_data)}章)')
        except Exception as exc:
            logger.error(f'[Import] 导入失败 {f.name}: {exc}')
            errors.append(f'{f.name}: {str(exc)[:100]}')
    return {'success': True, 'imported': imported, 'errors': errors, 'total': len(files)}


@router.get('/books/{book_id}/', response=BookDetailSchema, auth=optional_jwt_auth)
def get_book(request, book_id: int) -> dict:
    book = get_object_or_404(Book.objects.prefetch_related('tags'), id=book_id)
    is_fav: bool = False
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
        'gradient': book.cover_gradient,
        'is_favorited': is_fav,
        'reading_progress': progress,
        'created_at': book.created_at.isoformat(),
        'updated_at': book.updated_at.isoformat(),
    }


@router.get('/books/{book_id}/chapters/', response=list[ChapterSchema], auth=optional_jwt_auth)
def list_chapters(request, book_id: int):
    book = get_object_or_404(Book, id=book_id)
    return book.chapters.all()


@router.get('/books/{book_id}/chapters/{chapter_id}/', response=ChapterContentSchema, auth=optional_jwt_auth)
def get_chapter_content(request, book_id: int, chapter_id: int) -> dict:
    chapter = get_object_or_404(Chapter, book_id=book_id, id=chapter_id)
    content: str = ''
    cache_key = f'chapter_content:{chapter.id}'
    cached = cache.get(cache_key)
    if cached is not None:
        content = cached
    elif chapter.file_path:
        file_path = os.path.normpath(chapter.file_path)
        books_root = os.path.normpath(str(settings.BOOKS_DIR))
        if not file_path.startswith(books_root):
            logger.error(f'[Chapter] 文件路径越界: {chapter.file_path}')
        elif os.path.exists(file_path):
            for enc in ('utf-8', 'gbk', 'gb2312', 'utf-16'):
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        content = f.read()
                    cache.set(cache_key, content, 300)
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as exc:
                    logger.error(f'[Chapter] 读取失败 {file_path}: {exc}')
                    break
    return {
        'id': chapter.id,
        'chapter_number': chapter.chapter_number,
        'title': chapter.title,
        'word_count': chapter.word_count,
        'content': content or '',
    }


@router.get('/search/', response=SearchResponse, auth=optional_jwt_auth)
def search_books(request, q: str = '') -> dict:
    query: str = q.strip()
    results: list[dict] = []
    suggestions: list[str] = []
    total: int = 0
    if query:
        qs = Book.objects.filter(
            Q(title__icontains=query) | Q(author__icontains=query) | Q(description__icontains=query)
        )
        total = qs.count()
        results = [
            {'id': b.id, 'title': b.title, 'author': b.author, 'category': b.category}
            for b in qs[:20]
        ]
    if len(query) >= 2:
        suggestions = list(
            Book.objects.filter(title__istartswith=query).values_list('title', flat=True)[:10]
        )
    return {'query': query, 'results': results, 'total': total, 'suggestions': suggestions}
