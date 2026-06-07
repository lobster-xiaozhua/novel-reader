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

        # ── 自动扫描导入书籍 ──
        self._print('📚', '自动扫描书籍目录...')
        try:
            from apps.books.models import Book as BookModel
            from apps.chapters.models import Chapter as ChapterModel
            import os

            config_path = os.path.join(str(settings.BASE_DIR), 'data', 'book_dirs.json')
            import json as _json
            config = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = _json.load(f)
                except Exception:
                    pass
            scan_paths = [str(settings.BOOKS_DIR)] + config.get('extra_dirs', [])
            imported = 0
            scan_errors = []

            for base in scan_paths:
                if not os.path.isdir(base):
                    continue
                for entry in os.scandir(base):
                    if not entry.is_dir():
                        continue
                    book_name = entry.name
                    if BookModel.objects.filter(title=book_name).exists():
                        continue
                    ch_files = sorted(
                        [f for f in os.scandir(entry.path) if f.is_file() and f.name.endswith('.txt')],
                        key=lambda f: f.name,
                    )
                    if not ch_files:
                        continue
                    try:
                        # 读取 metadata.json
                        author = ''
                        category = ''
                        description = ''
                        meta_path = os.path.join(entry.path, 'metadata.json')
                        if os.path.exists(meta_path):
                            try:
                                with open(meta_path, 'r', encoding='utf-8') as mf:
                                    meta = _json.load(mf)
                                author = meta.get('author', '')
                                category = meta.get('category', '')
                                description = meta.get('description', '')
                            except Exception:
                                pass
                        book = BookModel.objects.create(
                            title=book_name,
                            author=author,
                            category=category,
                            description=description,
                            folder_path=entry.path,
                            total_chapters=len(ch_files),
                        )
                        for idx, f in enumerate(ch_files, 1):
                            ch_title = os.path.splitext(f.name)[0]
                            rel_path = os.path.relpath(f.path, str(settings.BOOKS_DIR))
                            if rel_path.startswith('..'):
                                rel_path = f.path
                            content = ''
                            for enc in ('utf-8', 'gbk', 'gb2312'):
                                try:
                                    with open(f.path, 'r', encoding=enc) as fh:
                                        content = fh.read()
                                    break
                                except (UnicodeDecodeError, Exception):
                                    continue
                            ChapterModel.objects.create(
                                book=book, chapter_number=idx,
                                title=ch_title, file_path=rel_path,
                                word_count=len(content),
                            )
                        imported += 1
                        self._print('📖', f'新书入库: {book_name} ({len(ch_files)}章)')
                    except Exception as exc:
                        scan_errors.append(f'{book_name}: {str(exc)[:100]}')

            if imported > 0:
                self._print('✅', f'自动扫描完成: {imported}本新书入库')
                # 重建搜索和推荐索引
                self._print('🔄', '重建搜索索引...')
                try:
                    from apps.recommender.search import build_index as build_search_index
                    from apps.recommender.engine import get_engine as get_rec_engine
                    build_search_index(force=True)
                    get_rec_engine().build_index(force=True)
                    self._print('✅', '搜索和推荐索引已更新')
                except Exception as e:
                    self._print('⚠️', f'索引重建失败: {e}')
            else:
                self._print('✅', f'无新书（已有 {BookModel.objects.count()} 本书）')
            if scan_errors:
                for err in scan_errors:
                    self._print('⚠️', f'导入错误: {err}')
        except Exception as e:
            self._print('⚠️', f'自动扫描失败: {e}')

        # ── 启动电子狗文件监控 ──
        self._print('🐕', '启动电子狗文件监控...')
        try:
            from utils.watchfile import start_watcher
            start_watcher(scan_interval=30)
            self._print('✅', '电子狗已启动（每30秒扫描一次）🐕')
        except Exception as e:
            self._print('⚠️', f'电子狗启动失败: {e}')

        self.stdout.write('')
        self.stdout.write('=' * 50)
        self._print('✅', '系统引擎初始化完成')
        self.stdout.write('=' * 50)
        self.stdout.write('')
