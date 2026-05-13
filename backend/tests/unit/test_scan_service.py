import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.scan_service import BookScanner


class TestBookScanner:
    @pytest.fixture
    def scanner(self, tmp_path):
        return BookScanner(books_dir=str(tmp_path))

    @pytest.fixture
    def tmp_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    def test_is_temp_file(self, scanner):
        assert scanner.is_temp_file("chapter1.txt~") is True
        assert scanner.is_temp_file("chapter1.tmp") is True
        assert scanner.is_temp_file("chapter1.bak") is True
        assert scanner.is_temp_file("chapter1.swp") is True
        assert scanner.is_temp_file("chapter1.txt") is False

    @pytest.mark.asyncio
    async def test_is_readable_utf8(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("测试内容", encoding="utf-8")
        
        scanner = BookScanner(str(tmp_path))
        result = await scanner.is_readable(test_file)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_is_readable_gbk(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_bytes("测试内容".encode("gbk"))
        
        scanner = BookScanner(str(tmp_path))
        result = await scanner.is_readable(test_file)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_is_readable_corrupted(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"\xff\xfe\xfd")  # Invalid bytes
        
        scanner = BookScanner(str(tmp_path))
        result = await scanner.is_readable(test_file)
        
        assert result is False

    def test_extract_chapter_title(self, tmp_path):
        test_file = tmp_path / "chapter1.txt"
        test_file.write_text("第一章 开始\n\n内容...", encoding="utf-8")
        
        scanner = BookScanner(str(tmp_path))
        title = scanner._extract_chapter_title(test_file)
        
        assert title == "第一章 开始"

    def test_extract_chapter_title_empty(self, tmp_path):
        test_file = tmp_path / "chapter1.txt"
        test_file.write_text("", encoding="utf-8")
        
        scanner = BookScanner(str(tmp_path))
        title = scanner._extract_chapter_title(test_file)
        
        assert title == "chapter1"

    def test_count_words(self, tmp_path):
        test_file = tmp_path / "chapter1.txt"
        test_file.write_text("Hello World", encoding="utf-8")
        
        scanner = BookScanner(str(tmp_path))
        count = scanner._count_words(test_file)
        
        assert count == 11

    def test_detect_author_from_info_file(self, tmp_path):
        info_file = tmp_path / "info.txt"
        info_file.write_text("作者：张三\n书名：测试小说", encoding="utf-8")
        
        scanner = BookScanner(str(tmp_path))
        author = scanner._detect_author(tmp_path)
        
        assert author == "张三"

    def test_detect_author_colon(self, tmp_path):
        info_file = tmp_path / "info.txt"
        info_file.write_text("作者: John Doe", encoding="utf-8")
        
        scanner = BookScanner(str(tmp_path))
        author = scanner._detect_author(tmp_path)
        
        assert author == "John Doe"

    def test_detect_author_no_info_file(self, tmp_path):
        scanner = BookScanner(str(tmp_path))
        author = scanner._detect_author(tmp_path)
        
        assert author == ""

    @pytest.mark.asyncio
    async def test_process_file_txt_valid(self, scanner, tmp_path):
        test_file = tmp_path / "chapter1.txt"
        test_file.write_text("测试内容", encoding="utf-8")
        
        result = await scanner.process_file(test_file)
        
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_process_file_system_file(self, scanner, tmp_path):
        test_file = tmp_path / ".DS_Store"
        test_file.write_text("", encoding="utf-8")
        
        result = await scanner.process_file(test_file)
        
        assert result == "deleted"
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_temp_file(self, scanner, tmp_path):
        test_file = tmp_path / "chapter1.txt.bak"
        test_file.write_text("测试内容", encoding="utf-8")
        
        result = await scanner.process_file(test_file)
        
        assert result == "deleted"
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_convert_md(self, scanner, tmp_path):
        test_file = tmp_path / "chapter1.md"
        test_file.write_text("# 第一章\n\n内容", encoding="utf-8")
        
        result = await scanner.process_file(test_file)
        
        assert result == "converted"
        assert not test_file.exists()
        assert (tmp_path / "chapter1.txt").exists()

    @pytest.mark.asyncio
    async def test_process_file_unsupported_extension(self, scanner, tmp_path):
        test_file = tmp_path / "chapter1.pdf"
        test_file.write_text("pdf content", encoding="utf-8")
        
        result = await scanner.process_file(test_file)
        
        assert result == "deleted"
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_empty(self, scanner, tmp_path):
        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding="utf-8")
        
        result = await scanner.process_file(test_file)
        
        assert result == "deleted"
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_process_file_corrupted(self, scanner, tmp_path):
        test_file = tmp_path / "corrupted.txt"
        test_file.write_bytes(b"\xff\xfe\xfd")
        
        result = await scanner.process_file(test_file)
        
        assert result == "deleted"
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_scan_directory_empty(self, scanner):
        await scanner.scan_directory()
        
        assert True

    @pytest.mark.asyncio
    async def test_scan_directory_with_books(self, scanner, tmp_path):
        book_dir = tmp_path / "TestBook"
        book_dir.mkdir()
        
        chapter1 = book_dir / "chapter1.txt"
        chapter1.write_text("第一章\n\n内容", encoding="utf-8")
        
        chapter2 = book_dir / "chapter2.txt"
        chapter2.write_text("第二章\n\n内容", encoding="utf-8")
        
        with patch('app.services.scan_service.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result
            
            mock_db.commit = AsyncMock()
            mock_db.flush = AsyncMock()
            mock_db.add = MagicMock()
            
            await scanner.scan_directory()
            
            assert mock_db.add.call_count > 0