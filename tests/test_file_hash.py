"""Tests for utils/file_hash.py — file hash utility module."""

import json
import os
import tempfile
import pytest

# Import after temp dir setup to avoid module-level side effects
from utils.file_hash import compute_file_hash, compute_dir_hash, hash_storage


class TestComputeFileHash:
    """Tests for compute_file_hash."""

    def test_returns_sha256_hex(self):
        """compute_file_hash returns a 64-char hex string."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('hello world')
            tmp = f.name
        try:
            h = compute_file_hash(tmp)
            assert isinstance(h, str)
            assert len(h) == 64
            assert all(c in '0123456789abcdef' for c in h)
        finally:
            os.unlink(tmp)

    def test_same_content_same_hash(self):
        """Same file content produces same hash."""
        content = 'the quick brown fox jumps over the lazy dog'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            tmp1 = f.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            tmp2 = f.name
        try:
            assert compute_file_hash(tmp1) == compute_file_hash(tmp2)
        finally:
            os.unlink(tmp1)
            os.unlink(tmp2)

    def test_different_content_different_hash(self):
        """Different content produces different hash."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('alpha')
            tmp1 = f.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('beta')
            tmp2 = f.name
        try:
            assert compute_file_hash(tmp1) != compute_file_hash(tmp2)
        finally:
            os.unlink(tmp1)
            os.unlink(tmp2)

    def test_nonexistent_file_returns_none(self):
        """compute_file_hash returns None for nonexistent file."""
        assert compute_file_hash('/nonexistent/path/file.txt') is None


class TestComputeDirHash:
    """Tests for compute_dir_hash."""

    def test_aggregates_txt_files(self):
        """compute_dir_hash returns {filename: hash} for all .txt files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .txt files
            with open(os.path.join(tmpdir, 'a.txt'), 'w') as f:
                f.write('content a')
            with open(os.path.join(tmpdir, 'b.txt'), 'w') as f:
                f.write('content b')
            # Create a non-.txt file — should be ignored
            with open(os.path.join(tmpdir, 'c.log'), 'w') as f:
                f.write('log content')

            result = compute_dir_hash(tmpdir)
            assert isinstance(result, dict)
            assert 'a.txt' in result
            assert 'b.txt' in result
            assert 'c.log' not in result
            assert len(result['a.txt']) == 64
            assert len(result['b.txt']) == 64

    def test_empty_dir_returns_empty_dict(self):
        """Empty directory returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert compute_dir_hash(tmpdir) == {}


class TestHashStorage:
    """Tests for hash_storage context manager."""

    def test_save_and_load(self):
        """hash_storage saves and loads hash dict as JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            tmp = f.name
        try:
            # Load existing, modify, save
            with hash_storage(tmp) as hashes:
                assert hashes == {}
                hashes['chapter1.txt'] = 'a' * 64
                hashes['chapter2.txt'] = 'b' * 64

            # Verify saved to disk
            with open(tmp, 'r') as f:
                data = json.load(f)
            assert data == {'chapter1.txt': 'a' * 64, 'chapter2.txt': 'b' * 64}

            # Load again and verify
            with hash_storage(tmp) as hashes:
                assert hashes == {'chapter1.txt': 'a' * 64, 'chapter2.txt': 'b' * 64}
        finally:
            os.unlink(tmp)

    def test_creates_file_if_not_exists(self):
        """hash_storage creates the JSON file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, 'hashes.json')
            assert not os.path.exists(storage_path)

            with hash_storage(storage_path) as hashes:
                assert hashes == {}
                hashes['key'] = 'value'

            # File should now exist
            assert os.path.exists(storage_path)
            with open(storage_path, 'r') as f:
                data = json.load(f)
            assert data == {'key': 'value'}