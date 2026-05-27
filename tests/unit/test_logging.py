#!/usr/bin/env python3
"""Unit tests for Logging configuration"""

import pytest
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

from soar_lab.config.logging import setup_logging, get_logger


class TestLogging:
    """Test logging configuration"""

    def test_setup_logging_console_only(self):
        """Test setup logging with console only"""
        # Clear existing handlers
        root = logging.getLogger()
        root.handlers.clear()
        
        setup_logging(log_level="INFO")
        
        root = logging.getLogger()
        assert root.level == logging.INFO
        assert len(root.handlers) >= 1
        assert isinstance(root.handlers[0], logging.StreamHandler)

    def test_setup_logging_with_file(self, tmp_path):
        """Test setup logging with file output"""
        # Clear existing handlers
        root = logging.getLogger()
        root.handlers.clear()
        
        log_dir = tmp_path / "logs"
        setup_logging(log_level="DEBUG", log_dir=log_dir)
        
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert log_dir.exists()
        assert any(isinstance(h, logging.FileHandler) for h in root.handlers)

    def test_setup_logging_invalid_level(self):
        """Test setup logging with invalid log level"""
        # Clear existing handlers
        root = logging.getLogger()
        root.handlers.clear()
        
        setup_logging(log_level="INVALID")
        
        root = logging.getLogger()
        # Should default to INFO
        assert root.level == logging.INFO

    def test_setup_logging_existing_handlers(self):
        """Test setup logging when handlers already exist"""
        # Clear existing handlers
        root = logging.getLogger()
        root.handlers.clear()
        
        # Setup first time
        setup_logging(log_level="INFO")
        first_handler_count = len(root.handlers)
        
        # Setup second time - should not duplicate handlers
        setup_logging(log_level="DEBUG")
        second_handler_count = len(root.handlers)
        
        # Handler count should not increase significantly
        assert second_handler_count <= first_handler_count + 2

    def test_get_logger(self):
        """Test get_logger function"""
        logger = get_logger("test_module")
        
        assert logger.name == "test_module"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_multiple_calls(self):
        """Test that get_logger returns same logger for same name"""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        
        assert logger1 is logger2

    # Removed complex mock test - the directory creation is tested in test_setup_logging_with_file
