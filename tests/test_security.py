import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from utils.security import RateLimiter, SecurityValidator, InputValidator
from apps.books.models import Book


@pytest.mark.django_db
class RateLimiterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_rate_limit_check(self):
        identifier = "test_user_1"
        allowed, info = RateLimiter.check_rate_limit(identifier, "authenticated")

        self.assertTrue(allowed)
        self.assertIn("limit", info)
        self.assertIn("remaining", info)

    def test_rate_limit_exceeded(self):
        identifier = "test_user_limit"
        from utils.security import RateLimiter
        from django.core.cache import cache

        cache.clear()

        for _ in range(100):
            RateLimiter.check_rate_limit(identifier, "authenticated")

        allowed, info = RateLimiter.check_rate_limit(identifier, "authenticated")
        self.assertFalse(allowed)
        self.assertEqual(info["remaining"], 0)


class SecurityValidatorTest(TestCase):
    def test_validate_safe_url(self):
        is_valid, message = SecurityValidator.validate_url("https://example.com/novel/123")
        self.assertTrue(is_valid)

    def test_validate_localhost_url(self):
        is_valid, message = SecurityValidator.validate_url("http://localhost:8000/")
        self.assertFalse(is_valid)

    def test_validate_private_ip(self):
        is_valid, message = SecurityValidator.validate_url("http://192.168.1.1/")
        self.assertFalse(is_valid)

    def test_sanitize_input(self):
        text = '  <script>alert("xss")</script>  Hello World  '
        sanitized = SecurityValidator.sanitize_input(text)
        self.assertNotIn("<script>", sanitized)
        self.assertIn("Hello World", sanitized)

    def test_sanitize_long_text(self):
        long_text = "a" * 10000
        sanitized = SecurityValidator.sanitize_input(long_text, max_length=5000)
        self.assertEqual(len(sanitized), 5000)


class InputValidatorTest(TestCase):
    def test_validate_book_data_valid(self):
        data = {
            "title": "Test Book",
            "author": "Test Author",
            "category": "Fiction",
            "description": "A test book description",
        }
        errors = InputValidator.validate_book_data(data)
        self.assertIsNone(errors)

    def test_validate_book_data_invalid_title(self):
        data = {"title": "", "author": "Test Author"}
        errors = InputValidator.validate_book_data(data)
        self.assertIn("title", errors)

    def test_validate_book_data_title_too_long(self):
        data = {"title": "a" * 201, "author": "Test Author"}
        errors = InputValidator.validate_book_data(data)
        self.assertIn("title", errors)

    def test_validate_review_data_valid(self):
        data = {"content": "This is a great book with amazing plot and characters!", "rating": 5}
        errors = InputValidator.validate_review_data(data)
        self.assertIsNone(errors)

    def test_validate_review_data_short_content(self):
        data = {"content": "Good!", "rating": 4}
        errors = InputValidator.validate_review_data(data)
        self.assertIn("content", errors)

    def test_validate_review_data_invalid_rating(self):
        data = {"content": "This is a valid review content for testing.", "rating": 10}
        errors = InputValidator.validate_review_data(data)
        self.assertIn("rating", errors)

    def test_validate_note_data_valid(self):
        data = {"content": "This is my note about an important plot point in the book."}
        errors = InputValidator.validate_note_data(data)
        self.assertIsNone(errors)

    def test_validate_note_data_empty(self):
        data = {"content": ""}
        errors = InputValidator.validate_note_data(data)
        self.assertIn("content", errors)
