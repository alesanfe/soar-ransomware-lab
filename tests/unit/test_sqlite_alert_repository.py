#!/usr/bin/env python3
"""
Unit tests for sqlite_alert_repository module
"""

import gc
import os
import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

# Add src to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.infrastructure.persistence.sqlite_alert_repository import SqliteAlertRepository


class TestSqliteAlertRepository:
    """Tests for SqliteAlertRepository class."""

    def test_initialization_with_db_path(self):
        """Test initialization with explicit db_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            assert repo.db_path == Path(db_path)
            assert repo.db_path.exists()
            repo.close()
            del repo
            gc.collect()

    def test_initialization_no_db_path_no_config(self):
        """Test initialization without db_path or config raises ValueError."""
        with pytest.raises(ValueError, match="db_path, config_provider, or path_service must be supplied"):
            SqliteAlertRepository()

    def test_initialization_with_config_provider(self):
        """Test initialization with config_provider."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            mock_config = Mock()
            mock_config.get.return_value = db_path

            repo = SqliteAlertRepository(config_provider=mock_config)

            assert repo.db_path == Path(db_path)
            repo.close()
            del repo
            gc.collect()

    def test_initialization_with_path_service(self):
        """Test initialization with path_service."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_path_service = Mock()
            mock_path_service.base_dir = Path(tmpdir)

            repo = SqliteAlertRepository(path_service=mock_path_service)

            assert repo.db_path.exists()
            repo.close()
            del repo
            gc.collect()

    def test_store_alert(self):
        """Test storing an alert."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            alert_data = {
                'alert_id': 'ALERT-001',
                'alert_type': 'ransomware',
                'severity': 'critical',
                'hostname': 'test-host',
                'data': {'key': 'value'},
                'status': 'new'
            }

            result = repo.store_alert(alert_data)

            assert result == 'ALERT-001'
            repo.close()
            del repo
            gc.collect()

    def test_get_alert(self):
        """Test getting an alert by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            alert_data = {
                'alert_id': 'ALERT-001',
                'alert_type': 'ransomware',
                'severity': 'critical',
                'hostname': 'test-host',
                'data': {'key': 'value'},
                'status': 'new'
            }
            repo.store_alert(alert_data)

            result = repo.get_alert('ALERT-001')

            assert result is not None
            assert result['alert_id'] == 'ALERT-001'
            assert result['alert_type'] == 'ransomware'
            assert result['severity'] == 'critical'
            repo.close()
            del repo
            gc.collect()

    def test_get_alert_not_found(self):
        """Test getting a non-existent alert."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            result = repo.get_alert('NONEXISTENT')

            assert result is None
            repo.close()
            del repo
            gc.collect()

    def test_get_alerts(self):
        """Test getting alerts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            repo.store_alert({
                'alert_id': 'ALERT-001',
                'alert_type': 'ransomware',
                'severity': 'critical',
                'hostname': 'test-host',
                'data': {},
                'status': 'new'
            })
            repo.store_alert({
                'alert_id': 'ALERT-002',
                'alert_type': 'ransomware',
                'severity': 'high',
                'hostname': 'test-host',
                'data': {},
                'status': 'new'
            })

            result = repo.get_alerts()

            assert len(result) == 2
            repo.close()
            del repo
            gc.collect()

    def test_get_alerts_with_severity_filter(self):
        """Test getting alerts with severity filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            repo.store_alert({
                'alert_id': 'ALERT-001',
                'alert_type': 'ransomware',
                'severity': 'critical',
                'hostname': 'test-host',
                'data': {},
                'status': 'new'
            })
            repo.store_alert({
                'alert_id': 'ALERT-002',
                'alert_type': 'ransomware',
                'severity': 'high',
                'hostname': 'test-host',
                'data': {},
                'status': 'new'
            })

            result = repo.get_alerts(severity='critical')

            assert len(result) == 1
            assert result[0]['severity'] == 'critical'
            repo.close()
            del repo
            gc.collect()

    def test_count_alerts(self):
        """Test counting alerts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            repo.store_alert({
                'alert_id': 'ALERT-001',
                'alert_type': 'ransomware',
                'severity': 'critical',
                'hostname': 'test-host',
                'data': {},
                'status': 'new'
            })
            repo.store_alert({
                'alert_id': 'ALERT-002',
                'alert_type': 'ransomware',
                'severity': 'high',
                'hostname': 'test-host',
                'data': {},
                'status': 'new'
            })

            result = repo.count_alerts()

            assert result == 2
            repo.close()
            del repo
            gc.collect()

    def test_store_case(self):
        """Test storing a case."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            case_data = {
                'case_id': 'CASE-001',
                'title': 'Test Case',
                'description': 'Test description',
                'severity': 'critical',
                'alert_id': 'ALERT-001',
                'status': 'open'
            }

            result = repo.store_case(case_data)

            assert result == 'CASE-001'
            repo.close()
            del repo
            gc.collect()

    def test_get_cases(self):
        """Test getting cases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            repo.store_case({
                'case_id': 'CASE-001',
                'title': 'Test Case 1',
                'description': 'Test description',
                'severity': 'critical',
                'alert_id': 'ALERT-001',
                'status': 'open'
            })
            repo.store_case({
                'case_id': 'CASE-002',
                'title': 'Test Case 2',
                'description': 'Test description',
                'severity': 'high',
                'alert_id': 'ALERT-002',
                'status': 'closed'
            })

            result = repo.get_cases()

            assert len(result) == 2
            repo.close()
            del repo
            gc.collect()

    def test_get_cases_with_status_filter(self):
        """Test getting cases with status filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            repo.store_case({
                'case_id': 'CASE-001',
                'title': 'Test Case 1',
                'description': 'Test description',
                'severity': 'critical',
                'alert_id': 'ALERT-001',
                'status': 'open'
            })
            repo.store_case({
                'case_id': 'CASE-002',
                'title': 'Test Case 2',
                'description': 'Test description',
                'severity': 'high',
                'alert_id': 'ALERT-002',
                'status': 'closed'
            })

            result = repo.get_cases(status='open')

            assert len(result) == 1
            assert result[0]['status'] == 'open'
            repo.close()
            del repo
            gc.collect()

    def test_count_cases_by_status(self):
        """Test counting cases by status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            repo.store_case({
                'case_id': 'CASE-001',
                'title': 'Test Case 1',
                'description': 'Test description',
                'severity': 'critical',
                'alert_id': 'ALERT-001',
                'status': 'open'
            })
            repo.store_case({
                'case_id': 'CASE-002',
                'title': 'Test Case 2',
                'description': 'Test description',
                'severity': 'high',
                'alert_id': 'ALERT-002',
                'status': 'open'
            })
            repo.store_case({
                'case_id': 'CASE-003',
                'title': 'Test Case 3',
                'description': 'Test description',
                'severity': 'high',
                'alert_id': 'ALERT-003',
                'status': 'closed'
            })

            result = repo.count_cases_by_status('open')

            assert result == 2
            repo.close()
            del repo
            gc.collect()

    def test_store_backup_info(self):
        """Test storing backup information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            backup_data = {
                'backup_name': 'backup-001',
                'backup_type': 'full',
                'status': 'completed',
                'file_path': '/tmp/backup.tar.gz',
                'size_bytes': 1024,
                'checksum': 'abc123',
                'created_by': 'admin'
            }

            result = repo.store_backup_info(backup_data)

            assert result == 'backup-001'
            repo.close()
            del repo
            gc.collect()

    def test_get_backups(self):
        """Test getting backups."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            repo.store_backup_info({
                'backup_name': 'backup-001',
                'backup_type': 'full',
                'status': 'completed',
                'file_path': '/tmp/backup1.tar.gz',
                'size_bytes': 1024,
                'checksum': 'abc123',
                'created_by': 'admin'
            })
            repo.store_backup_info({
                'backup_name': 'backup-002',
                'backup_type': 'incremental',
                'status': 'completed',
                'file_path': '/tmp/backup2.tar.gz',
                'size_bytes': 512,
                'checksum': 'def456',
                'created_by': 'admin'
            })

            result = repo.get_backups()

            assert len(result) == 2
            repo.close()
            del repo
            gc.collect()

    def test_store_test_coverage(self):
        """Test storing test coverage data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            coverage_data = {
                'test_category': 'unit',
                'coverage_percentage': 85.5,
                'tests_run': 100,
                'tests_passed': 95,
                'tests_failed': 5
            }

            repo.store_test_coverage(coverage_data)

            # Should not raise exception
            assert True
            repo.close()
            del repo
            gc.collect()

    def test_get_average_test_coverage(self):
        """Test getting average test coverage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            repo.store_test_coverage({
                'test_category': 'unit',
                'coverage_percentage': 85.0,
                'tests_run': 100,
                'tests_passed': 95,
                'tests_failed': 5
            })
            repo.store_test_coverage({
                'test_category': 'unit',
                'coverage_percentage': 90.0,
                'tests_run': 100,
                'tests_passed': 98,
                'tests_failed': 2
            })

            result = repo.get_average_test_coverage(hours=24)

            assert result == 87.5
            repo.close()
            del repo
            gc.collect()

    def test_get_average_test_coverage_no_data(self):
        """Test getting average test coverage with no data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            repo = SqliteAlertRepository(db_path=db_path)

            result = repo.get_average_test_coverage(hours=24)

            assert result is None
            repo.close()
            del repo
            gc.collect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
