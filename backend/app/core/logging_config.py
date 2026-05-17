import os
import sys
import re
import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Optional, Dict
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich._null_file import NullFile
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from app.core.config import get_settings

settings = get_settings()

SENSITIVE_PATTERNS = [
    re.compile(r'(password|passwd|pwd)\s*[=:]\s*\S+', re.IGNORECASE),
    re.compile(r'(secret|token|api_key|apikey)\s*[=:]\s*\S+', re.IGNORECASE),
    re.compile(r'(authorization)\s*[=:]\s*\S+', re.IGNORECASE),
    re.compile(r'(bearer)\s+\S+', re.IGNORECASE),
    re.compile(r'(jwt)\s*[=:]\s*\S+', re.IGNORECASE),
]

REDACTED = "***"


class LogLevel:
    TRACE = 5
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    LIGHT_GRAY = "\033[90m"
    LIGHT_RED = "\033[91m"
    LIGHT_GREEN = "\033[92m"
    LIGHT_YELLOW = "\033[93m"
    LIGHT_BLUE = "\033[94m"
    LIGHT_MAGENTA = "\033[95m"
    LIGHT_CYAN = "\033[96m"


LEVEL_COLORS = {
    LogLevel.TRACE: Colors.DIM,
    LogLevel.DEBUG: Colors.DIM,
    LogLevel.INFO: Colors.CYAN,
    LogLevel.SUCCESS: Colors.GREEN,
    LogLevel.WARNING: Colors.YELLOW,
    LogLevel.ERROR: Colors.RED,
    LogLevel.CRITICAL: Colors.BG_RED + Colors.WHITE,
}

LEVEL_NAMES = {
    LogLevel.TRACE: "TRACE",
    LogLevel.DEBUG: "DEBUG",
    LogLevel.INFO: "INFO",
    LogLevel.SUCCESS: "SUCCESS",
    LogLevel.WARNING: "WARN",
    LogLevel.ERROR: "ERROR",
    LogLevel.CRITICAL: "CRITICAL",
}

LEVEL_ICONS = {
    LogLevel.TRACE: ".",
    LogLevel.DEBUG: "-",
    LogLevel.INFO: "i",
    LogLevel.SUCCESS: "+",
    LogLevel.WARNING: "!",
    LogLevel.ERROR: "x",
    LogLevel.CRITICAL: "!!",
}


class ConsoleFormatter(logging.Formatter):
    def __init__(self, use_color: bool = True, show_trace: bool = False):
        super().__init__()
        self.use_color = use_color and sys.stdout.isatty()
        self.show_trace = show_trace

    def _sanitize(self, message: str) -> str:
        result = str(message)
        for pattern in SENSITIVE_PATTERNS:
            result = pattern.sub(lambda m: m.group(0).split('=')[0].split(':')[0] + '=***', result)
        return result

    def _format_time(self, record: logging.LogRecord) -> str:
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%H:%M:%S.%f")[:-3]

    def _get_level_info(self, record: logging.LogRecord) -> tuple:
        level = record.levelno
        if level not in LEVEL_NAMES:
            level = LogLevel.INFO
        return level, LEVEL_NAMES.get(level, "INFO"), LEVEL_ICONS.get(level, "i")

    def _colorize_level(self, level_name: str, level: int) -> str:
        if not self.use_color:
            return level_name
        color = LEVEL_COLORS.get(level, Colors.RESET)
        return f"{color}{level_name}{Colors.RESET}"

    def format(self, record: logging.LogRecord) -> str:
        level, level_name, icon = self._get_level_info(record)
        time_str = self._format_time(record)
        message = self._sanitize(record.getMessage())

        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            message = f"{message}\n{exc_text}"

        parts = [
            f"{Colors.DIM}{time_str}{Colors.RESET}",
            f"{self._colorize_level(level_name, level)}",
            f"{Colors.DIM}{record.name}{Colors.RESET}",
        ]

        if hasattr(record, 'request_id') and record.request_id:
            parts.append(f"{Colors.DIM}[{record.request_id}]{Colors.RESET}")

        parts.append(message)

        return " | ".join(parts)


class RichConsoleFormatter:
    def __init__(self):
        self.console = Console(file=sys.stdout, force_terminal=True) if RICH_AVAILABLE else None

    def print(self, level: int, message: str, name: str = None, request_id: str = None, exc_info: Exception = None):
        if not RICH_AVAILABLE or not self.console:
            return

        level_name = LEVEL_NAMES.get(level, "INFO")
        icon = LEVEL_ICONS.get(level, "i")

        text = Text()
        text.append(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} ", style="dim")
        text.append(f"{icon} ", style=self._get_rich_style(level))
        if name:
            text.append(f"[{name}] ", style="dim")
        if request_id:
            text.append(f"[{request_id}] ", style="dim")
        text.append(message)

        if level >= LogLevel.ERROR and exc_info:
            text.append(f"\n{''.join(traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__))}", style="red dim")

        self.console.print(text)

    def _get_rich_style(self, level: int) -> str:
        styles = {
            LogLevel.TRACE: "dim",
            LogLevel.DEBUG: "dim",
            LogLevel.INFO: "cyan",
            LogLevel.SUCCESS: "green",
            LogLevel.WARNING: "yellow",
            LogLevel.ERROR: "red bold",
            LogLevel.CRITICAL: "red bold reverse",
        }
        return styles.get(level, "white")


class ElegantLogger:
    _instances: Dict[str, 'ElegantLogger'] = {}

    def __init__(self, name: str):
        self.name = name
        self._logger = logging.getLogger(name)
        self._setup_levels()
        self._request_id: Optional[str] = None
        self._context: Dict[str, Any] = {}

    @classmethod
    def get_instance(cls, name: str) -> 'ElegantLogger':
        if name not in cls._instances:
            cls._instances[name] = cls(name)
        return cls._instances[name]

    def _setup_levels(self):
        if not hasattr(logging, 'SUCCESS'):
            logging.addLevelName(LogLevel.SUCCESS, 'SUCCESS')
        if not hasattr(logging, 'TRACE'):
            logging.addLevelName(LogLevel.TRACE, 'TRACE')

    def _sanitize(self, message: str) -> str:
        result = str(message)
        for pattern in SENSITIVE_PATTERNS:
            result = pattern.sub(lambda m: m.group(0).split('=')[0].split(':')[0] + '=***', result)
        return result

    def _log(self, level: int, message: str, *args: Any, exc_info: Exception = None, **kwargs: Any):
        message = self._sanitize(str(message).format(*args, **kwargs) if args or kwargs else message)

        if self._request_id:
            kwargs['request_id'] = self._request_id

        if exc_info:
            kwargs['exc_info'] = exc_info

        self._logger.log(level, message, **kwargs)

    def trace(self, message: str, *args: Any, **kwargs: Any):
        self._log(LogLevel.TRACE, message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any):
        self._log(logging.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any):
        self._log(logging.INFO, message, *args, **kwargs)

    def success(self, message: str, *args: Any, **kwargs: Any):
        self._log(LogLevel.SUCCESS, message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any):
        self._log(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args: Any, exc_info: Exception = None, **kwargs: Any):
        self._log(logging.ERROR, message, *args, exc_info=exc_info, **kwargs)

    def critical(self, message: str, *args: Any, exc_info: Exception = None, **kwargs: Any):
        self._log(logging.CRITICAL, message, *args, exc_info=exc_info, **kwargs)

    def exception(self, message: str, *args: Any, exc_info: Exception = None, **kwargs: Any):
        if exc_info is None and sys.exc_info()[0]:
            exc_info = sys.exc_info()[1]
        self._log(logging.ERROR, message, *args, exc_info=exc_info, **kwargs)

    def set_request_id(self, request_id: str):
        self._request_id = request_id

    def clear_request_id(self):
        self._request_id = None

    def bind(self, **kwargs: Any):
        self._context.update(kwargs)
        return self

    def child(self, name: str) -> 'ElegantLogger':
        child_logger = ElegantLogger.get_instance(f"{self.name}.{name}")
        child_logger._context = self._context.copy()
        child_logger._request_id = self._request_id
        return child_logger

    def with_context(self, **kwargs: Any) -> 'ElegantLogger':
        new_logger = ElegantLogger.get_instance(self.name)
        new_logger._context = {**self._context, **kwargs}
        new_logger._request_id = self._request_id
        return new_logger


def setup_logging():
    if not hasattr(logging, 'SUCCESS'):
        logging.addLevelName(LogLevel.SUCCESS, 'SUCCESS')
    if not hasattr(logging, 'TRACE'):
        logging.addLevelName(LogLevel.TRACE, 'TRACE')

    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    console_formatter = ConsoleFormatter(use_color=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    if settings.DEBUG:
        root_logger.debug(f"{Colors.CYAN}调试模式已启用{Colors.RESET}")
        root_logger.debug(f"{Colors.DIM}日志级别: DEBUG{Colors.RESET}")
    else:
        root_logger.info(f"{Colors.GREEN}+{Colors.RESET} {Colors.BOLD}{settings.APP_NAME}{Colors.RESET} v{settings.APP_VERSION}")


def get_logger(name: str) -> ElegantLogger:
    return ElegantLogger.get_instance(name)


class StructuredLogger:
    def __init__(self, logger: ElegantLogger):
        self._logger = logger

    def log_api_request(self, method: str, path: str, status_code: int, duration: float, request_id: str = None):
        if status_code >= 500:
            self._logger.error(
                f"API 请求失败 | {method} {path} | {status_code} | {duration:.3f}s",
                request_id=request_id
            )
        elif status_code >= 400:
            self._logger.warning(
                f"API 请求错误 | {method} {path} | {status_code} | {duration:.3f}s",
                request_id=request_id
            )
        else:
            self._logger.info(
                f"API 请求 | {method} {path} | {status_code} | {duration:.3f}s",
                request_id=request_id
            )

    def log_database_operation(self, operation: str, table: str, duration: float, success: bool = True):
        if success:
            self._logger.debug(f"DB {operation} | {table} | {duration:.3f}s")
        else:
            self._logger.error(f"DB {operation} 失败 | {table} | {duration:.3f}s")

    def log_crawler_event(self, event: str, url: str = None, error: str = None):
        if error:
            self._logger.error(f"爬虫错误 | {event} | {url or 'N/A'} | {error}")
        else:
            self._logger.info(f"爬虫 | {event} | {url or 'N/A'}")

    def log_update_event(self, instruction: str, files_created: int, files_modified: int, success: bool):
        if success:
            self._logger.success(
                f"代码更新 | {instruction} | 创建: {files_created} 修改: {files_modified}"
            )
        else:
            self._logger.error(f"代码更新失败 | {instruction}")

    def log_version_event(self, event: str, version_id: str, name: str = None, success: bool = True):
        if success:
            self._logger.success(f"版本 {event} | {version_id} | {name or ''}")
        else:
            self._logger.error(f"版本 {event} 失败 | {version_id}")
