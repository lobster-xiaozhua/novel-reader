import pytest
from app.core.terminal_compat import TerminalCompat
from app.core.safe_logger import SafeLogger


class TestTerminalCompat:
    def test_init(self):
        tc = TerminalCompat()
        assert hasattr(tc, 'encoding')
        assert hasattr(tc, 'supports_utf8')
        assert hasattr(tc, 'supports_emoji')

    def test_sym_utf8(self):
        tc = TerminalCompat()
        tc.supports_emoji = True
        assert tc.sym('✅') == '✅'

    def test_sym_fallback(self):
        tc = TerminalCompat()
        tc.supports_emoji = False
        assert tc.sym('✅') == '[OK]'

    def test_format_status_passed(self):
        tc = TerminalCompat()
        tc.supports_emoji = True
        assert tc.format_status(True) == '✅'

    def test_format_status_failed(self):
        tc = TerminalCompat()
        tc.supports_emoji = False
        assert tc.format_status(False) == '[ERR]'

    def test_container_detection(self):
        tc = TerminalCompat()
        assert isinstance(tc.is_container, bool)

    def test_ci_detection(self):
        tc = TerminalCompat()
        assert isinstance(tc.is_ci, bool)


class TestSafeLogger:
    def test_sanitize_password(self):
        logger = SafeLogger("test")
        message = "user password=secret123"
        result = logger._sanitize(message)
        assert "secret123" not in result
        assert "***" in result

    def test_sanitize_token(self):
        logger = SafeLogger("test")
        message = "api_key=abc123"
        result = logger._sanitize(message)
        assert "abc123" not in result

    def test_sanitize_bearer(self):
        logger = SafeLogger("test")
        message = "Bearer abc123token"
        result = logger._sanitize(message)
        assert "abc123token" not in result

    def test_sanitize_no_sensitive(self):
        logger = SafeLogger("test")
        message = "普通日志信息"
        result = logger._sanitize(message)
        assert result == "普通日志信息"
