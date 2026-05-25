import logging
from typing import Optional

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
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

logger = logging.getLogger(__name__)
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
def auth_login(request, payload: LoginIn) -> JsonResponse:
    user = authenticate(request, username=payload.username, password=payload.password)
    if user is None:
        logger.warning(f'[Auth] 登录失败: {payload.username}')
        return JsonResponse({'success': False, 'error': '用户名或密码错误'})
    logger.info(f'[Auth] 用户登录: {user.username}')
    data = _build_auth_payload(user)
    return set_jwt_cookies(JsonResponse(data), data['access_token'], data['refresh_token'])


@router.post('/auth/register/', response=AuthResponse, auth=None)
def auth_register(request, payload: RegisterIn) -> JsonResponse:
    if User.objects.filter(username=payload.username).exists():
        return JsonResponse({'success': False, 'error': '用户名已存在'})
    user = User.objects.create_user(username=payload.username, password=payload.password, email=payload.email)
    logger.info(f'[Auth] 新用户注册: {user.username}')
    data = _build_auth_payload(user)
    return set_jwt_cookies(JsonResponse(data), data['access_token'], data['refresh_token'])


@router.post('/auth/logout/', response=MessageSchema, auth=optional_jwt_auth)
def auth_logout(request) -> JsonResponse:
    username = request.user.username if request.user.is_authenticated else 'anonymous'
    logger.info(f'[Auth] 用户登出: {username}')
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
    token: str = ''
    if payload and payload.refresh_token:
        token = payload.refresh_token
    if not token:
        token = request.COOKIES.get('refresh_token', '')
    if not token:
        raise HttpError(401, '未提供刷新令牌')
    user = get_user_from_token(token, token_type='refresh')
    if user is None:
        raise HttpError(401, '刷新令牌无效或已过期')
    logger.info(f'[Auth] 令牌刷新: {user.username}')
    data = _build_auth_payload(user)
    return set_jwt_cookies(JsonResponse(data), data['access_token'], data['refresh_token'])
