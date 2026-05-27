#!/usr/bin/env python3
"""
Unit tests for file_log_reader.py
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from soar_lab.infrastructure.file_log_reader import FileLogReader


class TestFileLogReader:
    """Test FileLogReader infrastructure adapter"""

    def test_initialization_success(self):
        """Test successful initialization with path_service"""
        mock_path_service = Mock()
        
        reader = FileLogReader(path_service=mock_path_service)
        
        assert reader._path_service == mock_path_service

    def test_requires_path_service(self):
        """Test that path_service is required"""
        with pytest.raises(ValueError, match="path_service is required"):
            FileLogReader(path_service=None)

    def test_read_log_file_success(self, tmp_path):
        """Test successful log file reading"""
        mock_path_service = Mock()
        reader = FileLogReader(path_service=mock_path_service)
        
        log_file = tmp_path / "test.log"
        log_file.write_text("log line 1\nlog line 2\nlog line 3", encoding='utf-8')
        
        content = reader.read_log_file(str(log_file))
        
        assert content == "log line 1\nlog line 2\nlog line 3"

    def test_read_log_file_not_exists(self):
        """Test reading a non-existent log file"""
        mock_path_service = Mock()
        reader = FileLogReader(path_service=mock_path_service)
        
        content = reader.read_log_file("/nonexistent/path.log")
        
        assert content == ""

    def test_read_log_file_exception(self, tmp_path):
        """Test reading log file raises exception"""
        mock_path_service = Mock()
        reader = FileLogReader(path_service=mock_path_service)
        
        # Create a directory instead of a file to trigger read error
        log_dir = tmp_path / "log_dir"
        log_dir.mkdir()
        
        content = reader.read_log_file(str(log_dir))
        
        assert content == ""

    def test_read_log_file_empty(self, tmp_path):
        """Test reading an empty log file"""
        mock_path_service = Mock()
        reader = FileLogReader(path_service=mock_path_service)
        
        log_file = tmp_path / "empty.log"
        log_file.write_text("", encoding='utf-8')
        
        content = reader.read_log_file(str(log_file))
        
        assert content == ""

    def test_get_default_log_path(self):
        """Test getting default log path"""
        mock_path_service = Mock()
        mock_path_service.notify_log_file = Path("/default/path/notify.log")
        
        reader = FileLogReader(path_service=mock_path_service)
        
        default_path = reader.get_default_log_path()
        
        # Handle Windows path separators
        assert "notify.log" in default_path
        assert "default" in default_path
        assert "path" in default_path
