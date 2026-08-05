#!/usr/bin/env python3
"""
Unit tests for tar_backup_driver module
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.infrastructure.tar_backup_driver import TarBackupDriver


class TestTarBackupDriver:
    """Tests for TarBackupDriver class."""

    def test_initialization(self):
        """Test initialization with default timeout."""
        driver = TarBackupDriver()

        assert driver._runner is not None

    def test_initialization_custom_timeout(self):
        """Test initialization with custom timeout."""
        driver = TarBackupDriver(timeout=300)

        assert driver._runner is not None

    @patch('soar_lab.infrastructure.tar_backup_driver.SubprocessRunner')
    def test_create_success(self, mock_runner_class):
        """Test successful backup creation."""
        mock_runner = Mock()
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        driver = TarBackupDriver()
        driver.create("/source/dir", "/dest/backup.tar.gz")

        mock_runner.run.assert_called_once()
        call_args = mock_runner.run.call_args
        assert call_args[1]['cwd'] == "/source/dir"
        assert call_args[1]['raise_on_error'] == False
        assert 'tar' in call_args[0][0]
        assert '-czf' in call_args[0][0]
        assert '/dest/backup.tar.gz' in call_args[0][0]

    @patch('soar_lab.infrastructure.tar_backup_driver.SubprocessRunner')
    def test_create_failure(self, mock_runner_class):
        """Test backup creation failure."""
        from soar_lab.common.exceptions import BackupError

        mock_runner = Mock()
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "tar: error"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        driver = TarBackupDriver()

        with pytest.raises(BackupError, match="tar create failed"):
            driver.create("/source/dir", "/dest/backup.tar.gz")

    @patch('soar_lab.infrastructure.tar_backup_driver.SubprocessRunner')
    def test_extract_success(self, mock_runner_class):
        """Test successful backup extraction."""
        mock_runner = Mock()
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        driver = TarBackupDriver()
        driver.extract("/source/backup.tar.gz", "/dest/dir")

        mock_runner.run.assert_called_once()
        call_args = mock_runner.run.call_args
        assert call_args[1]['cwd'] == "/dest/dir"
        assert call_args[1]['raise_on_error'] == False
        assert 'tar' in call_args[0][0]
        assert '-xzf' in call_args[0][0]
        assert '/source/backup.tar.gz' in call_args[0][0]

    @patch('soar_lab.infrastructure.tar_backup_driver.SubprocessRunner')
    def test_extract_failure(self, mock_runner_class):
        """Test backup extraction failure."""
        from soar_lab.common.exceptions import BackupError

        mock_runner = Mock()
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "tar: error"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        driver = TarBackupDriver()

        with pytest.raises(BackupError, match="tar extract failed"):
            driver.extract("/source/backup.tar.gz", "/dest/dir")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
