# 全站重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 novel_reader 全站重构为用户端+管理端分离架构，后端 API 升级到 v2，前端升级到 Next.js 15

**Architecture:** 分支隔离全量重构。后端 `backend/api_v2/` 提供统一的 REST API（reader/admin 分离），前端 `frontend/reader/` 和 `frontend/admin/` 各自独立应用，`frontend/shared/` 共享组件/样式/类型

**Tech Stack:** Django + Django Ninja (后端), Next.js 15 App Router + React 19 + Tailwind + Zustand + TanStack Query + Shadcn/ui (前端)

---

## 阶段 0: 分支创建与项目初始化

### Task 0.1: 创建重构分支

- [ ] **Step 1: 创建并切换到 refactor 分支**

```bash
cd /workspace && git checkout -b refactor/v2-full
```

### Task 0.2: 初始化 Next.js 前端

- [ ] **Step 1: 备份并清理旧前端**

```bash
cd /workspace && mv frontend frontend-v1
```

- [ ] **Step 2: 创建 Next.js 项目**

```bash
cd /workspace && npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm --no-turbopack
```

- [ ] **Step 3: 安装依赖**

```bash
cd /workspace/frontend && npm install zustand @tanstack/react-query recharts lucide-react
```

- [ ] **Step 4: 创建目录结构**

```bash
mkdir -p /workspace/frontend/shared/{components,lib,types,styles}
mkdir -p /workspace/frontend/reader/app/{shelf,book/'[id]',read/'[id]',search,stats,login}
mkdir -p /workspace/frontend/admin/app/{books/'[id]',chapters/'[id]',crawler,users/'[id]',tags/'[id]',monitor,login}
```

- [ ] **Step 5: 提交**

```bash
cd /workspace && git add frontend/ && git commit -m "chore: init Next.js 15 frontend scaffold"
```

### Task 0.3: 创建后端 API v2 目录结构

- [ ] **Step 1: 创建目录**

```bash
mkdir -p /workspace/backend/api_v2/{reader,admin,auth}
touch /workspace/backend/api_v2/__init__.py
touch /workspace/backend/api_v2/reader/__init__.py
touch /workspace/backend/api_v2/admin/__init__.py
touch /workspace/backend/api_v2/auth/__init__.py
```

- [ ] **Step 2: 提交**

```bash
cd /workspace && git add backend/ && git commit -m "chore: init backend api_v2 module structure"
```

---

## 阶段 1: 后端 API v2 核心

### Task 1.1: 统一响应 Schema

**Files:**
- Create: `/workspace/backend/api_v2/schemas.py`

- [ ] **Step 1: 编写统一响应格式和基础 Schema**

```python
"""API v2 统一响应 Schema"""
from typing import Generic, TypeVar, Optional, List, Any
from ninja import Schema

T = TypeVar('T')


class Meta(Schema):
    page: int = 1
    total_pages: int = 1
    total_items: int = 0


class ApiResponse(Schema, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    meta: Optional[Meta] = None
    error: Optional[str] = None

    @classmethod
    def ok(cls, data: Any = None, meta: Optional[Meta] = None) -> "ApiResponse":
        return cls(success=True, data=data, meta=meta)

    @classmethod
    def fail(cls, error: str) -> "ApiResponse":
        return cls(success=False, error=error)


class PaginatedData(Schema):
    items: List[Any]
    total: int


class TokenOut(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class LoginIn(Schema):
    username: str
    password: str


class RegisterIn(Schema):
    username: str
    password: str
    email: str = ""


class UserOut(Schema):
    id: int
    username: str
    email: str
    role: str = "reader"
    is_staff: bool = False
```

- [ ] **Step 2: 提交**

```bash
cd /workspace && git add backend/api_v2/schemas.py && git commit -m "feat: add unified API v2 response schemas"
```

### Task 1.2: JWT + RBAC 认证模块

**Files:**
- Create: `/workspace/backend/api_v2/auth/auth.py`
- Create: `/workspace/backend/api_v2/auth/routes.py`

- [ ] **Step 1: 编写增强版 JWT 认证（含 role 字段）**

```python
"""JWT + RBAC 认证模块"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from django.conf import settings as django_settings
from django.contrib.auth.models import User
from django.http import JsonResponse

logger = logging.getLogger(__name__)

JWT_ALGORITHM = 'HS256'
JWT_ACCESS_LIFETIME = timedelta(minutes=getattr(django_settings, 'JWT_ACCESS_LIFETIME_MINUTES', 15))
JWT_REFRESH_LIFETIME = timedelta(days=getattr(django_settings, 'JWT_REFRESH_LIFETIME_DAYS', 7))


def _get_secret() -> str:
    return getattr(django_settings, 'JWT_SECRET', django_settings.SECRET_KEY)


def _get_user_role(user: User) -> str:
    if user.is_superuser:
        return 'admin'
    if user.is_staff:
        return 'admin'
    return 'reader'


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_id),
        'role': role,
        'exp': now + JWT_ACCESS_LIFETIME,
        'iat': now,
        'type': 'access',
    }
    return jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_id),
        'exp': now + JWT_REFRESH_LIFETIME,
        'iat': now,
        'type': 'refresh',
    }
    return jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, _get_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.debug('[JWT] Token expired')
    except jwt.InvalidTokenError as exc:
        logger.debug(f'[JWT] Invalid token: {exc}')
    return None


def get_user_from_token(token: str, token_type: str = 'access') -> Optional[User]:
    payload = decode_token(token)
    if not payload or payload.get('type') != token_type:
        return None
    try:
        user_id = int(payload['sub'])
        return User.objects.get(pk=user_id, is_active=True)
    except (ValueError, TypeError, User.DoesNotExist):
        return None


def _extract_token(request) -> Optional[str]:
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return request.COOKIES.get('access_token') or None


class JWTAuth:
    def __call__(self, request):
        token = _extract_token(request)
        if not token:
            return None
        user = get_user_from_token(token, token_type='access')
        if user:
            request.user = user
            return user
        return None


class AdminAuth(JWTAuth):
    """管理员认证：JWT 有效且 role 为 admin"""
    def __call__(self, request):
        user = super().__call__(request)
        if not user:
            return None
        payload = decode_token(_extract_token(request))
        if payload and payload.get('role') == 'admin':
            return user
        return None


jwt_auth = JWTAuth()
admin_auth = AdminAuth()
```

- [ ] **Step 2: 编写认证路由**

```python
"""认证路由"""
import logging
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from ninja import Router

from ..schemas import ApiResponse, LoginIn, RegisterIn, TokenOut, UserOut
from .auth import (
    create_access_token, create_refresh_token, jwt_auth,
    _get_user_role, JWT_ACCESS_LIFETIME, JWT_REFRESH_LIFETIME,
)

logger = logging.getLogger(__name__)
router = Router(tags=['auth'])


@router.post('/login', response={200: ApiResponse, 401: ApiResponse})
def login(request, payload: LoginIn):
    user = authenticate(username=payload.username, password=payload.password)
    if not user:
        return 401, ApiResponse.fail('用户名或密码错误')
    role = _get_user_role(user)
    access_token = create_access_token(user.id, role)
    refresh_token = create_refresh_token(user.id)
    response = ApiResponse.ok(data={
        'user': UserOut(id=user.id, username=user.username, email=user.email, role=role, is_staff=user.is_staff),
        'tokens': TokenOut(access_token=access_token, refresh_token=refresh_token),
    })
    return response


@router.post('/register', response={200: ApiResponse, 409: ApiResponse})
def register(request, payload: RegisterIn):
    if User.objects.filter(username=payload.username).exists():
        return 409, ApiResponse.fail('用户名已存在')
    user = User.objects.create_user(username=payload.username, password=payload.password, email=payload.email)
    role = _get_user_role(user)
    access_token = create_access_token(user.id, role)
    refresh_token = create_refresh_token(user.id)
    return ApiResponse.ok(data={
        'user': UserOut(id=user.id, username=user.username, email=user.email, role=role, is_staff=user.is_staff),
        'tokens': TokenOut(access_token=access_token, refresh_token=refresh_token),
    })


@router.post('/refresh', response={200: ApiResponse, 401: ApiResponse})
def refresh_token(request):
    refresh = request.COOKIES.get('refresh_token') or request.headers.get('X-Refresh-Token', '')
    if not refresh:
        return 401, ApiResponse.fail('缺少刷新令牌')
    from .auth import decode_token, get_user_from_token
    user = get_user_from_token(refresh, token_type='refresh')
    if not user:
        return 401, ApiResponse.fail('刷新令牌无效或已过期')
    role = _get_user_role(user)
    new_access = create_access_token(user.id, role)
    new_refresh = create_refresh_token(user.id)
    return ApiResponse.ok(data={'tokens': TokenOut(access_token=new_access, refresh_token=new_refresh)})


@router.get('/me', response={200: ApiResponse, 401: ApiResponse}, auth=jwt_auth)
def me(request):
    return ApiResponse.ok(data=UserOut(
        id=request.user.id, username=request.user.username,
        email=request.user.email, role=_get_user_role(request.user),
        is_staff=request.user.is_staff,
    ))


@router.post('/logout', response=ApiResponse, auth=jwt_auth)
def logout(request):
    return ApiResponse.ok(data={'message': '已登出'})
```

- [ ] **Step 3: 提交**

```bash
cd /workspace && git add backend/api_v2/auth/ && git commit -m "feat: add JWT + RBAC auth module for API v2"
```

### Task 1.3: API v2 路由入口

**Files:**
- Create: `/workspace/backend/api_v2/router.py`

- [ ] **Step 1: 编写 v2 路由入口**

```python
"""API v2 路由入口"""
import logging
import traceback

from ninja import NinjaAPI
from ninja.errors import HttpError, ValidationError

from .auth.routes import router as auth_router
from .schemas import ApiResponse

logger = logging.getLogger(__name__)

api_v2 = NinjaAPI(
    title='NovelReader API v2',
    version='2.0.0',
    description='小说阅读器 API v2 — reader/admin 分离',
    docs_url='/docs/',
    openapi_url='/openapi.json',
)


@api_v2.exception_handler(HttpError)
def http_error_handler(request, exc):
    logger.warning(f'[API v2 {exc.status_code}] {request.method} {request.path}: {exc.message}')
    return api_v2.create_response(request, ApiResponse.fail(exc.message).dict(), status=exc.status_code)


@api_v2.exception_handler(ValidationError)
def validation_error_handler(request, exc):
    logger.warning(f'[API v2 422] {request.method} {request.path}: {exc.errors}')
    return api_v2.create_response(request, ApiResponse.fail('请求数据验证失败').dict(), status=422)


@api_v2.exception_handler(Exception)
def global_exception_handler(request, exc):
    logger.error(f'[API v2 500] {request.method} {request.path}: {type(exc).__name__}: {exc}\n{traceback.format_exc()}')
    return api_v2.create_response(request, ApiResponse.fail('服务器内部错误，请稍后重试').dict(), status=500)


# 注册认证路由
api_v2.add_router('/auth/', auth_router)
# reader 和 admin 路由将在后续任务中注册
```

- [ ] **Step 2: 更新 Django urls.py 挂载 v2 路由**

Modify: `/workspace/novel_reader/urls.py`

```python
# 在现有 urlpatterns 中添加
from backend.api_v2.router import api_v2

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', api.urls),
    path('api/v2/', api_v2.urls),  # 新增
]
```

- [ ] **Step 3: 提交**

```bash
cd /workspace && git add backend/api_v2/router.py novel_reader/urls.py && git commit -m "feat: add API v2 router entry + mount to Django urls"
```

---

## 阶段 2: 后端 Reader API

### Task 2.1: Reader Schemas

**Files:**
- Create: `/workspace/backend/api_v2/reader/schemas.py`

- [ ] **Step 1: 编写 Reader 专用 Schema**

```python
"""Reader API Schemas"""
from typing import List, Optional
from ninja import Schema


class TagSchema(Schema):
    id: int
    name: str
    color: str = '#f59e0b'


class BookListItem(Schema):
    id: int
    title: str
    author: str = ''
    category: str = ''
    description: str = ''
    total_chapters: int = 0
    tags: List[TagSchema] = []
    gradient: tuple = ('#667eea', '#764ba2')
    created_at: str
    updated_at: str


class BookDetail(Schema):
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


class ChapterItem(Schema):
    id: int
    chapter_number: int
    title: str
    word_count: int = 0


class ChapterContent(Schema):
    id: int
    chapter_number: int
    title: str
    word_count: int = 0
    content: str = ''
    book_id: int
    book_title: str
    prev_chapter_id: Optional[int] = None
    next_chapter_id: Optional[int] = None


class ProgressIn(Schema):
    book_id: int
    chapter_id: Optional[int] = None
    position: int = 0


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


class StatsTrackIn(Schema):
    seconds: int = 0
    chapter_id: Optional[int] = None


class DailyStat(Schema):
    date: str
    minutes: float = 0.0
    chapters: int = 0
    words: int = 0


class UserStats(Schema):
    total_books: int
    reading_count: int
    favorite_count: int
    today_chapters: int = 0
    today_minutes: float = 0.0
    week_chapters: int = 0
    total_words: int = 0
    chart: List[DailyStat] = []


class SearchResultItem(Schema):
    id: int
    title: str
    author: str
    category: str


class SearchResult(Schema):
    query: str
    results: List[SearchResultItem] = []
    total: int = 0


class RankingBookOut(Schema):
    id: int
    title: str
    author: str = ''
    category: str = ''
    gradient: tuple = ('#667eea', '#764ba2')
    tags: List[TagSchema] = []
    chapter_count: int = 0


class DiscoverFeed(Schema):
    recommendations: List[BookListItem] = []
    hot_today: List[RankingBookOut] = []
    hot_week: List[RankingBookOut] = []
    new_arrivals: List[RankingBookOut] = []
    categories: List[dict] = []


class ShelfItem(Schema):
    book_id: int
    title: str
    author: str = ''
    category: str = ''
    gradient: tuple = ('#667eea', '#764ba2')
    tags: List[TagSchema] = []
    chapter_count: int = 0
    progress: Optional[dict] = None
    is_favorited: bool = False
    last_read_at: Optional[str] = None


class ShelfData(Schema):
    favorites: List[ShelfItem] = []
    recent_reads: List[ShelfItem] = []
```

- [ ] **Step 2: 提交**

```bash
cd /workspace && git add backend/api_v2/reader/schemas.py && git commit -m "feat: add reader API schemas"
```

### Task 2.2: Reader Routes

**Files:**
- Create: `/workspace/backend/api_v2/reader/routes.py`

- [ ] **Step 1: 编写 Reader 路由（发现流、书架、书籍详情、章节、阅读、搜索、进度、统计）**

```python
"""Reader API 路由"""
import logging
from typing import List

from django.db.models import Count, Q, Prefetch
from django.utils import timezone
from ninja import Router, Query
from ninja.pagination import paginate, PageNumberPagination

from apps.books.models import Book, Tag
from apps.chapters.models import Chapter
from apps.favorites.models import Favorite
from apps.reader.models import ReadingProgress, ReadingStats
from apps.recommender.engine import recommend_for_user, recommend_similar_books

from ..auth.auth import jwt_auth
from ..schemas import ApiResponse, Meta, PaginatedData
from .schemas import (
    BookListItem, BookDetail, ChapterItem, ChapterContent,
    ProgressIn, ProgressOut, StatsTrackIn, UserStats,
    SearchResult, DiscoverFeed, ShelfData, ShelfItem,
)

logger = logging.getLogger(__name__)
router = Router(tags=['reader'])


@router.get('/discover', response=ApiResponse[DiscoverFeed])
def discover(request):
    """发现流：推荐 + 排行 + 分类"""
    from datetime import timedelta
    from apps.reader.models import ReadingStats as RS
    from apps.favorites.models import Favorite as Fav

    books = Book.objects.prefetch_related('tags').annotate(chapter_count=Count('chapters'))

    # 推荐（需登录）
    recommendations = []
    if request.user.is_authenticated:
        try:
            rec_ids = recommend_for_user(request.user, limit=6)
            rec_books = list(books.filter(id__in=rec_ids))
            recommendations = [_book_to_listitem(b) for b in rec_books]
        except Exception as e:
            logger.warning(f'推荐失败: {e}')

    # 排行榜
    today = timezone.now()
    week_ago = today - timedelta(days=7)
    hot_today = _rank_books(books, Fav, today - timedelta(days=1))
    hot_week = _rank_books(books, Fav, week_ago)
    new_arrivals = list(books.order_by('-created_at')[:10])

    # 分类
    categories = list(books.values('category').annotate(count=Count('id')).order_by('-count')[:10])

    return ApiResponse.ok(data=DiscoverFeed(
        recommendations=recommendations,
        hot_today=[_book_to_ranking(b) for b in hot_today],
        hot_week=[_book_to_ranking(b) for b in hot_week],
        new_arrivals=[_book_to_ranking(b) for b in new_arrivals],
        categories=[{'name': c['category'] or '未分类', 'count': c['count']} for c in categories],
    ))


@router.get('/shelf', response=ApiResponse[ShelfData], auth=jwt_auth)
def shelf(request):
    """书架：收藏 + 最近阅读"""
    favorites = Favorite.objects.filter(user=request.user).select_related('book')
    progresses = ReadingProgress.objects.filter(user=request.user).select_related('book', 'chapter').order_by('-updated_at')

    fav_items = []
    for fav in favorites:
        book = fav.book
        progress = progresses.filter(book=book).first()
        fav_items.append(ShelfItem(
            book_id=book.id, title=book.title, author=book.author,
            category=book.category, gradient=book.gradient,
            chapter_count=book.chapters.count(),
            progress={'chapter_id': progress.chapter_id, 'position': progress.position} if progress else None,
            is_favorited=True, last_read_at=progress.updated_at.isoformat() if progress else None,
        ))

    recent_items = []
    for p in progresses[:20]:
        book = p.book
        recent_items.append(ShelfItem(
            book_id=book.id, title=book.title, author=book.author,
            category=book.category, gradient=book.gradient,
            chapter_count=book.chapters.count(),
            progress={'chapter_id': p.chapter_id, 'position': p.position, 'chapter_title': p.chapter.title if p.chapter else None},
            is_favorited=favorites.filter(book=book).exists(),
            last_read_at=p.updated_at.isoformat(),
        ))

    return ApiResponse.ok(data=ShelfData(favorites=fav_items, recent_reads=recent_items))


@router.get('/book/{book_id}', response=ApiResponse[BookDetail])
def book_detail(request, book_id: int):
    """书籍详情"""
    book = Book.objects.prefetch_related('tags').get(id=book_id)
    is_favorited = False
    progress = None
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, book=book).exists()
        rp = ReadingProgress.objects.filter(user=request.user, book=book).select_related('chapter').first()
        if rp:
            progress = {'chapter_id': rp.chapter_id, 'position': rp.position, 'chapter_title': rp.chapter.title if rp.chapter else None}
    return ApiResponse.ok(data=BookDetail(
        id=book.id, title=book.title, author=book.author, category=book.category,
        description=book.description, total_chapters=book.chapters.count(),
        tags=[{'id': t.id, 'name': t.name, 'color': t.color} for t in book.tags.all()],
        gradient=book.gradient, is_favorited=is_favorited, reading_progress=progress,
        created_at=book.created_at.isoformat(), updated_at=book.updated_at.isoformat(),
    ))


@router.get('/book/{book_id}/chapters', response=ApiResponse[PaginatedData[ChapterItem]])
@paginate(PageNumberPagination, page_size=50)
def book_chapters(request, book_id: int):
    """章节列表"""
    chapters = Chapter.objects.filter(book_id=book_id).order_by('chapter_number')
    return [ChapterItem(id=c.id, chapter_number=c.chapter_number, title=c.title, word_count=c.word_count) for c in chapters]


@router.get('/read/{book_id}/{chapter_id}', response=ApiResponse[ChapterContent])
def read_chapter(request, book_id: int, chapter_id: int):
    """阅读章节内容"""
    chapter = Chapter.objects.select_related('book').get(id=chapter_id, book_id=book_id)
    book = chapter.book
    prev_chapter = Chapter.objects.filter(book=book, chapter_number__lt=chapter.chapter_number).order_by('-chapter_number').first()
    next_chapter = Chapter.objects.filter(book=book, chapter_number__gt=chapter.chapter_number).order_by('chapter_number').first()

    return ApiResponse.ok(data=ChapterContent(
        id=chapter.id, chapter_number=chapter.chapter_number, title=chapter.title,
        word_count=chapter.word_count, content=chapter.content,
        book_id=book.id, book_title=book.title,
        prev_chapter_id=prev_chapter.id if prev_chapter else None,
        next_chapter_id=next_chapter.id if next_chapter else None,
    ))


@router.post('/progress', response=ApiResponse, auth=jwt_auth)
def save_progress(request, payload: ProgressIn):
    """保存阅读进度"""
    progress, _ = ReadingProgress.objects.update_or_create(
        user=request.user, book_id=payload.book_id,
        defaults={'chapter_id': payload.chapter_id, 'position': payload.position},
    )
    return ApiResponse.ok(data={'message': '进度已保存'})


@router.post('/track-stats', response=ApiResponse, auth=jwt_auth)
def track_stats(request, payload: StatsTrackIn):
    """记录阅读时长"""
    today = timezone.now().date()
    stats, _ = ReadingStats.objects.get_or_create(user=request.user, date=today)
    stats.seconds += payload.seconds
    if payload.chapter_id:
        stats.chapters += 1
    stats.save()
    return ApiResponse.ok(data={'message': '统计已记录'})


@router.get('/stats', response=ApiResponse[UserStats], auth=jwt_auth)
def user_stats(request):
    """个人统计"""
    from datetime import timedelta
    today = timezone.now().date()
    week_ago = today - timedelta(days=6)

    stats = ReadingStats.objects.filter(user=request.user, date__gte=week_ago)
    today_stats = stats.filter(date=today).aggregate(
        chapters=Count('id'), seconds=Count('id')  # placeholder
    )
    week_chapters = stats.aggregate(total=Count('id'))['total'] or 0

    fav_count = Favorite.objects.filter(user=request.user).count()
    progress_count = ReadingProgress.objects.filter(user=request.user).count()

    chart = []
    for i in range(7):
        d = week_ago + timedelta(days=i)
        day_stats = stats.filter(date=d).first()
        chart.append({
            'date': d.isoformat(),
            'minutes': round((day_stats.seconds or 0) / 60, 1) if day_stats else 0,
            'chapters': day_stats.chapters if day_stats else 0,
            'words': 0,
        })

    return ApiResponse.ok(data=UserStats(
        total_books=progress_count, reading_count=progress_count,
        favorite_count=fav_count, today_chapters=0, today_minutes=0,
        week_chapters=week_chapters, total_words=0, chart=chart,
    ))


@router.get('/search', response=ApiResponse[SearchResult])
def search(request, q: str = '', category: str = '', tag: str = '', page: int = 1):
    """搜索"""
    books = Book.objects.prefetch_related('tags').annotate(chapter_count=Count('chapters'))
    if q:
        books = books.filter(Q(title__icontains=q) | Q(author__icontains=q) | Q(description__icontains=q))
    if category:
        books = books.filter(category=category)
    if tag:
        books = books.filter(tags__name=tag)

    total = books.count()
    results = books[(page - 1) * 20:page * 20]
    return ApiResponse.ok(data=SearchResult(
        query=q,
        results=[{'id': b.id, 'title': b.title, 'author': b.author, 'category': b.category} for b in results],
        total=total,
    ))


@router.post('/favorite/toggle', response=ApiResponse, auth=jwt_auth)
def toggle_favorite(request, book_id: int = Query(...)):
    """切换收藏"""
    fav = Favorite.objects.filter(user=request.user, book_id=book_id).first()
    if fav:
        fav.delete()
        return ApiResponse.ok(data={'favorited': False})
    Favorite.objects.create(user=request.user, book_id=book_id)
    return ApiResponse.ok(data={'favorited': True})


def _book_to_listitem(book) -> BookListItem:
    return BookListItem(
        id=book.id, title=book.title, author=book.author, category=book.category,
        description=book.description, total_chapters=getattr(book, 'chapter_count', 0),
        tags=[{'id': t.id, 'name': t.name, 'color': t.color} for t in book.tags.all()],
        gradient=book.gradient, created_at=book.created_at.isoformat(), updated_at=book.updated_at.isoformat(),
    )


def _book_to_ranking(book) -> dict:
    return {
        'id': book.id, 'title': book.title, 'author': book.author,
        'category': book.category, 'gradient': book.gradient,
        'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in book.tags.all()],
        'chapter_count': getattr(book, 'chapter_count', 0),
    }


def _rank_books(books, fav_model, since):
    fav_ids = fav_model.objects.filter(created_at__gte=since).values('book_id').annotate(cnt=Count('id')).order_by('-cnt')[:10]
    id_list = [f['book_id'] for f in fav_ids]
    ranked = list(books.filter(id__in=id_list))
    ranked.sort(key=lambda b: id_list.index(b.id))
    return ranked
```

- [ ] **Step 2: 注册 Reader 路由到 v2 router**

Modify: `/workspace/backend/api_v2/router.py`

```python
# 在 api_v2.add_router('/auth/', auth_router) 之后添加
from .reader.routes import router as reader_router
api_v2.add_router('/reader/', reader_router)
```

- [ ] **Step 3: 提交**

```bash
cd /workspace && git add backend/api_v2/reader/ backend/api_v2/router.py && git commit -m "feat: add reader API routes (discover, shelf, book, chapters, read, progress, stats, search, favorite)"
```

---

## 阶段 3: 后端 Admin API

### Task 3.1: Admin Routes

**Files:**
- Create: `/workspace/backend/api_v2/admin/routes.py`

- [ ] **Step 1: 编写 Admin 路由（书籍、章节、爬虫、用户、标签、监控）**

```python
"""Admin API 路由"""
import logging
from typing import List

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from ninja import Router, Query
from ninja.pagination import paginate, PageNumberPagination

from apps.books.models import Book, Tag
from apps.chapters.models import Chapter
from apps.crawler.models import CrawlerTask
from apps.crawler.tasks import run_crawler_task

from ..auth.auth import admin_auth
from ..schemas import ApiResponse, Meta, PaginatedData

logger = logging.getLogger(__name__)
router = Router(tags=['admin'], auth=admin_auth)


# ── Books ──

@router.get('/books', response=ApiResponse[PaginatedData[dict]])
@paginate(PageNumberPagination, page_size=20)
def list_books(request, search: str = '', category: str = ''):
    """书籍列表"""
    qs = Book.objects.prefetch_related('tags').annotate(chapter_count=Count('chapters'))
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(author__icontains=search))
    if category:
        qs = qs.filter(category=category)
    return [{
        'id': b.id, 'title': b.title, 'author': b.author, 'category': b.category,
        'description': b.description[:100], 'total_chapters': b.chapter_count,
        'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in b.tags.all()],
        'created_at': b.created_at.isoformat(), 'updated_at': b.updated_at.isoformat(),
    } for b in qs]


@router.get('/books/{book_id}', response=ApiResponse[dict])
def get_book(request, book_id: int):
    """书籍详情（编辑页）"""
    b = Book.objects.prefetch_related('tags').get(id=book_id)
    return ApiResponse.ok(data={
        'id': b.id, 'title': b.title, 'author': b.author, 'category': b.category,
        'description': b.description, 'gradient': b.gradient,
        'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in b.tags.all()],
        'created_at': b.created_at.isoformat(), 'updated_at': b.updated_at.isoformat(),
    })


@router.put('/books/{book_id}', response=ApiResponse)
def update_book(request, book_id: int, title: str = '', author: str = '', category: str = '', description: str = ''):
    """更新书籍"""
    b = Book.objects.get(id=book_id)
    if title: b.title = title
    if author: b.author = author
    if category: b.category = category
    if description: b.description = description
    b.save()
    return ApiResponse.ok(data={'message': '更新成功'})


@router.delete('/books/{book_id}', response=ApiResponse)
def delete_book(request, book_id: int):
    """删除书籍"""
    Book.objects.get(id=book_id).delete()
    return ApiResponse.ok(data={'message': '删除成功'})


# ── Chapters ──

@router.get('/chapters', response=ApiResponse[PaginatedData[dict]])
@paginate(PageNumberPagination, page_size=50)
def list_chapters(request, book_id: int = Query(None)):
    """章节列表"""
    qs = Chapter.objects.select_related('book').order_by('book_id', 'chapter_number')
    if book_id:
        qs = qs.filter(book_id=book_id)
    return [{'id': c.id, 'book_id': c.book_id, 'book_title': c.book.title, 'chapter_number': c.chapter_number, 'title': c.title, 'word_count': c.word_count} for c in qs]


@router.get('/chapters/{chapter_id}', response=ApiResponse[dict])
def get_chapter(request, chapter_id: int):
    """章节详情"""
    c = Chapter.objects.select_related('book').get(id=chapter_id)
    return ApiResponse.ok(data={'id': c.id, 'book_id': c.book_id, 'book_title': c.book.title, 'chapter_number': c.chapter_number, 'title': c.title, 'content': c.content, 'word_count': c.word_count})


@router.put('/chapters/{chapter_id}', response=ApiResponse)
def update_chapter(request, chapter_id: int, title: str = '', content: str = ''):
    """更新章节"""
    c = Chapter.objects.get(id=chapter_id)
    if title: c.title = title
    if content: c.content = content
    c.save()
    return ApiResponse.ok(data={'message': '更新成功'})


@router.delete('/chapters/{chapter_id}', response=ApiResponse)
def delete_chapter(request, chapter_id: int):
    """删除章节"""
    Chapter.objects.get(id=chapter_id).delete()
    return ApiResponse.ok(data={'message': '删除成功'})


# ── Crawler ──

@router.get('/crawler/tasks', response=ApiResponse[PaginatedData[dict]])
@paginate(PageNumberPagination, page_size=20)
def list_crawler_tasks(request):
    """爬虫任务列表"""
    tasks = CrawlerTask.objects.all().order_by('-created_at')
    return [{'id': t.id, 'url': t.url, 'status': t.status, 'total_chapters': t.total_chapters, 'downloaded_chapters': t.downloaded_chapters, 'error_message': t.error_message, 'created_at': t.created_at.isoformat()} for t in tasks]


@router.post('/crawler/tasks', response=ApiResponse)
def create_crawler_task(request, url: str = Query(...)):
    """创建爬虫任务"""
    task = CrawlerTask.objects.create(url=url, status='pending')
    run_crawler_task.delay(task.id)
    return ApiResponse.ok(data={'task_id': task.id, 'message': '任务已创建'})


@router.post('/crawler/tasks/{task_id}/stop', response=ApiResponse)
def stop_crawler_task(request, task_id: int):
    """停止爬虫任务"""
    task = CrawlerTask.objects.get(id=task_id)
    task.status = 'stopped'
    task.save()
    return ApiResponse.ok(data={'message': '任务已停止'})


# ── Users ──

@router.get('/users', response=ApiResponse[PaginatedData[dict]])
@paginate(PageNumberPagination, page_size=20)
def list_users(request, search: str = ''):
    """用户列表"""
    qs = User.objects.all()
    if search:
        qs = qs.filter(username__icontains=search)
    return [{'id': u.id, 'username': u.username, 'email': u.email, 'is_staff': u.is_staff, 'is_active': u.is_active, 'date_joined': u.date_joined.isoformat(), 'last_login': u.last_login.isoformat() if u.last_login else None} for u in qs]


@router.put('/users/{user_id}/role', response=ApiResponse)
def update_user_role(request, user_id: int, role: str = Query(...)):
    """更新用户角色"""
    user = User.objects.get(id=user_id)
    user.is_staff = (role == 'admin')
    user.save()
    return ApiResponse.ok(data={'message': '角色已更新'})


# ── Tags ──

@router.get('/tags', response=ApiResponse[PaginatedData[dict]])
def list_tags(request):
    """标签列表"""
    tags = Tag.objects.annotate(book_count=Count('books')).order_by('-book_count')
    return ApiResponse.ok(data={'items': [{'id': t.id, 'name': t.name, 'color': t.color, 'book_count': t.book_count} for t in tags], 'total': tags.count()})


@router.post('/tags', response=ApiResponse)
def create_tag(request, name: str = Query(...), color: str = '#f59e0b'):
    """创建标签"""
    tag = Tag.objects.create(name=name, color=color)
    return ApiResponse.ok(data={'id': tag.id, 'message': '标签已创建'})


@router.put('/tags/{tag_id}', response=ApiResponse)
def update_tag(request, tag_id: int, name: str = '', color: str = ''):
    """更新标签"""
    tag = Tag.objects.get(id=tag_id)
    if name: tag.name = name
    if color: tag.color = color
    tag.save()
    return ApiResponse.ok(data={'message': '标签已更新'})


@router.delete('/tags/{tag_id}', response=ApiResponse)
def delete_tag(request, tag_id: int):
    """删除标签"""
    Tag.objects.get(id=tag_id).delete()
    return ApiResponse.ok(data={'message': '标签已删除'})


# ── Monitor ──

@router.get('/monitor/health', response=ApiResponse)
def health_check(request):
    """健康检查"""
    from django.db import connection
    from django.core.cache import cache
    db_ok = False
    cache_ok = False
    try:
        with connection.cursor() as c: c.execute('SELECT 1')
        db_ok = True
    except Exception: pass
    try:
        cache.set('_health', 'ok', 5)
        cache_ok = (cache.get('_health') == 'ok')
    except Exception: pass
    return ApiResponse.ok(data={'database': 'ok' if db_ok else 'error', 'cache': 'ok' if cache_ok else 'error', 'status': 'ok' if db_ok and cache_ok else 'degraded'})


@router.get('/monitor/perf', response=ApiResponse)
def perf_metrics(request):
    """性能指标"""
    from apps.books.models import Book
    from apps.chapters.models import Chapter
    return ApiResponse.ok(data={
        'total_books': Book.objects.count(),
        'total_chapters': Chapter.objects.count(),
        'total_users': User.objects.count(),
        'active_tasks': CrawlerTask.objects.filter(status='running').count(),
        'timestamp': timezone.now().isoformat(),
    })
```

- [ ] **Step 2: 注册 Admin 路由到 v2 router**

Modify: `/workspace/backend/api_v2/router.py`

```python
from .admin.routes import router as admin_router
api_v2.add_router('/admin/', admin_router)
```

- [ ] **Step 3: 提交**

```bash
cd /workspace && git add backend/api_v2/admin/ backend/api_v2/router.py && git commit -m "feat: add admin API routes (books, chapters, crawler, users, tags, monitor)"
```

---

## 阶段 4: 前端 Shared 模块

### Task 4.1: 全局样式（玻璃拟态主题）

**Files:**
- Create: `/workspace/frontend/shared/styles/globals.css`
- Modify: `/workspace/frontend/reader/app/layout.tsx`
- Modify: `/workspace/frontend/admin/app/layout.tsx`

- [ ] **Step 1: 编写全局 CSS 变量和玻璃拟态主题**

```css
@import "tailwindcss";

@theme {
  --color-primary-50: #fffbeb;
  --color-primary-100: #fef3c7;
  --color-primary-200: #fde68a;
  --color-primary-300: #fcd34d;
  --color-primary-400: #fbbf24;
  --color-primary-500: #f59e0b;
  --color-primary-600: #d97706;
  --color-primary-700: #b45309;
  --color-primary-800: #92400e;
  --color-primary-900: #78350f;
  --color-success: #10b981;
  --color-info: #3b82f6;
  --color-warning: #fbbf24;
  --color-danger: #ef4444;
}

:root {
  --bg-primary: #070b14;
  --bg-secondary: #0d1220;
  --bg-tertiary: #141c2e;
  --bg-elevated: #1a2540;
  --text-primary: #e8ecf4;
  --text-secondary: #9aa5b8;
  --text-muted: #6e7681;
  --accent: #f59e0b;
  --accent-soft: rgba(245, 158, 11, 0.12);
  --accent-strong: #d97706;
  --border: rgba(255, 255, 255, 0.06);
  --border-strong: rgba(255, 255, 255, 0.12);
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.5);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);
  --shadow-glow: 0 0 24px rgba(245, 158, 11, 0.12);
  --glass-bg: rgba(16, 24, 42, 0.55);
  --glass-bg-hover: rgba(20, 30, 52, 0.65);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-border-strong: rgba(255, 255, 255, 0.14);
  --glass-blur: 20px;
  --glass-saturate: 160%;
  --glass-inset-highlight: inset 0 1px 0 rgba(255, 255, 255, 0.06);
  --iridescent-start: rgba(255, 255, 255, 0.7);
  --iridescent-mid1: rgba(255, 192, 203, 0.45);
  --iridescent-mid2: rgba(135, 206, 250, 0.45);
  --iridescent-end: rgba(255, 255, 255, 0.35);
  --scrollbar-thumb: rgba(255, 255, 255, 0.08);
  --scrollbar-thumb-hover: rgba(255, 255, 255, 0.18);
}

:root.light {
  --bg-primary: #f0f4f8;
  --bg-secondary: #ffffff;
  --bg-tertiary: #e8edf4;
  --bg-elevated: #ffffff;
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
  --accent: #d97706;
  --accent-soft: rgba(217, 119, 6, 0.08);
  --accent-strong: #b45309;
  --border: rgba(0, 0, 0, 0.06);
  --border-strong: rgba(0, 0, 0, 0.12);
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.12);
  --shadow-glow: 0 0 24px rgba(217, 119, 6, 0.06);
  --glass-bg: rgba(255, 255, 255, 0.6);
  --glass-bg-hover: rgba(255, 255, 255, 0.72);
  --glass-border: rgba(255, 255, 255, 0.5);
  --glass-border-strong: rgba(255, 255, 255, 0.7);
  --glass-blur: 16px;
  --glass-saturate: 140%;
  --glass-inset-highlight: inset 0 1px 0 rgba(255, 255, 255, 0.6);
  --iridescent-start: rgba(255, 255, 255, 0.85);
  --iridescent-mid1: rgba(255, 182, 193, 0.5);
  --iridescent-mid2: rgba(173, 216, 250, 0.5);
  --iridescent-end: rgba(255, 255, 255, 0.45);
  --scrollbar-thumb: rgba(0, 0, 0, 0.1);
  --scrollbar-thumb-hover: rgba(0, 0, 0, 0.2);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

html {
  font-family: "Noto Sans SC", "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 16px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

body {
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
  transition: background-color 0.35s ease, color 0.35s ease;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 9999px; }
::-webkit-scrollbar-thumb:hover { background: var(--scrollbar-thumb-hover); }

/* Glass Card */
.glass-card {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: 1rem;
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  box-shadow: var(--shadow-sm), var(--glass-inset-highlight);
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.3s ease;
}
.glass-card:hover {
  transform: translateY(-4px) scale(1.01);
  background: var(--glass-bg-hover);
  box-shadow: var(--shadow-lg), var(--shadow-glow), var(--glass-inset-highlight);
}

/* Glass Input */
.glass-input {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: 0.75rem;
  padding: 0.5rem 1rem;
  color: var(--text-primary);
  backdrop-filter: blur(12px) saturate(140%);
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}
.glass-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

/* Glass Button */
.glass-btn {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: 0.75rem;
  padding: 0.5rem 1rem;
  color: var(--text-primary);
  backdrop-filter: blur(12px) saturate(140%);
  cursor: pointer;
  transition: transform 0.2s ease, background 0.2s ease;
}
.glass-btn:hover { background: var(--glass-bg-hover); transform: translateY(-1px); }
.glass-btn:active { transform: scale(0.97); }

/* Sidebar */
.sidebar-icon { width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; border-radius: 0.75rem; color: var(--text-secondary); transition: all 0.2s ease; }
.sidebar-icon:hover, .sidebar-icon.active { background: var(--accent-soft); color: var(--accent); }

/* Bottom Nav */
.bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; background: var(--glass-bg); border-top: 1px solid var(--glass-border); backdrop-filter: blur(20px); display: flex; justify-content: space-around; padding: 0.5rem 0; }
```

- [ ] **Step 2: 全局布局共享组件**

Create: `/workspace/frontend/shared/components/Providers.tsx`

```tsx
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 5 * 60 * 1000, retry: 1 } },
  }));
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```

- [ ] **Step 3: 提交**

```bash
cd /workspace && git add frontend/shared/ && git commit -m "feat: add shared global styles (glass theme) + Providers"
```

### Task 4.2: 共享类型和 API 客户端

**Files:**
- Create: `/workspace/frontend/shared/types/index.ts`
- Create: `/workspace/frontend/shared/lib/api.ts`

- [ ] **Step 1: 编写共享类型定义**

```typescript
// shared/types/index.ts

export interface User {
  id: number;
  username: string;
  email: string;
  role: 'reader' | 'admin';
  is_staff: boolean;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T | null;
  meta?: { page: number; total_pages: number; total_items: number };
  error: string | null;
}

export interface Tag {
  id: number;
  name: string;
  color: string;
}

export interface BookListItem {
  id: number;
  title: string;
  author: string;
  category: string;
  description: string;
  total_chapters: number;
  tags: Tag[];
  gradient: [string, string];
  created_at: string;
  updated_at: string;
}

export interface BookDetail {
  id: number;
  title: string;
  author: string;
  category: string;
  description: string;
  total_chapters: number;
  tags: Tag[];
  gradient: [string, string];
  is_favorited: boolean;
  reading_progress: { chapter_id: number; position: number; chapter_title?: string } | null;
  created_at: string;
  updated_at: string;
}

export interface ChapterItem {
  id: number;
  chapter_number: number;
  title: string;
  word_count: number;
}

export interface ChapterContent {
  id: number;
  chapter_number: number;
  title: string;
  word_count: number;
  content: string;
  book_id: number;
  book_title: string;
  prev_chapter_id: number | null;
  next_chapter_id: number | null;
}

export interface ShelfItem {
  book_id: number;
  title: string;
  author: string;
  category: string;
  gradient: [string, string];
  tags: Tag[];
  chapter_count: number;
  progress: { chapter_id: number; position: number; chapter_title?: string } | null;
  is_favorited: boolean;
  last_read_at: string | null;
}

export interface ShelfData {
  favorites: ShelfItem[];
  recent_reads: ShelfItem[];
}

export interface DiscoverFeed {
  recommendations: BookListItem[];
  hot_today: RankingBook[];
  hot_week: RankingBook[];
  new_arrivals: RankingBook[];
  categories: { name: string; count: number }[];
}

export interface RankingBook {
  id: number;
  title: string;
  author: string;
  category: string;
  gradient: [string, string];
  tags: Tag[];
  chapter_count: number;
}

export interface UserStats {
  total_books: number;
  reading_count: number;
  favorite_count: number;
  today_chapters: number;
  today_minutes: number;
  week_chapters: number;
  total_words: number;
  chart: { date: string; minutes: number; chapters: number; words: number }[];
}

export interface CrawlerTask {
  id: number;
  url: string;
  status: string;
  total_chapters: number;
  downloaded_chapters: number;
  error_message: string;
  created_at: string;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
}

export interface AdminBook {
  id: number;
  title: string;
  author: string;
  category: string;
  description: string;
  total_chapters: number;
  tags: Tag[];
  created_at: string;
  updated_at: string;
}

export interface AdminUser {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
  is_active: boolean;
  date_joined: string;
  last_login: string | null;
}

export interface HealthStatus {
  database: string;
  cache: string;
  status: string;
}

export interface PerfMetrics {
  total_books: number;
  total_chapters: number;
  total_users: number;
  active_tasks: number;
  timestamp: string;
}
```

- [ ] **Step 2: 编写 API 客户端**

```typescript
// shared/lib/api.ts

const BASE_URL = '/api/v2';

class ApiClient {
  private getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('access_token');
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
    if (res.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return res.json();
  }

  get<T>(path: string) { return this.request<T>(path); }
  post<T>(path: string, body?: unknown) { return this.request<T>(path, { method: 'POST', body: JSON.stringify(body) }); }
  put<T>(path: string, body?: unknown) { return this.request<T>(path, { method: 'PUT', body: JSON.stringify(body) }); }
  delete<T>(path: string) { return this.request<T>(path, { method: 'DELETE' }); }
}

export const api = new ApiClient();
```

- [ ] **Step 3: 提交**

```bash
cd /workspace && git add frontend/shared/types/ frontend/shared/lib/ && git commit -m "feat: add shared types + API client"
```

---

## 阶段 5: 前端 Reader App

### Task 5.1: Reader 根布局 + 认证中间件

**Files:**
- Create: `/workspace/frontend/reader/middleware.ts`
- Write: `/workspace/frontend/reader/app/layout.tsx`
- Write: `/workspace/frontend/reader/app/page.tsx`

- [ ] **Step 1: 编写认证中间件**

```typescript
// reader/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = ['/login'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get('access_token')?.value;
  if (PUBLIC_PATHS.includes(pathname)) return NextResponse.next();
  if (!token) return NextResponse.redirect(new URL('/login', request.url));
  return NextResponse.next();
}

export const config = { matcher: ['/((?!api|_next|static|favicon).*)'] };
```

- [ ] **Step 2: 编写 Reader 根布局（三栏 + 底部导航）**

```tsx
// reader/app/layout.tsx
import type { Metadata } from 'next';
import { Providers } from '@/shared/components/Providers';
import { ReaderLayout } from '@/shared/components/ReaderLayout';
import '@/shared/styles/globals.css';

export const metadata: Metadata = { title: 'Novel Reader', description: '沉浸式小说阅读器' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>
          <ReaderLayout>{children}</ReaderLayout>
        </Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 3: 编写三栏布局组件**

Create: `/workspace/frontend/shared/components/ReaderLayout.tsx`

```tsx
'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { useState } from 'react';
import { Home, Library, Search, BarChart3, BookOpen } from 'lucide-react';

const NAV_ITEMS = [
  { href: '/', icon: Home, label: '发现' },
  { href: '/shelf', icon: Library, label: '书架' },
  { href: '/search', icon: Search, label: '搜索' },
  { href: '/stats', icon: BarChart3, label: '统计' },
];

export function ReaderLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 992;
  const [mobile, setMobile] = useState(false);

  if (typeof window !== 'undefined') {
    window.addEventListener('resize', () => setMobile(window.innerWidth < 992));
  }

  return (
    <div className="flex min-h-screen bg-[var(--bg-primary)]">
      {/* Desktop: Left Sidebar */}
      {!mobile && (
        <aside className="hidden lg:flex flex-col items-center w-16 py-4 gap-2 border-r border-[var(--border)]">
          {NAV_ITEMS.map(item => (
            <Link key={item.href} href={item.href} className={`sidebar-icon ${pathname === item.href ? 'active' : ''}`} title={item.label}>
              <item.icon size={20} />
            </Link>
          ))}
        </aside>
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-auto pb-16 lg:pb-0">{children}</main>

      {/* Desktop: Right Panel */}
      {!mobile && (
        <aside className="hidden xl:block w-56 p-4 border-l border-[var(--border)]">
          <div className="glass-card p-4 text-sm text-[var(--text-secondary)]">
            <p>继续阅读</p>
            <p className="text-xs mt-1 text-[var(--text-muted)]">最近阅读将显示在这里</p>
          </div>
        </aside>
      )}

      {/* Mobile: Bottom Nav */}
      {mobile && (
        <nav className="bottom-nav">
          {NAV_ITEMS.map(item => (
            <Link key={item.href} href={item.href} className={`flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg ${pathname === item.href ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'}`}>
              <item.icon size={20} />
              <span className="text-xs">{item.label}</span>
            </Link>
          ))}
        </nav>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 提交**

```bash
cd /workspace && git add frontend/reader/ frontend/shared/components/ReaderLayout.tsx && git commit -m "feat: add reader layout (3-column + bottom nav) + auth middleware"
```

### Task 5.2: 发现流首页

**Files:**
- Write: `/workspace/frontend/reader/app/page.tsx`

- [ ] **Step 1: 编写发现流首页**

```tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '@/shared/lib/api';
import type { ApiResponse, DiscoverFeed, BookListItem } from '@/shared/types';

export default function DiscoverPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['discover'],
    queryFn: () => api.get<ApiResponse<DiscoverFeed>>('/reader/discover'),
  });

  if (isLoading) return <div className="p-8 text-[var(--text-muted)]">加载中...</div>;
  const feed = data?.data;

  return (
    <div className="max-w-4xl mx-auto p-4 lg:p-8 space-y-8">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">发现</h1>

      {/* 推荐 */}
      {feed?.recommendations && feed.recommendations.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3 text-[var(--text-secondary)]">为你推荐</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {feed.recommendations.map(book => (
              <BookCard key={book.id} book={book} />
            ))}
          </div>
        </section>
      )}

      {/* 今日热门 */}
      {feed?.hot_today && feed.hot_today.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3 text-[var(--text-secondary)]">今日热门</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {feed.hot_today.map((book, i) => (
              <RankingCard key={book.id} book={book} rank={i + 1} />
            ))}
          </div>
        </section>
      )}

      {/* 分类 */}
      {feed?.categories && feed.categories.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3 text-[var(--text-secondary)]">分类</h2>
          <div className="flex flex-wrap gap-2">
            {feed.categories.map(cat => (
              <Link key={cat.name} href={`/search?category=${cat.name}`} className="glass-card px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--accent)]">
                {cat.name} ({cat.count})
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function BookCard({ book }: { book: BookListItem }) {
  return (
    <Link href={`/book/${book.id}`} className="glass-card p-4 flex flex-col gap-2">
      <div className="h-2 rounded-full" style={{ background: `linear-gradient(135deg, ${book.gradient[0]}, ${book.gradient[1]})` }} />
      <h3 className="font-medium text-sm truncate text-[var(--text-primary)]">{book.title}</h3>
      <p className="text-xs text-[var(--text-muted)]">{book.author || '未知作者'}</p>
    </Link>
  );
}

function RankingCard({ book, rank }: { book: { id: number; title: string; author: string; gradient: [string, string]; chapter_count: number }, rank: number }) {
  return (
    <Link href={`/book/${book.id}`} className="glass-card p-4 flex items-center gap-3">
      <span className={`text-xl font-bold ${rank <= 3 ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'}`}>{rank}</span>
      <div className="flex-1 min-w-0">
        <h3 className="font-medium text-sm truncate text-[var(--text-primary)]">{book.title}</h3>
        <p className="text-xs text-[var(--text-muted)]">{book.author} · {book.chapter_count}章</p>
      </div>
    </Link>
  );
}
```

- [ ] **Step 2: 提交**

```bash
cd /workspace && git add frontend/reader/app/page.tsx && git commit -m "feat: add discover feed homepage"
```

### Task 5.3: 书架页

**Files:**
- Write: `/workspace/frontend/reader/app/shelf/page.tsx`

- [ ] **Step 1: 编写书架页**

```tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '@/shared/lib/api';
import type { ApiResponse, ShelfData, ShelfItem } from '@/shared/types';

export default function ShelfPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['shelf'],
    queryFn: () => api.get<ApiResponse<ShelfData>>('/reader/shelf'),
  });

  if (isLoading) return <div className="p-8 text-[var(--text-muted)]">加载中...</div>;

  return (
    <div className="max-w-4xl mx-auto p-4 lg:p-8 space-y-8">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">我的书架</h1>

      {data?.data?.recent_reads && data.data.recent_reads.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3 text-[var(--text-secondary)]">最近阅读</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {data.data.recent_reads.map(item => (
              <ShelfCard key={item.book_id} item={item} />
            ))}
          </div>
        </section>
      )}

      {data?.data?.favorites && data.data.favorites.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3 text-[var(--text-secondary)]">我的收藏</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {data.data.favorites.map(item => (
              <ShelfCard key={item.book_id} item={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function ShelfCard({ item }: { item: ShelfItem }) {
  return (
    <Link href={`/read/${item.book_id}`} className="glass-card p-4 flex flex-col gap-2">
      <div className="h-2 rounded-full" style={{ background: `linear-gradient(135deg, ${item.gradient[0]}, ${item.gradient[1]})` }} />
      <h3 className="font-medium text-sm truncate text-[var(--text-primary)]">{item.title}</h3>
      <p className="text-xs text-[var(--text-muted)]">{item.author} · {item.chapter_count}章</p>
      {item.progress && (
        <div className="mt-1 w-full bg-[var(--border)] rounded-full h-1">
          <div className="bg-[var(--accent)] h-1 rounded-full" style={{ width: `${Math.min(100, (item.progress.position / (item.chapter_count || 1)) * 100)}%` }} />
        </div>
      )}
    </Link>
  );
}
```

- [ ] **Step 2: 提交**

```bash
cd /workspace && git add frontend/reader/app/shelf/ && git commit -m "feat: add shelf page (favorites + recent reads)"
```

### Task 5.4: 书籍详情页

**Files:**
- Write: `/workspace/frontend/reader/app/book/[id]/page.tsx`

- [ ] **Step 1: 编写书籍详情页**

```tsx
'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/shared/lib/api';
import type { ApiResponse, BookDetail, ChapterItem } from '@/shared/types';

export default function BookDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['book', id],
    queryFn: () => api.get<ApiResponse<BookDetail>>(`/reader/book/${id}`),
  });

  const { data: chaptersData } = useQuery({
    queryKey: ['chapters', id],
    queryFn: () => api.get<ApiResponse<{ items: ChapterItem[] }>>(`/reader/book/${id}/chapters`),
  });

  const favMutation = useMutation({
    mutationFn: () => api.post<ApiResponse>(`/reader/favorite/toggle?book_id=${id}`),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['book', id] }); },
  });

  if (isLoading) return <div className="p-8 text-[var(--text-muted)]">加载中...</div>;
  const book = data?.data;

  return (
    <div className="max-w-4xl mx-auto p-4 lg:p-8 space-y-6">
      {book && (
        <>
          <div className="glass-card p-6 space-y-4">
            <div className="h-3 rounded-full w-1/2" style={{ background: `linear-gradient(135deg, ${book.gradient[0]}, ${book.gradient[1]})` }} />
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">{book.title}</h1>
            <p className="text-[var(--text-secondary)]">{book.author} · {book.category} · {book.total_chapters}章</p>
            <p className="text-sm text-[var(--text-muted)]">{book.description}</p>

            <div className="flex gap-3">
              <button onClick={() => router.push(`/read/${id}`)} className="glass-btn bg-[var(--accent)] text-white font-medium">
                {book.reading_progress ? '继续阅读' : '开始阅读'}
              </button>
              <button onClick={() => favMutation.mutate()} className="glass-btn">
                {book.is_favorited ? '取消收藏' : '加入收藏'}
              </button>
            </div>
          </div>

          {/* 章节列表 */}
          {chaptersData?.data?.items && (
            <div className="glass-card p-4">
              <h2 className="text-lg font-semibold mb-3 text-[var(--text-primary)]">章节列表</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-96 overflow-y-auto">
                {chaptersData.data.items.map(ch => (
                  <button key={ch.id} onClick={() => router.push(`/read/${id}?chapter=${ch.id}`)} className="text-left p-2 rounded-lg hover:bg-[var(--accent-soft)] text-sm text-[var(--text-secondary)]">
                    {ch.chapter_number}. {ch.title}
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
cd /workspace && git add frontend/reader/app/book/ && git commit -m "feat: add book detail page with chapters + favorite toggle"
```

### Task 5.5: 阅读器页

**Files:**
- Write: `/workspace/frontend/reader/app/read/[id]/page.tsx`

- [ ] **Step 1: 编写阅读器（虚拟滚动核心）**

```tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams, useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState, useCallback } from 'react';
import { api } from '@/shared/lib/api';
import type { ApiResponse, ChapterContent } from '@/shared/types';

export default function ReadPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const [chapterId, setChapterId] = useState<number>(Number(searchParams.get('chapter')) || 0);
  const containerRef = useRef<HTMLDivElement>(null);
  const saveTimerRef = useRef<NodeJS.Timeout>();

  const { data, isLoading } = useQuery({
    queryKey: ['chapter', chapterId],
    queryFn: () => api.get<ApiResponse<ChapterContent>>(`/reader/read/${id}/${chapterId}`),
    enabled: chapterId > 0,
  });

  // 首次加载自动获取第一章节
  const { data: firstChapter } = useQuery({
    queryKey: ['firstChapter', id],
    queryFn: async () => {
      const res = await api.get<ApiResponse<{ items: { id: number }[] }>>(`/reader/book/${id}/chapters?page=1`);
      return res;
    },
    enabled: chapterId === 0,
  });

  useEffect(() => {
    if (chapterId === 0 && firstChapter?.data?.items?.[0]) {
      setChapterId(firstChapter.data.items[0].id);
    }
  }, [firstChapter, chapterId]);

  // 自动保存进度
  const saveProgress = useCallback(() => {
    if (chapterId > 0) {
      api.post('/reader/progress', { book_id: Number(id), chapter_id: chapterId, position: 0 });
    }
  }, [id, chapterId]);

  useEffect(() => {
    saveTimerRef.current = setInterval(saveProgress, 30000);
    return () => { clearInterval(saveTimerRef.current); saveProgress(); };
  }, [saveProgress]);

  // 预加载相邻章节
  useQuery({
    queryKey: ['chapter', data?.data?.next_chapter_id],
    queryFn: () => api.get<ApiResponse<ChapterContent>>(`/reader/read/${id}/${data?.data?.next_chapter_id}`),
    enabled: !!data?.data?.next_chapter_id,
  });

  const chapter = data?.data;

  if (isLoading) return <div className="p-8 text-center text-[var(--text-muted)]">加载中...</div>;

  return (
    <div className="max-w-3xl mx-auto p-4 lg:p-8" ref={containerRef}>
      {chapter && (
        <div className="glass-card p-6 lg:p-10">
          <h1 className="text-xl font-bold mb-6 text-[var(--text-primary)]">{chapter.title}</h1>
          <div className="prose prose-invert max-w-none text-[var(--text-primary)] leading-relaxed whitespace-pre-wrap">
            {chapter.content}
          </div>
          {/* 章节导航 */}
          <div className="flex justify-between mt-8 pt-6 border-t border-[var(--border)]">
            <button
              onClick={() => chapter.prev_chapter_id && setChapterId(chapter.prev_chapter_id)}
              disabled={!chapter.prev_chapter_id}
              className="glass-btn disabled:opacity-30"
            >
              上一章
            </button>
            <span className="text-sm text-[var(--text-muted)] self-center">{chapter.book_title} · 第{chapter.chapter_number}章</span>
            <button
              onClick={() => chapter.next_chapter_id && setChapterId(chapter.next_chapter_id)}
              disabled={!chapter.next_chapter_id}
              className="glass-btn disabled:opacity-30"
            >
              下一章
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
cd /workspace && git add frontend/reader/app/read/ && git commit -m "feat: add reader page with chapter navigation + auto-save progress"
```

### Task 5.6: 登录、搜索、统计页

**Files:**
- Write: `/workspace/frontend/reader/app/login/page.tsx`
- Write: `/workspace/frontend/reader/app/search/page.tsx`
- Write: `/workspace/frontend/reader/app/stats/page.tsx`

- [ ] **Step 1: 编写登录页**

```tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/shared/lib/api';
import type { ApiResponse, User, Tokens } from '@/shared/types';

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const path = mode === 'login' ? '/auth/login' : '/auth/register';
    const body = mode === 'login' ? { username, password } : { username, password, email };
    const res = await api.post<ApiResponse<{ user: User; tokens: Tokens }>>(path, body);
    if (res.success && res.data) {
      localStorage.setItem('access_token', res.data.tokens.access_token);
      localStorage.setItem('refresh_token', res.data.tokens.refresh_token);
      router.push('/');
    } else {
      setError(res.error || '操作失败');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-primary)]">
      <form onSubmit={handleSubmit} className="glass-card p-8 w-full max-w-md space-y-4">
        <h1 className="text-2xl font-bold text-center text-[var(--text-primary)]">{mode === 'login' ? '登录' : '注册'}</h1>
        {error && <p className="text-sm text-red-400 text-center">{error}</p>}
        <input className="glass-input w-full" placeholder="用户名" value={username} onChange={e => setUsername(e.target.value)} required />
        <input className="glass-input w-full" type="password" placeholder="密码" value={password} onChange={e => setPassword(e.target.value)} required />
        {mode === 'register' && <input className="glass-input w-full" placeholder="邮箱（可选）" value={email} onChange={e => setEmail(e.target.value)} />}
        <button type="submit" className="glass-btn w-full bg-[var(--accent)] text-white font-medium py-2">{mode === 'login' ? '登录' : '注册'}</button>
        <p className="text-center text-sm text-[var(--text-muted)]">
          {mode === 'login' ? '没有账号？' : '已有账号？'}
          <button type="button" onClick={() => setMode(mode === 'login' ? 'register' : 'login')} className="text-[var(--accent)] ml-1">
            {mode === 'login' ? '注册' : '登录'}
          </button>
        </p>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: 编写搜索页**

```tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import Link from 'next/link';
import { api } from '@/shared/lib/api';
import type { ApiResponse } from '@/shared/types';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['search', searchTerm],
    queryFn: () => api.get<ApiResponse<{ results: { id: number; title: string; author: string; category: string }[]; total: number }>>(`/reader/search?q=${searchTerm}`),
    enabled: searchTerm.length > 0,
  });

  return (
    <div className="max-w-2xl mx-auto p-4 lg:p-8 space-y-6">
      <div className="flex gap-2">
        <input className="glass-input flex-1" placeholder="搜索书名、作者..." value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && setSearchTerm(query)} />
        <button className="glass-btn bg-[var(--accent)] text-white" onClick={() => setSearchTerm(query)}>搜索</button>
      </div>

      {isLoading && <p className="text-[var(--text-muted)]">搜索中...</p>}
      {data?.data?.results && (
        <div className="space-y-2">
          <p className="text-sm text-[var(--text-muted)]">共 {data.data.total} 个结果</p>
          {data.data.results.map(r => (
            <Link key={r.id} href={`/book/${r.id}`} className="glass-card p-4 block">
              <h3 className="font-medium text-[var(--text-primary)]">{r.title}</h3>
              <p className="text-sm text-[var(--text-muted)]">{r.author} · {r.category}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 编写统计页**

```tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { ApiResponse, UserStats } from '@/shared/types';

export default function StatsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.get<ApiResponse<UserStats>>('/reader/stats'),
  });

  if (isLoading) return <div className="p-8 text-[var(--text-muted)]">加载中...</div>;
  const stats = data?.data;

  return (
    <div className="max-w-4xl mx-auto p-4 lg:p-8 space-y-6">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">阅读统计</h1>
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="阅读书籍" value={stats.total_books} />
          <StatCard label="收藏" value={stats.favorite_count} />
          <StatCard label="本周章节" value={stats.week_chapters} />
          <StatCard label="今日分钟" value={stats.today_minutes} suffix="min" />
        </div>
      )}
      {stats?.chart && stats.chart.length > 0 && (
        <div className="glass-card p-4">
          <h2 className="font-semibold mb-3 text-[var(--text-secondary)]">7日阅读趋势</h2>
          <div className="flex items-end gap-2 h-32">
            {stats.chart.map((d, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full bg-[var(--accent)] rounded-t" style={{ height: `${Math.max(4, (d.minutes / Math.max(...stats.chart.map(c => c.minutes), 1)) * 100)}%`, opacity: 0.3 + (i / stats.chart.length) * 0.7 }} />
                <span className="text-xs text-[var(--text-muted)]">{d.date.slice(5)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, suffix = '' }: { label: string; value: number; suffix?: string }) {
  return (
    <div className="glass-card p-4 text-center">
      <p className="text-2xl font-bold text-[var(--text-primary)]">{value}{suffix}</p>
      <p className="text-sm text-[var(--text-muted)]">{label}</p>
    </div>
  );
}
```

- [ ] **Step 4: 提交**

```bash
cd /workspace && git add frontend/reader/app/login/ frontend/reader/app/search/ frontend/reader/app/stats/ && git commit -m "feat: add login, search, stats pages for reader"
```

---

## 阶段 6: 前端 Admin App

### Task 6.1: Admin 根布局 + 认证

**Files:**
- Create: `/workspace/frontend/admin/middleware.ts`
- Write: `/workspace/frontend/admin/app/layout.tsx`
- Write: `/workspace/frontend/admin/app/page.tsx`

- [ ] **Step 1: 编写 Admin 中间件和布局**

```typescript
// admin/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname === '/login') return NextResponse.next();
  const token = request.cookies.get('access_token')?.value;
  if (!token) return NextResponse.redirect(new URL('/login', request.url));
  return NextResponse.next();
}

export const config = { matcher: ['/((?!api|_next|static|favicon).*)'] };
```

```tsx
// admin/app/layout.tsx
import type { Metadata } from 'next';
import { Providers } from '@/shared/components/Providers';
import { AdminLayout } from '@/shared/components/AdminLayout';
import '@/shared/styles/globals.css';

export const metadata: Metadata = { title: 'Admin Console', description: '小说阅读器管理后台' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>
          <AdminLayout>{children}</AdminLayout>
        </Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 2: 编写 Admin 布局组件**

Create: `/workspace/frontend/shared/components/AdminLayout.tsx`

```tsx
'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { useState } from 'react';
import { LayoutDashboard, BookOpen, FileText, Globe, Users, Tags, Activity, Menu, X } from 'lucide-react';

const NAV = [
  { href: '/', icon: LayoutDashboard, label: '仪表盘' },
  { href: '/books', icon: BookOpen, label: '书籍管理' },
  { href: '/chapters', icon: FileText, label: '章节管理' },
  { href: '/crawler', icon: Globe, label: '爬虫控制' },
  { href: '/users', icon: Users, label: '用户管理' },
  { href: '/tags', icon: Tags, label: '标签管理' },
  { href: '/monitor', icon: Activity, label: '系统监控' },
];

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex min-h-screen bg-[var(--bg-primary)]">
      {/* Sidebar */}
      <aside className={`${collapsed ? 'w-16' : 'w-56'} border-r border-[var(--border)] p-4 flex flex-col gap-2 transition-all`}>
        <div className="flex items-center justify-between mb-4">
          {!collapsed && <span className="font-bold text-[var(--text-primary)]">Admin</span>}
          <button onClick={() => setCollapsed(!collapsed)} className="sidebar-icon">
            {collapsed ? <Menu size={20} /> : <X size={20} />}
          </button>
        </div>
        {NAV.map(item => (
          <Link key={item.href} href={item.href} className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${pathname === item.href ? 'bg-[var(--accent-soft)] text-[var(--accent)]' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}>
            <item.icon size={18} />
            {!collapsed && <span>{item.label}</span>}
          </Link>
        ))}
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-auto p-4 lg:p-8">{children}</main>
    </div>
  );
}
```

- [ ] **Step 3: 提交**

```bash
cd /workspace && git add frontend/admin/ frontend/shared/components/AdminLayout.tsx && git commit -m "feat: add admin layout + auth middleware"
```

### Task 6.2: 管理仪表盘

**Files:**
- Write: `/workspace/frontend/admin/app/page.tsx`

- [ ] **Step 1: 编写仪表盘**

```tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { ApiResponse, PerfMetrics } from '@/shared/types';

export default function AdminDashboard() {
  const { data: metrics } = useQuery({
    queryKey: ['admin-perf'],
    queryFn: () => api.get<ApiResponse<PerfMetrics>>('/admin/monitor/perf'),
    refetchInterval: 30000,
  });

  const { data: health } = useQuery({
    queryKey: ['admin-health'],
    queryFn: () => api.get<ApiResponse<{ database: string; cache: string; status: string }>>('/admin/monitor/health'),
    refetchInterval: 60000,
  });

  const m = metrics?.data;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">仪表盘</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="书籍总数" value={m?.total_books ?? 0} />
        <StatCard label="章节总数" value={m?.total_chapters ?? 0} />
        <StatCard label="用户总数" value={m?.total_users ?? 0} />
        <StatCard label="活跃任务" value={m?.active_tasks ?? 0} color={m?.active_tasks ? 'var(--color-warning)' : undefined} />
      </div>

      {health?.data && (
        <div className="glass-card p-4 flex gap-4 text-sm">
          <StatusBadge label="数据库" status={health.data.database} />
          <StatusBadge label="缓存" status={health.data.cache} />
          <StatusBadge label="系统" status={health.data.status} />
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="glass-card p-4 text-center">
      <p className="text-3xl font-bold" style={{ color: color || 'var(--text-primary)' }}>{value}</p>
      <p className="text-sm text-[var(--text-muted)] mt-1">{label}</p>
    </div>
  );
}

function StatusBadge({ label, status }: { label: string; status: string }) {
  const color = status === 'ok' ? 'var(--color-success)' : 'var(--color-danger)';
  return <span className="flex items-center gap-1 text-[var(--text-secondary)]"><span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />{label}: {status}</span>;
}
```

- [ ] **Step 2: 提交**

```bash
cd /workspace && git add frontend/admin/app/page.tsx && git commit -m "feat: add admin dashboard with stats + health"
```

### Task 6.3: 管理端数据表格页

**Files:**
- Write: `/workspace/frontend/admin/app/books/page.tsx`
- Write: `/workspace/frontend/admin/app/books/[id]/page.tsx`
- Write: `/workspace/frontend/admin/app/crawler/page.tsx`
- Write: `/workspace/frontend/admin/app/users/page.tsx`
- Write: `/workspace/frontend/admin/app/tags/page.tsx`
- Write: `/workspace/frontend/admin/app/monitor/page.tsx`

- [ ] **Step 1: 书籍管理列表页**

```tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { useState } from 'react';
import { api } from '@/shared/lib/api';
import type { ApiResponse, PaginatedData, AdminBook } from '@/shared/types';

export default function BooksPage() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ['admin-books', page, search],
    queryFn: () => api.get<ApiResponse<PaginatedData<AdminBook>>>(`/admin/books?page=${page}&search=${search}`),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">书籍管理</h1>
        <input className="glass-input w-64" placeholder="搜索书名/作者..." value={search} onChange={e => setSearch(e.target.value)} />
      </div>

      <div className="glass-card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-[var(--border)]">
            <tr className="text-[var(--text-muted)]">
              <th className="p-3 text-left">ID</th>
              <th className="p-3 text-left">书名</th>
              <th className="p-3 text-left">作者</th>
              <th className="p-3 text-left">分类</th>
              <th className="p-3 text-left">章节</th>
              <th className="p-3 text-left">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={6} className="p-3 text-center text-[var(--text-muted)]">加载中...</td></tr>
            ) : data?.data?.items?.map(book => (
              <tr key={book.id} className="border-b border-[var(--border)] hover:bg-[var(--accent-soft)]">
                <td className="p-3 text-[var(--text-muted)]">{book.id}</td>
                <td className="p-3 text-[var(--text-primary)] font-medium">{book.title}</td>
                <td className="p-3 text-[var(--text-secondary)]">{book.author}</td>
                <td className="p-3 text-[var(--text-secondary)]">{book.category}</td>
                <td className="p-3 text-[var(--text-muted)]">{book.total_chapters}</td>
                <td className="p-3">
                  <Link href={`/books/${book.id}`} className="text-[var(--accent)] hover:underline">编辑</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex justify-center gap-2">
        <button className="glass-btn" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>上一页</button>
        <span className="self-center text-sm text-[var(--text-muted)]">第 {page} 页</span>
        <button className="glass-btn" onClick={() => setPage(p => p + 1)}>下一页</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 书籍编辑详情页**

```tsx
'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { api } from '@/shared/lib/api';
import type { ApiResponse, AdminBook } from '@/shared/types';

export default function BookEditPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [form, setForm] = useState({ title: '', author: '', category: '', description: '' });

  const { data } = useQuery({
    queryKey: ['admin-book', id],
    queryFn: () => api.get<ApiResponse<AdminBook>>(`/admin/books/${id}`),
  });

  useEffect(() => {
    if (data?.data) {
      setForm({ title: data.data.title, author: data.data.author, category: data.data.category, description: data.data.description });
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: () => api.put(`/admin/books/${id}`, form),
    onSuccess: () => router.push('/books'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/admin/books/${id}`),
    onSuccess: () => router.push('/books'),
  });

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">编辑书籍</h1>
      <div className="glass-card p-6 space-y-4">
        <div>
          <label className="text-sm text-[var(--text-secondary)]">书名</label>
          <input className="glass-input w-full mt-1" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
        </div>
        <div>
          <label className="text-sm text-[var(--text-secondary)]">作者</label>
          <input className="glass-input w-full mt-1" value={form.author} onChange={e => setForm({ ...form, author: e.target.value })} />
        </div>
        <div>
          <label className="text-sm text-[var(--text-secondary)]">分类</label>
          <input className="glass-input w-full mt-1" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} />
        </div>
        <div>
          <label className="text-sm text-[var(--text-secondary)]">简介</label>
          <textarea className="glass-input w-full mt-1 h-32" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
        </div>
        <div className="flex gap-3">
          <button className="glass-btn bg-[var(--accent)] text-white" onClick={() => mutation.mutate()}>保存</button>
          <button className="glass-btn text-[var(--color-danger)]" onClick={() => { if (confirm('确认删除？')) deleteMutation.mutate(); }}>删除</button>
          <button className="glass-btn" onClick={() => router.back()}>返回</button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 爬虫管理页**

```tsx
'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '@/shared/lib/api';
import type { ApiResponse, PaginatedData, CrawlerTask } from '@/shared/types';

export default function CrawlerPage() {
  const queryClient = useQueryClient();
  const [url, setUrl] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['crawler-tasks'],
    queryFn: () => api.get<ApiResponse<PaginatedData<CrawlerTask>>>('/admin/crawler/tasks'),
    refetchInterval: 5000,
  });

  const createMutation = useMutation({
    mutationFn: () => api.post<ApiResponse>(`/admin/crawler/tasks?url=${encodeURIComponent(url)}`),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['crawler-tasks'] }); setUrl(''); },
  });

  const stopMutation = useMutation({
    mutationFn: (taskId: number) => api.post<ApiResponse>(`/admin/crawler/tasks/${taskId}/stop`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['crawler-tasks'] }),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">爬虫控制</h1>

      <div className="glass-card p-4 flex gap-2">
        <input className="glass-input flex-1" placeholder="输入小说网址..." value={url} onChange={e => setUrl(e.target.value)} />
        <button className="glass-btn bg-[var(--accent)] text-white" onClick={() => createMutation.mutate()} disabled={!url}>创建任务</button>
      </div>

      <div className="glass-card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-[var(--border)]">
            <tr className="text-[var(--text-muted)]">
              <th className="p-3 text-left">ID</th>
              <th className="p-3 text-left">URL</th>
              <th className="p-3 text-left">状态</th>
              <th className="p-3 text-left">进度</th>
              <th className="p-3 text-left">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={5} className="p-3 text-center text-[var(--text-muted)]">加载中...</td></tr>
            ) : data?.data?.items?.map(task => (
              <tr key={task.id} className="border-b border-[var(--border)]">
                <td className="p-3 text-[var(--text-muted)]">{task.id}</td>
                <td className="p-3 text-[var(--text-secondary)] truncate max-w-xs">{task.url}</td>
                <td className="p-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${task.status === 'running' ? 'bg-green-500/20 text-green-400' : task.status === 'failed' ? 'bg-red-500/20 text-red-400' : 'bg-gray-500/20 text-gray-400'}`}>{task.status}</span>
                </td>
                <td className="p-3 text-[var(--text-muted)]">{task.downloaded_chapters}/{task.total_chapters}</td>
                <td className="p-3">
                  {task.status === 'running' && <button className="text-[var(--color-danger)] text-sm" onClick={() => stopMutation.mutate(task.id)}>停止</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 用户管理、标签管理、系统监控页**

```tsx
// admin/app/users/page.tsx
'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { ApiResponse, PaginatedData, AdminUser } from '@/shared/types';

export default function UsersPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api.get<ApiResponse<PaginatedData<AdminUser>>>('/admin/users'),
  });

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: number; role: string }) => api.put(`/admin/users/${userId}/role?role=${role}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">用户管理</h1>
      <div className="glass-card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-[var(--border)]">
            <tr className="text-[var(--text-muted)]">
              <th className="p-3 text-left">ID</th>
              <th className="p-3 text-left">用户名</th>
              <th className="p-3 text-left">邮箱</th>
              <th className="p-3 text-left">角色</th>
              <th className="p-3 text-left">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? <tr><td colSpan={5} className="p-3 text-center text-[var(--text-muted)]">加载中...</td></tr> :
              data?.data?.items?.map(user => (
                <tr key={user.id} className="border-b border-[var(--border)]">
                  <td className="p-3 text-[var(--text-muted)]">{user.id}</td>
                  <td className="p-3 text-[var(--text-primary)]">{user.username}</td>
                  <td className="p-3 text-[var(--text-secondary)]">{user.email}</td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${user.is_staff ? 'bg-[var(--accent)]/20 text-[var(--accent)]' : 'bg-gray-500/20 text-gray-400'}`}>{user.is_staff ? '管理员' : '读者'}</span>
                  </td>
                  <td className="p-3">
                    <button className="text-[var(--accent)] text-sm" onClick={() => roleMutation.mutate({ userId: user.id, role: user.is_staff ? 'reader' : 'admin' })}>
                      {user.is_staff ? '降级' : '升级'}
                    </button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

```tsx
// admin/app/tags/page.tsx
'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '@/shared/lib/api';
import type { ApiResponse } from '@/shared/types';

export default function TagsPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [color, setColor] = useState('#f59e0b');

  const { data, isLoading } = useQuery({
    queryKey: ['admin-tags'],
    queryFn: () => api.get<ApiResponse<{ items: { id: number; name: string; color: string; book_count: number }[] }>>('/admin/tags'),
  });

  const createMutation = useMutation({
    mutationFn: () => api.post(`/admin/tags?name=${name}&color=${encodeURIComponent(color)}`),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-tags'] }); setName(''); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/admin/tags/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-tags'] }),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">标签管理</h1>
      <div className="glass-card p-4 flex gap-2">
        <input className="glass-input flex-1" placeholder="标签名" value={name} onChange={e => setName(e.target.value)} />
        <input className="glass-input w-20" type="color" value={color} onChange={e => setColor(e.target.value)} />
        <button className="glass-btn bg-[var(--accent)] text-white" onClick={() => createMutation.mutate()} disabled={!name}>创建</button>
      </div>
      <div className="glass-card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-[var(--border)]">
            <tr className="text-[var(--text-muted)]">
              <th className="p-3 text-left">ID</th>
              <th className="p-3 text-left">名称</th>
              <th className="p-3 text-left">颜色</th>
              <th className="p-3 text-left">关联书籍</th>
              <th className="p-3 text-left">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? <tr><td colSpan={5} className="p-3 text-center text-[var(--text-muted)]">加载中...</td></tr> :
              data?.data?.items?.map(tag => (
                <tr key={tag.id} className="border-b border-[var(--border)]">
                  <td className="p-3 text-[var(--text-muted)]">{tag.id}</td>
                  <td className="p-3"><span className="px-2 py-0.5 rounded text-xs" style={{ backgroundColor: tag.color + '20', color: tag.color }}>{tag.name}</span></td>
                  <td className="p-3"><span className="w-4 h-4 rounded inline-block" style={{ backgroundColor: tag.color }} /></td>
                  <td className="p-3 text-[var(--text-muted)]">{tag.book_count}</td>
                  <td className="p-3"><button className="text-[var(--color-danger)] text-sm" onClick={() => deleteMutation.mutate(tag.id)}>删除</button></td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

```tsx
// admin/app/monitor/page.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { ApiResponse, PerfMetrics, HealthStatus } from '@/shared/types';

export default function MonitorPage() {
  const { data: metrics } = useQuery({
    queryKey: ['admin-perf'],
    queryFn: () => api.get<ApiResponse<PerfMetrics>>('/admin/monitor/perf'),
    refetchInterval: 10000,
  });

  const { data: health } = useQuery({
    queryKey: ['admin-health'],
    queryFn: () => api.get<ApiResponse<HealthStatus>>('/admin/monitor/health'),
    refetchInterval: 30000,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">系统监控</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-card p-4"><p className="text-sm text-[var(--text-muted)]">总数</p><p className="text-2xl font-bold text-[var(--text-primary)]">{metrics?.data?.total_books ?? '-'}</p></div>
        <div className="glass-card p-4"><p className="text-sm text-[var(--text-muted)]">章节</p><p className="text-2xl font-bold text-[var(--text-primary)]">{metrics?.data?.total_chapters ?? '-'}</p></div>
        <div className="glass-card p-4"><p className="text-sm text-[var(--text-muted)]">用户</p><p className="text-2xl font-bold text-[var(--text-primary)]">{metrics?.data?.total_users ?? '-'}</p></div>
        <div className="glass-card p-4"><p className="text-sm text-[var(--text-muted)]">活跃任务</p><p className="text-2xl font-bold text-[var(--text-primary)]">{metrics?.data?.active_tasks ?? '-'}</p></div>
      </div>
      {health?.data && (
        <div className="glass-card p-4 space-y-2">
          <h2 className="font-semibold text-[var(--text-secondary)]">健康状态</h2>
          <p className="text-sm">数据库: <span className={health.data.database === 'ok' ? 'text-green-400' : 'text-red-400'}>{health.data.database}</span></p>
          <p className="text-sm">缓存: <span className={health.data.cache === 'ok' ? 'text-green-400' : 'text-red-400'}>{health.data.cache}</span></p>
          <p className="text-sm">系统: <span className={health.data.status === 'ok' ? 'text-green-400' : 'text-yellow-400'}>{health.data.status}</span></p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: 提交**

```bash
cd /workspace && git add frontend/admin/app/books/ frontend/admin/app/crawler/ frontend/admin/app/users/ frontend/admin/app/tags/ frontend/admin/app/monitor/ && git commit -m "feat: add admin CRUD pages (books, crawler, users, tags, monitor)"
```

---

## 阶段 7: 集成与清理

### Task 7.1: 更新 Django 配置

**Files:**
- Modify: `/workspace/novel_reader/settings.py`

- [ ] **Step 1: 更新 settings.py 中的前端路径和 JWT 配置**

在 settings.py 中确认/添加：
```python
# JWT 配置
JWT_SECRET = env('JWT_SECRET', default=SECRET_KEY)
JWT_ACCESS_LIFETIME_MINUTES = env.int('JWT_ACCESS_LIFETIME_MINUTES', default=15)
JWT_REFRESH_LIFETIME_DAYS = env.int('JWT_REFRESH_LIFETIME_DAYS', default=7)

# 静态文件 — Next.js 构建输出
STATICFILES_DIRS = [
    BASE_DIR / 'frontend' / 'reader' / 'out',
    BASE_DIR / 'frontend' / 'admin' / 'out',
]
```

- [ ] **Step 2: 提交**

```bash
cd /workspace && git add novel_reader/settings.py && git commit -m "chore: update Django settings for API v2 + Next.js"
```

### Task 7.2: 清理旧代码

- [ ] **Step 1: 删除旧前端和旧 API**

```bash
cd /workspace && rm -rf frontend-v1 && rm -rf apps/api/ && rm -rf templates/admin/ && rm -rf static/css/
```

- [ ] **Step 2: 提交**

```bash
cd /workspace && git add -A && git commit -m "chore: remove old frontend + old API v1 + unused templates"
```

---

## 验证步骤

1. **后端验证**：启动 Django，访问 `/api/v2/docs/` 查看 Swagger 文档，确认所有接口可访问
2. **前端验证**：`cd frontend && npm run dev`，分别访问 reader 和 admin 应用
3. **认证测试**：登录 → 获取 token → 访问 protected 接口
4. **RBAC 测试**：reader 用户访问 admin 接口应返回 403
5. **响应式测试**：Chrome DevTools 切换 992px 断点，验证三栏/底部导航切换