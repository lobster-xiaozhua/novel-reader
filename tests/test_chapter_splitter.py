"""Tests for utils/chapter_splitter.py - Smart chapter splitting utility."""

import os
import tempfile

import pytest

# ──────────────────────────────────────────────
# RED phase: import will fail until module exists
# ──────────────────────────────────────────────
from utils.chapter_splitter import split_text_to_chapters, auto_split_book_dir


# ──────────────────────────────────────────────
# Tests for split_text_to_chapters
# ──────────────────────────────────────────────

class TestSplitTextToChapters:
    """Tests for the split_text_to_chapters function."""

    def test_split_by_chinese_chapter(self):
        """Text with Chinese chapter headers should split into multiple chapters."""
        text = "第一章 山村的早晨\n清晨的阳光洒在山村的小路上。\n第二章 遇见师傅\n他在村口遇到了改变他一生的人。"
        result = split_text_to_chapters(text)
        assert len(result) == 2, f"Expected 2 chapters, got {len(result)}"
        assert result[0][0] == "第一章 山村的早晨"
        assert "清晨的阳光" in result[0][1]
        assert result[1][0] == "第二章 遇见师傅"
        assert "改变他一生的人" in result[1][1]

    def test_split_by_english_chapter(self):
        """Text with English chapter headers should split into multiple chapters."""
        text = "Chapter 1 The Beginning\nOnce upon a time in a distant land.\nChapter 2 The Journey\nHe set out on a great adventure."
        result = split_text_to_chapters(text)
        assert len(result) == 2, f"Expected 2 chapters, got {len(result)}"
        assert result[0][0] == "Chapter 1 The Beginning"
        assert "Once upon a time" in result[0][1]
        assert result[1][0] == "Chapter 2 The Journey"
        assert "great adventure" in result[1][1]

    def test_split_by_number_prefix(self):
        """Text with numbered sections should split into multiple chapters."""
        text = "1. 引言\n这是引言的内容。\n2. 正文\n这是正文的内容。"
        result = split_text_to_chapters(text)
        assert len(result) == 2, f"Expected 2 chapters, got {len(result)}"
        assert result[0][0] == "1. 引言"
        assert "引言的内容" in result[0][1]
        assert result[1][0] == "2. 正文"
        assert "正文的内容" in result[1][1]

    def test_no_chapter_headers(self):
        """Text without any chapter headers should return at least 1 chapter."""
        text = "这是一段没有任何章节标题的普通文本内容。\n" * 10
        result = split_text_to_chapters(text)
        assert len(result) >= 1, "Should return at least 1 chapter"
        assert isinstance(result[0], tuple)
        assert len(result[0]) == 2

    def test_empty_text(self):
        """Empty text should return an empty list."""
        result = split_text_to_chapters("")
        assert result == [], "Empty text should return empty list"
        result_none = split_text_to_chapters(None)
        assert result_none == [], "None should return empty list"

    def test_split_text_to_chapters_returns_list(self):
        """Function returns list of (title, content) tuples."""
        text = "第一章 测试\n这是测试内容。"
        result = split_text_to_chapters(text)
        assert isinstance(result, list), "Result should be a list"
        assert len(result) >= 1
        assert isinstance(result[0], tuple), "Each item should be a tuple"
        assert len(result[0]) == 2, "Each tuple should have 2 elements (title, content)"


# ──────────────────────────────────────────────
# Tests for auto_split_book_dir
# ──────────────────────────────────────────────

class TestAutoSplitBookDir:
    """Tests for the auto_split_book_dir function."""

    def test_auto_split_book_dir(self):
        """Creates temp dir with a single txt file, splits it into chapters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a single large txt file with multiple chapters
            book_file = os.path.join(tmpdir, "我的小说.txt")
            content = (
                "第一章 初入江湖\n"
                "少年背着一把生锈的铁剑，踏入了这座江湖小镇。街上人来人往。\n"
                "第二章 客栈风云\n"
                "客栈里坐满了江湖客，每个人身上都带着一股杀气。\n"
                "第三章 雨夜追杀\n"
                "雨夜，小镇外的树林里，一场追杀正在上演。\n"
            )
            with open(book_file, "w", encoding="utf-8") as f:
                f.write(content)

            result = auto_split_book_dir(tmpdir)
            assert result == 3, f"Expected 3 chapters created, got {result}"

            # Verify chapter files were created
            files = sorted(os.listdir(tmpdir))
            # Should have original + 3 chapter files
            txt_files = [f for f in files if f.endswith(".txt")]
            assert len(txt_files) == 4, f"Expected 4 txt files (1 original + 3 chapters), got {len(txt_files)}: {txt_files}"

            # Check one of the chapter files
            chapter1_file = os.path.join(tmpdir, "第一章 初入江湖.txt")
            assert os.path.exists(chapter1_file), f"Expected {chapter1_file} to exist"
            with open(chapter1_file, "r", encoding="utf-8") as f:
                c1_content = f.read()
            assert "少年背着一把生锈的铁剑" in c1_content

            chapter3_file = os.path.join(tmpdir, "第三章 雨夜追杀.txt")
            assert os.path.exists(chapter3_file), f"Expected {chapter3_file} to exist"