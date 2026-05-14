"""
测试过去 24 小时内发现的关键 Bug 修复
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime


class TestCrawlerServiceBugFixes:
    """测试爬虫服务的 Bug 修复"""

    @pytest.mark.asyncio
    async def test_fetch_page_uses_status_not_status_code(self):
        """Bug 1: 验证 _fetch_page 使用 resp.status 而非 resp.status_code"""
        from app.services.crawler_service import CrawlerService

        service = CrawlerService()

        # 模拟 aiohttp 响应对象
        mock_response = AsyncMock()
        mock_response.status = 200  # aiohttp 使用 status，不是 status_code
        mock_response.text = AsyncMock(return_value="<html>test</html>")

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        # 验证使用 status 属性
        result = await service._fetch_page(mock_session, "http://example.com")
        assert result == "<html>test</html>"

    @pytest.mark.asyncio
    async def test_fetch_page_handles_non_200_status(self):
        """验证非 200 状态码正确处理"""
        from app.services.crawler_service import CrawlerService

        service = CrawlerService()

        mock_response = AsyncMock()
        mock_response.status = 404

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await service._fetch_page(mock_session, "http://example.com")
        assert result is None


class TestConfigBugFixes:
    """测试配置类的 Bug 修复"""

    def test_db_pool_recycle_config_exists(self):
        """Bug 2: 验证 DB_POOL_RECYCLE 配置存在"""
        from app.core.config import get_settings

        settings = get_settings()
        assert hasattr(settings, 'DB_POOL_RECYCLE')
        assert isinstance(settings.DB_POOL_RECYCLE, int)
        assert settings.DB_POOL_RECYCLE > 0

    def test_login_rate_limit_configs_exist(self):
        """Bug 4: 验证登录限流配置存在"""
        from app.core.config import get_settings

        settings = get_settings()
        assert hasattr(settings, 'LOGIN_RATE_LIMIT_WINDOW')
        assert hasattr(settings, 'LOGIN_RATE_LIMIT_MAX')
        assert isinstance(settings.LOGIN_RATE_LIMIT_WINDOW, int)
        assert isinstance(settings.LOGIN_RATE_LIMIT_MAX, int)


class TestCacheServiceBugFixes:
    """测试缓存服务的 Bug 修复"""

    @pytest.mark.asyncio
    async def test_is_redis_available_property_exists(self):
        """Bug 4: 验证 is_redis_available 属性存在"""
        from app.services.cache_service import CacheService

        service = CacheService()
        assert hasattr(service, 'is_redis_available')

        # 测试当客户端为 None 时返回 False
        service._client = None
        assert service.is_redis_available is False

        # 测试当客户端存在时返回 True
        service._client = AsyncMock()
        assert service.is_redis_available is True

    @pytest.mark.asyncio
    async def test_setex_method_exists(self):
        """Bug 4: 验证 setex 方法存在"""
        from app.services.cache_service import CacheService

        service = CacheService()
        assert hasattr(service, 'setex')

        # 测试 setex 功能
        service._client = AsyncMock()
        service._client.setex = AsyncMock(return_value=True)

        result = await service.setex("key", 300, "value")
        assert result is True
        service._client.setex.assert_called_once_with("key", 300, "value")


class TestAuthApiBugFixes:
    """测试认证 API 的 Bug 修复"""

    def test_no_get_current_token_import(self):
        """Bug 3: 验证没有导入不存在的 get_current_token 函数"""
        from app.api import auth

        # 检查 auth 模块没有导入 get_current_token
        import inspect
        source = inspect.getsource(auth)
        assert "get_current_token" not in source


class TestCrawlerApiBugFixes:
    """测试爬虫 API 的 Bug 修复"""

    def test_execute_crawl_uses_service(self):
        """Bug 5: 验证 execute_crawl 使用 crawler_service"""
        from app.api import crawler
        import inspect

        source = inspect.getsource(crawler.execute_crawl)
        # 验证使用了 crawler_service
        assert "crawler_service" in source
        # 验证没有重复定义 crawl_url
        assert source.count("async def") == 1
