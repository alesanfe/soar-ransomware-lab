#!/usr/bin/env python3
"""
Unit tests for checksum_utils.py
Tests file checksum calculation functionality
"""

import pytest
import tempfile
from pathlib import Path

from soar_lab.infrastructure.checksum_utils import calculate_file_checksum


class TestCalculateFileChecksum:
    """Test calculate_file_checksum function"""

    def test_calculate_checksum_with_string_path(self):
        """Test checksum calculation with string path"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            checksum = calculate_file_checksum(temp_path)
            assert isinstance(checksum, str)
            assert len(checksum) == 64  # SHA-256 hex digest length
        finally:
            Path(temp_path).unlink()

    def test_calculate_checksum_with_path_object(self):
        """Test checksum calculation with Path object"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            checksum = calculate_file_checksum(temp_path)
            assert isinstance(checksum, str)
            assert len(checksum) == 64
        finally:
            temp_path.unlink()

    def test_calculate_checksum_consistent(self):
        """Test that checksum is consistent for same file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("consistent content")
            temp_path = f.name

        try:
            checksum1 = calculate_file_checksum(temp_path)
            checksum2 = calculate_file_checksum(temp_path)
            assert checksum1 == checksum2
        finally:
            Path(temp_path).unlink()

    def test_calculate_checksum_different_content(self):
        """Test that checksum differs for different content"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("content1")
            temp_path1 = f.name

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("content2")
            temp_path2 = f.name

        try:
            checksum1 = calculate_file_checksum(temp_path1)
            checksum2 = calculate_file_checksum(temp_path2)
            assert checksum1 != checksum2
        finally:
            Path(temp_path1).unlink()
            Path(temp_path2).unlink()

    def test_calculate_checksum_file_not_found(self):
        """Test checksum calculation with non-existent file"""
        with pytest.raises(FileNotFoundError):
            calculate_file_checksum("/nonexistent/file.txt")

    def test_calculate_checksum_large_file(self):
        """Test checksum calculation with large file"""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            # Write 1MB of data
            f.write(b"x" * (1024 * 1024))
            temp_path = f.name

        try:
            checksum = calculate_file_checksum(temp_path)
            assert isinstance(checksum, str)
            assert len(checksum) == 64
        finally:
            Path(temp_path).unlink()
