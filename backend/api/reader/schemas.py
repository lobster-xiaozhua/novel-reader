"""API v2 Reader Schemas"""
from typing import List, Optional
from ninja import Schema


class TagItem(Schema):
    id: int
    name: str
    color: str = '#f59e0b'


class BookListItem(Schema):
    id: int
    title: str
    author: str = ''
    category: str = ''
    description: str = ''
    gradient: tuple = ('#667eea', '#764ba2')
    tags: List[TagItem] = []
    chapter_count: int = 0
    total_chapters: int = 0
    created_at: str = ''
    updated_at: str = ''


class RankingBook(Schema):
    id: int
    title: str
    author: str = ''
    category: str = ''
    gradient: tuple = ('#667eea', '#764ba2')
    tags: List[TagItem] = []
    chapter_count: int = 0
    fav_count: int = 0


class CategoryItem(Schema):
    category: str
    count: int


class DiscoverFeed(Schema):
    recommendations: List[BookListItem] = []
    hot_today: List[RankingBook] = []
    hot_week: List[RankingBook] = []
    new_arrivals: List[RankingBook] = []
    categories: List[CategoryItem] = []


class ShelfBook(Schema):
    id: int
    book_id: int
    title: str
    author: str = ''
    category: str = ''
    gradient: tuple = ('#667eea', '#764ba2')
    chapter_count: int = 0
    progress: Optional[dict] = None
    created_at: str = ''


class ShelfData(Schema):
    favorites: List[ShelfBook] = []
    recent_reads: List[ShelfBook] = []


class BookDetail(Schema):
    id: int
    title: str
    author: str = ''
    category: str = ''
    description: str = ''
    total_chapters: int = 0
    tags: List[TagItem] = []
    gradient: tuple = ('#667eea', '#764ba2')
    is_favorited: bool = False
    reading_progress: Optional[dict] = None
    similar_books: List[BookListItem] = []
    created_at: str = ''
    updated_at: str = ''


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
    prev_chapter_id: Optional[int] = None
    next_chapter_id: Optional[int] = None
    book_id: int = 0
    book_title: str = ''


class ProgressIn(Schema):
    book_id: int
    chapter_id: Optional[int] = None
    position: int = 0


class ProgressOut(Schema):
    id: int
    book_id: int
    book_title: str = ''
    chapter_id: Optional[int] = None
    chapter_title: Optional[str] = None
    position: int = 0
    total_chapters: int = 0
    updated_at: str = ''


class StatsTrackIn(Schema):
    seconds: int = 0
    chapter_id: Optional[int] = None


class DailyChart(Schema):
    date: str
    minutes: float = 0.0
    chapters: int = 0
    words: int = 0


class UserStats(Schema):
    total_books: int = 0
    reading_count: int = 0
    favorite_count: int = 0
    today_chapters: int = 0
    today_minutes: float = 0.0
    week_chapters: int = 0
    total_words: int = 0
    chart: List[DailyChart] = []


class SearchBookItem(Schema):
    id: int
    title: str
    author: str = ''
    category: str = ''
    description: str = ''
    gradient: tuple = ('#667eea', '#764ba2')
    chapter_count: int = 0


class SearchResult(Schema):
    items: List[SearchBookItem]
    total: int
    page: int
    total_pages: int


class MessageOut(Schema):
    message: str