import pytest
import logging
from datetime import datetime

from app.core.logging_config import (
    LogLevel,
    Colors,
    ConsoleFormatter,
    ElegantLogger,
    StructuredLogger,
    get_logger,
)


class TestLogLevel:
    def test_log_levels_exist(self):
        assert hasattr(LogLevel, 'TRACE')
        assert hasattr(LogLevel, 'DEBUG')
        assert hasattr(LogLevel, 'INFO')
        assert hasattr(LogLevel, 'SUCCESS')
        assert hasattr(LogLevel, 'WARNING')
        assert hasattr(LogLevel, 'ERROR')
        assert hasattr(LogLevel, 'CRITICAL')

    def test_log_level_values(self):
        assert LogLevel.TRACE == 5
        assert LogLevel.DEBUG == 10
        assert LogLevel.INFO == 20
        assert LogLevel.SUCCESS == 25
        assert LogLevel.WARNING == 30
        assert LogLevel.ERROR == 40
        assert LogLevel.CRITICAL == 50


class TestColors:
    def test_color_constants_exist(self):
        assert hasattr(Colors, 'RESET')
        assert hasattr(Colors, 'BOLD')
        assert hasattr(Colors, 'DIM')
        assert hasattr(Colors, 'RED')
        assert hasattr(Colors, 'GREEN')
        assert hasattr(Colors, 'YELLOW')
        assert hasattr(Colors, 'BLUE')
        assert hasattr(Colors, 'CYAN')

    def test_color_values_are_strings(self):
        assert isinstance(Colors.RESET, str)
        assert Colors.RESET == "\033[0m"


class TestConsoleFormatter:
    def test_formatter_init(self):
        formatter = ConsoleFormatter(use_color=True, show_trace=True)
        assert formatter.show_trace is True

    def test_formatter_init_no_color(self):
        formatter = ConsoleFormatter(use_color=False)
        assert formatter.use_color is False

    def test_format_time(self):
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.created = datetime.now().timestamp()

        time_str = formatter._format_time(record)
        assert ":" in time_str
        assert len(time_str) >= 8

    def test_get_level_info(self):
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test",
            args=(),
            exc_info=None,
        )

        level, name, icon = formatter._get_level_info(record)
        assert level == logging.INFO
        assert name == "INFO"
        assert icon == "ℹ"

    def test_get_level_info_unknown(self):
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test",
            level=5,
            pathname="",
            lineno=0,
            msg="test",
            args=(),
            exc_info=None,
        )

        level, name, icon = formatter._get_level_info(record)
        assert name == "TRACE"

    def test_colorize_level_no_color(self):
        formatter = ConsoleFormatter(use_color=False)

        result = formatter._colorize_level("INFO", LogLevel.INFO)
        assert result == "INFO"

    def test_sanitize_removes_sensitive_data(self):
        formatter = ConsoleFormatter()

        message = "password=secret123"
        result = formatter._sanitize(message)
        assert "secret123" not in result
        assert "password=***" in result

    def test_sanitize_no_sensitive_data(self):
        formatter = ConsoleFormatter()

        message = "这是一条普通日志信息"
        result = formatter._sanitize(message)
        assert result == message


class TestElegantLogger:
    def test_get_instance(self):
        logger = ElegantLogger.get_instance("test_logger")
        assert isinstance(logger, ElegantLogger)
        assert logger.name == "test_logger"

    def test_get_instance_same_name(self):
        logger1 = ElegantLogger.get_instance("same_name")
        logger2 = ElegantLogger.get_instance("same_name")
        assert logger1 is logger2

    def test_logger_has_name(self):
        logger = ElegantLogger("test")
        assert logger.name == "test"

    def test_logger_initial_state(self):
        logger = ElegantLogger("test")
        assert logger._request_id is None
        assert isinstance(logger._context, dict)

    def test_set_request_id(self):
        logger = ElegantLogger("test")
        logger.set_request_id("req_123")

        assert logger._request_id == "req_123"

    def test_clear_request_id(self):
        logger = ElegantLogger("test")
        logger.set_request_id("req_123")
        logger.clear_request_id()

        assert logger._request_id is None

    def test_bind_context(self):
        logger = ElegantLogger("test")
        result = logger.bind(user_id="123", action="login")

        assert logger._context["user_id"] == "123"
        assert logger._context["action"] == "login"
        assert result is logger

    def test_child_logger(self):
        parent = ElegantLogger("parent")
        parent.set_request_id("req_123")
        parent.bind(component="parent_comp")

        child = parent.child("child")

        assert child.name == "parent.child"
        assert child._request_id == "req_123"
        assert child._context.get("component") == "parent_comp"

    def test_with_context(self):
        logger = ElegantLogger("test")
        logger.bind(original="value")

        new_logger = logger.with_context(additional="extra")

        assert new_logger._context.get("original") == "value"
        assert new_logger._context.get("additional") == "extra"

    def test_trace_method(self):
        logger = ElegantLogger("test")
        logger._logger = logging.getLogger("trace_test")

        logger.trace("trace message")
        logger.debug("debug message")
        logger.info("info message")
        logger.success("success message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")

    def test_sanitize_in_log(self):
        logger = ElegantLogger("sanitize_test")
        logger._logger = logging.getLogger("sanitize_test")

        logger.info("password=secret123")


class TestStructuredLogger:
    def test_initialization(self):
        elegant_logger = ElegantLogger("test")
        structured = StructuredLogger(elegant_logger)

        assert structured._logger is elegant_logger

    def test_log_database_operation_success(self):
        elegant_logger = ElegantLogger("db_test")
        structured = StructuredLogger(elegant_logger)

        structured.log_database_operation("INSERT", "books", 0.05)

    def test_log_database_operation_failure(self):
        elegant_logger = ElegantLogger("db_test_failure")
        structured = StructuredLogger(elegant_logger)

        structured.log_database_operation("UPDATE", "books", 5.0, success=False)

    def test_log_crawler_event(self):
        elegant_logger = ElegantLogger("crawler_test")
        structured = StructuredLogger(elegant_logger)

        structured.log_crawler_event("fetched", "https://example.com")

    def test_log_crawler_event_error(self):
        elegant_logger = ElegantLogger("crawler_test_error")
        structured = StructuredLogger(elegant_logger)

        structured.log_crawler_event("failed", "https://example.com", "connection timeout")

    def test_log_update_event_success(self):
        elegant_logger = ElegantLogger("update_test_success")
        structured = StructuredLogger(elegant_logger)

        structured.log_update_event("pull", 5, 10, success=True)

    def test_log_update_event_failure(self):
        elegant_logger = ElegantLogger("update_test_failure")
        structured = StructuredLogger(elegant_logger)

        structured.log_update_event("pull", 0, 0, success=False)

    def test_log_version_event_success(self):
        elegant_logger = ElegantLogger("version_test_success")
        structured = StructuredLogger(elegant_logger)

        structured.log_version_event("checked", "v1.0.0", "Release", success=True)

    def test_log_version_event_failure(self):
        elegant_logger = ElegantLogger("version_test_failure")
        structured = StructuredLogger(elegant_logger)

        structured.log_version_event("checked", "v1.0.0", success=False)


class TestGetLogger:
    def test_get_logger_returns_elegant_logger(self):
        logger = get_logger("test")
        assert isinstance(logger, ElegantLogger)

    def test_get_logger_name(self):
        logger = get_logger("specific_name")
        assert logger.name == "specific_name"
