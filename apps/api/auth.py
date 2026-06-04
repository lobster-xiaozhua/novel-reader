import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from django.conf import settings
from django.contrib.auth.models import User
from django.http import JsonResponse

logger = logging.getLogger(__name__)

JWT_ALGORITHM: str = 'HS256'
JWT_ACCESS_LIFETIME: timedelta = timedelta(hours=2)
JWT_REFRESH_LIFETIME: timedelta = timedelta(days=30)
JWT_COOKIE_SAMESITE: str = 'Lax'


def _get_secret() -> str:
    return getattr(settings, 'JWT_SECRET', settings.SECRET_KEY)


def _is_secure() -> bool:
    # 仅在 HTTPS 环境下启用 Secure 标志
    # http://localhost 不应设置 Secure，否则浏览器不会发送 cookie
    return getattr(settings, 'SECURE_SSL_REDIRECT', False)


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_id),
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
    except (ValueError, TypeError):
        logger.warning(f'[JWT] Invalid subject: {payload.get("sub")}')
        return None
    except User.DoesNotExist:
        logger.warning(f'[JWT] User not found: id={payload.get("sub")}')
        return None


def _extract_token(request) -> Optional[str]:
    auth_header: str = request.META.get('HTTP_AUTHORIZATION', '')
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


class OptionalJWTAuth(JWTAuth):
    def __call__(self, request):
        result = super().__call__(request)
        return result if result else True


jwt_auth = JWTAuth()
optional_jwt_auth = OptionalJWTAuth()


def set_jwt_cookies(response: JsonResponse, access_token: str, refresh_token: str) -> JsonResponse:
    secure = _is_secure()
    response.set_cookie(
        'access_token', access_token,
        httponly=True, samesite=JWT_COOKIE_SAMESITE,
        secure=secure,
        max_age=int(JWT_ACCESS_LIFETIME.total_seconds()),
        path='/',
    )
    response.set_cookie(
        'refresh_token', refresh_token,
        httponly=True, samesite=JWT_COOKIE_SAMESITE,
        secure=secure,
        max_age=int(JWT_REFRESH_LIFETIME.total_seconds()),
        path='/',
    )
    return response


def clear_jwt_cookies(response: JsonResponse) -> JsonResponse:
    response.delete_cookie('access_token', path='/')
    response.delete_cookie('refresh_token', path='/')
    return response
