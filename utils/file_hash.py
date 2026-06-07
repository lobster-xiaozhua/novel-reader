"""File hash utilities — SHA256 hashing for files and directories."""

import hashlib
import json
import logging
import os

logger = logging.getLogger(__name__)


def compute_file_hash(filepath: str) -> str | None:
    """Compute SHA256 hash of a file. Returns hex digest or None if missing."""
    if not os.path.isfile(filepath):
        return None
    sha = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            sha.update(chunk)
    return sha.hexdigest()


def compute_dir_hash(dirpath: str) -> dict:
    """Scan directory for .txt files, return {filename: hash} dict."""
    result = {}
    if not os.path.isdir(dirpath):
        logger.warning("compute_dir_hash: %s is not a directory", dirpath)
        return result
    for entry in sorted(os.listdir(dirpath)):
        if not entry.endswith('.txt'):
            continue
        full = os.path.join(dirpath, entry)
        if not os.path.isfile(full):
            continue
        h = compute_file_hash(full)
        if h:
            result[entry] = h
    return result


class hash_storage:
    """Context manager for reading/writing a hash dict to a JSON file.

    Usage:
        with hash_storage('/path/to/hashes.json') as hashes:
            hashes['file.txt'] = compute_file_hash('file.txt')
    """

    def __init__(self, storage_path: str):
        self._path = storage_path
        self._data: dict = {}

    def __enter__(self) -> dict:
        if os.path.isfile(self._path):
            try:
                with open(self._path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("hash_storage: failed to load %s: %s", self._path, e)
                self._data = {}
        else:
            self._data = {}
        return self._data

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            return False
        os.makedirs(os.path.dirname(self._path) or '.', exist_ok=True)
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        return False