import pytest
from app.core.error_reporter import (
    ErrorReporter,
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    StructuredError,
    StackFrame,
)


class TestErrorReporter:
    @pytest.fixture
    def reporter(self):
        return ErrorReporter()

    def test_reporter_initialization(self, reporter):
        assert reporter.max_stored == 100
        assert isinstance(reporter.errors, list)
        assert len(reporter.errors) == 0

    def test_categorize_database_error(self, reporter):
        category = reporter._categorize_error("DatabaseError", "connection failed")
        assert category == ErrorCategory.DATABASE

    def test_categorize_network_error(self, reporter):
        category = reporter._categorize_error("ConnectionError", "timeout")
        assert category == ErrorCategory.NETWORK

    def test_categorize_validation_error(self, reporter):
        category = reporter._categorize_error("ValidationError", "invalid input")
        assert category == ErrorCategory.VALIDATION

    def test_categorize_authentication_error(self, reporter):
        category = reporter._categorize_error("AuthError", "token expired")
        assert category == ErrorCategory.AUTHENTICATION

    def test_categorize_authorization_error(self, reporter):
        category = reporter._categorize_error("PermissionError", "access denied")
        assert category == ErrorCategory.AUTHORIZATION

    def test_categorize_not_found_error(self, reporter):
        category = reporter._categorize_error("NotFoundError", "resource not found")
        assert category == ErrorCategory.NOT_FOUND

    def test_categorize_crawler_error(self, reporter):
        category = reporter._categorize_error("CrawlerError", "crawl failed")
        assert category == ErrorCategory.CRAWLER

    def test_categorize_file_system_error(self, reporter):
        category = reporter._categorize_error("IOError", "file io operation failed")
        assert category == ErrorCategory.FILE_SYSTEM

    def test_categorize_unknown_error(self, reporter):
        category = reporter._categorize_error("UnknownError", "something went wrong")
        assert category == ErrorCategory.UNKNOWN

    def test_determine_severity_critical(self, reporter):
        severity = reporter._determine_severity("DatabaseConnectionError", ErrorCategory.DATABASE)
        assert severity == ErrorSeverity.CRITICAL

    def test_determine_severity_high(self, reporter):
        severity = reporter._determine_severity("NetworkError", ErrorCategory.NETWORK)
        assert severity == ErrorSeverity.HIGH

    def test_determine_severity_medium(self, reporter):
        severity = reporter._determine_severity("AuthError", ErrorCategory.AUTHENTICATION)
        assert severity == ErrorSeverity.MEDIUM

    def test_generate_suggestion_database(self, reporter):
        suggestion = reporter._generate_suggestion(ErrorCategory.DATABASE, "connection failed")
        assert "数据库" in suggestion

    def test_generate_suggestion_network(self, reporter):
        suggestion = reporter._generate_suggestion(ErrorCategory.NETWORK, "timeout")
        assert "网络" in suggestion

    def test_generate_suggestion_validation(self, reporter):
        suggestion = reporter._generate_suggestion(ErrorCategory.VALIDATION, "invalid input")
        assert "输入" in suggestion or "参数" in suggestion

    def test_generate_suggestion_authentication(self, reporter):
        suggestion = reporter._generate_suggestion(ErrorCategory.AUTHENTICATION, "token expired")
        assert "Token" in suggestion or "认证" in suggestion or "登录" in suggestion

    def test_generate_suggestion_authorization(self, reporter):
        suggestion = reporter._generate_suggestion(ErrorCategory.AUTHORIZATION, "access denied")
        assert "权限" in suggestion

    def test_generate_suggestion_not_found(self, reporter):
        suggestion = reporter._generate_suggestion(ErrorCategory.NOT_FOUND, "resource not found")
        assert "资源" in suggestion or "不存在" in suggestion

    def test_generate_suggestion_crawler(self, reporter):
        suggestion = reporter._generate_suggestion(ErrorCategory.CRAWLER, "crawl failed")
        assert "爬虫" in suggestion or "网站" in suggestion

    def test_generate_suggestion_file_system(self, reporter):
        suggestion = reporter._generate_suggestion(ErrorCategory.FILE_SYSTEM, "file not found")
        assert "文件" in suggestion or "路径" in suggestion

    def test_generate_suggestion_unknown(self, reporter):
        suggestion = reporter._generate_suggestion(ErrorCategory.UNKNOWN, "unknown error")
        assert len(suggestion) > 0

    def test_report_exception(self, reporter):
        try:
            raise ValueError("invalid input")
        except ValueError as e:
            error = reporter.report(e, "test_id_001", request_id="req_123")

        assert error is not None
        assert error.error_id == "test_id_001"
        assert error.request_id == "req_123"
        assert error.error_type == "ValueError"
        assert error.error_message == "invalid input"
        assert error.category == ErrorCategory.VALIDATION
        assert len(reporter.errors) == 1

    def test_report_stores_max_errors(self, reporter):
        reporter.max_stored = 3

        for i in range(5):
            try:
                raise ValueError(f"error {i}")
            except ValueError as e:
                reporter.report(e, f"id_{i}")

        assert len(reporter.errors) == 3
        assert reporter.errors[0].error_id == "id_2"
        assert reporter.errors[-1].error_id == "id_4"

    def test_report_with_user_id(self, reporter):
        try:
            raise RuntimeError("user error")
        except RuntimeError as e:
            error = reporter.report(e, "user_err", user_id="user_456")

        assert error.user_id == "user_456"


class TestStructuredError:
    def test_to_dict(self):
        context = ErrorContext(
            file_path="/app/test.py",
            function_name="test_func",
            line_number=10,
            code_snippet="raise ValueError()",
        )

        error = StructuredError(
            error_id="err123",
            timestamp="2024-01-01T00:00:00",
            error_type="ValueError",
            error_message="test message",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
            request_id="req_123",
            user_id="user_456",
            context=context,
            stack_trace=[],
            suggestion="Check input format",
            original_exception=None,
        )

        error_dict = error.to_dict()

        assert error_dict["error_id"] == "err123"
        assert error_dict["error_type"] == "ValueError"
        assert error_dict["severity"] == "medium"
        assert error_dict["category"] == "validation"
        assert error_dict["context"]["file"] == "/app/test.py"
        assert error_dict["context"]["function"] == "test_func"
        assert error_dict["suggestion"] == "Check input format"


class TestErrorContext:
    def test_error_context_creation(self):
        context = ErrorContext(
            file_path="/app/main.py",
            function_name="main",
            line_number=1,
            code_snippet="print('hello')",
        )

        assert context.file_path == "/app/main.py"
        assert context.function_name == "main"
        assert context.line_number == 1


class TestStackFrame:
    def test_stack_frame_creation(self):
        frame = StackFrame(
            file_path="/app/test.py",
            function_name="test_func",
            line_number=10,
            code_snippet="result = 1 + 1",
            locals_preview={"result": "2"},
        )

        assert frame.file_path == "/app/test.py"
        assert frame.function_name == "test_func"
        assert frame.locals_preview["result"] == "2"
