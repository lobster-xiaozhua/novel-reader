import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.core.config import Settings, get_settings


class TestSettings:
    def test_default_settings(self):
        settings = Settings()

        assert settings.APP_NAME == "Novel Reader"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.DEBUG is False

    def test_database_url_default(self):
        settings = Settings()

        assert "sqlite" in settings.DATABASE_URL
        assert "novel.db" in settings.DATABASE_URL

    def test_redis_url_default(self):
        settings = Settings()

        assert "redis://" in settings.REDIS_URL

    def test_password_min_length_default(self):
        settings = Settings()

        assert settings.PASSWORD_MIN_LENGTH == 8

    def test_token_expiry_defaults(self):
        settings = Settings()

        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60 * 24
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_crawler_defaults(self):
        settings = Settings()

        assert settings.CRAWLER_MAX_CONCURRENT == 5
        assert settings.CRAWLER_REQUEST_DELAY == 1.0
        assert settings.CRAWLER_MAX_RETRIES == 3
        assert settings.CRAWLER_TIMEOUT == 30

    def test_cache_defaults(self):
        settings = Settings()

        assert settings.CACHE_EXPIRE_MINUTES == 10
        assert settings.SEARCH_RESULTS_LIMIT == 50
        assert settings.PAGE_SIZE == 20

    def test_memory_optimization_defaults(self):
        settings = Settings()

        assert settings.MAX_CHAPTER_CONTENT_SIZE == 50000
        assert settings.CHAPTER_BATCH_SIZE == 50
        assert settings.FTS_BATCH_SIZE == 100
        assert settings.DB_POOL_SIZE == 5
        assert settings.DB_MAX_OVERFLOW == 10

    def test_directory_paths(self):
        settings = Settings()

        assert settings.DATA_DIR == "./data"
        assert settings.BOOKS_DIR == "./data/books"
        assert settings.INDEX_DIR == "./data/index"
        assert settings.LOGS_DIR == "./data/logs"
        assert settings.CACHE_DIR == "./data/cache"

    def test_settings_from_env(self):
        with patch.dict(os.environ, {
            "APP_NAME": "Test App",
            "DEBUG": "true",
            "PASSWORD_MIN_LENGTH": "12"
        }):
            settings = Settings()

            assert settings.APP_NAME == "Test App"
            assert settings.DEBUG is True
            assert settings.PASSWORD_MIN_LENGTH == 12

    def test_settings_case_sensitive(self):
        with patch.dict(os.environ, {"app_name": "lowercase"}):
            settings = Settings()
            assert settings.APP_NAME == "Novel Reader"

    def test_boolean_from_env(self):
        with patch.dict(os.environ, {"DEBUG": "True"}):
            settings = Settings()
            assert settings.DEBUG is True

        with patch.dict(os.environ, {"DEBUG": "False"}):
            settings = Settings()
            assert settings.DEBUG is False

        with patch.dict(os.environ, {"DEBUG": "0"}):
            settings = Settings()
            assert settings.DEBUG is False

    def test_integer_from_env(self):
        with patch.dict(os.environ, {"CRAWLER_TIMEOUT": "60"}):
            settings = Settings()
            assert settings.CRAWLER_TIMEOUT == 60

    def test_get_settings_returns_singleton(self):
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2


class TestSettingsValidation:
    def test_invalid_integer_type(self):
        with patch.dict(os.environ, {"CRAWLER_TIMEOUT": "not_a_number"}):
            with pytest.raises(ValueError):
                Settings()

    def test_negative_values_allowed(self):
        with patch.dict(os.environ, {"CRAWLER_MAX_CONCURRENT": "-1"}):
            settings = Settings()
            assert settings.CRAWLER_MAX_CONCURRENT == -1

    def test_zero_values_allowed(self):
        with patch.dict(os.environ, {"CRAWLER_MAX_RETRIES": "0"}):
            settings = Settings()
            assert settings.CRAWLER_MAX_RETRIES == 0


class TestSettingsEdgeCases:
    def test_very_long_string(self):
        long_value = "x" * 1000
        with patch.dict(os.environ, {"SECRET_KEY": long_value}):
            settings = Settings()
            assert settings.SECRET_KEY == long_value

    def test_empty_string(self):
        with patch.dict(os.environ, {"APP_NAME": ""}):
            settings = Settings()
            assert settings.APP_NAME == ""

    def test_special_characters_in_path(self):
        special_path = "./data with spaces/data!"
        with patch.dict(os.environ, {"DATA_DIR": special_path}):
            settings = Settings()
            assert settings.DATA_DIR == special_path
