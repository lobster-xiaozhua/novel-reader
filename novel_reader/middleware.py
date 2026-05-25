import logging


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            self._authenticate(request)
        return self.get_response(request)

    def _authenticate(self, request):
        from apps.api.auth import _extract_token, get_user_from_token
        token = _extract_token(request)
        if token:
            user = get_user_from_token(token, token_type='access')
            if user:
                request.user = user


class SuppressBadAuthLog(logging.Filter):
    _PATTERNS = ('"AUTH"', 'Bad request syntax')

    def filter(self, record):
        msg = record.getMessage()
        return not any(p in msg for p in self._PATTERNS)
