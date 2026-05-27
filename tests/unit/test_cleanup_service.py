#!/usr/bin/env python3
"""
Unit tests for cleanup_service.py
"""

import pytest
from unittest.mock import Mock
from pathlib import Path
from datetime import datetime, timezone, timedelta

from soar_lab.infrastructure.cleanup_service import CleanupService


class TestCleanupService:
    """Test CleanupService infrastructure adapter"""

    def test_initialization_success(self):
        """Test successful initialization with path_service"""
        mock_path_service = Mock()
        
        service = CleanupService(path_service=mock_path_service)
        
        assert service._path_service == mock_path_service
        assert service._config_provider is None

    def test_initialization_with_config_provider(self):
        """Test initialization with config_provider"""
        mock_path_service = Mock()
        mock_config_provider = Mock()
        
        service = CleanupService(path_service=mock_path_service, config_provider=mock_config_provider)
        
        assert service._path_service == mock_path_service
        assert service._config_provider == mock_config_provider

    def test_requires_path_service(self):
        """Test that path_service is required"""
        with pytest.raises(ValueError, match="path_service is required"):
            CleanupService(path_service=None)

    def test_cleanup_old_artifacts_default_retention(self, tmp_path):
        """Test cleanup with default retention days"""
        mock_path_service = Mock()
        mock_path_service.backup_dir = tmp_path / "backups"
        mock_path_service.results_dir = tmp_path / "results"
        mock_path_service.logs_dir = tmp_path / "logs"
        
        # Create directories
        mock_path_service.backup_dir.mkdir()
        mock_path_service.results_dir.mkdir()
        mock_path_service.logs_dir.mkdir()
        
        # Create old files - use a very old timestamp to ensure they're cleaned
        old_backup = mock_path_service.backup_dir / "old.tar.gz"
        old_backup.write_text("backup")
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=100)).timestamp()
        old_backup.touch(old_timestamp)
        
        old_result = mock_path_service.results_dir / "old.json"
        old_result.write_text("result")
        old_result.touch(old_timestamp)
        
        old_log = mock_path_service.logs_dir / "old.log"
        old_log.write_text("log")
        old_log.touch(old_timestamp)
        
        # Create new files
        new_backup = mock_path_service.backup_dir / "new.tar.gz"
        new_backup.write_text("backup")
        new_backup.touch((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
        
        service = CleanupService(path_service=mock_path_service)
        result = service.cleanup_old_artifacts()
        
        # At minimum, verify the structure of the response
        assert "backups_cleaned" in result
        assert "results_cleaned" in result
        assert "logs_cleaned" in result
        assert isinstance(result["backups_cleaned"], int)
        assert isinstance(result["results_cleaned"], int)
        assert isinstance(result["logs_cleaned"], int)

    def test_cleanup_old_artifacts_custom_retention(self, tmp_path):
        """Test cleanup with custom retention days"""
        mock_path_service = Mock()
        mock_path_service.backup_dir = tmp_path / "backups"
        mock_path_service.results_dir = tmp_path / "results"
        mock_path_service.logs_dir = tmp_path / "logs"
        
        # Create directories
        mock_path_service.backup_dir.mkdir()
        mock_path_service.results_dir.mkdir()
        mock_path_service.logs_dir.mkdir()
        
        # Create file
        old_backup = mock_path_service.backup_dir / "old.tar.gz"
        old_backup.write_text("backup")
        old_backup.touch((datetime.now(timezone.utc) - timedelta(days=20)).timestamp())
        
        service = CleanupService(path_service=mock_path_service)
        result = service.cleanup_old_artifacts(retention_days=10)
        
        # Verify the structure of the response
        assert "backups_cleaned" in result
        assert isinstance(result["backups_cleaned"], int)

    def test_cleanup_old_artifacts_with_config_provider(self, tmp_path):
        """Test cleanup with config_provider for retention days"""
        mock_path_service = Mock()
        mock_path_service.backup_dir = tmp_path / "backups"
        mock_path_service.results_dir = tmp_path / "results"
        mock_path_service.logs_dir = tmp_path / "logs"
        
        # Create directories
        mock_path_service.backup_dir.mkdir()
        mock_path_service.results_dir.mkdir()
        mock_path_service.logs_dir.mkdir()
        
        mock_config_provider = Mock()
        mock_config_provider.get.return_value = 15
        
        # Create file
        old_backup = mock_path_service.backup_dir / "old.tar.gz"
        old_backup.write_text("backup")
        old_backup.touch((datetime.now(timezone.utc) - timedelta(days=20)).timestamp())
        
        service = CleanupService(path_service=mock_path_service, config_provider=mock_config_provider)
        result = service.cleanup_old_artifacts()
        
        # Verify config_provider was called
        mock_config_provider.get.assert_called_once_with('retention_days', 30)
        # Verify the structure of the response
        assert "backups_cleaned" in result
        assert isinstance(result["backups_cleaned"], int)

    def test_cleanup_directory_not_exists(self):
        """Test cleanup when directory doesn't exist"""
        mock_path_service = Mock()
        mock_path_service.backup_dir = Path("/nonexistent")
        
        service = CleanupService(path_service=mock_path_service)
        result = service._cleanup_directory(mock_path_service.backup_dir, datetime.now(timezone.utc), "*.tar.gz")
        
        assert result == 0

    def test_cleanup_directory_no_files(self, tmp_path):
        """Test cleanup when directory has no matching files"""
        mock_path_service = Mock()
        mock_path_service.backup_dir = tmp_path / "backups"
        mock_path_service.backup_dir.mkdir()
        
        service = CleanupService(path_service=mock_path_service)
        result = service._cleanup_directory(mock_path_service.backup_dir, datetime.now(timezone.utc), "*.tar.gz")
        
        assert result == 0

    def test_get_artifact_stats(self, tmp_path):
        """Test getting artifact statistics"""
        mock_path_service = Mock()
        mock_path_service.backup_dir = tmp_path / "backups"
        mock_path_service.results_dir = tmp_path / "results"
        mock_path_service.logs_dir = tmp_path / "logs"
        
        # Create directories
        mock_path_service.backup_dir.mkdir()
        mock_path_service.results_dir.mkdir()
        mock_path_service.logs_dir.mkdir()
        
        # Create files
        (mock_path_service.backup_dir / "backup1.tar.gz").write_text("x" * 1024 * 1024)  # 1MB
        (mock_path_service.results_dir / "result1.json").write_text("x" * 512 * 1024)  # 0.5MB
        (mock_path_service.logs_dir / "log1.log").write_text("x" * 256 * 1024)  # 0.25MB
        
        service = CleanupService(path_service=mock_path_service)
        stats = service.get_artifact_stats()
        
        assert stats["backups"]["count"] == 1
        assert stats["results"]["count"] == 1
        assert stats["logs"]["count"] == 1
        assert stats["total"]["count"] == 3
        assert stats["total"]["size_mb"] == pytest.approx(1.75, rel=0.1)

    def test_get_artifact_stats_directory_not_exists(self):
        """Test getting stats when directory doesn't exist"""
        mock_path_service = Mock()
        mock_path_service.backup_dir = Path("/nonexistent")
        mock_path_service.results_dir = Path("/nonexistent2")
        mock_path_service.logs_dir = Path("/nonexistent3")
        
        service = CleanupService(path_service=mock_path_service)
        stats = service.get_artifact_stats()
        
        assert stats["backups"]["count"] == 0
        assert stats["backups"]["size_mb"] == 0.0
        assert stats["total"]["count"] == 0
        assert stats["total"]["size_mb"] == 0.0

    def test_get_directory_stats_no_files(self, tmp_path):
        """Test getting directory stats with no files"""
        mock_path_service = Mock()
        mock_path_service.backup_dir = tmp_path / "backups"
        mock_path_service.backup_dir.mkdir()
        
        service = CleanupService(path_service=mock_path_service)
        stats = service._get_directory_stats(mock_path_service.backup_dir, "*.tar.gz")
        
        assert stats["count"] == 0
        assert stats["size_mb"] == 0.0
