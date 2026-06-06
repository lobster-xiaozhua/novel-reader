"""Configuration Models - system-wide settings managed via admin interface"""
import json
import logging
from typing import Any, Optional
from django.db import models
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY = 'config:all'
CACHE_TIMEOUT = 300  # 5 minutes


class Config(models.Model):
    """系统配置项模型"""

    key = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='配置键',
        help_text='配置项的唯一标识'
    )
    value = models.TextField(
        verbose_name='配置值',
        help_text='配置项的具体值'
    )
    description = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name='配置描述',
        help_text='配置项的简要说明'
    )
    value_type = models.CharField(
        max_length=50,
        default='string',
        choices=[
            ('string', '字符串'),
            ('integer', '整数'),
            ('float', '浮点数'),
            ('boolean', '布尔值'),
            ('json', 'JSON'),
        ],
        verbose_name='值类型',
        help_text='配置值的数据类型'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )

    class Meta:
        db_table = 'config_config'
        verbose_name = '系统配置'
        verbose_name_plural = '系统配置'
        ordering = ['key']

    def __str__(self):
        return f'{self.key} = {self.get_parsed_value()}'

    def get_parsed_value(self) -> Any:
        """获取解析后的值"""
        if self.value_type == 'integer':
            try:
                return int(self.value)
            except (ValueError, TypeError):
                return 0
        elif self.value_type == 'float':
            try:
                return float(self.value)
            except (ValueError, TypeError):
                return 0.0
        elif self.value_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.value_type == 'json':
            try:
                return json.loads(self.value)
            except (json.JSONDecodeError, ValueError, TypeError):
                return {}
        return self.value

    def set_value(self, value: Any):
        """设置值（根据类型自动转换）"""
        if self.value_type == 'boolean':
            self.value = 'true' if value else 'false'
        elif self.value_type == 'json':
            self.value = json.dumps(value, ensure_ascii=False)
        else:
            self.value = str(value)
        self.save()

    def save(self, *args, **kwargs):
        """保存时清除缓存"""
        super().save(*args, **kwargs)
        cache.delete(CACHE_KEY)
        logger.info(f'Config saved: {self.key}, cache cleared')

    def delete(self, *args, **kwargs):
        """删除时清除缓存"""
        super().delete(*args, **kwargs)
        cache.delete(CACHE_KEY)
        logger.info(f'Config deleted: {self.key}, cache cleared')


class ConfigManager:
    """配置管理器 - 提供便捷的配置访问 API"""

    _defaults = {
        'site.name': {'value': 'Novel Reader', 'value_type': 'string', 'description': '网站名称'},
        'site.title': {'value': 'Novel Reader - 在线小说阅读', 'value_type': 'string', 'description': '网站标题'},
        'site.description': {'value': '现代、快速的在线小说阅读平台', 'value_type': 'string', 'description': '网站描述'},
        'reader.pagination.page_size': {'value': '50', 'value_type': 'integer', 'description': '章节列表分页大小'},
        'reader.auto_save_progress': {'value': 'true', 'value_type': 'boolean', 'description': '是否自动保存阅读进度'},
        'crawler.enabled': {'value': 'true', 'value_type': 'boolean', 'description': '是否启用爬虫功能'},
        'crawler.max_concurrent_tasks': {'value': '3', 'value_type': 'integer', 'description': '最大并发爬虫任务数'},
        'crawler.timeout_seconds': {'value': '30', 'value_type': 'integer', 'description': '爬虫请求超时时间（秒）'},
        'crawler.user_agent': {'value': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'value_type': 'string', 'description': '爬虫 User-Agent'},
        'search.enabled': {'value': 'true', 'value_type': 'boolean', 'description': '是否启用搜索功能'},
        'recommender.enabled': {'value': 'true', 'value_type': 'boolean', 'description': '是否启用推荐功能'},
        'cache.ttl.books': {'value': '300', 'value_type': 'integer', 'description': '书籍缓存时长（秒）'},
        'cache.ttl.chapters': {'value': '3600', 'value_type': 'integer', 'description': '章节缓存时长（秒）'},
        'registration.enabled': {'value': 'true', 'value_type': 'boolean', 'description': '是否允许新用户注册'},
        'max.upload.size_mb': {'value': '10', 'value_type': 'integer', 'description': '最大上传文件大小（MB）'},
        'books.allowed_extensions': {'value': '["txt", "md", "html"]', 'value_type': 'json', 'description': '允许的书籍文件格式'},
    }

    @classmethod
    def _get_all_configs(cls) -> dict:
        """从缓存或数据库获取所有配置"""
        cached = cache.get(CACHE_KEY)
        if cached is not None:
            return cached

        configs = {}
        for config in Config.objects.all():
            configs[config.key] = {
                'value': config.get_parsed_value(),
                'value_type': config.value_type,
                'description': config.description,
            }

        # 补全未在数据库中的默认配置
        for key, default in cls._defaults.items():
            if key not in configs:
                configs[key] = {
                    'value': Config(value=default['value'], value_type=default['value_type']).get_parsed_value(),
                    'value_type': default['value_type'],
                    'description': default['description'],
                }

        cache.set(CACHE_KEY, configs, CACHE_TIMEOUT)
        return configs

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """获取配置值"""
        configs = cls._get_all_configs()
        if key in configs:
            return configs[key]['value']
        if key in cls._defaults:
            return Config(
                value=cls._defaults[key]['value'],
                value_type=cls._defaults[key]['value_type']
            ).get_parsed_value()
        return default

    @classmethod
    def set(cls, key: str, value: Any, value_type: Optional[str] = None, description: str = ''):
        """设置配置值"""
        config, created = Config.objects.get_or_create(key=key)

        if value_type is None:
            if isinstance(value, bool):
                value_type = 'boolean'
            elif isinstance(value, int):
                value_type = 'integer'
            elif isinstance(value, float):
                value_type = 'float'
            elif isinstance(value, (dict, list)):
                value_type = 'json'
            else:
                value_type = 'string'

        config.value_type = value_type
        if description:
            config.description = description
        config.set_value(value)

    @classmethod
    def initialize_defaults(cls):
        """初始化默认配置到数据库"""
        initialized = 0
        for key, default in cls._defaults.items():
            if not Config.objects.filter(key=key).exists():
                Config.objects.create(
                    key=key,
                    value=default['value'],
                    value_type=default['value_type'],
                    description=default['description']
                )
                initialized += 1
        logger.info(f'Initialized {initialized} default configs')
        cache.delete(CACHE_KEY)
        return initialized


# 便捷访问函数
def get_config(key: str, default: Any = None) -> Any:
    return ConfigManager.get(key, default)


def set_config(key: str, value: Any, value_type: Optional[str] = None, description: str = ''):
    ConfigManager.set(key, value, value_type, description)
