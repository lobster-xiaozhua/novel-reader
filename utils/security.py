import logging
import time
from functools import wraps
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    DEFAULT_LIMITS = {
        "anonymous": {"requests": 30, "period": 60},
        "authenticated": {"requests": 100, "period": 60},
        "premium": {"requests": 500, "period": 60},
    }

    CACHE_PREFIX = "rate_limit"
    CACHE_TIMEOUT = 3600

    @classmethod
    def check_rate_limit(cls, identifier, limit_type="anonymous", custom_limits=None):
        limits = custom_limits or cls.DEFAULT_LIMITS
        limit_config = limits.get(limit_type, limits["anonymous"])

        max_requests = limit_config["requests"]
        period = limit_config["period"]

        cache_key = f"{cls.CACHE_PREFIX}_{identifier}_{int(time.time() // period)}"

        try:
            current_count = cache.get(cache_key, 0)

            if current_count >= max_requests:
                remaining_time = period - (time.time() % period)
                logger.warning(f"Rate limit exceeded: {identifier}, count={current_count}, limit={max_requests}")
                return False, {"limit": max_requests, "remaining": 0, "reset_time": int(remaining_time)}

            cache.set(cache_key, current_count + 1, timeout=period)

            return True, {"limit": max_requests, "remaining": max_requests - current_count - 1, "reset_time": period}
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True, {"limit": max_requests, "remaining": max_requests, "reset_time": period}

    @classmethod
    def get_client_identifier(cls, request):
        if request.user.is_authenticated:
            return f"user_{request.user.id}"
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")
        return f"ip_{ip}"


def rate_limit(limit_type="anonymous", custom_limits=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if getattr(settings, "DISABLE_RATE_LIMIT", False):
                return view_func(request, *args, **kwargs)

            identifier = RateLimiter.get_client_identifier(request)
            allowed, info = RateLimiter.check_rate_limit(identifier, limit_type, custom_limits)

            if not allowed:
                return JsonResponse(
                    {"error": "请求过于频繁，请稍后再试", "retry_after": info["reset_time"]}, status=429
                )

            response = view_func(request, *args, **kwargs)

            if hasattr(response, "__setitem__"):
                response["X-RateLimit-Limit"] = str(info["limit"])
                response["X-RateLimit-Remaining"] = str(info["remaining"])
                response["X-RateLimit-Reset"] = str(info["reset_time"])

            return response

        return wrapper

    return decorator


class SecurityValidator:
    SSRF_BLOCKED_IPS = {
        "169.254.169.254",
        "metadata.google.internal",
        "127.0.0.1",
        "localhost",
        "0.0.0.0",
        "::1",
        "metadata.googleusercontent.com",
    }

    DANGEROUS_PATTERNS = ["../", "..\\", "%2e%2e", "\x00", "\n", "\r", "<script", "javascript:", "onerror=", "onclick="]

    @classmethod
    def validate_url(cls, url):
        import re
        from urllib.parse import urlparse
        import socket
        import ipaddress

        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False, "不支持的URL协议"

            hostname = parsed.hostname
            if not hostname or hostname in cls.SSRF_BLOCKED_IPS:
                return False, "不允许访问该地址"

            try:
                resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
                for family, _, _, _, sockaddr in resolved_ips:
                    ip = sockaddr[0]
                    if ipaddress.ip_address(ip).is_private:
                        return False, "不允许访问内网地址"
            except socket.gaierror:
                return False, "无法解析域名"

            for pattern in cls.DANGEROUS_PATTERNS:
                if pattern.lower() in url.lower():
                    return False, f"URL包含危险模式: {pattern}"

            return True, "URL验证通过"

        except Exception as e:
            logger.error(f"URL验证失败: {e}")
            return False, f"URL验证失败: {str(e)}"

    @classmethod
    def sanitize_input(cls, text, max_length=None):
        import re

        text = text.strip()

        dangerous_patterns = [
            (r"<script[^>]*>.*?</script>", ""),
            (r"<iframe[^>]*>.*?</iframe>", ""),
            (r"javascript:", ""),
            (r"on\w+\s*=", ""),
        ]

        for pattern, replacement in dangerous_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE | re.DOTALL)

        text = text.replace("\x00", "")

        if max_length:
            text = text[:max_length]

        return text

    @classmethod
    def validate_file_path(cls, path, base_dir):
        import os
        from pathlib import Path

        try:
            base = Path(base_dir).resolve()
            target = (base / path).resolve()

            if not str(target).startswith(str(base)):
                return False, "路径越界"

            if not target.exists() and not target.parent.exists():
                return False, "路径不存在"

            return True, "路径验证通过"

        except Exception as e:
            logger.error(f"路径验证失败: {e}")
            return False, f"路径验证失败: {str(e)}"


class InputValidator:
    @staticmethod
    def validate_book_data(data):
        errors = {}

        title = data.get("title", "").strip()
        if not title:
            errors["title"] = "书名不能为空"
        elif len(title) > 200:
            errors["title"] = "书名不能超过200个字符"

        author = data.get("author", "").strip()
        if author and len(author) > 100:
            errors["author"] = "作者名不能超过100个字符"

        category = data.get("category", "").strip()
        if category and len(category) > 50:
            errors["category"] = "分类不能超过50个字符"

        description = data.get("description", "").strip()
        if description and len(description) > 2000:
            errors["description"] = "简介不能超过2000个字符"

        return errors if errors else None

    @staticmethod
    def validate_review_data(data):
        errors = {}

        content = data.get("content", "").strip()
        if not content:
            errors["content"] = "评论内容不能为空"
        elif len(content) < 10:
            errors["content"] = "评论内容至少需要10个字符"
        elif len(content) > 5000:
            errors["content"] = "评论内容不能超过5000个字符"

        rating = data.get("rating")
        if rating:
            try:
                rating = int(rating)
                if not 1 <= rating <= 5:
                    errors["rating"] = "评分必须在1-5之间"
            except (ValueError, TypeError):
                errors["rating"] = "评分格式不正确"

        return errors if errors else None

    @staticmethod
    def validate_note_data(data):
        errors = {}

        content = data.get("content", "").strip()
        if not content:
            errors["content"] = "笔记内容不能为空"
        elif len(content) > 10000:
            errors["content"] = "笔记内容不能超过10000个字符"

        return errors if errors else None
