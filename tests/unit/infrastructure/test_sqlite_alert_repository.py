#!/usr/bin/env python3
"""Unit tests for infrastructure.persistence.sqlite_alert_repository.

Tests the SqliteAlertRepository CRUD operations for alerts, cases,
backups, and test coverage data using a temporary database file.
"""

from pathlib import Path

import pytest

from soar_lab.infrastructure.persistence.sqlite_alert_repository import (
    SqliteAlertRepository,
)

__all__ = [
    "TestSqliteAlertRepositoryInit",
    "TestAlertCRUD",
    "TestCaseCRUD",
    "TestBackupCRUD",
    "TestTestCoverageOperations",
    "TestCountOperations",
    "TestClose",
]


class TestSqliteAlertRepositoryInit:
    """Tests for SqliteAlertRepository initialization."""

    def test_init_with_db_path(self, tmp_path):
        """Test initialization with explicit db_path."""
        db_path = str(tmp_path / "test.db")
        repo = SqliteAlertRepository(db_path=db_path)
        assert repo.db_path == Path(db_path)
        assert repo.db_path.exists()

    def test_init_with_path_service(self, tmp_path):
        """Test initialization with path_service for default path."""
        mock_path_service = Mock()
        mock_path_service.base_dir = tmp_path

        repo = SqliteAlertRepository(path_service=mock_path_service)
        expected = tmp_path / "runtime" / "data" / "soar_data.db"
        assert repo.db_path == expected

    def test_init_with_config_provider(self, tmp_path):
        """Test initialization with config_provider providing db_path."""
        db_path = str(tmp_path / "config_test.db")
        mock_config = Mock()
        mock_config.get.return_value = db_path

        repo = SqliteAlertRepository(config_provider=mock_config)
        assert repo.db_path == Path(db_path)

    def test_init_no_args_raises(self):
        """Test that ValueError is raised when no path source is provided."""
        with pytest.raises(ValueError, match="db_path, config_provider, or path_service"):
            SqliteAlertRepository()

    def test_init_config_provider_no_db_path_raises(self):
        """Test that ValueError is raised when config_provider has no db_path."""
        mock_config = Mock()
        mock_config.get.return_value = None

        with pytest.raises(ValueError, match="db_path must be provided"):
            SqliteAlertRepository(config_provider=mock_config)


class TestAlertCRUD:
    """Tests for alert CRUD operations."""

    @pytest.fixture()
    def repo(self, tmp_path):
        """Create a repository with a temp database."""
        return SqliteAlertRepository(db_path=str(tmp_path / "alerts.db"))

    def test_store_and_get_alert(self, repo):
        """Test storing an alert and retrieving it by ID."""
        alert_data = {
            "alert_id": "ALERT-001",
            "alert_type": "ransomware",
            "severity": "high",
            "hostname": "host-1",
            "data": {"key": "value"},
            "status": "new",
        }
        result_id = repo.store_alert(alert_data)
        assert result_id == "ALERT-001"

        retrieved = repo.get_alert("ALERT-001")
        assert retrieved is not None
        assert retrieved["alert_id"] == "ALERT-001"
        assert retrieved["alert_type"] == "ransomware"
        assert retrieved["severity"] == "high"
        assert retrieved["hostname"] == "host-1"
        assert retrieved["data"] == {"key": "value"}
        assert retrieved["status"] == "new"

    def test_get_alert_not_found(self, repo):
        """Test that get_alert returns None for non-existent alert."""
        result = repo.get_alert("NONEXISTENT")
        assert result is None

    def test_store_alert_replaces_existing(self, repo):
        """Test that storing an alert with same ID replaces the existing one."""
        repo.store_alert(
            {
                "alert_id": "ALERT-002",
                "alert_type": "ransomware",
                "severity": "low",
                "hostname": "host-2",
                "data": {},
            }
        )
        repo.store_alert(
            {
                "alert_id": "ALERT-002",
                "alert_type": "ransomware",
                "severity": "critical",
                "hostname": "host-2-updated",
                "data": {"updated": True},
            }
        )

        retrieved = repo.get_alert("ALERT-002")
        assert retrieved["severity"] == "critical"
        assert retrieved["hostname"] == "host-2-updated"
        assert retrieved["data"] == {"updated": True}

    def test_store_alert_default_status(self, repo):
        """Test that default status is 'new' when not provided."""
        repo.store_alert(
            {
                "alert_id": "ALERT-003",
                "alert_type": "test",
                "severity": "low",
                "hostname": "host-3",
            }
        )
        retrieved = repo.get_alert("ALERT-003")
        assert retrieved["status"] == "new"

    def test_store_alert_default_data(self, repo):
        """Test that default data is empty dict when not provided."""
        repo.store_alert(
            {
                "alert_id": "ALERT-004",
                "alert_type": "test",
                "severity": "low",
                "hostname": "host-4",
            }
        )
        retrieved = repo.get_alert("ALERT-004")
        assert retrieved["data"] == {}

    def test_get_alerts_all(self, repo):
        """Test getting all alerts without filtering."""
        for i in range(5):
            repo.store_alert(
                {
                    "alert_id": f"ALERT-{i}",
                    "alert_type": "test",
                    "severity": "high",
                    "hostname": f"host-{i}",
                    "data": {},
                }
            )
        alerts = repo.get_alerts()
        assert len(alerts) == 5

    def test_get_alerts_with_limit(self, repo):
        """Test getting alerts with a limit."""
        for i in range(10):
            repo.store_alert(
                {
                    "alert_id": f"ALERT-L{i}",
                    "alert_type": "test",
                    "severity": "high",
                    "hostname": f"host-{i}",
                    "data": {},
                }
            )
        alerts = repo.get_alerts(limit=3)
        assert len(alerts) == 3

    def test_get_alerts_by_severity(self, repo):
        """Test filtering alerts by severity."""
        repo.store_alert(
            {
                "alert_id": "ALERT-S1",
                "alert_type": "test",
                "severity": "high",
                "hostname": "host-1",
                "data": {},
            }
        )
        repo.store_alert(
            {
                "alert_id": "ALERT-S2",
                "alert_type": "test",
                "severity": "low",
                "hostname": "host-2",
                "data": {},
            }
        )
        alerts = repo.get_alerts(severity="high")
        assert len(alerts) == 1
        assert alerts[0]["alert_id"] == "ALERT-S1"

    def test_count_alerts(self, repo):
        """Test counting total alerts."""
        assert repo.count_alerts() == 0
        repo.store_alert(
            {
                "alert_id": "ALERT-C1",
                "alert_type": "test",
                "severity": "high",
                "hostname": "host-1",
                "data": {},
            }
        )
        assert repo.count_alerts() == 1
        repo.store_alert(
            {
                "alert_id": "ALERT-C2",
                "alert_type": "test",
                "severity": "low",
                "hostname": "host-2",
                "data": {},
            }
        )
        assert repo.count_alerts() == 2


class TestCaseCRUD:
    """Tests for case CRUD operations."""

    @pytest.fixture()
    def repo(self, tmp_path):
        """Create a repository with a temp database."""
        return SqliteAlertRepository(db_path=str(tmp_path / "cases.db"))

    def test_store_and_get_cases(self, repo):
        """Test storing a case and retrieving it."""
        repo.store_case(
            {
                "case_id": "CASE-001",
                "title": "Test Case",
                "description": "A test case",
                "severity": "high",
                "alert_id": "ALERT-001",
                "status": "open",
            }
        )
        cases = repo.get_cases()
        assert len(cases) == 1
        assert cases[0]["case_id"] == "CASE-001"
        assert cases[0]["title"] == "Test Case"
        assert cases[0]["description"] == "A test case"
        assert cases[0]["severity"] == "high"
        assert cases[0]["alert_id"] == "ALERT-001"
        assert cases[0]["status"] == "open"

    def test_store_case_default_status(self, repo):
        """Test that default case status is 'open'."""
        repo.store_case(
            {
                "case_id": "CASE-002",
                "title": "Test Case 2",
                "description": "desc",
                "severity": "low",
            }
        )
        cases = repo.get_cases()
        assert cases[0]["status"] == "open"

    def test_get_cases_by_status(self, repo):
        """Test filtering cases by status."""
        repo.store_case(
            {
                "case_id": "CASE-O1",
                "title": "Open Case",
                "description": "desc",
                "severity": "high",
                "status": "open",
            }
        )
        repo.store_case(
            {
                "case_id": "CASE-C1",
                "title": "Closed Case",
                "description": "desc",
                "severity": "low",
                "status": "closed",
            }
        )
        open_cases = repo.get_cases(status="open")
        assert len(open_cases) == 1
        assert open_cases[0]["case_id"] == "CASE-O1"

        closed_cases = repo.get_cases(status="closed")
        assert len(closed_cases) == 1
        assert closed_cases[0]["case_id"] == "CASE-C1"

    def test_count_cases_by_status(self, repo):
        """Test counting cases by status."""
        repo.store_case(
            {
                "case_id": "CASE-CS1",
                "title": "Case 1",
                "description": "desc",
                "severity": "high",
                "status": "open",
            }
        )
        repo.store_case(
            {
                "case_id": "CASE-CS2",
                "title": "Case 2",
                "description": "desc",
                "severity": "low",
                "status": "open",
            }
        )
        repo.store_case(
            {
                "case_id": "CASE-CS3",
                "title": "Case 3",
                "description": "desc",
                "severity": "low",
                "status": "closed",
            }
        )
        assert repo.count_cases_by_status("open") == 2
        assert repo.count_cases_by_status("closed") == 1

    def test_count_cases(self, repo):
        """Test counting total cases."""
        assert repo.count_cases() == 0
        repo.store_case(
            {
                "case_id": "CASE-CC1",
                "title": "Case",
                "description": "desc",
                "severity": "high",
            }
        )
        assert repo.count_cases() == 1


class TestBackupCRUD:
    """Tests for backup CRUD operations."""

    @pytest.fixture()
    def repo(self, tmp_path):
        """Create a repository with a temp database."""
        return SqliteAlertRepository(db_path=str(tmp_path / "backups.db"))

    def test_store_and_get_backup(self, repo):
        """Test storing backup info and retrieving it."""
        repo.store_backup_info(
            {
                "backup_name": "backup-001.tar.gz",
                "backup_type": "full",
                "status": "completed",
                "file_path": "/tmp/backup-001.tar.gz",
                "size_bytes": 1024,
                "checksum": "abc123",
                "created_by": "admin",
            }
        )
        backups = repo.get_backups()
        assert len(backups) == 1
        assert backups[0]["backup_name"] == "backup-001.tar.gz"
        assert backups[0]["backup_type"] == "full"
        assert backups[0]["status"] == "completed"
        assert backups[0]["file_path"] == "/tmp/backup-001.tar.gz"
        assert backups[0]["size_bytes"] == 1024
        assert backups[0]["checksum"] == "abc123"
        assert backups[0]["created_by"] == "admin"

    def test_store_backup_replaces_existing(self, repo):
        """Test that storing backup with same name replaces existing."""
        repo.store_backup_info(
            {
                "backup_name": "backup-002.tar.gz",
                "backup_type": "full",
                "status": "completed",
            }
        )
        repo.store_backup_info(
            {
                "backup_name": "backup-002.tar.gz",
                "backup_type": "incremental",
                "status": "failed",
            }
        )
        backups = repo.get_backups()
        assert len(backups) == 1
        assert backups[0]["backup_type"] == "incremental"
        assert backups[0]["status"] == "failed"

    def test_count_backups_by_status(self, repo):
        """Test counting backups by status."""
        repo.store_backup_info(
            {
                "backup_name": "b1.tar.gz",
                "backup_type": "full",
                "status": "completed",
            }
        )
        repo.store_backup_info(
            {
                "backup_name": "b2.tar.gz",
                "backup_type": "full",
                "status": "completed",
            }
        )
        repo.store_backup_info(
            {
                "backup_name": "b3.tar.gz",
                "backup_type": "full",
                "status": "failed",
            }
        )
        assert repo.count_backups_by_status("completed") == 2
        assert repo.count_backups_by_status("failed") == 1


class TestTestCoverageOperations:
    """Tests for test coverage operations."""

    @pytest.fixture()
    def repo(self, tmp_path):
        """Create a repository with a temp database."""
        return SqliteAlertRepository(db_path=str(tmp_path / "coverage.db"))

    def test_store_test_coverage(self, repo):
        """Test storing test coverage data."""
        repo.store_test_coverage(
            {
                "test_category": "unit",
                "coverage_percentage": 85.5,
                "tests_run": 100,
                "tests_passed": 95,
                "tests_failed": 5,
            }
        )
        results = repo.get_test_results(hours=24)
        assert len(results) == 1
        assert results[0]["test_category"] == "unit"
        assert results[0]["coverage_percentage"] == 85.5
        assert results[0]["tests_run"] == 100
        assert results[0]["tests_passed"] == 95
        assert results[0]["tests_failed"] == 5

    def test_get_average_test_coverage(self, repo):
        """Test getting average test coverage."""
        repo.store_test_coverage(
            {
                "test_category": "unit",
                "coverage_percentage": 80.0,
                "tests_run": 100,
                "tests_passed": 95,
                "tests_failed": 5,
            }
        )
        repo.store_test_coverage(
            {
                "test_category": "integration",
                "coverage_percentage": 90.0,
                "tests_run": 50,
                "tests_passed": 48,
                "tests_failed": 2,
            }
        )
        avg = repo.get_average_test_coverage(hours=24)
        assert avg is not None
        assert 80.0 <= avg <= 90.0

    def test_get_average_test_coverage_no_data(self, repo):
        """Test that get_average_test_coverage returns None when no data."""
        result = repo.get_average_test_coverage(hours=24)
        assert result is None

    def test_get_test_results_empty(self, repo):
        """Test that get_test_results returns empty list when no data."""
        results = repo.get_test_results(hours=24)
        assert results == []


class TestCountOperations:
    """Tests for count operations."""

    @pytest.fixture()
    def repo(self, tmp_path):
        """Create a repository with a temp database."""
        return SqliteAlertRepository(db_path=str(tmp_path / "counts.db"))

    def test_count_alerts_by_status(self, repo):
        """Test counting alerts by status."""
        repo.store_alert(
            {
                "alert_id": "A1",
                "alert_type": "test",
                "severity": "high",
                "hostname": "h1",
                "data": {},
                "status": "new",
            }
        )
        repo.store_alert(
            {
                "alert_id": "A2",
                "alert_type": "test",
                "severity": "high",
                "hostname": "h2",
                "data": {},
                "status": "resolved",
            }
        )
        assert repo.count_alerts_by_status("new") == 1
        assert repo.count_alerts_by_status("resolved") == 1
        assert repo.count_alerts_by_status("closed") == 0


class TestClose:
    """Tests for close and cleanup operations."""

    def test_close_is_noop(self, tmp_path):
        """Test that close() is a no-op and does not raise."""
        repo = SqliteAlertRepository(db_path=str(tmp_path / "close_test.db"))
        repo.close()  # Should not raise

    def test_del_does_not_raise(self, tmp_path):
        """Test that __del__ does not raise during garbage collection."""
        repo = SqliteAlertRepository(db_path=str(tmp_path / "del_test.db"))
        del repo  # Should not raise


# Need Mock for init tests
from unittest.mock import Mock

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
