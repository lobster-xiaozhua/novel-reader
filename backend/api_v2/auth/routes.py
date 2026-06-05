"""认证路由"""
import logging
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from ninja import Router

from ..schemas import ApiResponse, LoginIn, RegisterIn, TokenOut, UserOut
from .auth import (
    create_access_token, create_refresh_token, jwt_auth,
    _get_user_role, JWT_ACCESS_LIFETIME, JWT_REFRESH_LIFETIME,
)

logger = logging.getLogger(__name__)
router = Router(tags=['auth'])


@router.post('/login', response={200: ApiResponse, 401: ApiResponse})
def login(request, payload: LoginIn):
    user = authenticate(username=payload.username, password=payload.password)
    if not user:
        return 401, ApiResponse.fail('用户名或密码错误')
    role = _get_user_role(user)
    access_token = create_access_token(user.id, role)
    refresh_token = create_refresh_token(user.id)
    return ApiResponse.ok(data={
        'user': UserOut(id=user.id, username=user.username, email=user.email, role=role, is_staff=user.is_staff),
        'tokens': TokenOut(access_token=access_token, refresh_token=refresh_token),
    })


@router.post('/register', response={200: ApiResponse, 409: ApiResponse})
def register(request, payload: RegisterIn):
    if User.objects.filter(username=payload.username).exists():
        return 409, ApiResponse.fail('用户名已存在')
    user = User.objects.create_user(username=payload.username, password=payload.password, email=payload.email)
    role = _get_user_role(user)
    access_token = create_access_token(user.id, role)
    refresh_token = create_refresh_token(user.id)
    return ApiResponse.ok(data={
        'user': UserOut(id=user.id, username=user.username, email=user.email, role=role, is_staff=user.is_staff),
        'tokens': TokenOut(access_token=access_token, refresh_token=refresh_token),
    })


@router.post('/refresh', response={200: ApiResponse, 401: ApiResponse})
def refresh_token(request):
    refresh = request.COOKIES.get('refresh_token') or request.headers.get('X-Refresh-Token', '')
    if not refresh:
        return 401, ApiResponse.fail('缺少刷新令牌')
    from .auth import decode_token, get_user_from_token
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