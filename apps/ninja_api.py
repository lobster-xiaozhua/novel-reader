"""
NovelReader 后端 API —— 基于 Django Ninja 的高性能小说阅读器接口层。

提供认证、书籍管理、章节阅读、阅读进度、爬虫任务、
标签管理、收藏夹、用户管理、统计与仪表盘、全文搜索等 RESTful 接口。
"""

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
from django.db.models import Count, Q, Sum
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
    """可选 Session 认证：已登录返回 user 对象，未登录放行（返回 True）。

    适用于"登录用户可获取额外信息，但游客也可访问"的接口。
    """

    def __call__(self, request):
        return request.user if request.user.is_authenticated else True


class SessionAuthNoCSRF(SessionAuth):
    """免 CSRF 校验的 Session 认证。

    适用于 AJAX / SPA 前端以 JSON 方式调用的需要登录的接口，
    避免 Django 默认的 CSRF 拦截。
    """

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
    """全局异常处理器：捕获所有未处理异常并返回统一 JSON 错误响应。

    - HttpError 子类直接透传（已由业务代码指定状态码）
    - 其余异常记录日志后返回 500 + 错误信息
    """
    logger.error(f'API Error: {request.path} - {type(exc).__name__}: {str(exc)}')
    from ninja.errors import HttpError
    if isinstance(exc, HttpError):
        raise exc
    return api.create_response(request, {'error': str(exc)}, status=500)


# ========== Schemas ==========

class TagSchema(Schema):
    """标签输出 Schema，用于书籍列表中的标签信息展示。

    字段说明：
        id: 标签唯一 ID
        name: 标签名称
        color: 标签颜色（十六进制色值）
    """
    id: int
    name: str
    color: str = '#f59e0b'


class BookListSchema(Schema):
    """书籍列表项 Schema，用于 /books/ 列表接口返回。

    字段说明：
        id: 书籍唯一 ID
        title: 书名
        author: 作者
        category: 分类
        description: 简介
        total_chapters: 总章节数
        chapter_count: 章节数（兼容字段）
        tags: 关联标签列表（TagSchema 数组）
        gradient: 封面渐变色元组
        created_at: 创建时间（ISO 8601）
        updated_at: 更新时间（ISO 8601）
    """
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
        """将 ORM 对象的 created_at 字段转为 ISO 8601 字符串。"""
        if hasattr(obj, 'created_at'):
            val = obj.created_at
            return val.isoformat() if isinstance(val, timezone.datetime) else str(val)
        return ''

    @staticmethod
    def resolve_updated_at(obj):
        """将 ORM 对象的 updated_at 字段转为 ISO 8601 字符串。"""
        if hasattr(obj, 'updated_at'):
            val = obj.updated_at
            return val.isoformat() if isinstance(val, timezone.datetime) else str(val)
        return ''


class BookDetailSchema(Schema):
    """书籍详情 Schema，用于 /books/{id}/ 接口返回。

    字段说明：
        id: 书籍唯一 ID
        title: 书名
        author: 作者
        category: 分类
        description: 简介
        total_chapters: 总章节数
        tags: 关联标签列表
        gradient: 封面渐变色
        is_favorited: 当前用户是否已收藏
        reading_progress: 当前用户阅读进度（字典或 None）
        created_at: 创建时间
        updated_at: 更新时间
    """
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
    """章节摘要 Schema，用于章节列表（不含正文内容）。

    字段说明：
        id: 章节唯一 ID
        chapter_number: 章节序号
        title: 章节标题
        word_count: 字数
    """
    id: int
    chapter_number: int
    title: str
    word_count: int = 0


class ChapterContentSchema(Schema):
    """章节详情 Schema，含正文内容，用于获取单章阅读接口。

    字段说明：
        id: 章节唯一 ID
        chapter_number: 章节序号
        title: 章节标题
        word_count: 字数
        content: 章节正文
    """
    id: int
    chapter_number: int
    title: str
    word_count: int = 0
    content: str = ''


class ProgressOut(Schema):
    """阅读进度输出 Schema。

    字段说明：
        id: 进度记录 ID
        book_id: 书籍 ID
        book_title: 书名
        book_author: 作者
        chapter_id: 当前章节 ID（可为空）
        chapter_title: 当前章节标题（可为空）
        position: 阅读位置偏移量
        total_chapters: 书籍总章节数
        updated_at: 最后更新时间
    """
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
    """保存阅读进度请求 Schema。

    字段说明：
        book_id: 书籍 ID
        chapter_id: 当前章节 ID（可选）
        position: 阅读位置偏移量
    """
    book_id: int
    chapter_id: Optional[int] = None
    position: int = 0


class StatsTrackIn(Schema):
    """上报阅读统计数据请求 Schema。

    字段说明：
        seconds: 本次阅读时长（秒）
        chapter_id: 当前阅读的章节 ID（可选，用于统计字数）
    """
    seconds: int = 0
    chapter_id: Optional[int] = None


class CrawlerTaskSchema(Schema):
    """爬虫任务列表项 Schema。

    字段说明：
        id: 任务 ID
        url: 目标 URL
        status: 任务状态（pending/running/completed/failed）
        total_chapters: 识别到的总章节数
        downloaded_chapters: 已下载章节数
        error_message: 错误信息
        created_at: 创建时间
        updated_at: 更新时间
    """
    id: int
    url: str
    status: str
    total_chapters: int = 0
    downloaded_chapters: int = 0
    error_message: str = ''
    created_at: str
    updated_at: str


class CrawlerTaskIn(Schema):
    """创建爬虫任务请求 Schema。

    字段说明：
        url: 要抓取的小说页面 URL
    """
    url: str


class CrawlerTaskDetailSchema(Schema):
    """爬虫任务详情 Schema，包含日志列表。

    字段说明：
        id: 任务 ID
        url: 目标 URL
        status: 任务状态
        total_chapters: 总章节数
        downloaded_chapters: 已下载章节数
        error_message: 错误信息
        logs: 任务执行日志（字符串列表）
        created_at: 创建时间
        updated_at: 更新时间
    """
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
    """单日阅读统计 Schema，用于趋势图表。

    字段说明：
        date: 日期（ISO 8601）
        minutes: 阅读时长（分钟）
        chapters: 阅读章节数
        words: 阅读字数
    """
    date: str
    minutes: float = 0.0
    chapters: int = 0
    words: int = 0


class UserStatsSchema(Schema):
    """用户统计汇总 Schema。

    字段说明：
        total_books: 书库总书籍数
        reading_count: 有阅读进度的书籍数
        favorite_count: 收藏数
        today_chapters: 今日阅读章节数
        today_minutes: 今日阅读时长（分钟）
        week_chapters: 本周阅读章节数
        total_words: 累计阅读字数
        chart: 每日趋势数据（DailyStat 数组）
    """
    total_books: int
    reading_count: int
    favorite_count: int
    today_chapters: int = 0
    today_minutes: float = 0.0
    week_chapters: int = 0
    total_words: int = 0
    chart: List[DailyStat] = []


class MessageSchema(Schema):
    """通用消息返回 Schema，用于操作成功提示。

    字段说明：
        message: 提示信息
    """
    message: str


class TagListSchema(Schema):
    """标签列表 Schema，含关联书籍计数。

    字段说明：
        id: 标签 ID
        name: 标签名称
        color: 标签颜色
        book_count: 使用该标签的书籍数
    """
    id: int
    name: str
    color: str
    book_count: int


class TagIn(Schema):
    """创建标签请求 Schema。

    字段说明：
        name: 标签名称
        color: 标签颜色（默认琥珀色）
    """
    name: str
    color: str = '#f59e0b'


class FavoriteSchema(Schema):
    """收藏项 Schema。

    字段说明：
        id: 收藏记录 ID
        book_id: 书籍 ID
        title: 书名
        author: 作者
        category: 分类
        total_chapters: 总章节数
        created_at: 收藏时间
    """
    id: int
    book_id: int
    title: str
    author: str
    category: str
    total_chapters: int
    created_at: str


class FavoriteToggleIn(Schema):
    """切换收藏状态请求 Schema。

    字段说明：
        book_id: 书籍 ID
    """
    book_id: int


class UserSchema(Schema):
    """用户信息 Schema，用于用户列表展示。

    字段说明：
        id: 用户 ID
        username: 用户名
        email: 邮箱
        is_staff: 是否管理员
        date_joined: 注册时间
        last_login: 最后登录时间（可为空）
        book_count: 关联的阅读记录数
    """
    id: int
    username: str
    email: str
    is_staff: bool
    date_joined: str
    last_login: Optional[str] = None
    book_count: int = 0


class LoginIn(Schema):
    """登录请求 Schema。

    字段说明：
        username: 用户名
        password: 密码
    """
    username: str
    password: str


class RegisterIn(Schema):
    """注册请求 Schema。

    字段说明：
        username: 用户名
        password: 密码
        email: 邮箱（可选）
    """
    username: str
    password: str
    email: str = ''


class UserOut(Schema):
    """用户信息输出 Schema（精简版，不含敏感时间字段）。

    字段说明：
        id: 用户 ID
        username: 用户名
        email: 邮箱
        is_staff: 是否管理员
    """
    id: int
    username: str
    email: str
    is_staff: bool


class AuthResponse(Schema):
    """认证接口统一响应 Schema。

    字段说明：
        success: 是否成功
        user: 用户信息（成功时返回）
        error: 错误信息（失败时返回）
    """
    success: bool
    user: Optional[UserOut] = None
    error: str = ''


class BatchImportResult(Schema):
    """批量导入结果 Schema。

    字段说明：
        success: 是否整体成功
        imported: 成功导入的文件数
        errors: 错误详情列表
        total: 总处理文件数
    """
    success: bool
    imported: int = 0
    errors: List[str] = []
    total: int = 0


class HealthSchema(Schema):
    """健康检查响应 Schema。

    字段说明：
        status: 整体状态（ok/degraded）
        database: 数据库状态
        cache: 缓存状态
        disk_usage: 磁盘状态
        version: 服务版本号
    """
    status: str
    database: str = 'ok'
    cache: str = 'ok'
    disk_usage: str = 'ok'
    version: str = '2.0.0'


class SearchResult(Schema):
    """搜索结果项 Schema。

    字段说明：
        id: 书籍 ID
        title: 书名
        author: 作者
        category: 分类
    """
    id: int
    title: str
    author: str
    category: str


class SearchResponse(Schema):
    """搜索响应 Schema。

    字段说明：
        query: 搜索关键词
        results: 匹配结果列表
        total: 结果总数
        suggestions: 自动补全建议（前缀匹配）
    """
    query: str
    results: List[SearchResult] = []
    total: int = 0
    suggestions: List[str] = []


class CategoryStat(Schema):
    """分类统计项 Schema。

    字段说明：
        category: 分类名称
        count: 该分类下的书籍数
    """
    category: str
    count: int


class DashboardStatsSchema(Schema):
    """仪表盘汇总数据 Schema。

    字段说明：
        total_books: 书籍总数
        total_users: 用户总数
        total_chapters: 章节总数
        total_words: 字数总计
        category_stats: 各分类书籍统计
    """
    total_books: int
    total_users: int
    total_chapters: int
    total_words: int
    category_stats: List[CategoryStat] = []


# ========== Health Check ==========

@api.get('/health/', response=HealthSchema, auth=None)
def health_check(request):
    """GET /health/ — 服务健康检查。

    检查数据库连接、缓存读写、磁盘使用率三项指标。
    任意一项异常时 status 标记为 'degraded'。
    返回 HealthSchema。
    """
    checks = {'status': 'ok', 'database': 'ok', 'cache': 'ok', 'disk_usage': 'ok', 'version': '2.0.0'}
    try:
        # 检查数据库连接是否可用
        connection.ensure_connection()
    except Exception as e:
        logger.warning(f"数据库健康检查失败: {e}")
        checks['database'] = 'error'
        checks['status'] = 'degraded'
    try:
        # 检查缓存写入和回读是否正常
        cache.set('_health', '1', 5)
        if cache.get('_health') != '1':
            raise RuntimeError("cache readback failed")
    except Exception as e:
        logger.warning(f"缓存健康检查失败: {e}")
        checks['cache'] = 'error'
        checks['status'] = 'degraded'
    try:
        # 磁盘使用率超过 85% 告警，超过 95% 标记为严重
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
    """POST /auth/login/ — 用户登录。

    参数:
        payload: LoginIn {username: 用户名, password: 密码}
    返回:
        AuthResponse {success, user(成功时), error(失败时)}
    认证: 无需认证
    """
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
    """POST /auth/register/ — 用户注册。

    参数:
        payload: RegisterIn {username, password, email(可选)}
    返回:
        AuthResponse {success, user(成功时), error(失败时)}
    认证: 无需认证
    """
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
    """POST /auth/logout/ — 用户登出。

    返回:
        MessageSchema {message: '已退出登录'}
    认证: 需要登录 (session_auth)
    """
    username = request.user.username
    logout(request)
    logger.info(f'[Auth] 用户登出: {username}')
    return {'message': '已退出登录'}


@api.get('/auth/me/', response=AuthResponse, auth=optional_auth)
def auth_me(request):
    """GET /auth/me/ — 获取当前登录用户信息。

    返回:
        AuthResponse {success, user(已登录时), error(未登录时)}
    认证: 可选认证 (optional_auth)
    """
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
    """GET /books/ — 书籍列表（支持分页、标签/分类/搜索过滤）。

    查询参数:
        tag: 按标签名称过滤
        category: 按分类过滤
        search: 按书名或作者模糊搜索
    返回:
        书籍列表 List[BookListSchema]（分页后）
    认证: 可选认证
    """
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
    """POST /books/import/ — 批量导入 TXT 小说文件。

    请求体: multipart/form-data，files 字段包含一个或多个 .txt 文件
    处理流程:
        1. 校验文件格式（仅 .txt）
        2. 尝试 UTF-8 / GBK / GB2312 解码
        3. 用正则拆分章节（支持"第X章"、"chapter N"等格式）
        4. 拆分失败时按段落等量分块（最多 50 章）
        5. 写入文件系统并创建 Book + Chapter 记录
    返回:
        BatchImportResult {success, imported, errors, total}
    认证: 需要登录
    """
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
            # 依次尝试常见编码，兼容中文小说文件
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
            # 匹配章节标题（"第X章"、"chapter N"、"卷X"等）
            chapter_pattern = re.compile(
                r'^(第[零一二三四五六七八九十百千万\d]+章|chapter\s*\d+|第\d+章|卷[零一二三四五六七八九十百千万\d]+)',
                re.IGNORECASE | re.MULTILINE,
            )
            parts = chapter_pattern.split(text)
            chapters_data = []
            if len(parts) > 1:
                # 正则匹配成功：split 返回 [前缀, 标题, 正文, 标题, 正文, ...]
                i = 1
                while i < len(parts):
                    ch_title = parts[i].strip()
                    ch_content = parts[i + 1].strip() if i + 1 < len(parts) else ''
                    if ch_title:
                        chapters_data.append((ch_title, ch_content))
                    i += 2
            else:
                # 无章节标记：按段落等量分块（最多 50 块）
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
    """GET /books/{book_id}/ — 获取书籍详情。

    路径参数:
        book_id: 书籍 ID
    返回:
        BookDetailSchema {id, title, author, ..., is_favorited, reading_progress}
    说明:
        已登录用户会额外返回收藏状态和阅读进度
    认证: 可选认证
    """
    book = get_object_or_404(Book.objects.prefetch_related('tags'), id=book_id)
    is_fav = False
    progress = None
    if request.user.is_authenticated:
        # 仅登录用户才查询收藏和进度
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
    """GET /books/{book_id}/chapters/ — 获取书籍章节列表。

    路径参数:
        book_id: 书籍 ID
    返回:
        章节列表 List[ChapterSchema]（不含正文）
    认证: 可选认证
    """
    book = get_object_or_404(Book, id=book_id)
    return book.chapters.all()


@api.get('/books/{book_id}/chapters/{chapter_id}/', response=ChapterContentSchema, auth=optional_auth)
def get_chapter_content(request, book_id: int, chapter_id: int):
    """GET /books/{book_id}/chapters/{chapter_id}/ — 获取章节正文内容。

    路径参数:
        book_id: 书籍 ID
        chapter_id: 章节 ID
    返回:
        ChapterContentSchema {id, chapter_number, title, word_count, content}
    说明:
        内容缓存 5 分钟；文件读取前进行路径越界安全检查
    认证: 可选认证
    """
    chapter = get_object_or_404(Chapter, book_id=book_id, id=chapter_id)
    content = ''
    cache_key = f'chapter_content:{chapter.id}'
    content = cache.get(cache_key)
    if content is None and chapter.file_path:
        # 路径安全校验：防止目录穿越攻击
        raw_path = chapter.file_path
        # 兼容相对路径和绝对路径：统一转为绝对路径后再校验
        file_path = os.path.normpath(raw_path)
        if not os.path.isabs(file_path):
            file_path = os.path.normpath(os.path.join(str(settings.BASE_DIR), file_path))
        books_root = os.path.normpath(str(settings.BOOKS_DIR))
        if not file_path.startswith(books_root):
            logger.error(f'章节文件路径越界: {chapter.file_path}')
            content = ''
        elif os.path.exists(file_path):
            # 依次尝试多种编码读取文件
            for enc in ('utf-8', 'gbk', 'gb2312', 'utf-16'):
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        content = f.read()
                    cache.set(cache_key, content, 300)  # 缓存 5 分钟
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
    """GET /progress/ — 获取当前用户的所有阅读进度列表（分页）。

    返回:
        List[ProgressOut]（分页）
    认证: 需要登录
    """
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
    """POST /progress/ — 保存或更新阅读进度。

    参数:
        payload: ReadingProgressIn {book_id, chapter_id(可选), position}
    返回:
        ProgressOut（更新后的进度记录）
    认证: 需要登录
    """
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
    """POST /progress/track-stats/ — 上报本次阅读统计数据。

    参数:
        payload: StatsTrackIn {seconds: 阅读时长(秒), chapter_id(可选)}
    返回:
        MessageSchema {message: 'ok'}
    说明:
        阅读时长 <5 秒或 >1 小时的请求被忽略（防刷/后台挂机）
        查询章节字数用于累计总阅读量
    认证: 需要登录
    """
    if payload.seconds < 5 or payload.seconds > 3600:
        return {'message': 'ok'}  # 忽略过短或过长的异常上报
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
        # 已有今日统计记录：累加数据
        stats.read_seconds += payload.seconds
        stats.chapters_read += 1
        stats.words_read += words
        stats.save(update_fields=['read_seconds', 'chapters_read', 'words_read'])
    return {'message': 'ok'}


# ========== Crawler ==========

@api.get('/crawler/', response=List[CrawlerTaskSchema], auth=session_auth)
@paginate
def list_crawler_tasks(request):
    """GET /crawler/ — 获取当前用户的爬虫任务列表（分页）。

    返回:
        List[CrawlerTaskSchema]（分页）
    认证: 需要登录
    """
    return CrawlerTask.objects.filter(user=request.user)


@api.post('/crawler/', response=CrawlerTaskSchema, auth=session_auth)
def create_crawler_task(request, payload: CrawlerTaskIn):
    """POST /crawler/ — 创建爬虫抓取任务。

    参数:
        payload: CrawlerTaskIn {url: 目标小说页面 URL}
    返回:
        CrawlerTaskSchema
    说明:
        - 校验 URL 合法性（禁止内网地址）
        - 限制用户同时最多 5 个活跃任务
        - 创建后立即通过 Celery 异步执行
    认证: 需要登录
    """
    from utils.crawler_engine import validate_crawl_url
    if not validate_crawl_url(payload.url):
        raise HttpError(400, '目标 URL 不合法或指向内网地址')
    # 限制并发任务数，防止资源耗尽
    active_count = CrawlerTask.objects.filter(user=request.user, status__in=['pending', 'running']).count()
    if active_count >= 5:
        raise HttpError(429, '当前已有过多运行中的任务，请稍后再试')
    task = CrawlerTask.objects.create(user=request.user, url=payload.url, status='pending')
    from apps.crawler.tasks import run_crawler_task
    run_crawler_task.delay(task.id)  # 异步执行爬虫任务
    logger.info(f'[Crawler] 创建任务: {task.id} - {payload.url}')
    return task


@api.get('/crawler/{task_id}/', response=CrawlerTaskDetailSchema, auth=session_auth)
def get_crawler_task(request, task_id: int):
    """GET /crawler/{task_id}/ — 获取爬虫任务详情及日志。

    路径参数:
        task_id: 任务 ID
    返回:
        CrawlerTaskDetailSchema {含 logs 日志列表}
    认证: 需要登录（仅查看自己的任务）
    """
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
    """GET /tags/ — 获取标签列表（含关联书籍计数，分页）。

    返回:
        List[TagListSchema]（分页）
    认证: 可选认证
    """
    qs = Tag.objects.all()
    return [{
        'id': t.id,
        'name': t.name,
        'color': t.color,
        'book_count': t.books.count(),
    } for t in qs]


@api.post('/tags/', response=TagListSchema, auth=session_auth)
def create_tag(request, payload: TagIn):
    """POST /tags/ — 创建新标签。

    参数:
        payload: TagIn {name, color(默认 '#f59e0b')}
    返回:
        TagListSchema
    认证: 需要登录
    """
    tag = Tag.objects.create(name=payload.name, color=payload.color)
    logger.info(f'[Tag] 创建标签: {tag.name}')
    return {'id': tag.id, 'name': tag.name, 'color': tag.color, 'book_count': 0}


@api.delete('/tags/{tag_id}/', response=MessageSchema, auth=session_auth)
def delete_tag(request, tag_id: int):
    """DELETE /tags/{tag_id}/ — 删除标签。

    路径参数:
        tag_id: 标签 ID
    返回:
        MessageSchema {message: '删除成功'}
    认证: 需要登录
    """
    tag = get_object_or_404(Tag, id=tag_id)
    tag_name = tag.name
    tag.delete()
    logger.info(f'[Tag] 删除标签: {tag_name}')
    return {'message': '删除成功'}


# ========== Favorites ==========

@api.get('/favorites/', response=List[FavoriteSchema], auth=session_auth)
@paginate
def list_favorites(request):
    """GET /favorites/ — 获取当前用户的收藏列表（分页）。

    返回:
        List[FavoriteSchema]（分页）
    认证: 需要登录
    """
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
    """POST /favorites/toggle/ — 切换收藏状态（有则取消，无则添加）。

    参数:
        payload: FavoriteToggleIn {book_id}
    返回:
        MessageSchema {message}
    认证: 需要登录
    """
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
    """GET /users/ — 获取用户列表（含阅读记录计数，分页）。

    返回:
        List[UserSchema]（分页）
    认证: 需要登录
    """
    from django.db.models import Count as DbCount
    qs = User.objects.annotate(book_count=DbCount('readingprogress')).all()
    return [{
        'id': u.id,
        'username': u.username,
        'email': u.email or '',
        'is_staff': u.is_staff,
        'date_joined': u.date_joined.isoformat(),
        'last_login': u.last_login.isoformat() if u.last_login else None,
        'book_count': u.book_count,
    } for u in qs]


# ========== Stats ==========

@api.get('/stats/', response=UserStatsSchema, auth=session_auth)
def get_user_stats(request, days: int = 7):
    """GET /stats/ — 获取当前用户阅读统计汇总与趋势图数据。

    查询参数:
        days: 趋势天数，默认 7 天
    返回:
        UserStatsSchema {含 total_books, today_chapters, chart 等}
    说明:
        - chart 为连续日期数组（缺省天数补 0）
        - today_minutes 为今日阅读分钟数
        - week_chapters 为本周（周一至今）章节数
    认证: 需要登录
    """
    user = request.user
    today = date.today()
    total_books = Book.objects.count()
    reading_count = ReadingProgress.objects.filter(user=user).count()
    favorite_count = Favorite.objects.filter(user=user).count()
    today_stats = ReadingStats.objects.filter(user=user, date=today).first()
    week_start = today - timedelta(days=today.weekday())  # 本周一
    week_stats = ReadingStats.objects.filter(user=user, date__gte=week_start).aggregate(
        total_chapters=Sum('chapters_read'),
    )
    total_words = ReadingStats.objects.filter(user=user).aggregate(
        total=Sum('words_read'),
    )['total'] or 0
    start = today - timedelta(days=days - 1)
    daily_stats = ReadingStats.objects.filter(user=user, date__gte=start)
    stats_map = {s.date: s for s in daily_stats}  # 日期 → 统计记录映射
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
        'week_chapters': week_stats['total_chapters'] or 0,
        'total_words': total_words,
        'chart': chart,
    }


# ========== Dashboard ==========

@api.get('/dashboard/', response=DashboardStatsSchema, auth=optional_auth)
def get_dashboard_stats(request):
    """GET /dashboard/ — 获取仪表盘汇总数据。

    返回:
        DashboardStatsSchema {total_books, total_users, total_chapters, total_words, category_stats}
    说明:
        category_stats 为 TOP 10 分类（按书籍数降序）
    认证: 可选认证
    """
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
        'total_words': Chapter.objects.aggregate(total=Sum('word_count'))['total'] or 0,
        'category_stats': category_stats,
    }


# ========== Search ==========

class DiscoveryBookSchema(Schema):
    """发现页书籍展示 Schema。

    字段说明：
        id: 书籍 ID
        title: 书名
        author: 作者
        category: 分类
        description: 简介
        total_chapters: 总章节数
        tags: 关联标签列表
        gradient: 封面渐变色
        updated_at: 更新时间
    """
    id: int
    title: str
    author: str
    category: str = ''
    description: str = ''
    total_chapters: int
    tags: List[TagSchema] = []
    gradient: tuple = ('#667eea', '#764ba2')
    updated_at: str


class CategoryDiscoverySchema(Schema):
    """发现页分类展示 Schema。

    字段说明：
        category: 分类名称
        count: 书籍数量
        books: 该分类下的热门书籍列表
    """
    category: str
    count: int
    books: List[DiscoveryBookSchema]


class DiscoveryResponse(Schema):
    """发现页响应 Schema。

    字段说明：
        hot_books: 热门书籍（按章节数排序）
        recent_books: 最新更新书籍
        categories: 各分类及代表书籍
        stats: 基础统计信息
    """
    hot_books: List[DiscoveryBookSchema]
    recent_books: List[DiscoveryBookSchema]
    categories: List[CategoryDiscoverySchema]
    stats: dict


def _book_to_discovery(book):
    """将 Book 对象转为 DiscoveryBookSchema 字典。"""
    return {
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'category': book.category or '',
        'description': book.description or '',
        'total_chapters': book.total_chapters,
        'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in book.tags.all()],
        'gradient': book.cover_gradient,
        'updated_at': book.updated_at.isoformat(),
    }


@api.get('/discovery/', response=DiscoveryResponse, auth=None)
def discovery_page(request):
    """GET /discovery/ — 发现页数据（免登录）。

    返回:
        DiscoveryResponse {hot_books, recent_books, categories, stats}
    认证: 无需认证
    """
    from django.db.models import Sum
    hot_books = Book.objects.prefetch_related('tags').order_by('-total_chapters')[:8]
    recent_books = Book.objects.prefetch_related('tags').order_by('-updated_at')[:10]

    category_stats = (
        Book.objects.exclude(category='')
        .values('category')
        .annotate(count=Count('id'))
        .order_by('-count')[:6]
    )
    categories = []
    for cs in category_stats:
        cat_name = cs['category']
        cat_books = Book.objects.filter(category=cat_name).prefetch_related('tags').order_by('-total_chapters')[:4]
        categories.append({
            'category': cat_name,
            'count': cs['count'],
            'books': [_book_to_discovery(b) for b in cat_books],
        })

    total_books = Book.objects.count()
    total_chapters = Chapter.objects.count()
    total_words = Chapter.objects.aggregate(total=Sum('word_count'))['total'] or 0
    total_users = User.objects.count()

    return {
        'hot_books': [_book_to_discovery(b) for b in hot_books],
        'recent_books': [_book_to_discovery(b) for b in recent_books],
        'categories': categories,
        'stats': {
            'total_books': total_books,
            'total_chapters': total_chapters,
            'total_words': total_words,
            'total_users': total_users,
        },
    }


@api.get('/search/', response=SearchResponse, auth=optional_auth)
def search_books(request, q: str = ''):
    """GET /search/ — 搜索书籍（支持模糊匹配与自动补全）。

    查询参数:
        q: 搜索关键词
    返回:
        SearchResponse {query, results(最多 20 条), total, suggestions(前缀匹配，最多 10 条)}
    说明:
        - 当关键词 ≥2 字符时生成自动补全建议
        - 搜索范围涵盖书名、作者、简介
    认证: 可选认证
    """
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
        # 关键词≥2字符时：前缀匹配生成自动补全建议
        suggestions = list(Book.objects.filter(title__istartswith=query).values_list('title', flat=True)[:10])
    return {'query': query, 'results': results, 'total': total, 'suggestions': suggestions}
