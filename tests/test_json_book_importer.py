"""Tests for utils/json_book_importer.py - JSON book description importer."""

import json
import os
import tempfile

import pytest

# ──────────────────────────────────────────────
# RED phase: import will fail until module exists
# ──────────────────────────────────────────────
from utils.json_book_importer import detect_json_files, parse_book_json, import_json_book


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

SAMPLE_BOOK_JSON = {
    "id": "奴隶公司",
    "title": "奴隶公司",
    "author": "未知作者",
    "description": "暂无简介",
    "cover": "https://example.com/cover.jpg",
    "chapters": [
        {"id": "1", "title": "1", "file": "Database//data/books/奴隶公司/1.txt"},
        {"id": "2", "title": "2", "file": "Database//data/books/奴隶公司/2.txt"},
    ],
    "created_at": "2026-02-11T12:53:59.595792",
    "updated_at": "2026-02-13T15:42:34.706131",
}


# ──────────────────────────────────────────────
# Tests for detect_json_files
# ──────────────────────────────────────────────

class TestDetectJsonFiles:
    """Tests for detect_json_files function."""

    def test_detect_json_files_finds_book_json(self):
        """detect_json_files finds book.json but NOT metadata.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create book.json and metadata.json
            book_json_path = os.path.join(tmpdir, "book.json")
            metadata_path = os.path.join(tmpdir, "metadata.json")

            with open(book_json_path, "w", encoding="utf-8") as f:
                json.dump(SAMPLE_BOOK_JSON, f, ensure_ascii=False)
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump({"author": "test"}, f)

            result = detect_json_files(tmpdir)
            result_basenames = [os.path.basename(p) for p in result]

            assert "book.json" in result_basenames, f"book.json should be detected, got {result_basenames}"
            assert "metadata.json" not in result_basenames, "metadata.json should be excluded"
            assert len(result) == 1, f"Expected exactly 1 JSON file (book.json), got {len(result)}: {result}"

    def test_detect_json_files_empty_dir(self):
        """Empty directory returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = detect_json_files(tmpdir)
            assert result == [], f"Empty dir should return empty list, got {result}"

    def test_detect_json_files_multiple_book_jsons(self):
        """Directory with multiple book JSONs returns all non-metadata JSONs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["book1.json", "book2.json", "metadata.json"]:
                path = os.path.join(tmpdir, name)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(SAMPLE_BOOK_JSON, f, ensure_ascii=False)

            result = detect_json_files(tmpdir)
            result_basenames = sorted([os.path.basename(p) for p in result])

            assert result_basenames == ["book1.json", "book2.json"], \
                f"Expected only book1.json and book2.json, got {result_basenames}"


# ──────────────────────────────────────────────
# Tests for parse_book_json
# ──────────────────────────────────────────────

class TestParseBookJson:
    """Tests for parse_book_json function."""

    def test_parse_book_json_valid(self):
        """Parse a valid JSON with all fields, verify extraction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "book.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(SAMPLE_BOOK_JSON, f, ensure_ascii=False)

            result = parse_book_json(json_path)

            assert result["title"] == "奴隶公司"
            assert result["author"] == "未知作者"
            assert result["description"] == "暂无简介"
            assert result["cover"] == "https://example.com/cover.jpg"
            assert len(result["chapters"]) == 2
            assert result["chapters"][0]["title"] == "1"
            assert result["chapters"][1]["title"] == "2"

    def test_parse_book_json_missing_title(self):
        """JSON without title field uses directory name as title."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_data = {
                "author": "某作者",
                "description": "某简介",
                "chapters": [],
            }
            json_path = os.path.join(tmpdir, "my_novel.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False)

            result = parse_book_json(json_path)
            # Directory name is tmpdir basename, but we can check title exists
            assert "title" in result
            assert result["title"]  # should be non-empty (directory name)
            assert result["author"] == "某作者"
            assert result["description"] == "某简介"

    def test_parse_book_json_missing_author_description(self):
        """JSON without author/description uses empty defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_data = {
                "title": "无作者书",
                "chapters": [],
            }
            json_path = os.path.join(tmpdir, "book.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False)

            result = parse_book_json(json_path)
            assert result["title"] == "无作者书"
            assert result["author"] == ""
            assert result["description"] == ""

    def test_parse_book_json_missing_cover(self):
        """JSON without cover field uses empty string default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_data = {
                "title": "某书",
                "author": "某人",
                "chapters": [],
            }
            json_path = os.path.join(tmpdir, "book.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False)

            result = parse_book_json(json_path)
            assert result["cover"] == ""

    def test_parse_book_json_invalid_json(self):
        """Parse invalid JSON string returns error dict with 'error' key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "bad.json")
            with open(json_path, "w", encoding="utf-8") as f:
                f.write("this is not json {{{")

            result = parse_book_json(json_path)
            assert "error" in result, f"Should have 'error' key, got {result}"

    def test_parse_book_json_file_not_found(self):
        """Parse non-existent file returns error dict."""
        result = parse_book_json("/nonexistent/path/book.json")
        assert "error" in result


# ──────────────────────────────────────────────
# Tests for import_json_book
# ──────────────────────────────────────────────

class TestImportJsonBook:
    """Tests for import_json_book function."""

    def test_import_json_book_success(self):
        """Create JSON and chapter txt files, import, verify metadata and deletion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create chapter files
            chapter1_path = os.path.join(tmpdir, "1.txt")
            chapter2_path = os.path.join(tmpdir, "2.txt")
            with open(chapter1_path, "w", encoding="utf-8") as f:
                f.write("第一章内容")
            with open(chapter2_path, "w", encoding="utf-8") as f:
                f.write("第二章内容")

            # Create JSON that references chapter files by just filename
            json_data = {
                "title": "测试书",
                "author": "测试作者",
                "description": "测试简介",
                "cover": "https://example.com/cover.jpg",
                "chapters": [
                    {"id": "1", "title": "第一章", "file": "1.txt"},
                    {"id": "2", "title": "第二章", "file": "2.txt"},
                ],
            }
            json_path = os.path.join(tmpdir, "book.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False)

            result = import_json_book(json_path)

            assert result["success"] is True, f"Import should succeed, got {result}"
            assert result["title"] == "测试书"
            assert result["chapters"] == 2

            # metadata.json should exist
            metadata_path = os.path.join(tmpdir, "metadata.json")
            assert os.path.exists(metadata_path), "metadata.json should be created"

            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            assert metadata["title"] == "测试书"
            assert metadata["author"] == "测试作者"
            assert metadata["description"] == "测试简介"
            assert metadata["cover"] == "https://example.com/cover.jpg"

            # Original JSON should be deleted
            assert not os.path.exists(json_path), "Original JSON should be deleted after success"

    def test_import_json_book_chapter_file_missing(self):
        """JSON references missing chapter file — log warning, still create metadata and delete JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only one chapter file
            chapter1_path = os.path.join(tmpdir, "1.txt")
            with open(chapter1_path, "w", encoding="utf-8") as f:
                f.write("第一章内容")

            # JSON references a missing chapter
            json_data = {
                "title": "不完整书",
                "author": "测试",
                "chapters": [
                    {"id": "1", "title": "第一章", "file": "1.txt"},
                    {"id": "2", "title": "缺失章", "file": "2.txt"},
                ],
            }
            json_path = os.path.join(tmpdir, "book.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False)

            result = import_json_book(json_path)

            # Should still succeed (warning logged, but not fatal)
            assert result["success"] is True, f"Import should succeed even with missing chapters, got {result}"
            assert result["chapters"] == 2  # reports total chapters from JSON

            # metadata.json should still be created
            metadata_path = os.path.join(tmpdir, "metadata.json")
            assert os.path.exists(metadata_path), "metadata.json should be created despite missing chapters"

            # Original JSON should be deleted
            assert not os.path.exists(json_path), "Original JSON should be deleted on success"

    def test_import_json_book_keeps_json_on_failure(self):
        """When import fails, JSON file should be preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_data = {
                "title": "测试书",
                "author": "测试",
                "chapters": [{"id": "1", "title": "第一章", "file": "missing.txt"}],
            }
            json_path = os.path.join(tmpdir, "book.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False)

            # Make metadata.json undeditable by creating a directory with that name
            metadata_dir = os.path.join(tmpdir, "metadata.json")
            os.makedirs(metadata_dir, exist_ok=True)

            result = import_json_book(json_path)

            assert result["success"] is False, f"Import should fail when can't write metadata, got {result}"
            # JSON file should still exist (preserved on failure)
            assert os.path.exists(json_path), "JSON file should be preserved on failure"

    def test_import_json_book_chapter_file_with_path(self):
        """Chapter file field with path — only basename is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            chapter1_path = os.path.join(tmpdir, "1.txt")
            with open(chapter1_path, "w", encoding="utf-8") as f:
                f.write("第一章内容")

            json_data = {
                "title": "路径测试",
                "author": "测试",
                "chapters": [
                    {"id": "1", "title": "第一章",
                     "file": "Database//data/books/奴隶公司/1.txt"},
                ],
            }
            json_path = os.path.join(tmpdir, "book.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False)

            result = import_json_book(json_path)

            assert result["success"] is True, \
                f"Import with path-based file references should succeed, got {result}"
            assert result["chapters"] == 1

    def test_import_json_book_title_fallback(self):
        """Book without title uses directory name as title."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_data = {
                "author": "佚名",
                "chapters": [],
            }
            json_path = os.path.join(tmpdir, "book.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False)

            result = import_json_book(json_path)
            assert result["success"] is True
            # Title should be the directory name (tmpdir basename)
            assert result["title"] == os.path.basename(tmpdir)

            metadata_path = os.path.join(tmpdir, "metadata.json")
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            assert metadata["title"] == os.path.basename(tmpdir)