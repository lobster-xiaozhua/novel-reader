"""Redis-based API rate limiter using django.core.cache"""
import time
import logging
from functools import wraps

from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger('novel_reader.request')

RATE_LIMIT_MESSAGE = '请求过于频繁，请稍后再试'


def rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    """滑动窗口限流：返回 True 表示被限流，False 表示通过"""
    now = time.time()
    window_start = now - window_seconds
    cache_key = f'rl:{key}'

    timestamps = cache.get(cache_key)
    if timestamps is None:
        timestamps = [now]
        cache.set(cache_key, timestamps, window_seconds)
        return False

    # 清理过期时间戳
    timestamps = [t for t in timestamps if t > window_start]
    timestamps.append(now)
    cache.set(cache_key, timestamps, window_seconds)

    if len(timestamps) > max_requests:
        logger.warning(f'[RateLimit] {key}: {len(timestamps)}/{max_requests} in {window_seconds}s → BLOCKED')
        return True
    return False


def rate_limit_decorator(max_requests: int, window_seconds: int):
    """装饰器：对 Django Ninja 路由函数添加限流"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '?'))
            if isinstance(ip, str):
                ip = ip.split(',')[0].strip()
            key = f'{func.__name__}:{ip}'
            if rate_limit(key, max_requests, window_seconds):
                return JsonResponse({'error': RATE_LIMIT_MESSAGE}, status=429)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator