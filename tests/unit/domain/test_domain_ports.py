#!/usr/bin/env python3
"""
Unit tests for domain/ports.py
Tests Protocol interfaces for hexagonal architecture
"""

import pytest

from soar_lab.domain.ports import (
    AlertRepository,
    IocRepository,
    MetricRepository,
    CaseRepository,
    BackupRepository,
    TestResultRepository,
    ChecksumService,
    StorageProvider,
    BackupDriver,
    TestRunner
)


class TestAlertRepository:
    """Test AlertRepository Protocol"""

    def test_alert_repository_exists(self):
        """Test that AlertRepository protocol exists"""
        assert AlertRepository is not None


class TestIocRepository:
    """Test IocRepository Protocol"""

    def test_ioc_repository_exists(self):
        """Test that IocRepository protocol exists"""
        assert IocRepository is not None


class TestMetricRepository:
    """Test MetricRepository Protocol"""

    def test_metric_repository_exists(self):
        """Test that MetricRepository protocol exists"""
        assert MetricRepository is not None


class TestCaseRepository:
    """Test CaseRepository Protocol"""

    def test_case_repository_exists(self):
        """Test that CaseRepository protocol exists"""
        assert CaseRepository is not None


class TestBackupRepository:
    """Test BackupRepository Protocol"""

    def test_backup_repository_exists(self):
        """Test that BackupRepository protocol exists"""
        assert BackupRepository is not None


class TestTestResultRepository:
    """Test TestResultRepository Protocol"""

    def test_test_result_repository_exists(self):
        """Test that TestResultRepository protocol exists"""
        assert TestResultRepository is not None


class TestChecksumService:
    """Test ChecksumService Protocol"""

    def test_checksum_service_exists(self):
        """Test that ChecksumService protocol exists"""
        assert ChecksumService is not None


class TestStorageProvider:
    """Test StorageProvider Protocol"""

    def test_storage_provider_exists(self):
        """Test that StorageProvider protocol exists"""
        assert StorageProvider is not None


class TestBackupDriver:
    """Test BackupDriver Protocol"""

    def test_backup_driver_exists(self):
        """Test that BackupDriver protocol exists"""
        assert BackupDriver is not None


class TestTestRunner:
    """Test TestRunner Protocol"""

    def test_test_runner_exists(self):
        """Test that TestRunner protocol exists"""
        assert TestRunner is not None
