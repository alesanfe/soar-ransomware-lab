#!/usr/bin/env python3
"""
Unit tests for in_memory_storage.py
"""

import pytest

from soar_lab.infrastructure.in_memory_storage import InMemoryStorage


class TestInMemoryStorage:
    """Test InMemoryStorage infrastructure adapter"""

    def test_initialization(self):
        """Test initialization creates empty storage"""
        storage = InMemoryStorage()

        assert storage._store == {}
        assert storage._file_info == {}
        assert storage._directories == set()

    def test_write(self):
        """Test write stores data and metadata"""
        storage = InMemoryStorage()
        data = b"test data"

        storage.write("test.txt", data)

        assert storage._store["test.txt"] == data
        assert storage._file_info["test.txt"]["size"] == len(data)
        assert "modified_time" in storage._file_info["test.txt"]
        assert "created_time" in storage._file_info["test.txt"]

    def test_read(self):
        """Test read retrieves stored data"""
        storage = InMemoryStorage()
        data = b"test data"
        storage.write("test.txt", data)

        result = storage.read("test.txt")

        assert result == data

    def test_read_not_found(self):
        """Test read raises FileNotFoundError for missing key"""
        storage = InMemoryStorage()

        with pytest.raises(FileNotFoundError, match="Key not found"):
            storage.read("nonexistent.txt")

    def test_exists(self):
        """Test exists checks if key exists"""
        storage = InMemoryStorage()
        storage.write("test.txt", b"data")

        assert storage.exists("test.txt") is True
        assert storage.exists("nonexistent.txt") is False

    def test_list_keys(self):
        """Test list_keys returns keys with prefix"""
        storage = InMemoryStorage()
        storage.write("dir1/file1.txt", b"data1")
        storage.write("dir1/file2.txt", b"data2")
        storage.write("dir2/file3.txt", b"data3")

        keys = storage.list_keys("dir1/")

        assert len(keys) == 2
        assert "dir1/file1.txt" in keys
        assert "dir1/file2.txt" in keys

    def test_list_keys_empty_prefix(self):
        """Test list_keys with empty prefix returns all keys"""
        storage = InMemoryStorage()
        storage.write("file1.txt", b"data1")
        storage.write("file2.txt", b"data2")

        keys = storage.list_keys()

        assert len(keys) == 2

    def test_delete(self):
        """Test delete removes key and metadata"""
        storage = InMemoryStorage()
        storage.write("test.txt", b"data")

        storage.delete("test.txt")

        assert "test.txt" not in storage._store
        assert "test.txt" not in storage._file_info

    def test_delete_nonexistent(self):
        """Test delete nonexistent key does not raise error"""
        storage = InMemoryStorage()

        storage.delete("nonexistent.txt")  # Should not raise

    def test_clear(self):
        """Test clear removes all data"""
        storage = InMemoryStorage()
        storage.write("file1.txt", b"data1")
        storage.write("file2.txt", b"data2")
        storage.ensure_directory_exists("/dir")

        storage.clear()

        assert storage._store == {}
        assert storage._file_info == {}
        assert storage._directories == set()

    def test_ensure_directory_exists(self):
        """Test ensure_directory_exists adds directory"""
        storage = InMemoryStorage()

        storage.ensure_directory_exists("/test/dir")

        assert "/test/dir" in storage._directories

    def test_get_file_size(self):
        """Test get_file_size returns file size"""
        storage = InMemoryStorage()
        storage.write("test.txt", b"test data")

        size = storage.get_file_size("test.txt")

        assert size == 9  # len(b"test data")

    def test_get_file_size_nonexistent(self):
        """Test get_file_size returns 0 for nonexistent file"""
        storage = InMemoryStorage()

        size = storage.get_file_size("nonexistent.txt")

        assert size == 0

    def test_directory_exists(self):
        """Test directory_exists checks directory"""
        storage = InMemoryStorage()
        storage.ensure_directory_exists("/test/dir")

        assert storage.directory_exists("/test/dir") is True
        assert storage.directory_exists("/nonexistent") is False

    def test_file_exists(self):
        """Test file_exists checks file"""
        storage = InMemoryStorage()
        storage.write("test.txt", b"data")

        assert storage.file_exists("test.txt") is True
        assert storage.file_exists("nonexistent.txt") is False

    def test_list_files(self):
        """Test list_files returns files in directory"""
        storage = InMemoryStorage()
        storage.write("/dir/file1.txt", b"data1")
        storage.write("/dir/file2.txt", b"data2")
        storage.write("/other/file3.txt", b"data3")

        files = storage.list_files("/dir", "*")

        assert len(files) == 2
        assert "/dir/file1.txt" in files
        assert "/dir/file2.txt" in files

    def test_list_files_with_pattern(self):
        """Test list_files with pattern filters files"""
        storage = InMemoryStorage()
        storage.write("/dir/file1.txt", b"data1")
        storage.write("/dir/file2.log", b"data2")
        storage.write("/dir/file3.txt", b"data3")

        files = storage.list_files("/dir", "*.txt")

        assert len(files) == 2
        assert "/dir/file1.txt" in files
        assert "/dir/file3.txt" in files
        assert "/dir/file2.log" not in files

    def test_get_file_info(self):
        """Test get_file_info returns file metadata"""
        storage = InMemoryStorage()
        storage.write("test.txt", b"data")

        info = storage.get_file_info("test.txt")

        assert info is not None
        assert info["size"] == 4
        assert "modified_time" in info
        assert "created_time" in info

    def test_get_file_info_nonexistent(self):
        """Test get_file_info returns None for nonexistent file"""
        storage = InMemoryStorage()

        info = storage.get_file_info("nonexistent.txt")

        assert info is None

    def test_delete_file(self):
        """Test delete_file removes file and returns True"""
        storage = InMemoryStorage()
        storage.write("test.txt", b"data")

        result = storage.delete_file("test.txt")

        assert result is True
        assert "test.txt" not in storage._store

    def test_delete_file_nonexistent(self):
        """Test delete_file returns True even for nonexistent file (delete uses pop with default)"""
        storage = InMemoryStorage()

        result = storage.delete_file("nonexistent.txt")

        # delete() uses pop with default None, so it never raises
        assert result is True

    def test_store_backup_metadata(self):
        """Test store_backup_metadata is a no-op (placeholder)"""
        storage = InMemoryStorage()

        storage.store_backup_metadata("backup.tar.gz", {"user": "test"})

        # Should not raise, just a placeholder

    def test_log_restore_operation(self):
        """Test log_restore_operation is a no-op (placeholder)"""
        storage = InMemoryStorage()

        storage.log_restore_operation("backup.tar.gz", {"user": "test"})

        # Should not raise, just a placeholder

    def test_get_backup_directory(self):
        """Test get_backup_directory returns in-memory path"""
        storage = InMemoryStorage()

        result = storage.get_backup_directory()

        assert result == "/tmp/backups"

    def test_get_base_directory(self):
        """Test get_base_directory returns in-memory path"""
        storage = InMemoryStorage()

        result = storage.get_base_directory()

        assert result == "/tmp/base"

    def test_join_path(self):
        """Test join_path joins parts with forward slash"""
        storage = InMemoryStorage()

        result = storage.join_path("dir1", "dir2", "file.txt")

        assert result == "dir1/dir2/file.txt"
