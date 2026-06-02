import hashlib
import logging
import time
from collections import defaultdict
from threading import Lock

from django.core.cache import cache

logger = logging.getLogger(__name__)

_search_lock = Lock()
_SEARCH_RESULT_TTL = 300
_SEARCH_STATS_TTL = 60


class HybridSearchEngine:
    _instance = None

    def __new__(cls):
        with _search_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._books_index = {}
        self._chapters_index = {}
        self.is_ready = False
        self.total_books = 0
        self.total_chapters = 0
        self._perf_stats = {'total_searches': 0, 'cache_hits': 0, 'total_ms': 0}

    def _cache_key(self, query, limit):
        raw = f'search:{query.lower().strip()}:{limit}'
        return f'srch:{hashlib.md5(raw.encode()).hexdigest()[:12]}'

    def _get_stats_key(self):
        return 'search:perf_stats'

    def build_index(self, force=False):
        from apps.books.models import Book
        from apps.chapters.models import Chapter

        cache_key = 'search:engine:built'
        if not force and cache.get(cache_key) and self.is_ready:
            return self.total_books

        logger.info('[SearchEngine] 构建搜索索引...')
        start = time.time()

        books = Book.objects.prefetch_related('tags').all()
        self._books_index = {}
        self._chapters_index = {}
        total_ch = 0

        for book in books:
            self._books_index[book.id] = {
                'id': book.id,
                'title': book.title,
                'title_lower': book.title.lower(),
                'author': book.author or '',
                'author_lower': (book.author or '').lower(),
                'category': book.category or '',
                'description': book.description or '',
                'description_lower': (book.description or '').lower(),
                'tags': [t.name for t in book.tags.all()],
            }

            chapters = Chapter.objects.filter(book=book).order_by('chapter_number')
            book_chapters = {}
            for ch in chapters:
                content = self._read_chapter_file(ch.file_path)
                if content:
                    content = content[:5000]
                    book_chapters[ch.id] = {
                        'id': ch.id,
                        'title': ch.title,
                        'title_lower': ch.title.lower(),
                        'content': content,
                        'content_lower': content.lower(),
                        'content_length': len(content),
                        'chapter_number': ch.chapter_number,
                    }
                    total_ch += 1

            self._chapters_index[book.id] = book_chapters

        self.total_books = len(self._books_index)
        self.total_chapters = total_ch
        self.is_ready = True
        cache.set(cache_key, True, 600)

        elapsed = time.time() - start
        logger.info(f'[SearchEngine] 索引构建完成: {self.total_books}本书, {self.total_chapters}章, 耗时{elapsed:.2f}s')
        return self.total_books

    def _read_chapter_file(self, file_path):
        import os
        from django.conf import settings
        if not file_path:
            return ''
        norm = os.path.normpath(file_path)
        root = os.path.normpath(str(settings.BOOKS_DIR))
        if not norm.startswith(root):
            return ''
        if not os.path.exists(norm):
            return ''
        for enc in ('utf-8', 'gbk', 'gb2312'):
            try:
                with open(norm, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, Exception):
                continue
        return ''

    def search(self, query, limit=50):
        self._ensure_index()
        if not query or not self.is_ready:
            return []

        cache_key = self._cache_key(query, limit)
        cached = cache.get(cache_key)
        if cached is not None:
            self._perf_stats['cache_hits'] += 1
            logger.debug(f'[SearchEngine] 命中缓存: {query}')
            return cached

        start = time.time()
        query_lower = query.lower()
        query_terms = self._expand_query(query)

        book_scores = defaultdict(float)
        book_matches = defaultdict(lambda: {
            'chapters': [],
            'chapter_ids': set(),
            'match_reasons': [],
        })

        for book_id, book in self._books_index.items():
            book_score = 0

            for term in query_terms:
                tl = term.lower()
                if tl in book['title_lower']:
                    count = book['title_lower'].count(tl)
                    book_score += 10 + min(count * 2, 10)
                    book_matches[book_id]['match_reasons'].append('书名匹配')

                if tl in book['author_lower']:
                    book_score += 8
                    book_matches[book_id]['match_reasons'].append('作者匹配')

                if tl in book['description_lower']:
                    count = book['description_lower'].count(tl)
                    book_score += count * 3
                    book_matches[book_id]['match_reasons'].append('简介匹配')

                for tag in book.get('tags', []):
                    if tl in tag.lower():
                        book_score += 6
                        book_matches[book_id]['match_reasons'].append('标签匹配')
                        break

            chapters = self._chapters_index.get(book_id, {})
            for ch_id, chapter in chapters.items():
                ch_score = 0
                for term in query_terms:
                    tl = term.lower()
                    if tl in chapter.get('title_lower', ''):
                        ch_score += 15
                    if tl in chapter.get('content_lower', ''):
                        count = chapter['content_lower'].count(tl)
                        ch_score += count * 5
                        pos = chapter['content_lower'].find(tl)
                        pos_ratio = pos / max(chapter.get('content_length', 1), 1)
                        ch_score += int((1 - pos_ratio) * 10)

                if ch_score > 0:
                    preview = self._get_preview(chapter.get('content', ''), query)
                    book_matches[book_id]['chapters'].append({
                        'id': chapter['id'],
                        'title': chapter.get('title', ''),
                        'score': ch_score,
                        'content_preview': preview,
                        'chapter_number': chapter.get('chapter_number', 0),
                    })
                    book_score += ch_score

            if book_score > 0:
                book_scores[book_id] = book_score

        results = []
        for book_id, score in sorted(book_scores.items(), key=lambda x: x[1], reverse=True)[:limit]:
            book = self._books_index.get(book_id, {})
            matches = book_matches.get(book_id, {})
            matched_chapters = sorted(matches.get('chapters', []), key=lambda x: x['score'], reverse=True)[:3]

            results.append({
                'id': book_id,
                'book_id': book_id,
                'title': book.get('title', ''),
                'author': book.get('author', ''),
                'category': book.get('category', ''),
                'description': book.get('description', ''),
                'tags': book.get('tags', []),
                'total_score': score,
                'matched_chapters': matched_chapters,
                'total_matches': len(matches.get('chapters', [])),
                'match_reasons': list(set(matches.get('match_reasons', [])))[:3],
            })

        elapsed = time.time() - start
        elapsed_ms = int(elapsed * 1000)
        self._perf_stats['total_searches'] += 1
        self._perf_stats['total_ms'] += elapsed_ms

        logger.info(f'[SearchEngine] 搜索 "{query}": {len(results)}本书, 耗时{elapsed_ms}ms')

        cache.set(cache_key, results, _SEARCH_RESULT_TTL)
        return results

    def _expand_query(self, query):
        terms = [query]
        synonyms = {
            '科幻': ['三体', '刘慈欣', '未来'],
            '悬疑': ['推理', '东野圭吾', '侦探'],
            '经典': ['名著', '文学'],
            '爱情': ['言情', '浪漫'],
            '武侠': ['江湖', '功夫'],
            '修仙': ['仙侠', '修真'],
        }
        for key, syns in synonyms.items():
            if key in query:
                terms.extend(syns)
            for s in syns:
                if s in query:
                    terms.append(key)
                    break
        return list(set(terms))

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

    def _ensure_index(self):
        if not self.is_ready:
            self.build_index()

    def invalidate_cache(self, query=None):
        if query:
            key = self._cache_key(query, 50)
            cache.delete(key)
            logger.info(f'[SearchEngine] 缓存已清除: {query}')
        else:
            cache.delete_pattern('srch:*')
            logger.info('[SearchEngine] 搜索缓存已全部清除')

    def get_stats(self):
        stats = cache.get(self._get_stats_key())
        if stats:
            return stats

        total = self._perf_stats['total_searches']
        cache_hits = self._perf_stats['cache_hits']
        avg_ms = (self._perf_stats['total_ms'] / total) if total > 0 else 0

        stats = {
            'total_books': self.total_books,
            'total_chapters': self.total_chapters,
            'is_ready': self.is_ready,
            'total_searches': total,
            'cache_hits': cache_hits,
            'cache_misses': total - cache_hits,
            'avg_response_ms': round(avg_ms, 1),
        }
        cache.set(self._get_stats_key(), stats, _SEARCH_STATS_TTL)
        return stats


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = HybridSearchEngine()
    return _engine


def search(query, limit=50):
    engine = get_engine()
    return engine.search(query, limit)


def build_index(force=False):
    engine = get_engine()
    return engine.build_index(force)


def get_stats():
    engine = get_engine()
    return engine.get_stats()


def invalidate_cache(query=None):
    engine = get_engine()
    return engine.invalidate_cache(query)
