import logging
from typing import Optional

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from ninja import Router
from ninja.errors import HttpError

from .auth import (
    clear_jwt_cookies,
    create_access_token,
    create_refresh_token,
    get_user_from_token,
    jwt_auth,
    optional_jwt_auth,
    set_jwt_cookies,
)
from .schemas import AuthResponse, LoginIn, MessageSchema, RefreshIn, RegisterIn
from utils.throttle import rate_limit_decorator

logger = logging.getLogger('novel_reader.auth')
router = Router()


def _build_auth_payload(user: User) -> dict:
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    return {
        'success': True,
        'user': {'id': user.id, 'username': user.username, 'email': user.email or '', 'is_staff': user.is_staff},
        'access_token': access,
        'refresh_token': refresh,
    }


@router.post('/auth/login/', response=AuthResponse, auth=None)
@rate_limit_decorator(max_requests=10, window_seconds=60)
def auth_login(request, payload: LoginIn) -> JsonResponse:
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '?'))
    ua = request.META.get('HTTP_USER_AGENT', '')[:120]
    user = authenticate(request, username=payload.username, password=payload.password)
    if user is None:
        logger.warning(f'登录失败: username={payload.username} | IP={ip} | UA={ua}')
        return JsonResponse({'success': False, 'error': '用户名或密码错误'})
    logger.info(f'登录成功: user_id={user.id} username={user.username} | IP={ip} | UA={ua}')
    data = _build_auth_payload(user)
    return set_jwt_cookies(JsonResponse(data), data['access_token'], data['refresh_token'])


@router.post('/auth/register/', response=AuthResponse, auth=None)
@rate_limit_decorator(max_requests=5, window_seconds=600)
def auth_register(request, payload: RegisterIn) -> JsonResponse:
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '?'))
    if User.objects.filter(username=payload.username).exists():
        logger.warning(f'注册失败-用户名冲突: username={payload.username} | IP={ip}')
        return JsonResponse({'success': False, 'error': '用户名已存在'})
    try:
        validate_password(payload.password)
    except ValidationError as e:
        logger.warning(f'注册失败-密码弱: username={payload.username} | IP={ip} | errors={e.messages}')
        return JsonResponse({'success': False, 'error': '; '.join(e.messages)})
    user = User.objects.create_user(username=payload.username, password=payload.password, email=payload.email)
    logger.info(f'注册成功: user_id={user.id} username={user.username} email={payload.email} | IP={ip}')
    data = _build_auth_payload(user)
    return set_jwt_cookies(JsonResponse(data), data['access_token'], data['refresh_token'])


@router.post('/auth/logout/', response=MessageSchema, auth=optional_jwt_auth)
def auth_logout(request) -> JsonResponse:
    username = request.user.username if request.user.is_authenticated else 'anonymous'
    user_id = request.user.id if request.user.is_authenticated else None
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '?'))
    logger.info(f'登出: user_id={user_id} username={username} | IP={ip}')
    return clear_jwt_cookies(JsonResponse({'message': '已退出登录'}))


@router.get('/auth/me/', response=AuthResponse, auth=optional_jwt_auth)
def auth_me(request) -> dict:
    if request.user.is_authenticated:
        return {
            'success': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email or '',
                'is_staff': request.user.is_staff,
            },
        }
    return {'success': False, 'error': '未登录'}


@router.post('/auth/refresh/', response=AuthResponse, auth=None)
def auth_refresh(request, payload: Optional[RefreshIn] = None) -> JsonResponse:
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '?'))
    token: str = ''
    if payload and payload.refresh_token:
        token = payload.refresh_token
    if not token:
        token = request.COOKIES.get('refresh_token', '')
    if not token:
        logger.warning(f'令牌刷新失败-无token: IP={ip}')
        raise HttpError(401, '未提供刷新令牌')
    user = get_user_from_token(token, token_type='refresh')
    if user is None:
        logger.warning(f'令牌刷新失败-无效token: IP={ip}')
        raise HttpError(401, '刷新令牌无效或已过期')
    logger.info(f'令牌刷新成功: user_id={user.id} username={user.username} | IP={ip}')
    data = _build_auth_payload(user)
    return set_jwt_cookies(JsonResponse(data), data['access_token'], data['refresh_token'])
