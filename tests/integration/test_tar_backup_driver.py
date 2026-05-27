#!/usr/bin/env python3
"""
Unit tests for tar_backup_driver.py
"""

import pytest
from unittest.mock import Mock, patch

from soar_lab.infrastructure.tar_backup_driver import TarBackupDriver
from soar_lab.exceptions import BackupError


class TestTarBackupDriver:
    """Test TarBackupDriver infrastructure adapter"""

    def test_initialization(self):
        """Test successful initialization"""
        driver = TarBackupDriver(timeout=300)
        
        assert driver._runner is not None
        assert driver._runner.default_timeout == 300

    def test_initialization_default_timeout(self):
        """Test initialization with default timeout"""
        driver = TarBackupDriver()
        
        assert driver._runner.default_timeout == 600

    @patch('soar_lab.infrastructure.tar_backup_driver.SubprocessRunner')
    def test_create_success(self, mock_runner_class):
        """Test successful backup creation"""
        mock_runner = Mock()
        mock_result = Mock()
        mock_result.returncode = 0
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner
        
        driver = TarBackupDriver()
        driver.create("/source", "/dest/backup.tar.gz")
        
        mock_runner.run.assert_called_once()
        call_args = mock_runner.run.call_args
        assert call_args[1]['cwd'] == "/source"
        assert call_args[1]['raise_on_error'] == True
        assert 'tar' in call_args[0][0]
        assert '-czf' in call_args[0][0]
        assert '/dest/backup.tar.gz' in call_args[0][0]

    @patch('soar_lab.infrastructure.tar_backup_driver.SubprocessRunner')
    def test_create_failure(self, mock_runner_class):
        """Test backup creation failure"""
        mock_runner = Mock()
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "tar error"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner
        
        driver = TarBackupDriver()
        
        with pytest.raises(BackupError, match="tar create failed"):
            driver.create("/source", "/dest/backup.tar.gz")

    @patch('soar_lab.infrastructure.tar_backup_driver.SubprocessRunner')
    def test_extract_success(self, mock_runner_class):
        """Test successful backup extraction"""
        mock_runner = Mock()
        mock_result = Mock()
        mock_result.returncode = 0
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner
        
        driver = TarBackupDriver()
        driver.extract("/backup.tar.gz", "/dest")
        
        mock_runner.run.assert_called_once()
        call_args = mock_runner.run.call_args
        assert call_args[1]['cwd'] == "/dest"
        assert call_args[1]['raise_on_error'] == True
        assert 'tar' in call_args[0][0]
        assert '-xzf' in call_args[0][0]
        assert '/backup.tar.gz' in call_args[0][0]

    @patch('soar_lab.infrastructure.tar_backup_driver.SubprocessRunner')
    def test_extract_failure(self, mock_runner_class):
        """Test backup extraction failure"""
        mock_runner = Mock()
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "extract error"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner
        
        driver = TarBackupDriver()
        
        with pytest.raises(BackupError, match="tar extract failed"):
            driver.extract("/backup.tar.gz", "/dest")
