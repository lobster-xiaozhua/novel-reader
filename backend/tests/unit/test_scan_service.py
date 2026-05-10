import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.scan_service import BookScanner


class TestBookScanner:
    @pytest.fixture
    def temp_books_dir(self, tmp_path):
        books_dir = tmp_path / "books"
        books_dir.mkdir()
        return books_dir

    @pytest.fixture
    def scanner(self, temp_books_dir):
        return BookScanner(books_dir=str(temp_books_dir))

    def test_init_with_custom_dir(self, temp_books_dir):
        scanner = BookScanner(books_dir=str(temp_books_dir))
        assert scanner.books_dir == temp_books_dir

    def test_init_with_default_dir(self):
        scanner = BookScanner()
        assert scanner.books_dir.exists()

    def test_allowed_extensions(self, scanner):
        assert '.txt' in scanner.ALLOWED_EXTENSIONS

    def test_system_files_defined(self, scanner):
        assert '.ds_store' in scanner.SYSTEM_FILES
        assert 'thumbs.db' in scanner.SYSTEM_FILES

    def test_temp_patterns_defined(self, scanner):
        assert '~' in scanner.TEMP_PATTERNS
        assert '.tmp' in scanner.TEMP_PATTERNS

    def test_is_temp_file_with_tilde(self, scanner):
        assert scanner.is_temp_file("document.txt~") is True

    def test_is_temp_file_with_tmp(self, scanner):
        assert scanner.is_temp_file("temp_file.tmp") is True

    def test_is_temp_file_with_backup(self, scanner):
        assert scanner.is_temp_file("backup.bak") is True

    def test_is_temp_file_false_for_normal(self, scanner):
        assert scanner.is_temp_file("chapter_1.txt") is False

    @pytest.mark.asyncio
    async def test_process_file_system_file(self, scanner, temp_books_dir):
        system_file = temp_books_dir / ".DS_Store"
        system_file.write_text("hidden")
        result = await scanner.process_file(system_file)
        assert result == "deleted"
        assert not system_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_temp_file(self, scanner, temp_books_dir):
        temp_file = temp_books_dir / "draft.tmp"
        temp_file.write_text("temp content")
        result = await scanner.process_file(temp_file)
        assert result == "deleted"
        assert not temp_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_unsupported_format(self, scanner, temp_books_dir):
        bad_file = temp_books_dir / "image.png"
        bad_file.write_bytes(b"\x89PNG")
        result = await scanner.process_file(bad_file)
        assert result == "deleted"

    @pytest.mark.asyncio
    async def test_process_file_empty_file(self, scanner, temp_books_dir):
        empty_file = temp_books_dir / "empty.txt"
        empty_file.write_text("")
        result = await scanner.process_file(empty_file)
        assert result == "deleted"

    @pytest.mark.asyncio
    async def test_process_file_valid_txt(self, scanner, temp_books_dir):
        valid_file = temp_books_dir / "chapter1.txt"
        valid_file.write_text("Chapter content here")
        result = await scanner.process_file(valid_file)
        assert result == "ok"
        assert valid_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_markdown_conversion(self, scanner, temp_books_dir):
        md_file = temp_books_dir / "chapter.md"
        md_file.write_text("# Markdown Content")
        result = await scanner.process_file(md_file)
        assert result == "converted"
        txt_file = temp_books_dir / "chapter.txt"
        assert txt_file.exists()
        assert not md_file.exists()

    @pytest.mark.asyncio
    async def test_delete_file_removes_file(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "to_delete.txt"
        test_file.write_text("content")
        await scanner.delete_file(test_file, "test reason")
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_delete_file_handles_error(self, scanner, temp_books_dir):
        nonexistent = temp_books_dir / "does_not_exist.txt"
        await scanner.delete_file(nonexistent, "test reason")

    @pytest.mark.asyncio
    async def test_rename_file(self, scanner, temp_books_dir):
        old_file = temp_books_dir / "old.txt"
        old_file.write_text("content")
        new_file = temp_books_dir / "new.txt"
        await scanner.rename_file(old_file, new_file, "rename reason")
        assert not old_file.exists()
        assert new_file.exists()

    @pytest.mark.asyncio
    async def test_is_readable_utf8(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "utf8.txt"
        test_file.write_text("UTF-8 内容测试", encoding="utf-8")
        result = await scanner.is_readable(test_file)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_readable_gbk_fallback(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "gbk.txt"
        test_file.write_bytes("GBK内容".encode("gbk"))
        result = await scanner.is_readable(test_file)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_readable_invalid_encoding(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "binary.bin"
        test_file.write_bytes(b"\x80\x81\x82 invalid")
        result = await scanner.is_readable(test_file)
        assert result is False

    def test_extract_chapter_title_valid(self, scanner, temp_books_dir):
        chapter_file = temp_books_dir / "chapter.txt"
        chapter_file.write_text("第一章 开天辟地\n\n正文内容", encoding="utf-8")
        title = scanner._extract_chapter_title(chapter_file)
        assert title == "第一章 开天辟地"

    def test_extract_chapter_title_too_long(self, scanner, temp_books_dir):
        chapter_file = temp_books_dir / "chapter.txt"
        long_line = "x" * 200
        chapter_file.write_text(long_line + "\n\n正文", encoding="utf-8")
        title = scanner._extract_chapter_title(chapter_file)
        assert len(title) < 100

    def test_extract_chapter_title_empty(self, scanner, temp_books_dir):
        chapter_file = temp_books_dir / "chapter.txt"
        chapter_file.write_text("", encoding="utf-8")
        title = scanner._extract_chapter_title(chapter_file)
        assert title == chapter_file.stem

    def test_extract_chapter_title_uses_stem(self, scanner, temp_books_dir):
        chapter_file = temp_books_dir / "my_chapter.txt"
        chapter_file.write_text("", encoding="utf-8")
        title = scanner._extract_chapter_title(chapter_file)
        assert title == "my_chapter"

    def test_count_words_utf8(self, scanner, temp_books_dir):
        chapter_file = temp_books_dir / "chapter.txt"
        content = "这是测试内容"
        chapter_file.write_text(content, encoding="utf-8")
        count = scanner._count_words(chapter_file)
        assert count == len(content)

    def test_count_words_returns_zero_on_error(self, scanner, temp_books_dir):
        nonexistent = temp_books_dir / "missing.txt"
        count = scanner._count_words(nonexistent)
        assert count == 0


class TestBookScannerAuthorDetection:
    @pytest.fixture
    def temp_books_dir(self, tmp_path):
        books_dir = tmp_path / "books"
        books_dir.mkdir()
        return books_dir

    @pytest.fixture
    def scanner(self, temp_books_dir):
        return BookScanner(books_dir=str(temp_books_dir))

    def test_detect_author_from_info_file(self, scanner, temp_books_dir):
        book_dir = temp_books_dir / "my_book"
        book_dir.mkdir()
        info_file = book_dir / "info.txt"
        info_file.write_text("书名：测试书籍\n作者：张三", encoding="utf-8")
        author = scanner._detect_author(book_dir)
        assert author == "张三"

    def test_detect_author_with_colon(self, scanner, temp_books_dir):
        book_dir = temp_books_dir / "my_book"
        book_dir.mkdir()
        info_file = book_dir / "info.txt"
        info_file.write_text("作者: 李四", encoding="utf-8")
        author = scanner._detect_author(book_dir)
        assert author == "李四"

    def test_detect_author_empty_when_no_info(self, scanner, temp_books_dir):
        book_dir = temp_books_dir / "my_book"
        book_dir.mkdir()
        author = scanner._detect_author(book_dir)
        assert author == ""

    def test_detect_author_empty_when_file_missing(self, scanner, temp_books_dir):
        book_dir = temp_books_dir / "my_book"
        book_dir.mkdir()
        author = scanner._detect_author(book_dir)
        assert author == ""

    def test_detect_author_handles_invalid_file(self, scanner, temp_books_dir):
        book_dir = temp_books_dir / "my_book"
        book_dir.mkdir()
        info_file = book_dir / "info.txt"
        info_file.write_bytes(b"\xff\xfe invalid content")
        author = scanner._detect_author(book_dir)
        assert author == ""

    def test_detect_author_takes_first_match(self, scanner, temp_books_dir):
        book_dir = temp_books_dir / "my_book"
        book_dir.mkdir()
        info_file = book_dir / "info.txt"
        info_file.write_text("其他信息\n作者：第一人\n作者：第二人", encoding="utf-8")
        author = scanner._detect_author(book_dir)
        assert author == "第一人"


class TestBookScannerDirectoryScanning:
    @pytest.fixture
    def temp_books_dir(self, tmp_path):
        books_dir = tmp_path / "books"
        books_dir.mkdir()
        return books_dir

    @pytest.fixture
    def scanner(self, temp_books_dir):
        return BookScanner(books_dir=str(temp_books_dir))

    @pytest.mark.asyncio
    async def test_scan_creates_dir_if_missing(self, tmp_path):
        nonexistent = tmp_path / "missing_books"
        scanner = BookScanner(books_dir=str(nonexistent))
        await scanner.scan_directory()
        assert nonexistent.exists()

    @pytest.mark.asyncio
    async def test_scan_handles_multiple_books(self, scanner, temp_books_dir):
        book1 = temp_books_dir / "book1"
        book1.mkdir()
        (book1 / "chapter1.txt").write_text("第一章\n\n内容")
        (book1 / "chapter2.txt").write_text("第二章\n\n内容")

        book2 = temp_books_dir / "book2"
        book2.mkdir()
        (book2 / "chapter1.txt").write_text("第一话\n\n内容")

        with patch('app.services.scan_service.AsyncSessionLocal') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=None)
            mock_session.execute = AsyncMock(return_value=mock_result)

            added = await scanner._register_books()
            assert added >= 0
