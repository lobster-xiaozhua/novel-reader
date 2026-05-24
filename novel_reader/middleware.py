import logging

from django.http import StreamingHttpResponse


class DisableCSRFForAPI:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return self.get_response(request)


class AsyncStreamingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if isinstance(response, StreamingHttpResponse):
            content = response.streaming_content
            if not hasattr(content, '__aiter__'):
                response.streaming_content = self._make_async(content)
        return response

    @staticmethod
    def _make_async(sync_iter):
        async def _gen():
            for chunk in sync_iter:
                if isinstance(chunk, str):
                    chunk = chunk.encode()
                yield chunk
        return _gen()


class SuppressBadAuthLog(logging.Filter):
    _PATTERNS = ('"AUTH"', 'Bad request syntax')

    def filter(self, record):
        msg = record.getMessage()
        return not any(p in msg for p in self._PATTERNS)
