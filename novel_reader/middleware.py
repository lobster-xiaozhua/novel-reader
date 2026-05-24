"""
中间件模块

该模块定义了小说阅读器项目使用的自定义中间件和日志过滤器，包括：
- DisableCSRFForAPI: 为 /api/ 路径下的请求自动禁用 CSRF 校验，
  适用于前后端分离架构中基于 Token 认证的 API 请求。
- AsyncStreamingMiddleware: 将同步流式响应（StreamingHttpResponse）
  转换为异步流式响应，以适配 ASGI 异步服务器的流式传输需求。
- SuppressBadAuthLog: 日志过滤器，用于屏蔽来自恶意扫描器的
  无效认证请求日志，避免日志文件被无意义的错误信息淹没。
"""

import logging

from django.http import StreamingHttpResponse


class DisableCSRFForAPI:
    """
    为 API 请求禁用 CSRF 校验的中间件。

    在前后端分离架构中，API 请求通常使用 Token 或 Session 认证，
    不需要 CSRF 保护。此中间件自动识别以 '/api/' 开头的请求路径，
    并跳过该请求的 CSRF 校验，减少客户端在调用 API 时的 403 错误。
    """

    def __init__(self, get_response):
        """
        初始化中间件。

        参数:
            get_response (callable): Django 提供的下一个中间件或视图的可调用对象
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        处理请求，对 API 路径跳过 CSRF 校验。

        参数:
            request (HttpRequest): 当前 HTTP 请求对象

        返回:
            HttpResponse: 下一个中间件或视图返回的响应对象
        """
        if request.path.startswith('/api/'):
            # 设置内部标记，告知 Django 跳过此请求的 CSRF 校验
            setattr(request, '_dont_enforce_csrf_checks', True)
        return self.get_response(request)


class AsyncStreamingMiddleware:
    """
    异步流式响应中间件。

    当 Django 视图返回 StreamingHttpResponse 时，如果流式内容
    是同步迭代器而非异步迭代器，此中间件会自动将其包装为异步
    生成器，以适配 ASGI 服务器的异步流式传输机制，避免在异步
    环境中出现同步阻塞。
    """

    def __init__(self, get_response):
        """
        初始化中间件。

        参数:
            get_response (callable): Django 提供的下一个中间件或视图的可调用对象
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        处理请求，检查响应是否为流式响应并做异步化转换。

        参数:
            request (HttpRequest): 当前 HTTP 请求对象

        返回:
            HttpResponse: 处理后的响应对象（流式响应可能已被转换）
        """
        response = self.get_response(request)
        if isinstance(response, StreamingHttpResponse):
            # 获取流式内容迭代器
            content = response.streaming_content
            # 如果内容不支持异步迭代，将其包装为异步生成器
            if not hasattr(content, '__aiter__'):
                response.streaming_content = self._make_async(content)
        return response

    @staticmethod
    def _make_async(sync_iter):
        """
        将同步迭代器包装为异步生成器，并将字符串块编码为字节。

        参数:
            sync_iter (iterable): 同步迭代器，每次迭代产生数据块

        返回:
            async generator: 异步生成器，逐块产出字节数据
        """
        async def _gen():
            for chunk in sync_iter:
                # 确保所有数据块都是字节类型，字符串需要编码
                if isinstance(chunk, str):
                    chunk = chunk.encode()
                yield chunk
        return _gen()


class SuppressBadAuthLog(logging.Filter):
    """
    日志过滤器：屏蔽恶意扫描器产生的无效认证日志。

    某些恶意扫描器或自动化攻击工具会发送畸形的 HTTP 请求（如
    包含伪造 AUTH 头的请求或语法错误的请求行），Django 会为
    这些请求产生大量无意义的错误日志。此过滤器通过匹配日志
    消息中的特定模式来过滤掉这些噪音，保持日志文件的清洁。
    """

    # 需要过滤的日志消息模式：伪造认证头和错误请求语法
    _PATTERNS = ('"AUTH"', 'Bad request syntax')

    def filter(self, record):
        """
        判断该日志记录是否应该被允许通过。

        参数:
            record (logging.LogRecord): 待过滤的日志记录对象

        返回:
            bool: 返回 True 表示允许日志通过，False 表示拦截该日志
        """
        msg = record.getMessage()
        # 如果日志消息包含任何黑名单模式，则拦截（返回 False）
        return not any(p in msg for p in self._PATTERNS)
