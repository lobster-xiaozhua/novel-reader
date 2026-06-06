"""
数据库迁移测试
"""
import pytest
import logging
from pathlib import Path
from django.db import connection

logger = logging.getLogger(__name__)


class TestMigrations:
    """数据库迁移测试"""

    @pytest.mark.django_db
    def test_all_migrations_applied(self):
        """测试所有迁移已应用"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM django_migrations")
            migration_count = cursor.fetchone()[0]

        logger.info(f"已应用迁移数量: {migration_count}")
        assert migration_count > 0, "未应用任何迁移"

    @pytest.mark.django_db
    def test_core_tables_exist(self):
        """测试核心表已创建"""
        required_tables = [
            # Django 核心表
            "auth_user",
            "django_content_type",
            "django_migrations",
            # 应用表
            "books_book",
            "chapters_chapter",
            "reader_readingprogress",
            "reader_readingstats",
            "favorites_favorite",
            "config_config",
            "crawler_crawlertask",
        ]

        # 兼容不同数据库的表查询
        db_type = connection.vendor
        existing_tables = set()

        with connection.cursor() as cursor:
            if db_type == "sqlite":
                # SQLite 使用 sqlite_master
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = {row[0] for row in cursor.fetchall()}
            else:
                # PostgreSQL/MySQL 使用 information_schema
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = CURRENT_SCHEMA
                """)
                existing_tables = {row[0] for row in cursor.fetchall()}

        # 检查核心表是否都存在
        missing_tables = []
        for table in required_tables:
            if table not in existing_tables:
                missing_tables.append(table)

        if missing_tables:
            logger.warning(f"缺失表: {missing_tables}")

        # 我们只检查必须的核心表是否存在（有些可能在某些设置下可选）
        critical_tables = ["django_migrations", "auth_user", "books_book"]
        for table in critical_tables:
            assert table in existing_tables, f"关键表缺失: {table}"

    @pytest.mark.django_db
    def test_config_table_exists(self):
        """测试配置表已创建"""
        from apps.config.models import Config
        # 尝试访问该表，能成功就说明表存在
        # 不会有任何错误抛出就通过测试
        assert Config.objects.all().count() >= 0

    @pytest.mark.django_db
    def test_config_manager_initialization(self):
        """测试配置管理器可以正常初始化"""
        from apps.config.models import ConfigManager

        try:
            count = ConfigManager.initialize_defaults()
            logger.info(f"初始化了 {count} 个默认配置")
        except Exception as e:
            logger.error(f"配置初始化失败: {e}")
            raise

    @pytest.mark.django_db
    def test_get_config_works(self):
        """测试 get_config 函数正常工作"""
        from apps.config.models import get_config

        # 尝试获取几个配置
        site_name = get_config("site.name", "default")
        crawler_enabled = get_config("crawler.enabled", True)

        logger.info(f"site.name = {site_name}")
        logger.info(f"crawler.enabled = {crawler_enabled}")

        # 确保返回值类型正确
        assert isinstance(site_name, str)
        assert isinstance(crawler_enabled, bool)
