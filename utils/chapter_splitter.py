"""
Smart chapter splitter - automatically detects chapter boundaries and splits text.

Patterns:
1. Chinese chapter headers (第N章)
2. English chapter headers (Chapter N)
3. Numbered sections (N. / N、)

Fallback: split by paragraphs (every 50 paragraphs = 1 chapter)
"""

import logging
import os
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Compiled regex patterns for chapter detection
CHAPTER_PATTERNS = [
    # Pattern 1: Chinese chapter headers like "第一章", "第一百二十三章"
    re.compile(r'^第[零一二三四五六七八九十百千万\d]+章', re.MULTILINE),
    # Pattern 2: English chapter headers like "Chapter 1", "Chapter  23"
    re.compile(r'^Chapter\s*\d+', re.MULTILINE | re.IGNORECASE),
    # Pattern 3: Numbered sections like "1.", "2、", "3  "
    re.compile(r'^\d+[\.\、\s]', re.MULTILINE),
]


def split_text_to_chapters(text: str | None) -> List[Tuple[str, str]]:
    """
    Split raw text into list of (chapter_title, chapter_content) tuples.

    Args:
        text: Raw text content to split.

    Returns:
        List of tuples (chapter_title, chapter_content).
    """
    if not text or not isinstance(text, str):
        return []

    text = text.rstrip('\n')
    if not text:
        return []

    # Find all chapter matches across all patterns
    matches = []
    for pattern in CHAPTER_PATTERNS:
        found = list(pattern.finditer(text))
        if found:
            matches.extend(found)
            break

    # If no matches found, use fallback: split by paragraphs
    if not matches:
        return _split_by_paragraphs_fallback(text)

    # Sort matches by starting position
    matches.sort(key=lambda m: m.start())

    chapters = []
    lines = text.split('\n')

    for i, match in enumerate(matches):
        start_pos = match.start()

        # Find the line number where this match starts
        start_line = text.count('\n', 0, start_pos)
        end_line = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        end_line = text.count('\n', 0, end_line)

        # Extract title from the matched line
        title_line = lines[start_line]
        title = title_line.strip()

        # Extract content (from next line to end of chapter)
        content_lines = lines[start_line + 1: end_line + 1] if i + 1 < len(matches) else lines[start_line + 1:]
        content = '\n'.join(content_lines).strip()

        chapters.append((title, content))

    # Edge case: if all matched lines were at the end, fix it
    if not chapters:
        return _split_by_paragraphs_fallback(text)

    logger.debug(f"Split text into {len(chapters)} chapters using pattern matching")
    return chapters


def _split_by_paragraphs_fallback(text: str, paragraphs_per_chapter: int = 50) -> List[Tuple[str, str]]:
    """
    Fallback: split text into chapters by paragraph count.

    Args:
        text: Text to split.
        paragraphs_per_chapter: Number of paragraphs per chapter chunk.

    Returns:
        List of (chapter_title, content) tuples.
    """
    # Split by paragraphs (empty line separator)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    if not paragraphs:
        # If no empty lines, split by lines
        paragraphs = [line.strip() for line in text.split('\n') if line.strip()]

    if not paragraphs:
        return [("正文", text.strip())]

    chapters: List[Tuple[str, str]] = []
    chapter_num = 1

    for i in range(0, len(paragraphs), paragraphs_per_chapter):
        chunk = paragraphs[i:i + paragraphs_per_chapter]
        content = '\n\n'.join(chunk)
        title = f"第{chapter_num}章"
        chapters.append((title, content))
        chapter_num += 1

    logger.debug(f"No chapter patterns found, split into {len(chapters)} chapters by paragraph fallback")
    return chapters


def auto_split_book_dir(book_dir: str) -> int:
    """
    Scan a directory for single .txt files, split them into multiple chapter files.

    Only processes files that don't already look like chapter files (no "第.*章" in name).

    Args:
        book_dir: Directory containing the book's txt files.

    Returns:
        Number of chapters created.
    """
    if not os.path.isdir(book_dir):
        logger.error(f"Directory not found: {book_dir}")
        return 0

    total_created = 0

    # Iterate over .txt files in the directory
    for filename in os.listdir(book_dir):
        if not filename.lower().endswith('.txt'):
            continue

        # Skip files that already look like they are split chapters
        base_name = os.path.basename(filename)
        chapter_pattern = re.compile(r'第.*章|chapter\s*\d+', re.IGNORECASE)
        if chapter_pattern.search(base_name):
            logger.debug(f"Skipping already split chapter file: {filename}")
            continue

        file_path = os.path.join(book_dir, filename)

        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                logger.warning(f"Empty file, skipping: {file_path}")
                continue

            # Split into chapters
            chapters = split_text_to_chapters(content)

            if len(chapters) <= 1:
                logger.info(f"Only {len(chapters)} chapters found, not splitting: {filename}")
                continue

            # Write each chapter as separate file
            for chapter_title, chapter_content in chapters:
                # Sanitize filename - replace invalid chars
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', chapter_title)
                chapter_filename = f"{safe_title}.txt"
                chapter_path = os.path.join(book_dir, chapter_filename)

                # Write the chapter file
                with open(chapter_path, 'w', encoding='utf-8') as f:
                    f.write(chapter_content)

                total_created += 1
                logger.debug(f"Created chapter file: {chapter_filename}")

            logger.info(f"Split {filename} into {len(chapters)} chapters")

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}", exc_info=True)
            continue

    return total_created
