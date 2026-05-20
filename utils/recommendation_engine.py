import logging
from collections import defaultdict
from django.db.models import Q, Count
from django.core.cache import cache
from apps.books.models import Book
from apps.favorites.models import Favorite
from apps.reader.models import ReadingSession
from apps.reviews.models import BookRating

logger = logging.getLogger(__name__)


class RecommendationEngine:
    CACHE_TIMEOUT = 1800
    MAX_RECOMMENDATIONS = 10

    def __init__(self, user=None):
        self.user = user
        self.cache_prefix = f"recommendations_{user.id}" if user else "global_recommendations"
        self.user_preferences = None

    def _get_cache(self, key):
        return cache.get(f"{self.cache_prefix}_{key}")

    def _set_cache(self, key, value, timeout=None):
        timeout = timeout or self.CACHE_TIMEOUT
        cache.set(f"{self.cache_prefix}_{key}", value, timeout)

    def _invalidate_cache(self):
        cache.delete_pattern(f"{self.cache_prefix}_*")

    def get_content_based_recommendations(self, book_id=None, limit=None):
        limit = limit or self.MAX_RECOMMENDATIONS
        cache_key = f"content_{book_id}_{limit}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        if book_id:
            try:
                source_book = Book.objects.get(id=book_id)
                books = (
                    Book.objects.filter(Q(author=source_book.author) | Q(category=source_book.category))
                    .exclude(id=book_id)
                    .distinct()[:limit]
                )
                recommendations = list(books)
            except Book.DoesNotExist:
                recommendations = []
        elif self.user:
            favorites = Favorite.objects.filter(user=self.user).select_related("book").values_list("book_id", flat=True)
            if not favorites:
                recommendations = self._get_popular_books(limit)
                self._set_cache(cache_key, recommendations)
                return recommendations
            favorite_books = Book.objects.filter(id__in=favorites)
            authors = set(favorite_books.values_list("author", flat=True))
            categories = set(favorite_books.values_list("category", flat=True))
            books = (
                Book.objects.filter(Q(author__in=authors) | Q(category__in=categories))
                .exclude(id__in=favorites)
                .distinct()[:limit]
            )
            recommendations = list(books)
        else:
            recommendations = self._get_popular_books(limit)

        self._set_cache(cache_key, recommendations)
        return recommendations

    def get_collaborative_recommendations(self, limit=None):
        if not self.user:
            return self._get_popular_books(limit or self.MAX_RECOMMENDATIONS)

        limit = limit or self.MAX_RECOMMENDATIONS
        cache_key = f"collaborative_{limit}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        user_favorites = set(Favorite.objects.filter(user=self.user).values_list("book_id", flat=True))
        user_reading_books = set(ReadingSession.objects.filter(user=self.user).values_list("book_id", flat=True))
        user_books = user_favorites | user_reading_books

        if len(user_books) < 2:
            return self.get_content_based_recommendations(limit=limit)

        similar_users = self._find_similar_users(user_books, limit=20)
        if not similar_users:
            return self.get_content_based_recommendations(limit=limit)

        book_scores = defaultdict(float)
        for similar_user_id, similarity_score in similar_users:
            similar_user_favorites = Favorite.objects.filter(user_id=similar_user_id).values_list("book_id", flat=True)
            for book_id in similar_user_favorites:
                if book_id not in user_books:
                    book_scores[book_id] += similarity_score

        if not book_scores:
            return self.get_content_based_recommendations(limit=limit)

        top_book_ids = sorted(book_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        book_ids = [book_id for book_id, _ in top_book_ids]
        recommendations = list(Book.objects.filter(id__in=book_ids))

        recommendations.sort(key=lambda x: book_ids.index(x.id))
        self._set_cache(cache_key, recommendations)
        return recommendations

    def get_hybrid_recommendations(self, limit=None):
        limit = limit or self.MAX_RECOMMENDATIONS
        cache_key = f"hybrid_{limit}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        content_recs = self.get_content_based_recommendations(limit=limit * 2)
        collaborative_recs = self.get_collaborative_recommendations(limit=limit * 2)

        all_books = {}
        for i, book in enumerate(content_recs):
            score = (len(content_recs) - i) * 0.4
            if book.id in all_books:
                all_books[book.id]["score"] += score
                all_books[book.id]["book"] = book
            else:
                all_books[book.id] = {"score": score, "book": book}

        for i, book in enumerate(collaborative_recs):
            score = (len(collaborative_recs) - i) * 0.6
            if book.id in all_books:
                all_books[book.id]["score"] += score
            else:
                all_books[book.id] = {"score": score, "book": book}

        sorted_books = sorted(all_books.items(), key=lambda x: x[1]["score"], reverse=True)[:limit]
        recommendations = [item["book"] for _, item in sorted_books]

        self._set_cache(cache_key, recommendations)
        return recommendations

    def get_personalized_recommendations(self, limit=None):
        if not self.user:
            return self._get_popular_books(limit or self.MAX_RECOMMENDATIONS)

        limit = limit or self.MAX_RECOMMENDATIONS
        cache_key = f"personalized_{limit}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        user_categories = (
            Favorite.objects.filter(user=self.user).select_related("book").values_list("book__category", flat=True)
        )
        user_authors = (
            Favorite.objects.filter(user=self.user).select_related("book").values_list("book__author", flat=True)
        )

        high_rated_books = (
            Book.objects.filter(ratings__rating__gte=4)
            .annotate(avg_rating=Count("ratings"))
            .order_by("-ratings__rating", "-avg_rating")[:limit]
        )

        recommendations = []
        for book in high_rated_books:
            category_match = book.category in user_categories if book.category else False
            author_match = book.author in user_authors if book.author else False
            if category_match or author_match:
                recommendations.append(book)

        if len(recommendations) < limit:
            additional = (
                Book.objects.exclude(id__in=[r.id for r in recommendations])
                .filter(Q(category__in=user_categories) | Q(author__in=user_authors))
                .distinct()[: limit - len(recommendations)]
            )
            recommendations.extend(list(additional))

        self._set_cache(cache_key, recommendations)
        return recommendations

    def _find_similar_users(self, user_books, limit=20):
        similar_users = []
        favorite_counts = (
            Favorite.objects.filter(book_id__in=user_books)
            .values("user_id")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit]
        )

        total_books = len(user_books)
        for item in favorite_counts:
            if item["user_id"] != (self.user.id if self.user else None):
                similarity = item["count"] / total_books if total_books > 0 else 0
                similar_users.append((item["user_id"], similarity))

        return similar_users

    def _get_popular_books(self, limit=None):
        limit = limit or self.MAX_RECOMMENDATIONS
        cache_key = f"popular_{limit}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        books = Book.objects.annotate(favorite_count=Count("favorite"), rating_count=Count("ratings")).order_by(
            "-favorite_count", "-rating_count"
        )[:limit]

        recommendations = list(books)
        self._set_cache(cache_key, recommendations, timeout=3600)
        return recommendations

    def refresh_recommendations(self):
        self._invalidate_cache()
        logger.info(f'推荐缓存已刷新: 用户={self.user.username if self.user else "全局"}')
