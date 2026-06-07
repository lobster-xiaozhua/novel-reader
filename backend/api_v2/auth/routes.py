"""认证路由"""
import logging
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from ninja import Router

from apps.api.auth import _is_secure
from utils.throttle import rate_limit_decorator
from ..schemas import ApiResponse, LoginIn, RegisterIn, TokenOut, UserOut
from .auth import (
    create_access_token, create_refresh_token, jwt_auth,
    _get_user_role, decode_token, get_user_from_token,
)

logger = logging.getLogger(__name__)
router = Router(tags=['auth'])


def _set_auth_cookies(response, access_token, refresh_token):
    """设置认证 Cookie，refresh_token 为 HttpOnly，仅在非 DEBUG/HTTPS 时设置 Secure"""
    secure = _is_secure()
    # access token 仍然可以在 JS 获取，refresh token 使用 HttpOnly
    response.set_cookie(
        'access_token', access_token,
        httponly=False, samesite='Lax',
        secure=secure,
        max_age=30 * 60,  # 30 minutes
        path='/',
    )
    response.set_cookie(
        'refresh_token', refresh_token,
        httponly=True, samesite='Lax',
        secure=secure,
        max_age=7 * 24 * 60 * 60,  # 7 days
        path='/',
    )

@router.post('/login', response={200: ApiResponse, 401: ApiResponse})
@rate_limit_decorator(max_requests=10, window_seconds=60)
def login(request, payload: LoginIn):
    user = authenticate(username=payload.username, password=payload.password)
    if not user:
        return 401, ApiResponse.fail('用户名或密码错误')
    role = _get_user_role(user)
    access_token = create_access_token(user.id, role)
    refresh_token = create_refresh_token(user.id)
    resp = JsonResponse(ApiResponse.ok(data={
        'user': UserOut(id=user.id, username=user.username, email=user.email, role=role, is_staff=user.is_staff),
        'tokens': TokenOut(access_token=access_token, refresh_token=refresh_token),
    }).dict())
    _set_auth_cookies(resp, access_token, refresh_token)
    return resp


@router.post('/register', response={200: ApiResponse, 409: ApiResponse})
@rate_limit_decorator(max_requests=5, window_seconds=600)
def register(request, payload: RegisterIn):
    if User.objects.filter(username=payload.username).exists():
        return 409, ApiResponse.fail('用户名已存在')
    try:
        validate_password(payload.password)
    except ValidationError as e:
        return 409, ApiResponse.fail('; '.join(e.messages))
    user = User.objects.create_user(username=payload.username, password=payload.password, email=payload.email)
    role = _get_user_role(user)
    access_token = create_access_token(user.id, role)
    refresh_token = create_refresh_token(user.id)
    resp = JsonResponse(ApiResponse.ok(data={
        'user': UserOut(id=user.id, username=user.username, email=user.email, role=role, is_staff=user.is_staff),
        'tokens': TokenOut(access_token=access_token, refresh_token=refresh_token),
    }).dict())
    _set_auth_cookies(resp, access_token, refresh_token)
    return resp


@router.post('/refresh', response={200: ApiResponse, 401: ApiResponse})
def refresh_token(request):
    refresh = request.COOKIES.get('refresh_token') or request.headers.get('X-Refresh-Token', '')
    if not refresh:
        return 401, ApiResponse.fail('缺少刷新令牌')
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