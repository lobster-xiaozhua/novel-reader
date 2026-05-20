import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from apps.books.models import Book
from apps.chapters.models import Chapter
from apps.reader.models import ReadingSession, ReadingStatistics, ReadingGoal
from apps.reader.services import ReadingStatisticsService
from datetime import date, timedelta


@pytest.mark.django_db
class ReadingStatisticsServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.book = Book.objects.create(title="Test Book", author="Test Author", folder_path="/tmp/test_book")
        self.chapter = Chapter.objects.create(
            book=self.book,
            chapter_number=1,
            title="Chapter 1",
            file_path="/tmp/test_book/chapter1.txt",
            word_count=3000,
        )
        self.service = ReadingStatisticsService(self.user)

    def test_track_reading_session(self):
        session = self.service.track_reading_session(
            book=self.book,
            chapter=self.chapter,
            words_read=1000,
            duration_seconds=300,
            start_position=0,
            end_position=1000,
        )
        self.assertIsNotNone(session)
        self.assertEqual(session.words_read, 1000)
        self.assertEqual(session.duration_seconds, 300)
        self.assertGreater(session.reading_speed, 0)

    def test_get_today_summary(self):
        self.service.track_reading_session(book=self.book, chapter=self.chapter, words_read=1000, duration_seconds=300)
        summary = self.service.get_today_summary()
        self.assertEqual(summary["total_words"], 1000)
        self.assertEqual(summary["total_time"], 300)

    def test_create_goal(self):
        goal = self.service.create_goal(
            goal_type="words", target_value=10000, start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        self.assertEqual(goal.target_value, 10000)
        self.assertEqual(goal.goal_type, "words")
        self.assertTrue(goal.is_active)

    def test_update_goals(self):
        goal = self.service.create_goal(goal_type="words", target_value=5000)
        self.service.update_goals(words_read=3000)
        goal.refresh_from_db()
        self.assertEqual(goal.current_value, 3000)

    def test_get_streak_info(self):
        streak_info = self.service.get_streak_info()
        self.assertIn("current_streak", streak_info)
        self.assertIn("longest_streak", streak_info)


@pytest.mark.django_db
class ReadingSessionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser2", password="testpass")
        self.book = Book.objects.create(title="Test Book 2", author="Author 2", folder_path="/tmp/test_book2")
        self.chapter = Chapter.objects.create(
            book=self.book,
            chapter_number=1,
            title="Chapter 1",
            file_path="/tmp/test_book2/chapter1.txt",
            word_count=5000,
        )

    def test_reading_speed_calculation(self):
        session = ReadingSession.objects.create(
            user=self.user, book=self.book, chapter=self.chapter, words_read=2000, duration_seconds=600
        )
        expected_speed = (2000 / 600) * 60
        self.assertAlmostEqual(session.reading_speed, expected_speed, places=1)

    def test_reading_session_ordering(self):
        session1 = ReadingSession.objects.create(
            user=self.user, book=self.book, chapter=self.chapter, words_read=1000, duration_seconds=300
        )
        session2 = ReadingSession.objects.create(
            user=self.user, book=self.book, chapter=self.chapter, words_read=2000, duration_seconds=600
        )
        sessions = ReadingSession.objects.filter(user=self.user)
        self.assertEqual(sessions[0], session2)


@pytest.mark.django_db
class ReadingGoalModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser3", password="testpass")

    def test_progress_percentage(self):
        goal = ReadingGoal.objects.create(
            user=self.user,
            goal_type="words",
            target_value=10000,
            current_value=5000,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        self.assertEqual(goal.progress_percentage, 50.0)

    def test_check_completion(self):
        goal = ReadingGoal.objects.create(
            user=self.user,
            goal_type="words",
            target_value=5000,
            current_value=5000,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        self.assertTrue(goal.check_completion())
        self.assertTrue(goal.is_completed)
        self.assertFalse(goal.is_active)

    def test_update_progress(self):
        goal = ReadingGoal.objects.create(
            user=self.user,
            goal_type="words",
            target_value=5000,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        goal.current_value = 3000
        goal.save()
        goal.refresh_from_db()
        self.assertEqual(goal.current_value, 3000)
        self.assertFalse(goal.is_completed)
        goal.current_value = 5000
        goal.save()
        goal.refresh_from_db()
        self.assertEqual(goal.current_value, 5000)
        self.assertTrue(goal.check_completion())
        self.assertTrue(goal.is_completed)
        self.assertFalse(goal.is_active)
