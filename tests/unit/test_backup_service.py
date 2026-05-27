#!/usr/bin/env python3
"""
Unit tests for backup_service.py
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

from soar_lab.services.backup_service import BackupService


class TestBackupService:
    """Test BackupService with mocked dependencies"""

    def test_initialization_success(self):
        """Test successful initialization"""
        mock_driver = Mock()
        mock_storage = Mock()
        
        service = BackupService(driver=mock_driver, storage=mock_storage)
        
        assert service.driver == mock_driver
        assert service.storage == mock_storage

    def test_requires_storage(self):
        """Test that storage is required"""
        with pytest.raises(ValueError, match="storage.*required"):
            BackupService(driver=Mock(), storage=None)

    def test_create_backup_success(self):
        """Test successful backup creation"""
        mock_driver = Mock()
        mock_storage = Mock()
        mock_storage.get_backup_directory.return_value = "/backups"
        mock_storage.get_base_directory.return_value = "/project"
        mock_storage.get_file_size.return_value = 1024 * 1024
        mock_storage.join_path.return_value = "/backups/soar_backup_test.tar.gz"
        
        service = BackupService(driver=mock_driver, storage=mock_storage)
        result = service.create(user="testuser")
        
        assert "filename" in result
        assert result["message"] == "Backup created successfully"
        assert "soar_backup_" in result["filename"]
        mock_driver.create.assert_called_once()
        mock_storage.ensure_directory_exists.assert_called_once_with("/backups")

    def test_create_backup_without_user(self):
        """Test backup creation without user"""
        mock_driver = Mock()
        mock_storage = Mock()
        mock_storage.get_backup_directory.return_value = "/backups"
        mock_storage.get_base_directory.return_value = "/project"
        mock_storage.get_file_size.return_value = 1024 * 1024
        mock_storage.join_path.return_value = "/backups/soar_backup_test.tar.gz"
        
        service = BackupService(driver=mock_driver, storage=mock_storage)
        result = service.create()
        
        assert result["message"] == "Backup created successfully"
        mock_driver.create.assert_called_once()

    def test_list_backups_success(self):
        """Test successful backup listing"""
        mock_driver = Mock()
        mock_storage = Mock()
        mock_storage.get_backup_directory.return_value = "/backups"
        mock_storage.directory_exists.return_value = True
        mock_storage.list_files.return_value = ["backup1.tar.gz", "backup2.tar.gz"]
        mock_storage.get_file_info.side_effect = [
            {'size': 1024 * 1024, 'modified_time': 1609459200},
            {'size': 2 * 1024 * 1024, 'modified_time': 1609459300}
        ]
        mock_storage.join_path.side_effect = ["/backups/backup1.tar.gz", "/backups/backup2.tar.gz"]
        
        service = BackupService(driver=mock_driver, storage=mock_storage)
        result = service.list_backups()
        
        assert "backups" in result
        assert len(result["backups"]) == 2

    def test_list_backups_directory_not_exists(self):
        """Test backup listing when directory doesn't exist"""
        mock_driver = Mock()
        mock_storage = Mock()
        mock_storage.get_backup_directory.return_value = "/backups"
        mock_storage.directory_exists.return_value = False
        
        service = BackupService(driver=mock_driver, storage=mock_storage)
        result = service.list_backups()
        
        assert "backups" in result
        assert result["backups"] == []

    def test_restore_backup_success(self):
        """Test successful backup restoration"""
        mock_driver = Mock()
        mock_storage = Mock()
        mock_storage.get_backup_directory.return_value = "/backups"
        mock_storage.get_base_directory.return_value = "/project"
        mock_storage.file_exists.return_value = True
        mock_storage.join_path.return_value = "/backups/backup1.tar.gz"
        
        service = BackupService(driver=mock_driver, storage=mock_storage)
        result = service.restore("backup1.tar.gz", user="testuser")
        
        assert "message" in result
        assert "restored successfully" in result["message"]
        mock_driver.extract.assert_called_once()

    def test_restore_backup_file_not_found(self):
        """Test backup restoration when file doesn't exist"""
        mock_driver = Mock()
        mock_storage = Mock()
        mock_storage.get_backup_directory.return_value = "/backups"
        mock_storage.file_exists.return_value = False
        mock_storage.join_path.return_value = "/backups/backup1.tar.gz"
        
        service = BackupService(driver=mock_driver, storage=mock_storage)
        
        with pytest.raises(FileNotFoundError) as exc_info:
            service.restore("backup1.tar.gz")
        
        assert "backup1.tar.gz" in str(exc_info.value)
