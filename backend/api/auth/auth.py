"""API v2 JWT Auth - re-exports from v1 for compatibility + additional admin auth"""
from backend.api.auth.jwt_utils import (
    jwt_auth,
    optional_jwt_auth,
    JWTAuth,
    OptionalJWTAuth,
    create_access_token as v1_create_access_token,
    create_refresh_token as v1_create_refresh_token,
    decode_token,
    get_user_from_token,
    _extract_token,
)
from django.contrib.auth.models import User
from ninja.security import HttpBearer

JWT_ACCESS_LIFETIME_MINUTES = 60
JWT_REFRESH_LIFETIME_DAYS = 7


def _get_user_role(user):
    """获取用户角色：admin 或 reader"""
    if user.is_staff or user.is_superuser:
        return "admin"
    return "reader"


def create_access_token(user_id: int, role: str = "reader"):
    """创建访问令牌（兼容角色参数）"""
    return v1_create_access_token(user_id)


def create_refresh_token(user_id: int):
    """创建刷新令牌"""
    return v1_create_refresh_token(user_id)


class AdminAuth(HttpBearer):
    """管理员认证"""

    def authenticate(self, request, token):
        # 首先尝试从提供的 token 中获取用户
        user = get_user_from_token(token, token_type='access')
        if user and (user.is_staff or user.is_superuser):
            return user
        # 如果 header 方式不行，尝试使用 cookie 方式
        cookie_token = request.COOKIES.get('access_token')
        if cookie_token and cookie_token != token:
            user = get_user_from_token(cookie_token, token_type='access')
            if user and (user.is_staff or user.is_superuser):
                return user
        return None


admin_auth = AdminAuth()

__all__ = [
    "jwt_auth",
    "optional_jwt_auth",
    "JWTAuth",
    "OptionalJWTAuth",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_user_from_token",
    "_get_user_role",
    "admin_auth",
    "AdminAuth",
    "JWT_ACCESS_LIFETIME_MINUTES",
    "JWT_REFRESH_LIFETIME_DAYS",
]
