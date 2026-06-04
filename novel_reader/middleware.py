import logging
import time
import json
from collections import defaultdict
from threading import Lock

from django.core.cache import cache

logger = logging.getLogger('novel_reader.request')
auth_logger = logging.getLogger('novel_reader.auth')

_JWT_USER_CACHE_TTL = 300

_perf_lock = Lock()
_api_perf_data = {
    'total_requests': 0,
    'total_errors': 0,
    'path_stats': defaultdict(lambda: {'count': 0, 'total_ms': 0, 'errors': 0}),
    'window_start': time.time(),
    'window_requests': 0,
}


class APIMonitorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        elapsed_ms = (time.monotonic() - start) * 1000

        self._record(request.path, request.method, response.status_code, elapsed_ms)
        return response

    def _record(self, path, method, status, elapsed_ms):
        with _perf_lock:
            _api_perf_data['total_requests'] += 1
            _api_perf_data['window_requests'] += 1
            if status >= 500:
                _api_perf_data['total_errors'] += 1

            key = f'{method} {path}'
            stats = _api_perf_data['path_stats'][key]
            stats['count'] += 1
            stats['total_ms'] += elapsed_ms
            if status >= 500:
                stats['errors'] += 1

    @staticmethod
    def get_summary():
        now = time.time()
        with _perf_lock:
            window_duration = now - _api_perf_data['window_start']
            window_reqs = _api_perf_data['window_requests']
            qps = round(window_reqs / window_duration, 1) if window_duration > 0 else 0

            path_summary = {}
            for path, stats in sorted(
                _api_perf_data['path_stats'].items(),
                key=lambda x: x[1]['total_ms'],
                reverse=True
            )[:20]:
                count = stats['count']
                path_summary[path] = {
                    'count': count,
                    'avg_ms': round(stats['total_ms'] / count, 1) if count else 0,
                    'errors': stats['errors'],
                }

            if window_duration > 60:
                _api_perf_data['window_start'] = now
                _api_perf_data['window_requests'] = 0

            return {
                'total_requests': _api_perf_data['total_requests'],
                'total_errors': _api_perf_data['total_errors'],
                'qps': qps,
                'uptime_seconds': round(window_duration, 0),
                'top_paths': path_summary,
            }


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 只在用户未认证时尝试 JWT 认证，避免覆盖已认证用户
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            self._authenticate(request)
        return self.get_response(request)

    # 公开 API 路径前缀，无需认证，无效 token 不记录 WARNING
    _PUBLIC_PREFIXES = (
        '/api/v1/books/', '/api/v1/books/rankings/', '/api/v1/books/categories/',
        '/api/v1/search/', '/api/v1/recommendations/', '/api/v1/auth/',
        '/api/v1/health/', '/static/', '/admin/',
    )

    def _authenticate(self, request):
        from apps.api.auth import _extract_token, decode_token
        token = _extract_token(request)
        if not token:
            return

        payload = decode_token(token)
        if not payload or payload.get('type') != 'access':
            # 公开接口上的无效 token 降级为 DEBUG，避免刷屏
            path = request.path
            is_public = any(path.startswith(p) for p in self._PUBLIC_PREFIXES)
            log_fn = auth_logger.debug if is_public else auth_logger.warning
            log_fn(f'认证失败: {path} | IP: {self._get_client_ip(request)} | token_type={payload.get("type") if payload else "invalid"}')
            return

        try:
            user_id = int(payload['sub'])
        except (ValueError, TypeError, KeyError):
            auth_logger.warning(f'无效token: user_id解析失败 | IP: {self._get_client_ip(request)}')
            return

        cache_key = f'jwt_user:{user_id}'
        user = cache.get(cache_key)
        cache_hit = user is not None
        if not cache_hit:
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(pk=user_id, is_active=True)
            except User.DoesNotExist:
                auth_logger.warning(f'用户不存在: user_id={user_id}')
                return
            cache.set(cache_key, user, _JWT_USER_CACHE_TTL)

        request.user = user
        auth_logger.debug(f'认证成功: user_id={user_id} ({user.username}) | path={request.path} | cache_hit={cache_hit} | IP={self._get_client_ip(request)}')

    def _get_client_ip(self, request):
        """获取客户端真实 IP，支持 X-Forwarded-For"""
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            # X-Forwarded-For 可能包含多个 IP，取第一个
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '?')


class RequestTimingMiddleware:
    SLOW_THRESHOLD = 1.0

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        ip = self._get_client_ip(request)
        method = request.method
        path = request.path
        qs = request.META.get('QUERY_STRING', '')
        user = getattr(request, 'user', None)
        user_str = f'{user.username}(id={user.id})' if user and user.is_authenticated else 'anonymous'

        response = self.get_response(request)

        elapsed = time.monotonic() - start
        status = response.status_code
        content_length = len(response.content) if hasattr(response, 'content') else 0

        # 统一请求日志
        log_level = 'error' if status >= 500 else 'warning' if status >= 400 else 'info'
        if elapsed > self.SLOW_THRESHOLD:
            log_level = 'warning' if status < 400 else 'error'

        msg_parts = [
            f'{method} {path}',
        ]
        if qs:
            msg_parts.append(f'?{qs}')
        msg_parts.extend([
            f' | status={status}',
            f' | {elapsed:.3f}s',
            f' | size={content_length}B',
            f' | user={user_str}',
            f' | ip={ip}',
        ])
        if elapsed > self.SLOW_THRESHOLD:
            msg_parts.append(f' | ⚠️ 慢请求 {elapsed:.1f}s')

        logger.log(
            getattr(logging, log_level.upper(), logging.INFO),
            ''.join(msg_parts),
        )

        return response

    def _get_client_ip(self, request):
        """获取客户端真实 IP，支持 X-Forwarded-For"""
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '?')


class SuppressBadAuthLog(logging.Filter):
    _PATTERNS = ('"AUTH"', 'Bad request syntax')

    def filter(self, record):
        msg = record.getMessage()
        return not any(p in msg for p in self._PATTERNS)
