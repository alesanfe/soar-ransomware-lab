#!/usr/bin/env python3
"""Unit tests for tar_backup_driver module.

Consolidated from tests/integration/test_tar_backup_driver.py (which was a
duplicate — mock-based tests belong in unit/, not integration/).
"""

from unittest.mock import Mock, patch

import pytest

from soar_lab.common.exceptions import BackupError
from soar_lab.infrastructure.tar_backup_driver import (
    TarBackupDriver,
    _read_only_mounts,
)


class TestTarBackupDriver:
    """Tests for TarBackupDriver class."""

    def test_initialization(self):
        """Test initialization with default timeout."""
        driver = TarBackupDriver()

        assert driver._runner is not None
        assert driver._runner.default_timeout == 600

    def test_initialization_custom_timeout(self):
        """Test initialization with custom timeout."""
        driver = TarBackupDriver(timeout=300)

        assert driver._runner is not None
        assert driver._runner.default_timeout == 300

    @patch("soar_lab.infrastructure.tar_backup_driver.SubprocessRunner")
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
        assert call_args[1]["cwd"] == "/source/dir"
        assert call_args[1]["raise_on_error"] is False
        assert "tar" in call_args[0][0]
        assert "-czf" in call_args[0][0]
        assert "/dest/backup.tar.gz" in call_args[0][0]

    @patch("soar_lab.infrastructure.tar_backup_driver.SubprocessRunner")
    def test_create_failure(self, mock_runner_class):
        """Test backup creation failure."""
        mock_runner = Mock()
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "tar: error"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        driver = TarBackupDriver()

        with pytest.raises(BackupError, match="tar create failed"):
            driver.create("/source/dir", "/dest/backup.tar.gz")

    @patch("soar_lab.infrastructure.tar_backup_driver.SubprocessRunner")
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

        # P0.3: verify (tar -tzf) runs before extract — two subprocess calls.
        assert mock_runner.run.call_count == 2
        assert "-tzf" in mock_runner.run.call_args_list[0][0][0]
        call_args = mock_runner.run.call_args
        assert call_args[1]["cwd"] == "/dest/dir"
        assert call_args[1]["raise_on_error"] is False
        assert "tar" in call_args[0][0]
        assert "-xzf" in call_args[0][0]
        assert "/source/backup.tar.gz" in call_args[0][0]

    @patch("soar_lab.infrastructure.tar_backup_driver.SubprocessRunner")
    def test_extract_failure(self, mock_runner_class):
        """Test backup extraction failure."""
        mock_runner = Mock()
        # Verify (tar -tzf) passes, extract (-xzf) fails.
        mock_runner.run.side_effect = [
            Mock(returncode=0, stderr=""),
            Mock(returncode=1, stderr="tar: error"),
        ]
        mock_runner_class.return_value = mock_runner

        driver = TarBackupDriver()

        with pytest.raises(BackupError, match="tar extract failed"):
            driver.extract("/source/backup.tar.gz", "/dest/dir")

    @patch("soar_lab.infrastructure.tar_backup_driver.SubprocessRunner")
    def test_extract_must_overwrite_existing_files(self, mock_runner_class):
        """Bug: --skip-old-files made restore a no-op for files that
        already exist — a restore must overwrite."""
        mock_runner = Mock()
        mock_runner.run.return_value = Mock(returncode=0, stderr="")
        mock_runner_class.return_value = mock_runner

        TarBackupDriver().extract("/src/b.tar.gz", "/dest")
        args = mock_runner.run.call_args[0][0]
        assert "--skip-old-files" not in args
        assert "--keep-old-files" not in args

    def test_read_only_mounts_detected(self, tmp_path, monkeypatch):
        """BUG-074: restore must skip bind mounts marked ro in
        /proc/mounts or tar fails with Read-only file system."""
        mounts = (
            "tmpfs /app rw 0 0\n"
            "drvfs /app/infra drvfs ro,noatime 0 0\n"
            "drvfs /app/docs drvfs ro,noatime 0 0\n"
            "drvfs /app/src drvfs rw,noatime 0 0\n"
            "drvfs /other drvfs ro 0 0\n"
        )
        monkeypatch.setattr("builtins.open", lambda *a, **k: __import__("io").StringIO(mounts))
        monkeypatch.setattr("os.path.realpath", lambda p: p)
        result = _read_only_mounts("/app")
        assert sorted(result) == ["docs", "infra"]

    @patch("soar_lab.infrastructure.tar_backup_driver._read_only_mounts")
    @patch("soar_lab.infrastructure.tar_backup_driver.SubprocessRunner")
    def test_extract_excludes_ro_mounts(self, mock_runner_class, mock_ro):
        """BUG-074: extract adds --exclude for each read-only mount."""
        mock_runner = Mock()
        mock_runner.run.return_value = Mock(returncode=0, stderr="")
        mock_runner_class.return_value = mock_runner
        mock_ro.return_value = ["infra", "docs"]

        TarBackupDriver().extract("/src/b.tar.gz", "/app")
        args = mock_runner.run.call_args[0][0]
        assert "--exclude=./infra" in args
        assert "--exclude=./docs" in args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
