"""API v2 JWT Auth - re-exports from v1 for compatibility"""
import logging
from django.contrib.auth.models import User
from ninja.security import HttpBearer
from ninja.errors import HttpError
from apps.api.auth import jwt_auth, optional_jwt_auth, JWTAuth, OptionalJWTAuth

logger = logging.getLogger(__name__)


class AdminJWTAuth(JWTAuth):
    def __call__(self, request):
        user = super().__call__(request)
        if not user:
            raise HttpError(401, '未登录')
        if not user.is_staff and not user.is_superuser:
            logger.warning(f'[AdminV2] 非管理员尝试访问: {user.username}')
            raise HttpError(403, '需要管理员权限')
        return user


admin_auth = AdminJWTAuth()


def _get_user_role(user: User):
    if user.is_superuser:
        return 'admin'
    if user.is_staff:
        return 'staff'
    return 'reader'


JWT_ACCESS_LIFETIME = 3600 * 24  # 24h
JWT_REFRESH_LIFETIME = 3600 * 24 * 7  # 7d


def create_access_token(user_id: int, role: str):
    from apps.api.auth import create_access_token as _create
    return _create(user_id)


def create_refresh_token(user_id: int):
    from apps.api.auth import create_refresh_token as _create
    return _create(user_id)


def decode_token(token: str, token_type: str = 'access'):
    from apps.api.auth import decode_token as _decode
    return _decode(token)


def get_user_from_token(token: str, token_type: str = 'access'):
    from apps.api.auth import get_user_from_token as _get
    return _get(token)