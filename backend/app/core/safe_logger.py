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
            # Function to replace each match: capture group 1 is the key, then redact the value
            def replace_match(match):
                # Check if the pattern has a capture group (the key)
                if match.groups():
                    key = match.group(1)
                    # Check if there's an = or : separator
                    if '=' in match.group(0):
                        return f"{key}=***"
                    elif ':' in match.group(0):
                        return f"{key}:***"
                    else:
                        # For things like "Bearer token123"
                        return f"{key} ***"
                return match.group(0)
            result = pattern.sub(replace_match, result)
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
