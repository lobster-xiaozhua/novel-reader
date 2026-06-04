import hashlib
import logging
import time
from collections import defaultdict
from threading import Lock

from django.core.cache import cache
from django.db.models import Count, Q

logger = logging.getLogger(__name__)

_cache_lock = Lock()
_ENGINE_CACHE_TTL = 600
_RESULT_CACHE_TTL = 300


class RecommendationEngine:
    _instance = None

    def __new__(cls):
        with _cache_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._books_cache = None
        self._tags_index = {}
        self._category_index = {}
        self._last_build = 0
        self._stats = {'cache_hits': 0, 'cache_misses': 0, 'total_queries': 0}

    def _cache_key(self, prefix, **kwargs):
        raw = f'{prefix}:{sorted(kwargs.items())}'
        return f'rec:{prefix}:{hashlib.md5(raw.encode()).hexdigest()[:12]}'

    def _get_cached(self, key):
        result = cache.get(key)
        if result is not None:
            self._stats['cache_hits'] += 1
        return result

    def _set_cached(self, key, value, ttl=_RESULT_CACHE_TTL):
        cache.set(key, value, ttl)
        self._stats['cache_misses'] += 1

    def build_index(self, force=False):
        from apps.books.models import Book
        now = time.time()
        if not force and self._books_cache and (now - self._last_build) < 300:
            return len(self._books_cache)

        logger.info('[Recommender] 构建推荐索引...')
        start = time.time()

        # 一次性获取所有书籍和标签，避免 N+1 查询
        books = list(
            Book.objects.prefetch_related('tags')
            .annotate(_ch_count=Count('chapters'))
            .values('id', 'title', 'author', 'category', 'total_chapters',
                    'description', 'created_at', 'updated_at', '_ch_count')
        )

        self._books_cache = books
        self._tags_index = defaultdict(list)
        self._category_index = defaultdict(list)

        # 直接从 prefetch_related 获取标签，不需要额外查询
        for book in books:
            bid = book['id']
            # 注意：values() + prefetch_related 不直接返回标签，需要单独获取
            # 这里用更高效的方式：一次性获取所有标签关系
            cat = book.get('category', '')
            if cat:
                self._category_index[cat].append(bid)

        # 一次性获取所有书籍的标签
        from apps.books.models import BookTag
        tag_map = defaultdict(list)
        for bt in BookTag.objects.select_related('tag').all():
            tag_map[bt.book_id].append(bt.tag.name)

        for book in books:
            bid = book['id']
            tags = tag_map.get(bid, [])
            for tag in tags:
                self._tags_index[tag].append(bid)

        self._last_build = now
        elapsed = time.time() - start
        logger.info(f'[Recommender] 索引构建完成: {len(books)}本书, 耗时{elapsed:.2f}s')
        return len(books)

    def _ensure_index(self):
        if not self._books_cache:
            self.build_index()

    def get_hot_recommendations(self, limit=20):
        from apps.books.models import Book

        cache_key = self._cache_key('hot', limit=limit)
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug(f'[Recommender] 命中缓存: {cache_key}')
            return cached

        self._ensure_index()

        books = Book.objects.prefetch_related('tags').annotate(
            _ch_count=Count('chapters'),
            _fav_count=Count('favorite'),
        ).order_by('-_fav_count', '-updated_at')[:limit]

        results = []
        for b in books:
            results.append(self._book_to_recommendation(b, reason='🔥 热门推荐'))

        self._set_cached(cache_key, results)
        return results

    def get_new_recommendations(self, limit=10):
        from apps.books.models import Book

        cache_key = self._cache_key('new', limit=limit)
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug(f'[Recommender] 命中缓存: {cache_key}')
            return cached

        self._ensure_index()

        books = Book.objects.prefetch_related('tags').annotate(
            _ch_count=Count('chapters'),
        ).order_by('-created_at')[:limit]

        results = []
        for b in books:
            results.append(self._book_to_recommendation(b, reason='✨ 新书上架'))

        self._set_cached(cache_key, results)
        return results

    def get_personalized_recommendations(self, user, limit=20):
        from apps.books.models import Book
        from apps.reader.models import ReadingProgress

        cache_key = self._cache_key('personalized', user_id=user.id if user and user.is_authenticated else 'anon', limit=limit)
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug(f'[Recommender] 命中个性化缓存: {cache_key}')
            return cached

        self._ensure_index()

        if not user or not user.is_authenticated:
            results = self.get_hot_recommendations(limit)
            self._set_cached(cache_key, results)
            return results

        # 使用 prefetch_related 避免 N+1
        read_books = ReadingProgress.objects.filter(user=user).select_related('book').prefetch_related('book__tags')[:20]
        read_tags = set()
        read_categories = set()
        for rp in read_books:
            for tag in rp.book.tags.all():
                read_tags.add(tag.name)
            if rp.book.category:
                read_categories.add(rp.book.category)

        if not read_tags and not read_categories:
            results = self.get_hot_recommendations(limit)
            self._set_cached(cache_key, results)
            return results

        qs = Book.objects.prefetch_related('tags').annotate(
            _ch_count=Count('chapters'),
        )

        tag_filter = Q(tags__name__in=read_tags) if read_tags else Q()
        cat_filter = Q(category__in=read_categories) if read_categories else Q()

        books = qs.filter(tag_filter | cat_filter).distinct().order_by('-updated_at')[:limit * 2]

        results = []
        seen = set()
        for b in books:
            if b.id in seen:
                continue
            seen.add(b.id)
            results.append(self._book_to_recommendation(b, reason='🎯 猜你喜欢'))
            if len(results) >= limit:
                break

        if len(results) < limit:
            remaining = self.get_hot_recommendations(limit - len(results))
            existing_ids = {r['id'] for r in results}
            for r in remaining:
                if r['id'] not in existing_ids:
                    results.append(r)

        self._set_cached(cache_key, results)
        return results

    def get_similar_books(self, book_id, limit=6):
        from apps.books.models import Book

        cache_key = self._cache_key('similar', book_id=book_id, limit=limit)
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug(f'[Recommender] 命中相似缓存: {cache_key}')
            return cached

        self._ensure_index()

        try:
            target = Book.objects.prefetch_related('tags').get(id=book_id)
        except Book.DoesNotExist:
            return []

        target_tags = {t.name for t in target.tags.all()}
        target_cat = target.category

        if not target_tags and not target_cat:
            results = self.get_hot_recommendations(limit)
            self._set_cached(cache_key, results)
            return results

        # 限制候选集大小，避免全表扫描
        candidate_ids = set()
        for tag in target_tags:
            candidate_ids.update(self._tags_index.get(tag, [])[:50])
        if target_cat:
            candidate_ids.update(self._category_index.get(target_cat, [])[:50])
        candidate_ids.discard(book_id)

        if not candidate_ids:
            results = self.get_hot_recommendations(limit)
            self._set_cached(cache_key, results)
            return results

        qs = Book.objects.prefetch_related('tags').annotate(
            _ch_count=Count('chapters'),
        ).filter(id__in=list(candidate_ids)[:100])

        candidates = []
        for b in qs:
            book_tags = {t.name for t in b.tags.all()}
            tag_sim = len(target_tags & book_tags) / max(len(target_tags), 1)
            cat_sim = 1.0 if b.category == target_cat and target_cat else 0.0
            author_sim = 0.5 if b.author == target.author and target.author else 0.0
            score = tag_sim * 0.5 + cat_sim * 0.3 + author_sim * 0.2
            if score > 0:
                candidates.append((b, score))

        candidates.sort(key=lambda x: x[1], reverse=True)

        results = []
        for b, score in candidates[:limit]:
            pct = round(score * 100, 1)
            results.append(self._book_to_recommendation(
                b, reason=f'📚 相似度 {pct}%', score=pct
            ))

        self._set_cached(cache_key, results)
        return results

    def get_hybrid_recommendations(self, user=None, limit=30):
        hot_count = int(limit * 0.6)
        new_count = int(limit * 0.4)

        hot = self.get_hot_recommendations(hot_count)
        new = self.get_new_recommendations(new_count)

        seen = set()
        results = []
        for rec in hot + new:
            if rec['id'] not in seen:
                seen.add(rec['id'])
                results.append(rec)

        return results[:limit]

    def invalidate_cache(self, pattern=None):
        """安全清除缓存，兼容所有缓存后端"""
        try:
            if pattern:
                # 尝试使用 keys/delete_pattern（Redis 支持）
                if hasattr(cache, 'keys'):
                    keys = cache.keys(f'rec:{pattern}:*')
                    for k in keys:
                        cache.delete(k)
                else:
                    # 降级：直接删除特定 key
                    cache.delete(f'rec:{pattern}')
            else:
                if hasattr(cache, 'delete_pattern'):
                    cache.delete_pattern('rec:*')
                else:
                    # 降级：清空整个缓存
                    cache.clear()
            logger.info(f'[Recommender] 缓存已清除: {pattern or "all"}')
        except Exception as e:
            logger.warning(f'[Recommender] 缓存清除失败: {e}')

    def get_stats(self):
        total = self._stats['cache_hits'] + self._stats['cache_misses']
        hit_rate = (self._stats['cache_hits'] / total * 100) if total > 0 else 0
        return {
            'cache_hits': self._stats['cache_hits'],
            'cache_misses': self._stats['cache_misses'],
            'cache_hit_rate': f'{hit_rate:.1f}%',
            'total_queries': total,
            'index_size': len(self._books_cache) if self._books_cache else 0,
        }

    def _book_to_recommendation(self, book, reason='', score=0):
        from django.utils import timezone
        tags = [{'id': t.id, 'name': t.name, 'color': t.color} for t in book.tags.all()]
        ch_count = getattr(book, '_ch_count', None) or book.total_chapters or 0
        is_new = False
        if book.created_at:
            delta = timezone.now() - book.created_at
            is_new = delta.days <= 7

        return {
            'id': book.id,
            'title': book.title,
            'author': book.author or '未知作者',
            'category': book.category or '',
            'description': book.description or '暂无简介',
            'tags': tags,
            'gradient': book.cover_gradient,
            'chapter_count': ch_count,
            'reason': reason,
            'score': score,
            'is_new': is_new,
            'updated_at': book.updated_at.isoformat() if book.updated_at else '',
            'created_at': book.created_at.isoformat() if book.created_at else '',
        }


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = RecommendationEngine()
    return _engine


def recommend_for_user(user=None, limit=30, strategy='hybrid'):
    engine = get_engine()
    if strategy == 'hot':
        return engine.get_hot_recommendations(limit)
    elif strategy == 'new':
        return engine.get_new_recommendations(limit)
    elif strategy == 'personalized':
        return engine.get_personalized_recommendations(user, limit)
    else:
        return engine.get_hybrid_recommendations(user, limit)


def recommend_similar_books(book_id, limit=6):
    engine = get_engine()
    return engine.get_similar_books(book_id, limit)
