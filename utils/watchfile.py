"""电子狗文件监控 - 自动监测书籍目录变更并入库"""
import logging
import os
import threading
import time
from pathlib import Path

from django.conf import settings
from django.core.management import call_command

logger = logging.getLogger(__name__)


class BookWatcher:
    """
    书籍目录文件监控器（电子狗）
    使用轮询方式监控书籍目录，检测新增/删除/修改的书籍
    """
    def __init__(self, scan_interval=30):
        self._scan_interval = scan_interval  # 扫描间隔（秒）
        self._running = False
        self._thread = None
        self._known_books = {}  # {book_dir_name: chapter_count}
        self._last_scan_time = 0

    def _get_scan_paths(self):
        """获取所有需要监控的路径"""
        paths = [str(settings.BOOKS_DIR)]
        # 从配置文件读取外挂目录
        import json
        config_path = os.path.join(str(settings.BASE_DIR), 'data', 'book_dirs.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                paths.extend(config.get('extra_dirs', []))
            except Exception:
                pass
        return [p for p in paths if os.path.isdir(p)]

    def _scan_books(self):
        """扫描所有书籍目录，返回 {book_dir_name: chapter_count} 的快照"""
        books = {}
        for base in self._get_scan_paths():
            try:
                for entry in os.scandir(base):
                    if entry.is_dir():
                        ch_count = sum(
                            1 for _ in os.scandir(entry.path)
                            if _.is_file() and _.name.endswith('.txt')
                        )
                        if ch_count > 0:
                            # 读取 metadata.json
                            meta = {}
                            meta_path = os.path.join(entry.path, 'metadata.json')
                            if os.path.exists(meta_path):
                                try:
                                    import json
                                    with open(meta_path, 'r', encoding='utf-8') as f:
                                        meta = json.load(f)
                                except Exception:
                                    pass
                            books[entry.name] = {
                                'path': entry.path,
                                'chapters': ch_count,
                                'mtime': entry.stat().st_mtime,
                                'author': meta.get('author', ''),
                                'category': meta.get('category', ''),
                                'description': meta.get('description', ''),
                            }
                    elif entry.is_file() and entry.name.endswith('.txt'):
                        # 单文件书籍（散落txt）
                        name = os.path.splitext(entry.name)[0]
                        books[name] = {
                            'path': base,
                            'chapters': 1,
                            'mtime': entry.stat().st_mtime,
                        }
            except PermissionError:
                logger.warning(f'[BookWatcher] 无权限扫描目录: {base}')
            except Exception as e:
                logger.error(f'[BookWatcher] 扫描目录出错 {base}: {e}')
        return books

    def _diff_and_import(self, current_books):
        """对比新旧状态，自动导入变更的书籍"""
        from apps.books.models import Book
        from apps.chapters.models import Chapter

        old_keys = set(self._known_books.keys())
        new_keys = set(current_books.keys())

        added = new_keys - old_keys
        removed = old_keys - new_keys
        modified = set()

        for key in new_keys & old_keys:
            if current_books[key]['chapters'] != self._known_books[key]['chapters']:
                modified.add(key)
            elif current_books[key]['mtime'] > self._known_books[key].get('mtime', 0) + 1:
                modified.add(key)

        imported = 0
        errors = []

        for book_name in added:
            try:
                info = current_books[book_name]
                self._import_book(book_name, info)
                imported += 1
                logger.info(f'[BookWatcher] 新书入库: {book_name} ({info["chapters"]}章)')
            except Exception as e:
                errors.append(f'{book_name}: {str(e)[:100]}')
                logger.error(f'[BookWatcher] 入库失败 {book_name}: {e}')

        for book_name in modified:
            try:
                # 重新导入已存在的书籍（更新章节）
                book = Book.objects.filter(title=book_name).first()
                if book:
                    info = current_books[book_name]
                    self._update_book(book, info)
                    imported += 1
                    logger.info(f'[BookWatcher] 书籍更新: {book_name} ({info["chapters"]}章)')
            except Exception as e:
                errors.append(f'{book_name}: {str(e)[:100]}')
                logger.error(f'[BookWatcher] 更新失败 {book_name}: {e}')

        for book_name in removed:
            logger.info(f'[BookWatcher] 书籍目录已移除: {book_name}（数据库记录保留）')

        if imported > 0:
            # 重建搜索和推荐索引
            try:
                from apps.recommender.engine import get_engine as get_rec_engine
                from apps.recommender.search import build_index as build_search_index
                get_rec_engine().build_index(force=True)
                build_search_index(force=True)
                logger.info(f'[BookWatcher] 索引已更新（{imported}本书变更）')
            except Exception as e:
                logger.error(f'[BookWatcher] 索引重建失败: {e}')

        self._known_books = {
            k: {'chapters': v['chapters'], 'mtime': v['mtime']}
            for k, v in current_books.items()
        }

        return imported, errors

    def _import_book(self, book_name, info):
        """导入一本新书"""
        from apps.books.models import Book
        from apps.chapters.models import Chapter

        book = Book.objects.create(
            title=book_name,
            author=info.get('author', ''),
            category=info.get('category', ''),
            description=info.get('description', ''),
            folder_path=info['path'],
            total_chapters=info['chapters'],
        )

        book_dir = info['path']
        if os.path.isdir(book_dir):
            ch_files = sorted(
                [f for f in os.scandir(book_dir) if f.is_file() and f.name.endswith('.txt')],
                key=lambda f: f.name,
            )
        else:
            # 单文件书籍
            ch_files = []

        for idx, f in enumerate(ch_files, 1):
            ch_title = os.path.splitext(f.name)[0]
            rel_path = str(f.path)
            try:
                rel_path = os.path.relpath(f.path, str(settings.BOOKS_DIR))
            except ValueError:
                pass
            content = ''
            for enc in ('utf-8', 'gbk', 'gb2312'):
                try:
                    with open(f.path, 'r', encoding=enc) as fh:
                        content = fh.read()
                    break
                except (UnicodeDecodeError, Exception):
                    continue
            Chapter.objects.create(
                book=book,
                chapter_number=idx,
                title=ch_title,
                file_path=rel_path,
                word_count=len(content),
            )

    def _update_book(self, book, info):
        """更新已有书籍的章节"""
        from apps.chapters.models import Chapter

        book.folder_path = info['path']
        book.total_chapters = info['chapters']
        book.save()

        book_dir = info['path']
        if os.path.isdir(book_dir):
            ch_files = sorted(
                [f for f in os.scandir(book_dir) if f.is_file() and f.name.endswith('.txt')],
                key=lambda f: f.name,
            )
            existing_numbers = set(Chapter.objects.filter(book=book).values_list('chapter_number', flat=True))
            for idx, f in enumerate(ch_files, 1):
                if idx not in existing_numbers:
                    ch_title = os.path.splitext(f.name)[0]
                    rel_path = str(f.path)
                    try:
                        rel_path = os.path.relpath(f.path, str(settings.BOOKS_DIR))
                    except ValueError:
                        pass
                    content = ''
                    for enc in ('utf-8', 'gbk', 'gb2312'):
                        try:
                            with open(f.path, 'r', encoding=enc) as fh:
                                content = fh.read()
                            break
                        except (UnicodeDecodeError, Exception):
                            continue
                    Chapter.objects.create(
                        book=book,
                        chapter_number=idx,
                        title=ch_title,
                        file_path=rel_path,
                        word_count=len(content),
                    )

    def _watch_loop(self):
        """监控循环"""
        logger.info('[BookWatcher] 电子狗监控已启动，扫描间隔: %ds', self._scan_interval)
        # 初始化快照
        self._known_books = {
            k: {'chapters': v['chapters'], 'mtime': v['mtime']}
            for k, v in self._scan_books().items()
        }
        logger.info('[BookWatcher] 初始快照: %d本书', len(self._known_books))

        while self._running:
            try:
                time.sleep(self._scan_interval)
                current = self._scan_books()
                imported, errors = self._diff_and_import(current)
                if imported > 0:
                    logger.info('[BookWatcher] 本次扫描发现 %d 本书变更', imported)
                if errors:
                    logger.warning('[BookWatcher] 导入错误: %s', errors)
            except Exception as e:
                logger.error('[BookWatcher] 监控循环异常: %s', e)

    def start(self):
        """启动监控"""
        if self._running:
            logger.warning('[BookWatcher] 监控已在运行中')
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True, name='book-watcher')
        self._thread.start()
        logger.info('[BookWatcher] 电子狗已启动 🐕')

    def stop(self):
        """停止监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info('[BookWatcher] 电子狗已停止')

    def scan_now(self):
        """立即执行一次扫描"""
        current = self._scan_books()
        return self._diff_and_import(current)

    def get_status(self):
        """获取监控状态"""
        return {
            'running': self._running,
            'known_books': len(self._known_books),
            'scan_interval': self._scan_interval,
            'last_scan_time': self._last_scan_time,
            'paths': self._get_scan_paths(),
        }


# 全局单例
_watcher = None


def get_watcher(scan_interval=30) -> BookWatcher:
    global _watcher
    if _watcher is None:
        _watcher = BookWatcher(scan_interval=scan_interval)
    return _watcher


def start_watcher(scan_interval=30):
    """启动电子狗监控"""
    w = get_watcher(scan_interval)
    w.start()
    return w


def stop_watcher():
    """停止电子狗监控"""
    global _watcher
    if _watcher:
        _watcher.stop()
        _watcher = None