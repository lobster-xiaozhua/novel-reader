from typing import List, Optional

from ninja import Schema
from django.utils import timezone


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
    access_token: str = ''
    refresh_token: str = ''


class RefreshIn(Schema):
    refresh_token: str = ''


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


class RankingsResponse(Schema):
    hot_today: List['RankingBookSchema'] = []
    hot_week: List['RankingBookSchema'] = []
    new_arrivals: List['RankingBookSchema'] = []


class RankingBookSchema(Schema):
    id: int
    title: str
    author: str = ''
    category: str = ''
    gradient: tuple = ('#667eea', '#764ba2')
    tags: List[TagSchema] = []
    chapter_count: int = 0


class CategoryWithCount(Schema):
    category: str
    count: int


class DashboardStatsSchema(Schema):
    total_books: int
    total_users: int
    total_chapters: int
    total_words: int
    category_stats: List[CategoryStat] = []


class ErrorResponse(Schema):
    success: bool = False
    error: str
    message: str = ''
    detail: str = ''
    code: str = ''
    suggestion: str = ''


ERROR_SUGGESTIONS = {
    400: '请检查请求参数是否正确',
    401: '请先登录后再执行此操作',
    403: '您没有执行此操作的权限，请联系管理员',
    404: '请求的资源不存在，请检查路径',
    409: '数据存在冲突，请检查后重试',
    422: '请检查数据格式是否符合要求',
    429: '请求过于频繁，请稍后重试',
    500: '服务器暂时出现问题，请稍后重试',
}
