import traceback
import inspect
import linecache
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

try:
    from rich.console import Console
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    DATABASE = "database"
    NETWORK = "network"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    CRAWLER = "crawler"
    FILE_SYSTEM = "file_system"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    file_path: str
    function_name: str
    line_number: int
    code_snippet: str
    local_variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StackFrame:
    file_path: str
    function_name: str
    line_number: int
    code_snippet: str
    locals_preview: Dict[str, str] = field(default_factory=dict)


@dataclass
class StructuredError:
    error_id: str
    timestamp: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    request_id: Optional[str]
    user_id: Optional[str]
    context: ErrorContext
    stack_trace: List[StackFrame]
    suggestion: str
    original_exception: Optional[Exception]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "context": {
                "file": self.context.file_path,
                "function": self.context.function_name,
                "line": self.context.line_number,
                "code": self.context.code_snippet,
            },
            "stack_trace": [
                {
                    "file": f.file_path,
                    "function": f.function_name,
                    "line": f.line_number,
                    "code": f.code_snippet,
                }
                for f in self.stack_trace
            ],
            "suggestion": self.suggestion,
        }


class ErrorReporter:
    def __init__(self):
        self.errors: List[StructuredError] = []
        self.max_stored = 100

    def _get_code_snippet(self, filename: str, lineno: int, context: int = 3) -> str:
        try:
            if not filename or filename == "unknown":
                return "<代码位置未知>"

            lines = linecache.getlines(filename)
            if not lines:
                return f"<无法读取 {filename}>"

            start = max(0, lineno - context - 1)
            end = min(len(lines), lineno + context)
            snippet_lines = lines[start:end]

            result = []
            for i, line in enumerate(snippet_lines, start=start + 1):
                marker = ">>>" if i == lineno else "   "
                result.append(f"{marker} {i:4d} │ {line.rstrip()}")

            return "\n".join(result)
        except Exception:
            return f"<读取失败 {filename}:{lineno}>"

    def _extract_locals(self, frame) -> Dict[str, str]:
        locals_preview = {}
        try:
            for key, value in frame.f_locals.items():
                if not key.startswith('__'):
                    try:
                        value_str = repr(value)
                        if len(value_str) > 100:
                            value_str = value_str[:100] + "..."
                        locals_preview[key] = value_str
                    except Exception:
                        locals_preview[key] = "<无法序列化>"
        except Exception:
            pass
        return locals_preview

    def _get_traceback_info(self, exc_tb):
        if exc_tb is None:
            return "unknown", "unknown", 0

        try:
            frame = exc_tb.tb_frame
            filename = getattr(exc_tb, 'tb_filename', None) or getattr(frame, 'f_code', None) and getattr(frame.f_code, 'co_filename', None) or "unknown"
            lineno = getattr(exc_tb, 'tb_lineno', 0) or 0
            return filename, lineno
        except Exception:
            return "unknown", 0

    def _build_stack_trace(self, exc_tb) -> List[StackFrame]:
        stack = []
        current_tb = exc_tb
        while current_tb:
            try:
                frame = current_tb.tb_frame
                filename = getattr(current_tb, 'tb_filename', None)
                if not filename:
                    filename = getattr(frame, 'f_code', None) and getattr(frame.f_code, 'co_filename', None) or "unknown"
                lineno = getattr(current_tb, 'tb_lineno', 0) or 0
                func_name = getattr(frame, 'f_code', None) and getattr(frame.f_code, 'co_name', None) or "unknown"

                stack.append(StackFrame(
                    file_path=filename or "unknown",
                    function_name=func_name or "unknown",
                    line_number=lineno,
                    code_snippet=self._get_code_snippet(filename, lineno),
                    locals_preview=self._extract_locals(frame),
                ))
            except Exception:
                break
            current_tb = getattr(current_tb, 'tb_next', None)
        return stack

    def _get_error_context(self, exc_tb) -> ErrorContext:
        if exc_tb:
            try:
                frame = exc_tb.tb_frame
                filename = getattr(exc_tb, 'tb_filename', None)
                if not filename:
                    filename = getattr(frame, 'f_code', None) and getattr(frame.f_code, 'co_filename', None) or "unknown"
                lineno = getattr(exc_tb, 'tb_lineno', 0) or 0
                func_name = getattr(frame, 'f_code', None) and getattr(frame.f_code, 'co_name', None) or "unknown"

                return ErrorContext(
                    file_path=filename or "unknown",
                    function_name=func_name or "unknown",
                    line_number=lineno,
                    code_snippet=self._get_code_snippet(filename, lineno),
                    local_variables=self._extract_locals(frame),
                )
            except Exception:
                pass

        return ErrorContext(
            file_path="unknown",
            function_name="unknown",
            line_number=0,
            code_snippet="",
        )

    def _categorize_error(self, error_type: str, error_message: str) -> ErrorCategory:
        error_lower = f"{error_type} {error_message}".lower()

        if any(kw in error_lower for kw in ['database', 'sql', 'db', 'sqlite', 'asyncpg']):
            return ErrorCategory.DATABASE
        elif any(kw in error_lower for kw in ['connection', 'timeout', 'network', 'http', 'request']):
            return ErrorCategory.NETWORK
        elif any(kw in error_lower for kw in ['validation', 'invalid', 'parse']):
            return ErrorCategory.VALIDATION
        elif any(kw in error_lower for kw in ['auth', 'token', 'jwt', 'credential']):
            return ErrorCategory.AUTHENTICATION
        elif any(kw in error_lower for kw in ['permission', 'forbidden', 'access']):
            return ErrorCategory.AUTHORIZATION
        elif any(kw in error_lower for kw in ['not found', 'does not exist', '404']):
            return ErrorCategory.NOT_FOUND
        elif any(kw in error_lower for kw in ['crawl', 'scrap', 'parse error']):
            return ErrorCategory.CRAWLER
        elif any(kw in error_lower for kw in ['file', 'path', 'directory', 'io', 'permission']):
            return ErrorCategory.FILE_SYSTEM
        return ErrorCategory.UNKNOWN

    def _determine_severity(self, error_type: str, category: ErrorCategory) -> ErrorSeverity:
        critical_types = ['database', 'connection', 'memory', 'system']
        if any(ct in error_type.lower() for ct in critical_types):
            return ErrorSeverity.CRITICAL
        if category in [ErrorCategory.DATABASE, ErrorCategory.NETWORK]:
            return ErrorSeverity.HIGH
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.AUTHORIZATION]:
            return ErrorSeverity.MEDIUM
        return ErrorSeverity.MEDIUM

    def _generate_suggestion(self, category: ErrorCategory, error_message: str) -> str:
        suggestions = {
            ErrorCategory.DATABASE: "检查数据库连接配置，确认数据库服务是否运行，查看数据库日志获取更多详情。",
            ErrorCategory.NETWORK: "检查网络连接，确认目标服务是否可达，考虑增加超时时间或重试机制。",
            ErrorCategory.VALIDATION: "检查输入参数格式，确保符合API规范要求，参考API文档。",
            ErrorCategory.AUTHENTICATION: "确认凭据有效，检查Token是否过期，尝试重新登录获取新Token。",
            ErrorCategory.AUTHORIZATION: "检查用户权限配置，确认当前用户是否有权执行此操作。",
            ErrorCategory.NOT_FOUND: "确认请求的资源ID或路径是否正确，资源可能已被删除。",
            ErrorCategory.CRAWLER: "检查目标网站是否可访问，确认爬虫规则是否符合网站要求。",
            ErrorCategory.FILE_SYSTEM: "检查文件路径和权限配置，确认目标目录是否存在且可访问。",
            ErrorCategory.UNKNOWN: "查看详细错误信息和堆栈跟踪，联系技术支持获取帮助。",
        }
        return suggestions.get(category, "查看详细错误信息，联系技术支持。")

    def report(
        self,
        exception: Exception,
        error_id: str,
        request_id: str = None,
        user_id: str = None,
    ) -> StructuredError:
        exc_type = type(exception)
        exc_tb = exception.__traceback__

        category = self._categorize_error(exc_type.__name__, str(exception))
        severity = self._determine_severity(exc_type.__name__, category)

        structured = StructuredError(
            error_id=error_id,
            timestamp=datetime.now().isoformat(),
            error_type=exc_type.__name__,
            error_message=str(exception),
            severity=severity,
            category=category,
            request_id=request_id,
            user_id=user_id,
            context=self._get_error_context(exc_tb),
            stack_trace=self._build_stack_trace(exc_tb) if exc_tb else [],
            suggestion=self._generate_suggestion(category, str(exception)),
            original_exception=exception,
        )

        if len(self.errors) >= self.max_stored:
            self.errors.pop(0)
        self.errors.append(structured)

        return structured

    def print_error_report(self, error: StructuredError):
        if not RICH_AVAILABLE:
            self._print_error_plain(error)
            return

        print()
        panel = Panel(
            f"[bold red]{error.error_type}[/bold red]\n"
            f"[yellow]{error.error_message}[/yellow]\n\n"
            f"[dim]错误ID:[/dim] [cyan]{error.error_id}[/cyan]\n"
            f"[dim]时间:[/dim] [cyan]{error.timestamp}[/cyan]\n"
            f"[dim]严重性:[/dim] [red]{error.severity.value.upper()}[/red]\n"
            f"[dim]类别:[/dim] [blue]{error.category.value}[/blue]",
            title="错误报告",
            border_style="red",
        )
        console.print(panel)

        context_panel = Panel(
            f"[dim]文件:[/dim] [white]{error.context.file_path}[/white]\n"
            f"[dim]函数:[/dim] [green]{error.context.function_name}()[/green]\n"
            f"[dim]行号:[/dim] [yellow]{error.context.line_number}[/yellow]",
            title="错误位置",
            border_style="blue",
        )
        console.print(context_panel)

        if error.context.code_snippet:
            code_panel = Panel(
                error.context.code_snippet,
                title="代码片段",
                border_style="green",
            )
            console.print(code_panel)

        if error.stack_trace:
            table = Table(title="调用栈", show_header=True, header_style="bold magenta")
            table.add_column("文件", style="cyan", no_wrap=False)
            table.add_column("函数", style="green")
            table.add_column("行号", style="yellow", justify="right")

            for frame in error.stack_trace[:10]:
                table.add_row(
                    frame.file_path.split("/")[-1],
                    frame.function_name,
                    str(frame.line_number)
                )
            console.print(table)

        suggestion_panel = Panel(
            f"[bold]建议:[/bold] {error.suggestion}",
            title="解决方案",
            border_style="yellow",
        )
        console.print(suggestion_panel)
        print()

    def _print_error_plain(self, error: StructuredError):
        print()
        print("=" * 70)
        print(f" 错误报告 #{error.error_id}")
        print("=" * 70)
        print(f"类型: {error.error_type}")
        print(f"消息: {error.error_message}")
        print(f"时间: {error.timestamp}")
        print(f"严重性: {error.severity.value.upper()}")
        print(f"类别: {error.category.value}")
        print()
        print("-" * 70)
        print("错误位置:")
        print(f"  文件: {error.context.file_path}")
        print(f"  函数: {error.context.function_name}()")
        print(f"  行号: {error.context.line_number}")
        print()
        if error.context.code_snippet:
            print("代码片段:")
            for line in error.context.code_snippet.split('\n'):
                print(f"  {line}")
        print()
        print("-" * 70)
        print(f"建议: {error.suggestion}")
        print("=" * 70)
        print()


error_reporter = ErrorReporter()
