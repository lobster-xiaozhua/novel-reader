from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="密码")


class UserResponse(UserBase):
    id: int
    is_admin: bool
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class BookBase(BaseModel):
    title: str = Field(..., max_length=200, description="书名")
    author: Optional[str] = Field(None, max_length=100, description="作者")
    description: Optional[str] = Field(None, description="简介")


class BookCreate(BookBase):
    folder_path: str = Field(..., max_length=500, description="文件夹路径")


class BookResponse(BookBase):
    id: int
    total_chapters: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BookListResponse(BaseModel):
    items: List[BookResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ChapterResponse(BaseModel):
    id: int
    book_id: int
    chapter_number: int
    title: str
    word_count: int

    class Config:
        from_attributes = True


class ChapterContentResponse(BaseModel):
    id: int
    book_id: int
    chapter_number: int
    title: str
    word_count: int
    content: str

    class Config:
        from_attributes = True


class FavoriteCreate(BaseModel):
    book_id: int = Field(..., description="书籍ID")
    folder_id: Optional[int] = Field(None, description="收藏夹ID")


class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    folder_id: Optional[int]
    notes: Optional[str]
    is_synced: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FavoriteFolderCreate(BaseModel):
    name: str = Field(..., max_length=50, description="收藏夹名称")
    description: Optional[str] = Field(None, max_length=200, description="描述")
    color: Optional[str] = Field(None, max_length=7, description="颜色（hex格式）")


class FavoriteFolderResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    color: Optional[str]
    sort_order: int

    class Config:
        from_attributes = True


class ReadingProgressUpdate(BaseModel):
    book_id: int = Field(..., description="书籍ID")
    chapter_id: int = Field(..., description="章节ID")
    position: int = Field(0, ge=0, description="字符位置")


class ReadingProgressResponse(BaseModel):
    id: int
    book_id: int
    chapter_id: int
    position: int
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CrawlerTaskCreate(BaseModel):
    url: str = Field(..., max_length=500, description="目标URL")


class CrawlerTaskResponse(BaseModel):
    id: int
    url: str
    status: str
    total_chapters: int
    downloaded_chapters: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    id: int
    title: str
    author: Optional[str]
    relevance: float


class SearchSuggestion(BaseModel):
    text: str
    type: str
