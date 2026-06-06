import logging
import time

from django.core.cache import cache

logger = logging.getLogger('novel_reader.request')
auth_logger = logging.getLogger('novel_reader.auth')

_JWT_USER_CACHE_TTL = 300


class APIMonitorMiddleware:
    _PERF_KEY = 'api_perf_data'
    _PERF_TTL = 300
    _PERF_WINDOW = 60

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        elapsed_ms = (time.monotonic() - start) * 1000

        self._record(request.path, request.method, response.status_code, elapsed_ms)
        return response

    def _record(self, path, method, status, elapsed_ms):
        try:
            perf = cache.get(self._PERF_KEY, {
                'total_requests': 0, 'total_errors': 0,
                'path_stats': {}, 'window_start': time.time(), 'window_requests': 0,
            })
            perf['total_requests'] = perf.get('total_requests', 0) + 1
            perf['window_requests'] = perf.get('window_requests', 0) + 1
            if status >= 500:
                perf['total_errors'] = perf.get('total_errors', 0) + 1

            key = f'{method} {path}'
            path_stats = perf.get('path_stats', {})
            stats = path_stats.get(key, {'count': 0, 'total_ms': 0, 'errors': 0})
            stats['count'] = stats.get('count', 0) + 1
            stats['total_ms'] = stats.get('total_ms', 0) + elapsed_ms
            if status >= 500:
                stats['errors'] = stats.get('errors', 0) + 1
            path_stats[key] = stats
            perf['path_stats'] = path_stats

            cache.set(self._PERF_KEY, perf, self._PERF_TTL)
        except Exception:
            pass

    @staticmethod
    def get_summary():
        try:
            perf = cache.get(APIMonitorMiddleware._PERF_KEY, {})
        except Exception:
            perf = {}

        now = time.time()
        window_duration = now - perf.get('window_start', now)
        window_reqs = perf.get('window_requests', 0)
        qps = round(window_reqs / window_duration, 1) if window_duration > 0 else 0

        path_summary = {}
        for path, stats in sorted(
            perf.get('path_stats', {}).items(),
            key=lambda x: x[1].get('total_ms', 0),
            reverse=True
        )[:20]:
            count = stats.get('count', 0)
            path_summary[path] = {
                'count': count,
                'avg_ms': round(stats.get('total_ms', 0) / count, 1) if count else 0,
                'errors': stats.get('errors', 0),
            }

        if window_duration > APIMonitorMiddleware._PERF_WINDOW:
            perf['window_start'] = now
            perf['window_requests'] = 0
            try:
                cache.set(APIMonitorMiddleware._PERF_KEY, perf, APIMonitorMiddleware._PERF_TTL)
            except Exception:
                pass

        return {
            'total_requests': perf.get('total_requests', 0),
            'total_errors': perf.get('total_errors', 0),
            'qps': qps,
            'uptime_seconds': round(window_duration, 0),
            'top_paths': path_summary,
        }


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            self._authenticate(request)
        return self.get_response(request)

    _PUBLIC_PREFIXES = (
        '/api/v2/books/', '/api/v2/books/rankings/', '/api/v2/books/categories/',
        '/api/v2/search/', '/api/v2/recommendations/', '/api/v2/auth/',
        '/api/v2/health/', '/static/', '/admin/',
    )

    def _authenticate(self, request):
        from backend.api.auth.auth import _extract_token, decode_token
        token = _extract_token(request)
        if not token:
            return

        payload = decode_token(token)
        if not payload or payload.get('type') != 'access':
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
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
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

        # CSP 安全头
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        log_level = 'error' if status >= 500 else 'warning' if status >= 400 else 'info'
        if elapsed > self.SLOW_THRESHOLD:
            log_level = 'warning' if status < 400 else 'error'

        msg_parts = [f'{method} {path}']
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
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '?')


class SuppressBadAuthLog(logging.Filter):
    _PATTERNS = ('"AUTH"', 'Bad request syntax')

    def filter(self, record):
        msg = record.getMessage()
        return not any(p in msg for p in self._PATTERNS)


class LoginRateLimitMiddleware:
    """登录/注册接口速率限制：每IP每分钟5次"""
    PROTECTED_PATHS = [
        '/api/v2/auth/login',
        '/api/v2/auth/register',
    ]
    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 60

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST' and any(request.path.startswith(p) for p in self.PROTECTED_PATHS):
            ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '?')).split(',')[0].strip()
            cache_key = f'login_rate:{ip}'
            attempts = cache.get(cache_key, 0)
            if isinstance(attempts, str):
                attempts = int(attempts)
            if attempts >= self.MAX_ATTEMPTS:
                from django.http import JsonResponse
                return JsonResponse({'error': '操作过于频繁，请稍后重试'}, status=429)
            cache.set(cache_key, attempts + 1, self.WINDOW_SECONDS)
        return self.get_response(request)
