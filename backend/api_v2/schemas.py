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