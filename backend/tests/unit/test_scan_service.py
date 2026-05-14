import pytest
import tempfile
import shutil
from pathlib import Path

from app.services.scan_service import BookScanner


class TestBookScanner:
    @pytest.fixture
    def temp_books_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def scanner(self, temp_books_dir):
        return BookScanner(books_dir=str(temp_books_dir))

    def test_scanner_initialization(self, scanner, temp_books_dir):
        assert scanner.books_dir == temp_books_dir
        assert BookScanner.ALLOWED_EXTENSIONS == {'.txt'}
        assert BookScanner.AUTO_CONVERT_EXTENSIONS == {'.md', '.markdown'}

    def test_is_temp_file_detection(self, scanner):
        assert scanner.is_temp_file("file.txt~") is True
        assert scanner.is_temp_file("file.tmp") is True
        assert scanner.is_temp_file("file.bak") is True
        assert scanner.is_temp_file("file.swp") is True
        assert scanner.is_temp_file("normal_file.txt") is False

    @pytest.mark.asyncio
    async def test_delete_file(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "to_delete.txt"
        test_file.write_text("content")
        await scanner.delete_file(test_file, "test deletion")
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_rename_file_converts_extension(self, scanner, temp_books_dir):
        old_file = temp_books_dir / "file.md"
        old_file.write_text("# Markdown Content")
        new_file = temp_books_dir / "file.txt"
        await scanner.rename_file(old_file, new_file, "format conversion")
        assert not old_file.exists()
        assert new_file.exists()
        assert new_file.read_text() == "# Markdown Content"

    @pytest.mark.asyncio
    async def test_is_readable_utf8_file(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "utf8.txt"
        test_file.write_text("UTF-8 内容测试", encoding="utf-8")
        result = await scanner.is_readable(test_file)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_readable_gbk_file_fallback(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "gbk.txt"
        test_file.write_bytes("GBK 内容".encode("gbk"))
        result = await scanner.is_readable(test_file)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_readable_returns_false_for_corrupted(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "corrupt.bin"
        test_file.write_bytes(b"\x80\x81\x82\x83")
        result = await scanner.is_readable(test_file)
        assert result is False

    @pytest.mark.asyncio
    async def test_process_file_deletes_system_files(self, scanner, temp_books_dir):
        test_file = temp_books_dir / ".DS_Store"
        test_file.write_text("system")
        result = await scanner.process_file(test_file)
        assert result == "deleted"
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_deletes_temp_files(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "file.txt.tmp"
        test_file.write_text("temp")
        result = await scanner.process_file(test_file)
        assert result == "deleted"

    @pytest.mark.asyncio
    async def test_process_file_converts_markdown(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "book.md"
        test_file.write_text("# Book Content")
        result = await scanner.process_file(test_file)
        assert result == "converted"
        assert not test_file.exists()
        assert (temp_books_dir / "book.txt").exists()

    @pytest.mark.asyncio
    async def test_process_file_deletes_unsupported_format(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "data.csv"
        test_file.write_text("csv,data")
        result = await scanner.process_file(test_file)
        assert result == "deleted"
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_deletes_empty_file(self, scanner, temp_books_dir):
        test_file = temp_books_dir / "empty.txt"
        test_file.write_text("")
        result = await scanner.process_file(test_file)
        assert result == "deleted"

    def test_detect_author_from_info_file(self, scanner, temp_books_dir):
        book_dir = temp_books_dir / "mybook"
        book_dir.mkdir()
        info_file = book_dir / "info.txt"
        info_file.write_text("书名：测试书籍\n作者：张三\n分类：玄幻")
        author = scanner._detect_author(book_dir)
        assert author == "张三"

    def test_detect_author_returns_empty_when_no_info(self, scanner, temp_books_dir):
        book_dir = temp_books_dir / "nobook"
        book_dir.mkdir()
        author = scanner._detect_author(book_dir)
        assert author == ""

    def test_extract_chapter_title_from_file(self, scanner, temp_books_dir):
        chapter_file = temp_books_dir / "chapter_1.txt"
        chapter_file.write_text("第一章 入门\n\n正文内容...")
        title = scanner._extract_chapter_title(chapter_file)
        assert title == "第一章 入门"

    def test_count_words(self, scanner, temp_books_dir):
        chapter_file = temp_books_dir / "words.txt"
        chapter_file.write_text("这是一个测试章节内容。")
        count = scanner._count_words(chapter_file)
        assert count == len("这是一个测试章节内容。")

    def test_count_words_returns_zero_on_error(self, scanner):
        count = scanner._count_words(Path("/nonexistent/file.txt"))
        assert count == 0
