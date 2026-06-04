"""系统初始化管理命令 - 启动时预热推荐/搜索/缓存引擎"""
import time
import logging

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '初始化系统引擎（推荐、搜索、缓存预热）'

    def _print(self, icon, msg):
        self.stdout.write(f'  {icon} {msg}')

    def handle(self, *args, **options):
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self._print('🚀', '初始化系统引擎...')
        self.stdout.write('=' * 50)

        # ── 数据库 ──
        self._print('📊', '数据库检查...')
        try:
            start = time.time()
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            elapsed = (time.time() - start) * 1000
            self._print('✅', f'数据库连接正常 ({elapsed:.0f}ms) | {connection.vendor}')
        except Exception as e:
            self._print('❌', f'数据库连接失败: {e}')
            return

        # ── 缓存 ──
        self._print('💾', '缓存系统检查...')
        try:
            cache.set('_init_check', 'ok', 10)
            if cache.get('_init_check') == 'ok':
                backend = settings.CACHES['default']['BACKEND'].split('.')[-1]
                self._print('✅', f'缓存就绪 | 后端: {backend}')
            else:
                self._print('⚠️', '缓存读写不一致')
        except Exception as e:
            self._print('⚠️', f'Redis 连接失败: {e}')
            self._print('ℹ️', '将使用降级模式（本地内存缓存）')

        # ── 统计 ──
        self._print('📈', '数据统计...')
        try:
            from apps.books.models import Book
            from apps.chapters.models import Chapter
            from apps.reader.models import ReadingProgress
            from apps.favorites.models import Favorite

            book_count = Book.objects.count()
            chapter_count = Chapter.objects.count()
            user_count = User.objects.count()
            progress_count = ReadingProgress.objects.count()
            favorite_count = Favorite.objects.count()
            self._print('✅', f'书籍: {book_count} | 章节: {chapter_count} | 用户: {user_count} | 阅读记录: {progress_count} | 收藏: {favorite_count}')
        except Exception as e:
            self._print('⚠️', f'统计查询失败: {e}')

        # ── 推荐引擎 ──
        self._print('🔥', '推荐算法引擎初始化...')
        try:
            start = time.time()
            from apps.recommender.engine import get_engine
            engine = get_engine()
            count = engine.build_index()
            elapsed = time.time() - start
            self._print('✅', f'推荐引擎就绪 | {count} 本书已索引 | 耗时{elapsed:.2f}s')

            # 预热推荐缓存
            self._print('🔥', '预热推荐缓存...')
            start = time.time()
            engine.get_hot_recommendations(10)
            engine.get_new_recommendations(10)
            elapsed = time.time() - start
            self._print('✅', f'推荐缓存预热完成 | 耗时{elapsed:.2f}s')
        except Exception as e:
            self._print('⚠️', f'推荐引擎初始化失败: {e}')

        # ── 搜索引擎 ──
        self._print('🔍', '搜索引擎初始化...')
        try:
            start = time.time()
            from apps.recommender.search import get_engine as get_search_engine
            sengine = get_search_engine()
            book_count = sengine.build_index()
            stats = sengine.get_stats()
            elapsed = time.time() - start
            self._print('✅', f'搜索引擎就绪 | {stats["total_books"]} 本书, {stats["total_chapters"]} 章 | 耗时{elapsed:.2f}s')
        except Exception as e:
            self._print('⚠️', f'搜索引擎初始化失败: {e}')

        # ── 相似度引擎 ──
        self._print('📊', '相似度引擎初始化...')
        try:
            from apps.recommender.engine import get_engine
            engine = get_engine()
            rec_stats = engine.get_stats()
            self._print('✅', f'相似度引擎就绪 | 索引: {rec_stats["index_size"]} 本书 | 缓存命中率: {rec_stats["cache_hit_rate"]}')
        except Exception as e:
            self._print('⚠️', f'相似度引擎初始化失败: {e}')

        # ── 文件监控 ──
        self._print('👀', '书籍目录检查...')
        try:
            import os
            for i, root in enumerate(settings.BOOKS_ROOTS):
                label = '主目录' if i == 0 else f'外挂目录{i}'
                if root.exists():
                    file_count = sum(1 for _, _, files in os.walk(root) for f in files)
                    self._print('✅', f'{label}: {root} | {file_count} 个文件')
                else:
                    self._print('ℹ️', f'{label}不存在: {root}（将自动创建）')
                    root.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self._print('⚠️', f'目录检查失败: {e}')

        self.stdout.write('')
        self.stdout.write('=' * 50)
        self._print('✅', '系统引擎初始化完成')
        self.stdout.write('=' * 50)
        self.stdout.write('')
