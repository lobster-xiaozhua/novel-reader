import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from apps.books.models import Book
from apps.favorites.models import Favorite
from apps.reader.models import ReadingSession
from apps.reviews.models import BookRating
from utils.recommendation_engine import RecommendationEngine


@pytest.mark.django_db
class RecommendationEngineTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.book1 = Book.objects.create(
            title="Science Fiction 1", author="Author A", category="Sci-Fi", folder_path="/tmp/book1"
        )
        self.book2 = Book.objects.create(
            title="Science Fiction 2", author="Author A", category="Sci-Fi", folder_path="/tmp/book2"
        )
        self.book3 = Book.objects.create(
            title="Fantasy Novel", author="Author B", category="Fantasy", folder_path="/tmp/book3"
        )
        self.book4 = Book.objects.create(
            title="Horror Story", author="Author C", category="Horror", folder_path="/tmp/book4"
        )

    def test_content_based_recommendations(self):
        engine = RecommendationEngine(user=self.user)

        Favorite.objects.create(user=self.user, book=self.book1)

        recs = engine.get_content_based_recommendations()
        book_ids = [r.id for r in recs]

        self.assertIn(self.book2.id, book_ids)
        self.assertNotIn(self.book1.id, book_ids)
        self.assertNotIn(self.book4.id, book_ids)

    def test_content_based_with_author(self):
        engine = RecommendationEngine(user=self.user)

        recs = engine.get_content_based_recommendations(book_id=self.book1.id)
        book_ids = [r.id for r in recs]

        self.assertIn(self.book2.id, book_ids)

    def test_popular_books(self):
        Favorite.objects.create(user=self.user, book=self.book1)
        Favorite.objects.create(user=self.user, book=self.book2)

        other_user = User.objects.create_user(username="otheruser", password="testpass")
        Favorite.objects.create(user=other_user, book=self.book1)
        Favorite.objects.create(user=other_user, book=self.book2)
        Favorite.objects.create(user=other_user, book=self.book3)

        engine = RecommendationEngine(user=None)
        popular = engine._get_popular_books(limit=3)
        book_ids = [r.id for r in popular]

        self.assertIn(self.book1.id, book_ids)
        self.assertIn(self.book2.id, book_ids)
        self.assertIn(self.book3.id, book_ids)

    def test_collaborative_recommendations(self):
        user1 = User.objects.create_user(username="user1", password="testpass")
        user2 = User.objects.create_user(username="user2", password="testpass")

        Favorite.objects.create(user=user1, book=self.book1)
        Favorite.objects.create(user=user1, book=self.book2)
        Favorite.objects.create(user=user2, book=self.book1)
        Favorite.objects.create(user=user2, book=self.book2)
        Favorite.objects.create(user=user2, book=self.book3)

        engine = RecommendationEngine(user=user1)
        recs = engine.get_collaborative_recommendations()
        book_ids = [r.id for r in recs]

        self.assertIn(self.book3.id, book_ids)
        self.assertNotIn(self.book1.id, book_ids)

    def test_hybrid_recommendations(self):
        Favorite.objects.create(user=self.user, book=self.book1)
        BookRating.objects.create(user=self.user, book=self.book1, rating=5)

        engine = RecommendationEngine(user=self.user)
        recs = engine.get_hybrid_recommendations()
        self.assertIsInstance(recs, list)


@pytest.mark.django_db
class BookRatingModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.book = Book.objects.create(title="Test Book", author="Test Author", folder_path="/tmp/test_book")

    def test_rating_creation(self):
        rating = BookRating.objects.create(user=self.user, book=self.book, rating=5)
        self.assertEqual(rating.rating, 5)
        self.assertEqual(str(rating), f"{self.user.username} - {self.book.title} - 5星")

    def test_rating_validation(self):
        from django.core.exceptions import ValidationError

        rating = BookRating(user=self.user, book=self.book, rating=6)
        with self.assertRaises(ValueError):
            rating.save()

    def test_unique_user_book(self):
        BookRating.objects.create(user=self.user, book=self.book, rating=5)
        with self.assertRaises(Exception):
            BookRating.objects.create(user=self.user, book=self.book, rating=4)
