import logging
import time

from django.core.cache import cache

logger = logging.getLogger(__name__)

_JWT_USER_CACHE_TTL = 300


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            self._authenticate(request)
        return self.get_response(request)

    def _authenticate(self, request):
        from apps.api.auth import _extract_token, decode_token
        token = _extract_token(request)
        if not token:
            return
        payload = decode_token(token)
        if not payload or payload.get('type') != 'access':
            return
        try:
            user_id = int(payload['sub'])
        except (ValueError, TypeError):
            return

        cache_key = f'jwt_user:{user_id}'
        user = cache.get(cache_key)
        if user is None:
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(pk=user_id, is_active=True)
            except User.DoesNotExist:
                return
            cache.set(cache_key, user, _JWT_USER_CACHE_TTL)
        request.user = user


class RequestTimingMiddleware:
    SLOW_THRESHOLD = 1.0

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        elapsed = time.monotonic() - start
        if elapsed > self.SLOW_THRESHOLD:
            logger.warning(
                f'[Slow] {request.method} {request.path} - {elapsed:.3f}s'
            )
        return response


class SuppressBadAuthLog(logging.Filter):
    _PATTERNS = ('"AUTH"', 'Bad request syntax')

    def filter(self, record):
        msg = record.getMessage()
        return not any(p in msg for p in self._PATTERNS)
