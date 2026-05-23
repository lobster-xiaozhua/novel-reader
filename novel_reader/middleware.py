import logging


class DisableCSRFForAPI:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return self.get_response(request)


class SuppressBadAuthLog(logging.Filter):
    _PATTERNS = ('"AUTH"', 'Bad request syntax')

    def filter(self, record):
        msg = record.getMessage()
        return not any(p in msg for p in self._PATTERNS)
