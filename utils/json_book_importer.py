"""
JSON book importer — detects and converts JSON-format book descriptions
into the standard format (txt chapters + metadata.json).

JSON format:
{
    "title": "...",
    "author": "...",
    "description": "...",
    "cover": "...",
    "chapters": [
        {"id": "1", "title": "...", "file": "path/to/chapter.txt"},
    ]
}
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

# Encodings to try when reading chapter files
_CHAPTER_ENCODINGS = ["utf-8", "gbk", "gb2312"]


def detect_json_files(book_dir: str) -> list[str]:
    """Detect JSON book description files in a directory.

    Returns list of absolute JSON file paths, EXCLUDING metadata.json.
    """
    if not os.path.isdir(book_dir):
        logger.warning(f"detect_json_files: not a directory: {book_dir}")
        return []

    json_files = []
    try:
        for entry in os.listdir(book_dir):
            if not entry.lower().endswith(".json"):
                continue
            if entry == "metadata.json":
                continue
            json_files.append(os.path.join(book_dir, entry))
    except OSError as e:
        logger.error(f"detect_json_files: failed to list {book_dir}: {e}")

    logger.debug(f"detect_json_files: found {len(json_files)} JSON(s) in {book_dir}")
    return json_files


def parse_book_json(json_path: str) -> dict:
    """Parse a JSON book description file.

    Returns dict with keys: title, author, description, cover, chapters.
    On error returns {'error': 'message'}.
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"error": f"JSON file not found: {json_path}"}
    except json.JSONDecodeError as e:
        logger.error(f"parse_book_json: invalid JSON in {json_path}: {e}")
        return {"error": f"Invalid JSON in {json_path}: {e}"}
    except Exception as e:
        logger.error(f"parse_book_json: failed to read {json_path}: {e}")
        return {"error": f"Failed to read {json_path}: {e}"}

    book_dir = os.path.dirname(json_path) or "."

    title = data.get("title") or os.path.basename(book_dir)
    author = data.get("author", "")
    description = data.get("description", "")
    cover = data.get("cover", "")
    chapters = data.get("chapters", [])
    if not isinstance(chapters, list):
        chapters = []

    logger.info(
        f"parse_book_json: title={title!r}, author={author!r}, "
        f"chapters={len(chapters)}"
    )
    return {
        "title": title,
        "author": author,
        "description": description,
        "cover": cover,
        "chapters": chapters,
    }


def import_json_book(json_path: str) -> dict:
    """Complete import workflow for a JSON book description file.

    1. Parse the JSON file
    2. Extract book info
    3. Create metadata.json in the same directory
    4. Verify chapter files exist
    5. Delete the original JSON file on success
    6. Return {'success': True/False, 'title': ..., 'chapters': N, 'error': ...}
    """
    parsed = parse_book_json(json_path)
    if "error" in parsed:
        return {"success": False, "title": "", "chapters": 0, "error": parsed["error"]}

    book_dir = os.path.dirname(json_path) or "."
    title = parsed["title"]
    author = parsed["author"]
    description = parsed["description"]
    cover = parsed["cover"]
    chapters = parsed["chapters"]

    # Verify chapter files
    found_count = 0
    for chapter in chapters:
        chapter_file = chapter.get("file", "")
        if not chapter_file:
            logger.warning(f"import_json_book: chapter has no file field, skipping: {chapter}")
            continue

        # Extract just the filename (ignore path components)
        filename = os.path.basename(chapter_file)
        chapter_path = os.path.join(book_dir, filename)

        if not os.path.exists(chapter_path):
            logger.warning(
                f"import_json_book: chapter file missing: {chapter_path}"
            )
            continue

        # Try to read the chapter file with multiple encodings
        content = None
        for enc in _CHAPTER_ENCODINGS:
            try:
                with open(chapter_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, Exception):
                continue

        if content is not None:
            found_count += 1
            logger.debug(
                f"import_json_book: verified chapter {chapter.get('title')!r} "
                f"at {filename}"
            )
        else:
            logger.warning(
                f"import_json_book: cannot decode chapter file: {chapter_path}"
            )

    # Write metadata.json
    metadata = {
        "title": title,
        "author": author,
        "description": description,
        "cover": cover,
    }
    metadata_path = os.path.join(book_dir, "metadata.json")

    try:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"import_json_book: wrote metadata.json for {title!r}")
    except Exception as e:
        logger.error(
            f"import_json_book: failed to write metadata.json: {e}"
        )
        return {
            "success": False,
            "title": title,
            "chapters": len(chapters),
            "error": str(e),
        }

    # Delete original JSON on success
    try:
        os.remove(json_path)
        logger.info(f"import_json_book: deleted source JSON: {json_path}")
    except OSError as e:
        logger.warning(f"import_json_book: could not delete source JSON: {e}")

    return {
        "success": True,
        "title": title,
        "chapters": len(chapters),
    }