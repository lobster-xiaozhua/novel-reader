import logging
import os
import re
import time

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.pagination import paginate

from apps.books.models import Book
from apps.chapters.models import Chapter
from apps.favorites.models import Favorite
from apps.reader.models import ReadingProgress
from apps.recommender.engine import recommend_for_user, recommend_similar_books, get_engine as get_rec_engine
from apps.recommender.search import search as hybrid_search, build_index as build_search_index, get_stats as get_search_stats

from .auth import jwt_auth, optional_jwt_auth
from .schemas import (
    BatchImportResult,
    BookDetailSchema,
    BookListSchema,
    CategoryWithCount,
    ChapterContentSchema,
    ChapterSchema,
    RankingBookSchema,
    RankingsResponse,
    SearchResponse,
)

logger = logging.getLogger(__name__)
router = Router()


@router.get('/books/', response=list[BookListSchema], auth=optional_jwt_auth)
@paginate
def list_books(request, tag: str = None, category: str = None, search: str = None):
    qs = Book.objects.prefetch_related('tags').annotate(
        _chapter_count=Count('chapters', output_field=models.IntegerField())
    )
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


# Specific routes MUST be defined before parameterized routes
@router.get('/books/rankings/', response=RankingsResponse, auth=optional_jwt_auth)
def get_rankings(request) -> dict:
    now = timezone.now()
    limit = 10

    today_cutoff = now - timezone.timedelta(hours=24)
    hot_today_qs = (
        Book.objects.prefetch_related('tags')
        .annotate(
            _today_favs=Count('favorite', filter=Q(favorite__created_at__gte=today_cutoff)),
            _ch_count=Count('chapters'),
        )
        .filter(_today_favs__gt=0)
        .order_by('-_today_favs', '-updated_at')[:limit]
    )
    if not hot_today_qs:
        hot_today_qs = (
            Book.objects.prefetch_related('tags')
            .annotate(_ch_count=Count('chapters'))
            .order_by('-updated_at')[:limit]
        )

    week_cutoff = now - timezone.timedelta(days=7)
    hot_week_qs = (
        Book.objects.prefetch_related('tags')
        .annotate(
            _week_favs=Count('favorite', filter=Q(favorite__created_at__gte=week_cutoff)),
            _ch_count=Count('chapters'),
        )
        .filter(_week_favs__gt=0)
        .order_by('-_week_favs', '-_ch_count', '-updated_at')[:limit]
    )
    if not hot_week_qs:
        hot_week_qs = (
            Book.objects.prefetch_related('tags')
            .annotate(_ch_count=Count('chapters'))
            .order_by('-_ch_count', '-updated_at')[:limit]
        )

    new_arrivals_qs = (
        Book.objects.prefetch_related('tags')
        .annotate(_ch_count=Count('chapters'))
        .order_by('-created_at')[:30]
    )

    logger.info('[Rankings] 获取排行榜成功')
    return {
        'hot_today': [
            {
                'id': b.id,
                'title': b.title,
                'author': b.author,
                'category': b.category,
                'gradient': b.cover_gradient,
                'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in b.tags.all()],
                'chapter_count': getattr(b, '_ch_count', None) or b.total_chapters or 0,
            }
            for b in hot_today_qs
        ],
        'hot_week': [
            {
                'id': b.id,
                'title': b.title,
                'author': b.author,
                'category': b.category,
                'gradient': b.cover_gradient,
                'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in b.tags.all()],
                'chapter_count': getattr(b, '_ch_count', None) or b.total_chapters or 0,
            }
            for b in hot_week_qs
        ],
        'new_arrivals': [
            {
                'id': b.id,
                'title': b.title,
                'author': b.author,
                'category': b.category,
                'gradient': b.cover_gradient,
                'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in b.tags.all()],
                'chapter_count': getattr(b, '_ch_count', None) or b.total_chapters or 0,
            }
            for b in new_arrivals_qs
        ],
    }


@router.get('/search/', response=SearchResponse, auth=optional_jwt_auth)
def search_books(request, q: str = '') -> dict:
    """快速搜索端点 - 使用SQL进行书名/作者/简介匹配"""
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


@router.get('/books/categories/', response=list[CategoryWithCount], auth=optional_jwt_auth)
def get_categories(request) -> list:
    qs = (
        Book.objects.filter(category__isnull=False)
        .exclude(category='')
        .values('category')
        .annotate(count=Count('id'))
        .order_by('-count', 'category')
    )
    logger.info(f'[Categories] 获取分类列表成功 ({qs.count()}个分类)')
    return list(qs)


# ── 书籍目录管理（必须在 /books/{book_id}/ 之前注册）──

import json as _json

_DIRS_CONFIG_PATH = os.path.join(str(settings.BASE_DIR), 'data', 'book_dirs.json')


def _load_dirs_config() -> dict:
    if os.path.exists(_DIRS_CONFIG_PATH):
        try:
            with open(_DIRS_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return _json.load(f)
        except Exception:
            pass
    return {'extra_dirs': []}


def _save_dirs_config(config: dict):
    os.makedirs(os.path.dirname(_DIRS_CONFIG_PATH), exist_ok=True)
    with open(_DIRS_CONFIG_PATH, 'w', encoding='utf-8') as f:
        _json.dump(config, f, ensure_ascii=False, indent=2)


def _scan_dir(path: str) -> dict:
    """扫描目录，返回书籍子文件夹列表"""
    if not os.path.isdir(path):
        return {'exists': False, 'books': [], 'file_count': 0}
    books = []
    file_count = 0
    try:
        for entry in sorted(os.scandir(path), key=lambda e: e.name):
            if entry.is_dir():
                ch_count = sum(1 for _ in os.scandir(entry.path) if _.is_file() and _.name.endswith('.txt'))
                if ch_count > 0:
                    books.append({'name': entry.name, 'chapters': ch_count})
            elif entry.is_file() and entry.name.endswith('.txt'):
                file_count += 1
        file_count += sum(b['chapters'] for b in books)
    except PermissionError:
        return {'exists': True, 'accessible': False, 'books': [], 'file_count': 0}
    return {'exists': True, 'accessible': True, 'books': books, 'file_count': file_count}


@router.get('/books/dirs/', auth=jwt_auth)
def list_book_dirs(request) -> dict:
    """列出所有书籍目录及其状态"""
    config = _load_dirs_config()
    main_dir = str(settings.BOOKS_DIR)
    dirs = [{'path': main_dir, 'type': '主目录', **_scan_dir(main_dir)}]
    for p in config.get('extra_dirs', []):
        dirs.append({'path': p, 'type': '外挂目录', **_scan_dir(p)})
    return {'success': True, 'dirs': dirs}


@router.post('/books/dirs/', auth=jwt_auth)
def add_book_dir(request, path: str) -> dict:
    """添加外挂书籍目录"""
    path = os.path.normpath(path)
    if not os.path.isabs(path):
        return {'success': False, 'error': '必须使用绝对路径'}
    config = _load_dirs_config()
    if path in config.get('extra_dirs', []):
        return {'success': False, 'error': '该目录已存在'}
    if path == str(settings.BOOKS_DIR):
        return {'success': False, 'error': '不能添加主目录'}
    config.setdefault('extra_dirs', []).append(path)
    _save_dirs_config(config)
    if not hasattr(settings, 'BOOKS_ROOTS'):
        settings.BOOKS_ROOTS = [settings.BOOKS_DIR]
    if path not in [str(r) for r in settings.BOOKS_ROOTS]:
        settings.BOOKS_ROOTS.append(type(settings.BOOKS_DIR)(path))
    os.makedirs(path, exist_ok=True)
    logger.info(f'[BookDirs] 添加外挂目录: {path}')
    return {'success': True, 'message': f'已添加: {path}', 'scan': _scan_dir(path)}


@router.delete('/books/dirs/', auth=jwt_auth)
def remove_book_dir(request, path: str) -> dict:
    """移除外挂书籍目录"""
    path = os.path.normpath(path)
    config = _load_dirs_config()
    if path not in config.get('extra_dirs', []):
        return {'success': False, 'error': '该目录不在外挂列表中'}
    config['extra_dirs'].remove(path)
    _save_dirs_config(config)
    if hasattr(settings, 'BOOKS_ROOTS'):
        settings.BOOKS_ROOTS = [r for r in settings.BOOKS_ROOTS if str(r) != path]
    logger.info(f'[BookDirs] 移除外挂目录: {path}')
    return {'success': True, 'message': f'已移除: {path}'}


@router.post('/books/dirs/scan/', auth=jwt_auth)
def scan_book_dir(request, path: str = '') -> dict:
    """扫描指定目录（或所有目录），发现新书籍并入库"""
    from apps.books.models import Book as BookModel
    from apps.chapters.models import Chapter as ChapterModel

    scan_paths = []
    if path:
        scan_paths = [os.path.normpath(path)]
    else:
        config = _load_dirs_config()
        scan_paths = [str(settings.BOOKS_DIR)] + config.get('extra_dirs', [])

    imported = 0
    errors = []
    for base in scan_paths:
        if not os.path.isdir(base):
            continue
        for entry in os.scandir(base):
            if not entry.is_dir():
                continue
            book_name = entry.name
            if BookModel.objects.filter(title=book_name).exists():
                continue
            ch_files = sorted(
                [f for f in os.scandir(entry.path) if f.is_file() and f.name.endswith('.txt')],
                key=lambda f: f.name,
            )
            if not ch_files:
                continue
            try:
                book = BookModel.objects.create(
                    title=book_name,
                    folder_path=entry.path,
                    total_chapters=len(ch_files),
                )
                for idx, f in enumerate(ch_files, 1):
                    ch_title = os.path.splitext(f.name)[0]
                    rel_path = os.path.relpath(f.path, str(settings.BOOKS_DIR))
                    if rel_path.startswith('..'):
                        rel_path = f.path
                    content = ''
                    for enc in ('utf-8', 'gbk', 'gb2312'):
                        try:
                            content = open(f.path, 'r', encoding=enc).read()
                            break
                        except (UnicodeDecodeError, Exception):
                            continue
                    ChapterModel.objects.create(
                        book=book, chapter_number=idx,
                        title=ch_title, file_path=rel_path,
                        word_count=len(content),
                    )
                imported += 1
                logger.info(f'[Scan] 发现新书: {book_name} ({len(ch_files)}章)')
            except Exception as exc:
                errors.append(f'{book_name}: {str(exc)[:100]}')

    if imported > 0:
        try:
            get_rec_engine().build_index(force=True)
            build_search_index(force=True)
        except Exception:
            pass

    return {'success': True, 'imported': imported, 'errors': errors}


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
    content = cache.get(cache_key)

    if content is None:
        if not chapter.file_path:
            logger.warning(f'[Chapter] 章节无文件路径: book_id={book_id}, chapter_id={chapter_id}')
        else:
            # 构建绝对路径：file_path 可能是相对路径或绝对路径
            raw_path = chapter.file_path

            if os.path.isabs(raw_path):
                file_path = os.path.normpath(raw_path)
            else:
                # 相对路径：依次尝试 BOOKS_ROOTS 中的每个根目录
                file_path = None
                for root in settings.BOOKS_ROOTS:
                    candidate = os.path.normpath(os.path.join(str(root), raw_path))
                    if os.path.exists(candidate):
                        file_path = candidate
                        break
                if not file_path:
                    # 兜底：拼接 BASE_DIR
                    file_path = os.path.normpath(os.path.join(str(settings.BASE_DIR), raw_path))

            # 安全检查：确保文件在任一 BOOKS_ROOTS 下
            real_file_path = os.path.realpath(file_path)
            allowed = any(
                real_file_path.startswith(os.path.realpath(str(root)))
                for root in settings.BOOKS_ROOTS
            )
            if not allowed:
                logger.error(f'[Chapter] 文件路径越界: real_path={real_file_path}, raw={raw_path}')
            elif not os.path.exists(file_path):
                logger.error(f'[Chapter] 文件不存在: {file_path}')
            else:
                # 尝试多种编码读取
                for enc in ('utf-8', 'gbk', 'gb2312', 'utf-16'):
                    try:
                        with open(file_path, 'r', encoding=enc) as f:
                            content = f.read()
                        if content.strip():
                            cache.set(cache_key, content, 300)
                            logger.info(f'[Chapter] 读取成功: {file_path} (编码: {enc}, 字数: {len(content)})')
                            break
                        else:
                            logger.warning(f'[Chapter] 文件内容为空: {file_path}')
                            break
                    except UnicodeDecodeError:
                        continue
                    except Exception as exc:
                        logger.error(f'[Chapter] 读取失败 {file_path}: {exc}')
                        break
                else:
                    logger.error(f'[Chapter] 所有编码都无法读取: {file_path}')

    return {
        'id': chapter.id,
        'chapter_number': chapter.chapter_number,
        'title': chapter.title,
        'word_count': chapter.word_count,
        'content': content or '',
    }


@router.get('/recommendations/', auth=optional_jwt_auth)
def get_recommendations(request, strategy: str = 'hybrid', limit: int = 20, page: int = 1):
    user = request.user if request.user.is_authenticated else None
    limit = min(limit, 50)
    all_recs = recommend_for_user(user=user, limit=limit * page, strategy=strategy)
    start = (page - 1) * limit
    page_recs = all_recs[start:start + limit]
    has_next = len(all_recs) > start + limit
    logger.info(f'[Recommendations] strategy={strategy}, page={page}, limit={limit}, returned={len(page_recs)}')
    return {
        'success': True,
        'data': page_recs,
        'pagination': {
            'page': page,
            'per_page': limit,
            'total': len(all_recs),
            'has_next': has_next,
        },
    }


@router.get('/books/{book_id}/similar/', auth=optional_jwt_auth)
def get_similar_books(request, book_id: int, limit: int = 6):
    results = recommend_similar_books(book_id, limit)
    logger.info(f'[Similar] book_id={book_id}, found={len(results)}')
    return {'success': True, 'data': results}


@router.get('/search/advanced/', auth=optional_jwt_auth)
def advanced_search(request, q: str = '', limit: int = 20, page: int = 1):
    query = q.strip()
    if not query or len(query) < 2:
        return {
            'success': False,
            'data': [],
            'pagination': {'page': page, 'per_page': limit, 'total': 0, 'has_next': False},
            'search_time_ms': 0,
        }

    start_time = time.monotonic()
    all_results = hybrid_search(query, limit=100)
    search_time_ms = (time.monotonic() - start_time) * 1000

    total = len(all_results)
    start = (page - 1) * limit
    page_results = all_results[start:start + limit]
    has_next = total > start + limit

    logger.info(f'[AdvancedSearch] query="{query}", total={total}, time={search_time_ms:.0f}ms')
    return {
        'success': True,
        'data': page_results,
        'pagination': {'page': page, 'per_page': limit, 'total': total, 'has_next': has_next},
        'search_time_ms': round(search_time_ms, 1),
    }


@router.get('/search/stats/', auth=optional_jwt_auth)
def search_engine_stats(request):
    stats = get_search_stats()
    return {'success': True, 'data': stats}


@router.post('/search/build-index/', auth=jwt_auth)
def build_search_engine_index(request, force: bool = False):
    count = build_search_index(force=force)
    logger.info(f'[SearchIndex] 索引构建完成: {count}本书')
    return {'success': True, 'message': f'索引构建完成: {count}本书'}


@router.post('/recommendations/build-index/', auth=jwt_auth)
def build_recommendation_index(request, force: bool = False):
    engine = get_rec_engine()
    count = engine.build_index(force=force)
    logger.info(f'[RecIndex] 推荐索引构建完成: {count}本书')
    return {'success': True, 'message': f'推荐索引构建完成: {count}本书'}

