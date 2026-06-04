import logging
import os
import time

from django.conf import settings

logger = logging.getLogger(__name__)

ES_HOST = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
_TIMEOUT = 2


def _get_es_client():
    try:
        from elasticsearch import Elasticsearch
        return Elasticsearch(
            [ES_HOST],
            request_timeout=_TIMEOUT,
            max_retries=0,
            retry_on_timeout=False,
        )
    except ImportError:
        logger.warning('[ESSearch] elasticsearch 库未安装，使用数据库搜索降级')
        return None
    except Exception as e:
        logger.warning(f'[ESSearch] Elasticsearch 客户端初始化失败: {e}')
        return None


class SearchService:
    _instance = None
    _client = None
    _available = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._client = _get_es_client()
        self._available = False
        from apps.search.mappings import BOOK_INDEX, CHAPTER_INDEX
        self._book_index = BOOK_INDEX
        self._chapter_index = CHAPTER_INDEX

    def _check_connection(self):
        try:
            if self._client.ping():
                logger.info('[ESSearch] Elasticsearch 连接成功')
                return True
        except Exception as e:
            logger.debug(f'[ESSearch] Elasticsearch 不可用: {e}')
        return False

    @property
    def available(self):
        if not self._available:
            self._available = self._check_connection()
        return self._available

    def _ensure_index(self, index_name, mapping_func):
        if not self.available:
            return
        try:
            if not self._client.indices.exists(index=index_name):
                mapping = mapping_func()
                self._client.indices.create(index=index_name, body=mapping)
                logger.info(f'[ESSearch] 索引 {index_name} 创建成功')
        except Exception as e:
            logger.error(f'[ESSearch] 索引 {index_name} 创建失败: {e}')

    def _read_chapter_content(self, file_path):
        if not file_path:
            return ''
        if os.path.isabs(file_path):
            norm = os.path.normpath(file_path)
        else:
            norm = None
            for root in settings.BOOKS_ROOTS:
                candidate = os.path.normpath(os.path.join(str(root), file_path))
                if os.path.exists(candidate):
                    norm = candidate
                    break
            if not norm:
                norm = os.path.normpath(os.path.join(str(settings.BASE_DIR), file_path))
        real_norm = os.path.realpath(norm)
        allowed = any(real_norm.startswith(os.path.realpath(str(r))) for r in settings.BOOKS_ROOTS)
        if not allowed or not os.path.exists(norm):
            return ''
        for enc in ('utf-8', 'gbk', 'gb2312'):
            try:
                with open(norm, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, Exception):
                continue
        return ''

    # ── 公开 API ──

    def index_book(self, book):
        """索引单本书籍"""
        if not self.available:
            return
        self._ensure_index(self._book_index, lambda: None)
        try:
            from apps.search.mappings import get_book_mapping
            self._ensure_index(self._book_index, get_book_mapping)
            doc = {
                'id': book.id,
                'title': book.title,
                'author': book.author or '',
                'category': book.category or '',
                'description': book.description or '',
                'tags': [t.name for t in book.tags.all()],
                'total_chapters': book.total_chapters,
                'created_at': book.created_at.isoformat() if book.created_at else None,
                'updated_at': book.updated_at.isoformat() if book.updated_at else None,
            }
            self._client.index(index=self._book_index, id=book.id, document=doc)
            logger.debug(f'[ESSearch] 书籍索引成功: {book.title}')
        except Exception as e:
            logger.error(f'[ESSearch] 书籍索引失败 {getattr(book, "id", "?")}: {e}')

    def index_chapter(self, chapter):
        """索引单个章节内容"""
        if not self.available:
            return
        try:
            from apps.search.mappings import get_chapter_mapping
            self._ensure_index(self._chapter_index, get_chapter_mapping)
            content = self._read_chapter_content(chapter.file_path)[:100000]
            doc = {
                'id': chapter.id,
                'book_id': chapter.book_id,
                'chapter_number': chapter.chapter_number,
                'title': chapter.title,
                'content': content,
                'word_count': chapter.word_count,
                'created_at': chapter.created_at.isoformat() if chapter.created_at else None,
            }
            self._client.index(index=self._chapter_index, id=chapter.id, document=doc)
            logger.debug(f'[ESSearch] 章节索引成功: {chapter.title}')
        except Exception as e:
            logger.error(f'[ESSearch] 章节索引失败 {getattr(chapter, "id", "?")}: {e}')

    def search(self, keyword, page=1, page_size=20):
        """
        搜索书籍和章节，返回带高亮的结果
        如果 ES 不可用则降级为数据库搜索
        """
        start = time.monotonic()
        if not keyword or not keyword.strip():
            return {'books': [], 'chapters': [], 'total': 0, 'search_time_ms': 0}

        if self.available:
            try:
                return self._es_search(keyword, page, page_size, start)
            except Exception as e:
                logger.warning(f'[ESSearch] ES 搜索失败，降级到数据库搜索: {e}')
                self._available = False

        return self._db_search(keyword, page, page_size, start)

    def _es_search(self, keyword, page, page_size, start_time):
        from elasticsearch.exceptions import ConnectionError as ESConnectionError
        try:
            books = self._search_books_es(keyword, page_size)
            chapters = self._search_chapters_es(keyword, page_size)
        except ESConnectionError:
            self._available = False
            raise

        books_list = []
        for hit in books.get('hits', {}).get('hits', []):
            src = hit['_source']
            hl = hit.get('highlight', {})
            books_list.append({
                'id': src['id'],
                'title': hl.get('title', [src.get('title', '')])[0],
                'author': src.get('author', ''),
                'category': src.get('category', ''),
                'description': hl.get('description', [src.get('description', '')])[0],
                'score': hit.get('_score', 0),
            })

        chapters_list = []
        chapter_book_ids = set()
        for hit in chapters.get('hits', {}).get('hits', []):
            src = hit['_source']
            hl = hit.get('highlight', {})
            chapter_book_ids.add(src['book_id'])
            chapters_list.append({
                'id': src['id'],
                'book_id': src['book_id'],
                'chapter_number': src['chapter_number'],
                'title': hl.get('title', [src.get('title', '')])[0],
                'content_preview': hl.get('content', [''])[0][:200],
                'score': hit.get('_score', 0),
            })

        total = books.get('hits', {}).get('total', {}).get('value', 0) + \
                chapters.get('hits', {}).get('total', {}).get('value', 0)

        elapsed = (time.monotonic() - start_time) * 1000
        logger.info(f'[ESSearch] 搜索 "{keyword}": {len(books_list)}本书, {len(chapters_list)}章节, {elapsed:.0f}ms')

        return {'books': books_list, 'chapters': chapters_list, 'total': total, 'search_time_ms': round(elapsed, 1)}

    def _search_books_es(self, keyword, size):
        query = {
            'query': {
                'multi_match': {
                    'query': keyword,
                    'fields': ['title^3', 'author^2', 'description', 'tags'],
                    'type': 'best_fields',
                },
            },
            'highlight': {
                'fields': {
                    'title': {'type': 'plain', 'pre_tags': ['<em>'], 'post_tags': ['</em>']},
                    'description': {'type': 'plain', 'pre_tags': ['<em>'], 'post_tags': ['</em>']},
                },
                'fragment_size': 150,
                'number_of_fragments': 1,
            },
            'size': size,
        }
        return self._client.search(index=self._book_index, body=query)

    def _search_chapters_es(self, keyword, size):
        query = {
            'query': {
                'multi_match': {
                    'query': keyword,
                    'fields': ['title^3', 'content'],
                    'type': 'best_fields',
                },
            },
            'highlight': {
                'fields': {
                    'title': {'type': 'plain', 'pre_tags': ['<em>'], 'post_tags': ['</em>']},
                    'content': {
                        'type': 'plain',
                        'pre_tags': ['<em>'],
                        'post_tags': ['</em>'],
                        'fragment_size': 120,
                        'number_of_fragments': 1,
                    },
                },
                'fragment_size': 150,
                'number_of_fragments': 1,
            },
            'size': size,
        }
        return self._client.search(index=self._chapter_index, body=query)

    def _db_search(self, keyword, page, page_size, start_time):
        from django.db.models import Q
        from apps.books.models import Book
        from apps.chapters.models import Chapter

        books_qs = Book.objects.filter(
            Q(title__icontains=keyword) | Q(author__icontains=keyword) | Q(description__icontains=keyword)
        )[:page_size]
        books_list = [
            {'id': b.id, 'title': b.title, 'author': b.author or '', 'category': b.category or '', 'description': b.description or '', 'score': 0}
            for b in books_qs
        ]

        chapters_qs = Chapter.objects.select_related('book').filter(
            Q(title__icontains=keyword)
        )[:page_size]
        chapters_list = []
        for ch in chapters_qs:
            content = self._read_chapter_content(ch.file_path)[:5000]
            preview = self._get_preview(content, keyword)
            chapters_list.append({
                'id': ch.id,
                'book_id': ch.book_id,
                'chapter_number': ch.chapter_number,
                'title': ch.title,
                'content_preview': preview,
                'score': 0,
            })

        total = len(books_list) + len(chapters_list)
        elapsed = (time.monotonic() - start_time) * 1000
        logger.info(f'[ESSearch] 数据库降级搜索 "{keyword}": {len(books_list)}本书, {len(chapters_list)}章节, {elapsed:.0f}ms')
        return {'books': books_list, 'chapters': chapters_list, 'total': total, 'search_time_ms': round(elapsed, 1)}

    def _get_preview(self, content, query, length=120):
        if not content:
            return ''
        content_lower = content.lower()
        query_lower = query.lower()
        pos = content_lower.find(query_lower)
        if pos == -1:
            return content[:length] + '...' if len(content) > length else content
        start = max(0, pos - 40)
        end = min(len(content), pos + len(query) + 60)
        preview = content[start:end]
        if start > 0:
            preview = '...' + preview
        if end < len(content):
            preview = preview + '...'
        return preview

    def delete_book(self, book_id):
        """从索引中删除书籍及其所有章节"""
        if not self.available:
            return
        try:
            self._client.delete_by_query(
                index=self._book_index,
                body={'query': {'term': {'id': book_id}}},
            )
            self._client.delete_by_query(
                index=self._chapter_index,
                body={'query': {'term': {'book_id': book_id}}},
            )
            logger.debug(f'[ESSearch] 书籍 {book_id} 已删除')
        except Exception as e:
            logger.error(f'[ESSearch] 删除书籍 {book_id} 失败: {e}')

    def rebuild_index(self):
        """从数据库重建所有索引"""
        if not self.available:
            logger.warning('[ESSearch] Elasticsearch 不可用，跳过索引重建')
            return
        from apps.books.models import Book
        from apps.chapters.models import Chapter

        start = time.time()
        logger.info('[ESSearch] 开始重建索引...')

        try:
            from apps.search.mappings import get_book_mapping, get_chapter_mapping
            for idx in (self._book_index, self._chapter_index):
                if self._client.indices.exists(index=idx):
                    self._client.indices.delete(index=idx)
                    logger.info(f'[ESSearch] 索引 {idx} 已删除')

            self._client.indices.create(index=self._book_index, body=get_book_mapping())
            self._client.indices.create(index=self._chapter_index, body=get_chapter_mapping())
            logger.info('[ESSearch] 索引结构创建完成')
        except Exception as e:
            logger.error(f'[ESSearch] 索引结构创建失败: {e}')
            return

        books = Book.objects.prefetch_related('tags').all()
        book_docs = []
        for book in books:
            book_docs.append({
                '_index': self._book_index,
                '_id': book.id,
                '_source': {
                    'id': book.id,
                    'title': book.title,
                    'author': book.author or '',
                    'category': book.category or '',
                    'description': book.description or '',
                    'tags': [t.name for t in book.tags.all()],
                    'total_chapters': book.total_chapters,
                    'created_at': book.created_at.isoformat() if book.created_at else None,
                    'updated_at': book.updated_at.isoformat() if book.updated_at else None,
                },
            })

        chapters = Chapter.objects.select_related('book').all()
        chapter_docs = []
        for ch in chapters:
            content = self._read_chapter_content(ch.file_path)[:100000]
            chapter_docs.append({
                '_index': self._chapter_index,
                '_id': ch.id,
                '_source': {
                    'id': ch.id,
                    'book_id': ch.book_id,
                    'chapter_number': ch.chapter_number,
                    'title': ch.title,
                    'content': content,
                    'word_count': ch.word_count,
                    'created_at': ch.created_at.isoformat() if ch.created_at else None,
                },
            })

        bulk_count = 0
        try:
            from elasticsearch.helpers import bulk
            if book_docs:
                success, errors = bulk(self._client, book_docs)
                bulk_count += success
                if errors:
                    logger.warning(f'[ESSearch] 书籍批量导入部分失败: {len(errors)} 条')
            if chapter_docs:
                success, errors = bulk(self._client, chapter_docs)
                bulk_count += success
                if errors:
                    logger.warning(f'[ESSearch] 章节批量导入部分失败: {len(errors)} 条')
        except Exception as e:
            logger.error(f'[ESSearch] 批量导入失败: {e}')

        elapsed = time.time() - start
        logger.info(f'[ESSearch] 索引重建完成: {len(book_docs)}本书, {len(chapter_docs)}章节, 成功导入{bulk_count}条, 耗时{elapsed:.2f}s')
        return {'books': len(book_docs), 'chapters': len(chapter_docs), 'imported': bulk_count, 'elapsed': round(elapsed, 2)}

    def refresh(self):
        if self.available:
            try:
                self._client.indices.refresh(index=[self._book_index, self._chapter_index])
            except Exception:
                pass


_service = None


def get_service():
    global _service
    if _service is None:
        _service = SearchService()
    return _service


def index_book(book):
    get_service().index_book(book)


def index_chapter(chapter):
    get_service().index_chapter(chapter)


def search(keyword, page=1, page_size=20):
    return get_service().search(keyword, page, page_size)


def delete_book(book_id):
    get_service().delete_book(book_id)


def rebuild_index():
    return get_service().rebuild_index()
