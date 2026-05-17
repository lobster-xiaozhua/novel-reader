import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.scan_service import BookScanner


class TestBookScanner:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = BookScanner(books_dir=self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_default_books_dir(self):
        scanner = BookScanner()
        assert scanner.books_dir is not None

    def test_allowed_extensions(self):
        assert '.txt' in BookScanner.ALLOWED_EXTENSIONS

    def test_system_files(self):
        assert '.ds_store' in BookScanner.SYSTEM_FILES
        assert 'thumbs.db' in BookScanner.SYSTEM_FILES

    def test_temp_patterns(self):
        assert '~' in BookScanner.TEMP_PATTERNS
        assert '.tmp' in BookScanner.TEMP_PATTERNS


class TestBookScannerProcessFile:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = BookScanner(books_dir=self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_process_file_deletes_system_file(self):
        file_path = Path(self.temp_dir) / ".DS_Store"
        file_path.write_text("hidden")

        result = await self.scanner.process_file(file_path)
        assert result == "deleted"
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_process_file_deletes_temp_file(self):
        file_path = Path(self.temp_dir) / "document.tmp"
        file_path.write_text("temp")

        result = await self.scanner.process_file(file_path)
        assert result == "deleted"

    @pytest.mark.asyncio
    async def test_process_file_deletes_backup_file(self):
        file_path = Path(self.temp_dir) / "notes.bak"
        file_path.write_text("backup")

        result = await self.scanner.process_file(file_path)
        assert result == "deleted"

    @pytest.mark.asyncio
    async def test_process_file_converts_markdown(self):
        file_path = Path(self.temp_dir) / "chapter.md"
        file_path.write_text("# Chapter content")

        result = await self.scanner.process_file(file_path)
        assert result == "converted"
        assert file_path.with_suffix('.txt').exists()
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_process_file_converts_md_extension(self):
        file_path = Path(self.temp_dir) / "intro.markdown"
        file_path.write_text("Content")

        result = await self.scanner.process_file(file_path)
        assert result == "converted"

    @pytest.mark.asyncio
    async def test_process_file_deletes_unsupported_format(self):
        file_path = Path(self.temp_dir) / "document.pdf"
        file_path.write_bytes(b"PDF content")

        result = await self.scanner.process_file(file_path)
        assert result == "deleted"

    @pytest.mark.asyncio
    async def test_process_file_deletes_empty_file(self):
        file_path = Path(self.temp_dir) / "empty.txt"
        file_path.write_text("")

        result = await self.scanner.process_file(file_path)
        assert result == "deleted"

    @pytest.mark.asyncio
    async def test_process_file_accepts_valid_txt(self):
        file_path = Path(self.temp_dir) / "valid.txt"
        file_path.write_text("Valid content here")

        result = await self.scanner.process_file(file_path)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_process_file_handles_utf8_encoding(self):
        file_path = Path(self.temp_dir) / "chinese.txt"
        file_path.write_text("中文内容测试")

        result = await self.scanner.process_file(file_path)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_process_file_handles_gbk_encoding(self):
        file_path = Path(self.temp_dir) / "gbk.txt"
        file_path.write_bytes("中文内容".encode('gbk'))

        result = await self.scanner.process_file(file_path)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_process_file_handles_large_binary_file(self):
        file_path = Path(self.temp_dir) / "large_binary.bin"
        file_path.write_bytes(b'\x00\x01\x02\xff\xfe\xfd' * 10000)
        result = await self.scanner.process_file(file_path)
        assert result in ["ok", "deleted"]


class TestBookScannerIsTempFile:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = BookScanner(books_dir=self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detects_tilde_suffix(self):
        assert self.scanner.is_temp_file("document~") is True

    def test_detects_tmp_extension(self):
        assert self.scanner.is_temp_file("file.tmp") is True

    def test_detects_temp_extension(self):
        assert self.scanner.is_temp_file("data.temp") is True

    def test_detects_bak_extension(self):
        assert self.scanner.is_temp_file("backup.bak") is True

    def test_detects_swp_extension(self):
        assert self.scanner.is_temp_file(".swp") is True

    def test_accepts_normal_filename(self):
        assert self.scanner.is_temp_file("chapter_1.txt") is False

    def test_case_insensitive(self):
        assert self.scanner.is_temp_file("File.TMP") is True
        assert self.scanner.is_temp_file("Document.BAK") is True


class TestBookScannerHelpers:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = BookScanner(books_dir=self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_delete_file(self):
        file_path = Path(self.temp_dir) / "to_delete.txt"
        file_path.write_text("content")

        await self.scanner.delete_file(file_path, "Test deletion")
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_file_nonexistent(self):
        file_path = Path(self.temp_dir) / "nonexistent.txt"
        await self.scanner.delete_file(file_path, "Test")

    @pytest.mark.asyncio
    async def test_rename_file(self):
        old_path = Path(self.temp_dir) / "old.txt"
        new_path = Path(self.temp_dir) / "new.txt"
        old_path.write_text("content")

        await self.scanner.rename_file(old_path, new_path, "Test rename")
        assert not old_path.exists()
        assert new_path.exists()

    @pytest.mark.asyncio
    async def test_is_readable_utf8(self):
        file_path = Path(self.temp_dir) / "utf8.txt"
        file_path.write_text("UTF-8 content こんにちは")

        result = await self.scanner.is_readable(file_path)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_readable_gbk(self):
        file_path = Path(self.temp_dir) / "gbk.txt"
        file_path.write_bytes("GBK内容".encode('gbk'))

        result = await self.scanner.is_readable(file_path)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_readable_binary_fails(self):
        file_path = Path(self.temp_dir) / "binary.bin"
        file_path.write_bytes(b'\xff\xfe\x00\x01')

        result = await self.scanner.is_readable(file_path)
        assert result is False

    @pytest.mark.asyncio
    async def test_extract_chapter_title_from_file(self):
        file_path = Path(self.temp_dir) / "chapter.txt"
        file_path.write_text("第一章：开篇\n\n正文内容...")

        title = await self.scanner._extract_chapter_title(file_path)
        assert title == "第一章：开篇"

    @pytest.mark.asyncio
    async def test_extract_chapter_title_uses_stem_if_empty(self):
        file_path = Path(self.temp_dir) / "chapter_10.txt"
        file_path.write_text("\n\n正文内容...")

        title = await self.scanner._extract_chapter_title(file_path)
        assert title == "chapter_10"

    @pytest.mark.asyncio
    async def test_extract_chapter_title_truncates_long_title(self):
        file_path = Path(self.temp_dir) / "chapter.txt"
        file_path.write_text("A" * 150 + "\n\n正文")

        title = await self.scanner._extract_chapter_title(file_path)
        assert len(title) <= 100

    @pytest.mark.asyncio
    async def test_count_words(self):
        file_path = Path(self.temp_dir) / "words.txt"
        content = "这是测试内容，共包含一些中文字符。"
        file_path.write_text(content)

        count = await self.scanner._count_words(file_path)
        assert count == len(content)

    @pytest.mark.asyncio
    async def test_count_words_handles_error(self):
        file_path = Path(self.temp_dir) / "error.txt"
        count = await self.scanner._count_words(file_path)
        assert count == 0
