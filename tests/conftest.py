import pytest
from django.contrib.auth.models import User
from apps.books.models import Book
from apps.chapters.models import Chapter


@pytest.fixture
def user(db):
    return User.objects.create_user('testuser', 'test@example.com', 'testpass123')


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser('admin', 'admin@example.com', 'adminpass123')


@pytest.fixture
def client():
    from django.test import Client
    return Client()


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def book(db):
    return Book.objects.create(
        title='测试小说',
        author='测试作者',
        folder_path='data/books/test_book',
        description='这是一本测试用的小说',
    )


@pytest.fixture
def chapter(book, tmp_path):
    chapter_file = tmp_path / '第1章.txt'
    chapter_file.write_text('第一章 测试章节\n\n这是测试内容。', encoding='utf-8')
    return Chapter.objects.create(
        book=book,
        chapter_number=1,
        title='第一章 测试章节',
        file_path=str(chapter_file),
        word_count=100,
    )
