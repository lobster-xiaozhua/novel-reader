import json
import logging
import os
import re
import shutil
from datetime import date, timedelta
from typing import List, Optional

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from ninja.pagination import paginate
from ninja.security import SessionAuth

from apps.books.models import Book, Tag
from apps.chapters.models import Chapter
from apps.reader.models import ReadingProgress, ReadingStats
from apps.favorites.models import Favorite
from apps.crawler.models import CrawlerTask

logger = logging.getLogger(__name__)


class OptionalSessionAuth(SessionAuth):
    def __call__(self, request):
        return request.user if request.user.is_authenticated else True


class SessionAuthNoCSRF(SessionAuth):
    def __call__(self, request):
        if request.user and request.user.is_authenticated:
            return request.user
        return None


optional_auth = OptionalSessionAuth()
session_auth = SessionAuthNoCSRF()

api = NinjaAPI(
    title='NovelReader API',
    version='2.0.0',
    description='高性能小说阅读器 API',
    docs_url='/docs/',
    openapi_url='/openapi.json',
)


@api.exception_handler(Exception)
def global_exception_handler(request, exc):
    logger.error(f'API Error: {request.path} - {type(exc).__name__}: {str(exc)}')
    from ninja.errors import HttpError
    if isinstance(exc, HttpError):
        raise exc
    return api.create_response(request, {'error': str(exc)}, status=500)


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

    @staticmethod
    def resolve_created_at(obj):
        if hasattr(obj, 'created_at'):
            val = obj.created_at
            return val.isoformat() if isinstance(val, timezone.datetime) else str(val)
        return ''

    @staticmethod
    def resolve_updated_at(obj):
        if hasattr(obj, 'updated_at'):
            val = obj.updated_at
            return val.isoformat() if isinstance(val, timezone.datetime) else str(val)
        return ''


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


class ProgressOut(Schema):
    id: int
    book_id: int
    book_title: str
    book_author: str
    chapter_id: Optional[int] = None
    chapter_title: Optional[str] = None
    position: int
    total_chapters: int
    updated_at: str


class ReadingProgressIn(Schema):
    book_id: int
    chapter_id: Optional[int] = None
    position: int = 0


class StatsTrackIn(Schema):
    seconds: int = 0
    chapter_id: Optional[int] = None


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


class CrawlerTaskDetailSchema(Schema):
    id: int
    url: str
    status: str
    total_chapters: int = 0
    downloaded_chapters: int = 0
    error_message: str = ''
    logs: list = []
    created_at: str
    updated_at: str


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


class TagListSchema(Schema):
    id: int
    name: str
    color: str
    book_count: int


class TagIn(Schema):
    name: str
    color: str = '#f59e0b'


class FavoriteSchema(Schema):
    id: int
    book_id: int
    title: str
    author: str
    category: str
    total_chapters: int
    created_at: str


class FavoriteToggleIn(Schema):
    book_id: int


class UserSchema(Schema):
    id: int
    username: str
    email: str
    is_staff: bool
    date_joined: str
    last_login: Optional[str] = None
    book_count: int = 0


class LoginIn(Schema):
    username: str
    password: str


class RegisterIn(Schema):
    username: str
    password: str
    email: str = ''


class UserOut(Schema):
    id: int
    username: str
    email: str
    is_staff: bool


class AuthResponse(Schema):
    success: bool
    user: Optional[UserOut] = None
    error: str = ''


class BatchImportResult(Schema):
    success: bool
    imported: int = 0
    errors: List[str] = []
    total: int = 0


class HealthSchema(Schema):
    status: str
    database: str = 'ok'
    cache: str = 'ok'
    disk_usage: str = 'ok'
    version: str = '2.0.0'


class SearchResult(Schema):
    id: int
    title: str
    author: str
    category: str


class SearchResponse(Schema):
    query: str
    results: List[SearchResult] = []
    total: int = 0
    suggestions: List[str] = []


class CategoryStat(Schema):
    category: str
    count: int


class DashboardStatsSchema(Schema):
    total_books: int
    total_users: int
    total_chapters: int
    total_words: int
    category_stats: List[CategoryStat] = []


# ========== Health Check ==========

@api.get('/health/', response=HealthSchema, auth=None)
def health_check(request):
    checks = {'status': 'ok', 'database': 'ok', 'cache': 'ok', 'disk_usage': 'ok', 'version': '2.0.0'}
    try:
        connection.ensure_connection()
    except Exception as e:
        logger.warning(f"数据库健康检查失败: {e}")
        checks['database'] = 'error'
        checks['status'] = 'degraded'
    try:
        cache.set('_health', '1', 5)
        if cache.get('_health') != '1':
            raise RuntimeError("cache readback failed")
    except Exception as e:
        logger.warning(f"缓存健康检查失败: {e}")
        checks['cache'] = 'error'
        checks['status'] = 'degraded'
    try:
        usage = shutil.disk_usage('/')
        used_pct = (usage.used / usage.total) * 100
        if used_pct > 95:
            checks['disk_usage'] = f'critical ({used_pct:.0f}%)'
            checks['status'] = 'degraded'
        elif used_pct > 85:
            checks['disk_usage'] = f'warning ({used_pct:.0f}%)'
    except Exception as e:
        logger.warning(f"磁盘健康检查失败: {e}")
        checks['disk_usage'] = 'unknown'
    return checks


# ========== Auth ==========

@api.post('/auth/login/', response=AuthResponse, auth=None)
def auth_login(request, payload: LoginIn):
    user = authenticate(request, username=payload.username, password=payload.password)
    if user is not None:
        login(request, user)
        logger.info(f'[Auth] 用户登录: {user.username}')
        return {
            'success': True,
            'user': {'id': user.id, 'username': user.username, 'email': user.email or '', 'is_staff': user.is_staff},
        }
    logger.warning(f'[Auth] 登录失败: {payload.username}')
    return {'success': False, 'error': '用户名或密码错误'}


@api.post('/auth/register/', response=AuthResponse, auth=None)
def auth_register(request, payload: RegisterIn):
    if User.objects.filter(username=payload.username).exists():
        return {'success': False, 'error': '用户名已存在'}
    user = User.objects.create_user(username=payload.username, password=payload.password, email=payload.email)
    login(request, user)
    logger.info(f'[Auth] 新用户注册: {user.username}')
    return {
        'success': True,
        'user': {'id': user.id, 'username': user.username, 'email': user.email or '', 'is_staff': user.is_staff},
    }


@api.post('/auth/logout/', response=MessageSchema, auth=session_auth)
def auth_logout(request):
    username = request.user.username
    logout(request)
    logger.info(f'[Auth] 用户登出: {username}')
    return {'message': '已退出登录'}


@api.get('/auth/me/', response=AuthResponse, auth=optional_auth)
def auth_me(request):
    if request.user.is_authenticated:
        return {
            'success': True,
            'user': {'id': request.user.id, 'username': request.user.username, 'email': request.user.email or '', 'is_staff': request.user.is_staff},
        }
    return {'success': False, 'error': '未登录'}


# ========== Books ==========

@api.get('/books/', response=List[BookListSchema], auth=optional_auth)
@paginate
def list_books(request, tag: Optional[str] = None, category: Optional[str] = None, search: Optional[str] = None):
    qs = Book.objects.prefetch_related('tags').all()
    if tag:
        qs = qs.filter(tags__name=tag)
    if category:
        qs = qs.filter(category=category)
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(author__icontains=search))
    return qs


@api.post('/books/import/', response=BatchImportResult, auth=session_auth)
def batch_import(request):
    files = request.FILES.getlist('files')
    if not files:
        return {'success': False, 'errors': ['未选择文件'], 'total': 0}
    imported = 0
    errors = []
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
            book_dir = os.path.join('data/books', safe_name)
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
            chapters_data = []
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
            logger.info(f'[BatchImport] 导入成功: {title} ({len(chapters_data)}章)')
        except Exception as e:
            logger.error(f'[BatchImport] 导入失败 {f.name}: {e}')
            errors.append(f'{f.name}: {str(e)[:100]}')
    return {'success': True, 'imported': imported, 'errors': errors, 'total': len(files)}


@api.get('/books/{book_id}/', response=BookDetailSchema, auth=optional_auth)
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
        'gradient': book.cover_gradient,
        'is_favorited': is_fav,
        'reading_progress': progress,
        'created_at': book.created_at.isoformat(),
        'updated_at': book.updated_at.isoformat(),
    }


@api.get('/books/{book_id}/chapters/', response=List[ChapterSchema], auth=optional_auth)
def list_chapters(request, book_id: int):
    book = get_object_or_404(Book, id=book_id)
    return book.chapters.all()


@api.get('/books/{book_id}/chapters/{chapter_id}/', response=ChapterContentSchema, auth=optional_auth)
def get_chapter_content(request, book_id: int, chapter_id: int):
    chapter = get_object_or_404(Chapter, book_id=book_id, id=chapter_id)
    content = ''
    cache_key = f'chapter_content:{chapter.id}'
    content = cache.get(cache_key)
    if content is None and chapter.file_path:
        file_path = os.path.normpath(chapter.file_path)
        books_root = os.path.normpath(str(settings.BOOKS_DIR))
        if not file_path.startswith(books_root):
            logger.error(f'章节文件路径越界: {chapter.file_path}')
            content = ''
        elif os.path.exists(file_path):
            for enc in ('utf-8', 'gbk', 'gb2312', 'utf-16'):
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        content = f.read()
                    cache.set(cache_key, content, 300)
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    logger.error(f'读取章节文件失败 {file_path}: {e}')
                    break
    return {
        'id': chapter.id,
        'chapter_number': chapter.chapter_number,
        'title': chapter.title,
        'word_count': chapter.word_count,
        'content': content,
    }


# ========== Progress ==========

@api.get('/progress/', response=List[ProgressOut], auth=session_auth)
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


@api.post('/progress/', response=ProgressOut, auth=session_auth)
def create_progress(request, payload: ReadingProgressIn):
    book = get_object_or_404(Book, id=payload.book_id)
    progress, _ = ReadingProgress.objects.update_or_create(
        user=request.user,
        book=book,
        defaults={'chapter_id': payload.chapter_id, 'position': payload.position},
    )
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


@api.post('/progress/track-stats/', response=MessageSchema, auth=session_auth)
def track_stats(request, payload: StatsTrackIn):
    if payload.seconds < 5 or payload.seconds > 3600:
        return {'message': 'ok'}
    today = timezone.now().date()
    words = 0
    if payload.chapter_id:
        try:
            ch = Chapter.objects.get(pk=payload.chapter_id)
            words = ch.word_count or 0
        except Chapter.DoesNotExist:
            pass
    stats, created = ReadingStats.objects.get_or_create(
        user=request.user, date=today,
        defaults={'read_seconds': payload.seconds, 'chapters_read': 1, 'words_read': words},
    )
    if not created:
        stats.read_seconds += payload.seconds
        stats.chapters_read += 1
        stats.words_read += words
        stats.save(update_fields=['read_seconds', 'chapters_read', 'words_read'])
    return {'message': 'ok'}


# ========== Crawler ==========

@api.get('/crawler/', response=List[CrawlerTaskSchema], auth=session_auth)
@paginate
def list_crawler_tasks(request):
    return CrawlerTask.objects.filter(user=request.user)


@api.post('/crawler/', response=CrawlerTaskSchema, auth=session_auth)
def create_crawler_task(request, payload: CrawlerTaskIn):
    from utils.crawler_engine import validate_crawl_url
    if not validate_crawl_url(payload.url):
        raise HttpError(400, '目标 URL 不合法或指向内网地址')
    active_count = CrawlerTask.objects.filter(user=request.user, status__in=['pending', 'running']).count()
    if active_count >= 5:
        raise HttpError(429, '当前已有过多运行中的任务，请稍后再试')
    task = CrawlerTask.objects.create(user=request.user, url=payload.url, status='pending')
    from apps.crawler.tasks import run_crawler_task
    run_crawler_task.delay(task.id)
    logger.info(f'[Crawler] 创建任务: {task.id} - {payload.url}')
    return task


@api.get('/crawler/{task_id}/', response=CrawlerTaskDetailSchema, auth=session_auth)
def get_crawler_task(request, task_id: int):
    task = get_object_or_404(CrawlerTask, id=task_id, user=request.user)
    logs = []
    if task.logs:
        try:
            logs = json.loads(task.logs)
        except Exception as e:
            logger.warning(f'解析任务日志失败: {e}')
    return {
        'id': task.id,
        'url': task.url,
        'status': task.status,
        'total_chapters': task.total_chapters,
        'downloaded_chapters': task.downloaded_chapters,
        'error_message': task.error_message,
        'logs': logs,
        'created_at': task.created_at.isoformat(),
        'updated_at': task.updated_at.isoformat(),
    }


# ========== Tags ==========

@api.get('/tags/', response=List[TagListSchema], auth=optional_auth)
@paginate
def list_tags(request):
    qs = Tag.objects.all()
    return [{
        'id': t.id,
        'name': t.name,
        'color': t.color,
        'book_count': t.books.count(),
    } for t in qs]


@api.post('/tags/', response=TagListSchema, auth=session_auth)
def create_tag(request, payload: TagIn):
    tag = Tag.objects.create(name=payload.name, color=payload.color)
    logger.info(f'[Tag] 创建标签: {tag.name}')
    return {'id': tag.id, 'name': tag.name, 'color': tag.color, 'book_count': 0}


@api.delete('/tags/{tag_id}/', response=MessageSchema, auth=session_auth)
def delete_tag(request, tag_id: int):
    tag = get_object_or_404(Tag, id=tag_id)
    tag_name = tag.name
    tag.delete()
    logger.info(f'[Tag] 删除标签: {tag_name}')
    return {'message': '删除成功'}


# ========== Favorites ==========

@api.get('/favorites/', response=List[FavoriteSchema], auth=session_auth)
@paginate
def list_favorites(request):
    qs = Favorite.objects.filter(user=request.user).select_related('book')
    return [{
        'id': f.id,
        'book_id': f.book_id,
        'title': f.book.title,
        'author': f.book.author,
        'category': f.book.category,
        'total_chapters': f.book.total_chapters,
        'created_at': f.created_at.isoformat(),
    } for f in qs]


@api.post('/favorites/toggle/', response=MessageSchema, auth=session_auth)
def toggle_favorite(request, payload: FavoriteToggleIn):
    book = get_object_or_404(Book, id=payload.book_id)
    fav = Favorite.objects.filter(user=request.user, book=book).first()
    if fav:
        fav.delete()
        logger.info(f'[Favorite] 取消收藏: {book.title}')
        return {'message': '已取消收藏'}
    Favorite.objects.create(user=request.user, book=book)
    logger.info(f'[Favorite] 添加收藏: {book.title}')
    return {'message': '已收藏'}


# ========== Users ==========

@api.get('/users/', response=List[UserSchema], auth=session_auth)
@paginate
def list_users(request):
    qs = User.objects.all()
    return [{
        'id': u.id,
        'username': u.username,
        'email': u.email or '',
        'is_staff': u.is_staff,
        'date_joined': u.date_joined.isoformat(),
        'last_login': u.last_login.isoformat() if u.last_login else None,
        'book_count': ReadingProgress.objects.filter(user=u).count(),
    } for u in qs]


# ========== Stats ==========

@api.get('/stats/', response=UserStatsSchema, auth=session_auth)
def get_user_stats(request, days: int = 7):
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


# ========== Dashboard ==========

@api.get('/dashboard/', response=DashboardStatsSchema, auth=optional_auth)
def get_dashboard_stats(request):
    category_stats = list(
        Book.objects.exclude(category='')
        .values('category')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    return {
        'total_books': Book.objects.count(),
        'total_users': User.objects.count(),
        'total_chapters': Chapter.objects.count(),
        'total_words': Chapter.objects.aggregate(total=Count('word_count'))['total'] or 0,
        'category_stats': category_stats,
    }


# ========== Search ==========

@api.get('/search/', response=SearchResponse, auth=optional_auth)
def search_books(request, q: str = ''):
    query = q.strip()
    results = []
    suggestions = []
    total = 0
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
        suggestions = list(Book.objects.filter(title__istartswith=query).values_list('title', flat=True)[:10])
    return {'query': query, 'results': results, 'total': total, 'suggestions': suggestions}
