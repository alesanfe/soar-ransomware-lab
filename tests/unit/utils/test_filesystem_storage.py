#!/usr/bin/env python3
"""Unit tests for FilesystemStorage."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from soar_lab.infrastructure.filesystem_storage import FilesystemStorage


class TestFilesystemStorage:
    """Test FilesystemStorage with temporary directory."""

    def test_init_with_base_dir(self, tmp_path):
        """Test initialization with base directory."""
        storage = FilesystemStorage(str(tmp_path))

        assert storage._base == tmp_path
        assert tmp_path.exists()

    def test_write_and_read(self, tmp_path):
        """Test write and read operations."""
        storage = FilesystemStorage(str(tmp_path))

        storage.write("test/file.txt", b"test data")
        result = storage.read("test/file.txt")

        assert result == b"test data"
        assert (tmp_path / "test" / "file.txt").exists()

    def test_exists(self, tmp_path):
        """Test exists operation."""
        storage = FilesystemStorage(str(tmp_path))

        assert not storage.exists("nonexistent.txt")

        storage.write("existing.txt", b"data")
        assert storage.exists("existing.txt")

    def test_list_keys(self, tmp_path):
        """Test list_keys operation."""
        storage = FilesystemStorage(str(tmp_path))

        storage.write("test1.txt", b"data1")
        storage.write("test2.txt", b"data2")
        storage.write("other.txt", b"data3")

        keys = storage.list_keys("test")

        assert len(keys) == 2
        assert "test1.txt" in keys
        assert "test2.txt" in keys

    def test_delete(self, tmp_path):
        """Test delete operation."""
        storage = FilesystemStorage(str(tmp_path))

        storage.write("to_delete.txt", b"data")
        assert storage.exists("to_delete.txt")

        storage.delete("to_delete.txt")
        assert not storage.exists("to_delete.txt")

    def test_delete_nonexistent(self, tmp_path):
        """Test delete operation on nonexistent file."""
        storage = FilesystemStorage(str(tmp_path))

        # Should not raise error
        storage.delete("nonexistent.txt")

    def test_ensure_directory_exists(self, tmp_path):
        """Test ensure_directory_exists."""
        storage = FilesystemStorage(str(tmp_path))

        new_dir = str(tmp_path / "new" / "nested" / "dir")
        storage.ensure_directory_exists(new_dir)

        assert Path(new_dir).exists()
        assert Path(new_dir).is_dir()

    def test_get_file_size(self, tmp_path):
        """Test get_file_size."""
        storage = FilesystemStorage(str(tmp_path))

        storage.write("size_test.txt", b"test data")
        file_path = str(tmp_path / "size_test.txt")

        size = storage.get_file_size(file_path)

        assert size == 9  # len(b"test data")

    def test_directory_exists(self, tmp_path):
        """Test directory_exists."""
        storage = FilesystemStorage(str(tmp_path))

        assert storage.directory_exists(str(tmp_path))
        assert not storage.directory_exists(str(tmp_path / "nonexistent"))

        (tmp_path / "new_dir").mkdir()
        assert storage.directory_exists(str(tmp_path / "new_dir"))

    def test_file_exists(self, tmp_path):
        """Test file_exists."""
        storage = FilesystemStorage(str(tmp_path))

        storage.write("file.txt", b"data")

        assert storage.file_exists(str(tmp_path / "file.txt"))
        assert not storage.file_exists(str(tmp_path / "nonexistent.txt"))

    def test_list_files(self, tmp_path):
        """Test list_files."""
        storage = FilesystemStorage(str(tmp_path))

        (tmp_path / "file1.txt").write_text("data1")
        (tmp_path / "file2.txt").write_text("data2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("data3")

        files = storage.list_files(str(tmp_path), "*.txt")

        assert len(files) == 2
        assert "file1.txt" in files
        assert "file2.txt" in files

    def test_get_file_info(self, tmp_path):
        """Test get_file_info."""
        storage = FilesystemStorage(str(tmp_path))

        storage.write("info_test.txt", b"data")
        file_path = str(tmp_path / "info_test.txt")

        info = storage.get_file_info(file_path)

        assert info is not None
        assert "size" in info
        assert "modified_time" in info
        assert "created_time" in info
        assert info["size"] == 4

    def test_get_file_info_nonexistent(self, tmp_path):
        """Test get_file_info for nonexistent file."""
        storage = FilesystemStorage(str(tmp_path))

        info = storage.get_file_info(str(tmp_path / "nonexistent.txt"))

        assert info is None

    def test_delete_file(self, tmp_path):
        """Test delete_file."""
        storage = FilesystemStorage(str(tmp_path))

        storage.write("to_delete.txt", b"data")
        file_path = str(tmp_path / "to_delete.txt")

        result = storage.delete_file(file_path)

        assert result is True
        assert not Path(file_path).exists()

    def test_delete_file_nonexistent(self, tmp_path):
        """Test delete_file for nonexistent file."""
        storage = FilesystemStorage(str(tmp_path))

        result = storage.delete_file(str(tmp_path / "nonexistent.txt"))

        assert result is True  # missing_ok=True

    def test_store_backup_metadata(self, tmp_path):
        """Test store_backup_metadata (placeholder)"""
        storage = FilesystemStorage(str(tmp_path))

        # Should not raise error (placeholder implementation)
        storage.store_backup_metadata("backup.tar.gz", {"key": "value"})

    def test_log_restore_operation(self, tmp_path):
        """Test log_restore_operation (placeholder)"""
        storage = FilesystemStorage(str(tmp_path))

        # Should not raise error (placeholder implementation)
        storage.log_restore_operation("backup.tar.gz", {"key": "value"})

    def test_get_base_directory(self, tmp_path):
        """Test get_base_directory."""
        storage = FilesystemStorage(str(tmp_path))

        assert storage.get_base_directory() == str(tmp_path)

    def test_init_with_config_provider(self, tmp_path):
        """Test initialization with config_provider."""
        mock_config = Mock()
        mock_config.get.return_value = str(tmp_path)

        storage = FilesystemStorage(config_provider=mock_config)

        assert storage._base == tmp_path
        mock_config.get.assert_called_once_with("base_dir", ".")

    def test_init_without_base_dir_or_config(self):
        """Test initialization without base_dir or config_provider raises
        ValueError."""
        with pytest.raises(ValueError, match="base_dir or config_provider must be supplied"):
            FilesystemStorage()

    def test_read_file_exception(self, tmp_path):
        """Test read_file when file cannot be read."""
        storage = FilesystemStorage(str(tmp_path))

        result = storage.read_file("nonexistent.txt")

        assert result is None

    def test_delete_file_exception(self, tmp_path):
        """Test delete_file when exception occurs."""
        storage = FilesystemStorage(str(tmp_path))

        # Create a directory instead of a file to cause error
        (tmp_path / "dir").mkdir()

        result = storage.delete_file(str(tmp_path / "dir"))

        assert result is False

    def test_get_backup_directory_without_config_provider(self, tmp_path):
        """Test get_backup_directory without config_provider raises
        ValueError."""
        storage = FilesystemStorage(str(tmp_path))

        with pytest.raises(ValueError, match="config_provider is required"):
            storage.get_backup_directory()

    def test_get_backup_directory_with_config_provider(self, tmp_path):
        """Test get_backup_directory with config_provider."""
        mock_config = Mock()
        mock_config.get.return_value = str(tmp_path / "backups")

        storage = FilesystemStorage(str(tmp_path), config_provider=mock_config)

        result = storage.get_backup_directory()

        assert result == str(tmp_path / "backups")
        mock_config.get.assert_called_once_with("BACKUP_DIR", str(tmp_path / "backups"))

    def test_join_path(self, tmp_path):
        """Test join_path."""
        storage = FilesystemStorage(str(tmp_path))

        result = storage.join_path("dir1", "dir2", "file.txt")

        assert result == str(Path("dir1", "dir2", "file.txt"))
