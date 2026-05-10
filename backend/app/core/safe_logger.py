import logging
import re
from typing import Any, Optional


SENSITIVE_PATTERNS = [
    re.compile(r'(password|passwd|pwd)\s*[=:]\s*\S+', re.IGNORECASE),
    re.compile(r'(secret|token|api_key|apikey)\s*[=:]\s*\S+', re.IGNORECASE),
    re.compile(r'(authorization)\s*[=:]\s*\S+', re.IGNORECASE),
    re.compile(r'(bearer)\s+\S+', re.IGNORECASE),
    re.compile(r'(jwt)\s+[=:]\s*\S+', re.IGNORECASE),
]

REDACTED = '[REDACTED]'


class SafeLogger:
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def _sanitize(self, message: str) -> str:
        result = str(message)
        for pattern in SENSITIVE_PATTERNS:
            result = pattern.sub(lambda m: m.group(0).split('=')[0].split(':')[0] + '=***', result)
        return result

    def debug(self, message: str, *args: Any, **kwargs: Any):
        self._logger.debug(self._sanitize(message), *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any):
        self._logger.info(self._sanitize(message), *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any):
        self._logger.warning(self._sanitize(message), *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any):
        self._logger.error(self._sanitize(message), *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any):
        self._logger.critical(self._sanitize(message), *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any):
        self._logger.exception(self._sanitize(message), *args, **kwargs)


def get_safe_logger(name: str) -> SafeLogger:
    return SafeLogger(name)
