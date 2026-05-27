#!/usr/bin/env python3
"""
Unit tests for infrastructure/persistence/sqlite_alert_repository.py
Tests SQLite alert repository CRUD operations
"""

import pytest
import tempfile
import os
from pathlib import Path

from soar_lab.infrastructure.persistence.sqlite_alert_repository import SqliteAlertRepository


@pytest.fixture
def temp_db_path():
    """Create a temporary database path and clean up after test"""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except:
            pass
    try:
        os.rmdir(tmpdir)
    except:
        pass


class TestSqliteAlertRepository:
    """Test SqliteAlertRepository CRUD operations"""

    def test_initialization_with_db_path(self, temp_db_path):
        """Test initialization with explicit db_path"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        assert repo.db_path == Path(temp_db_path)
        assert repo.db_path.exists()

    def test_initialization_with_config_provider(self, temp_db_path):
        """Test initialization with config_provider"""
        config_provider = type('ConfigProvider', (), {
            'get': lambda self, key, default=None: temp_db_path if key == 'db_path' else default
        })()
        repo = SqliteAlertRepository(config_provider=config_provider)
        assert repo.db_path == Path(temp_db_path)

    def test_initialization_with_path_service(self):
        """Test initialization with path_service"""
        tmpdir = tempfile.mkdtemp()
        try:
            path_service = type('PathService', (), {
                'base_dir': Path(tmpdir)
            })()
            repo = SqliteAlertRepository(path_service=path_service)
            assert repo.db_path == Path(tmpdir) / "artifacts" / "data" / "soar_data.db"
        finally:
            # Cleanup
            import shutil
            try:
                shutil.rmtree(tmpdir)
            except:
                pass

    def test_initialization_without_required_params(self):
        """Test initialization raises error without required params"""
        with pytest.raises(ValueError, match="db_path, config_provider, or path_service must be supplied"):
            SqliteAlertRepository()

    def test_initialization_config_provider_without_db_path(self):
        """Test initialization with config_provider but no db_path"""
        config_provider = type('ConfigProvider', (), {
            'get': lambda self, key, default=None: None
        })()
        with pytest.raises(ValueError, match="db_path must be provided"):
            SqliteAlertRepository(config_provider=config_provider)

    def test_store_alert(self, temp_db_path):
        """Test storing an alert"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        alert_data = {
            'alert_id': 'ALERT-001',
            'alert_type': 'ransomware',
            'severity': 'high',
            'hostname': 'test-host',
            'data': {'key': 'value'},
            'status': 'new'
        }
        
        alert_id = repo.store_alert(alert_data)
        assert alert_id == 'ALERT-001'

    def test_get_alert(self, temp_db_path):
        """Test retrieving an alert"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        alert_data = {
            'alert_id': 'ALERT-002',
            'alert_type': 'ransomware',
            'severity': 'critical',
            'hostname': 'test-host',
            'data': {'key': 'value'},
            'status': 'new'
        }
        
        repo.store_alert(alert_data)
        alert = repo.get_alert('ALERT-002')
        
        assert alert is not None
        assert alert['alert_id'] == 'ALERT-002'
        assert alert['severity'] == 'critical'
        assert alert['data'] == {'key': 'value'}

    def test_get_alert_not_found(self, temp_db_path):
        """Test retrieving non-existent alert returns None"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        alert = repo.get_alert('NONEXISTENT')
        assert alert is None

    def test_get_alerts(self, temp_db_path):
        """Test retrieving multiple alerts"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        for i in range(3):
            alert_data = {
                'alert_id': f'ALERT-{i:03d}',
                'alert_type': 'ransomware',
                'severity': 'high',
                'hostname': 'test-host',
                'data': {},
                'status': 'new'
            }
            repo.store_alert(alert_data)
        
        alerts = repo.get_alerts(limit=10)
        assert len(alerts) == 3

    def test_get_alerts_with_severity_filter(self, temp_db_path):
        """Test retrieving alerts filtered by severity"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        repo.store_alert({
            'alert_id': 'ALERT-001',
            'alert_type': 'ransomware',
            'severity': 'high',
            'hostname': 'test-host',
            'data': {},
            'status': 'new'
        })
        repo.store_alert({
            'alert_id': 'ALERT-002',
            'alert_type': 'ransomware',
            'severity': 'critical',
            'hostname': 'test-host',
            'data': {},
            'status': 'new'
        })
        
        high_alerts = repo.get_alerts(severity='high')
        assert len(high_alerts) == 1
        assert high_alerts[0]['alert_id'] == 'ALERT-001'

    def test_count_alerts(self, temp_db_path):
        """Test counting alerts"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        assert repo.count_alerts() == 0
        
        for i in range(5):
            alert_data = {
                'alert_id': f'ALERT-{i:03d}',
                'alert_type': 'ransomware',
                'severity': 'high',
                'hostname': 'test-host',
                'data': {},
                'status': 'new'
            }
            repo.store_alert(alert_data)
        
        assert repo.count_alerts() == 5

    def test_store_case(self, temp_db_path):
        """Test storing a case"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        case_data = {
            'case_id': 'CASE-001',
            'title': 'Test Case',
            'description': 'Test description',
            'severity': 'high',
            'alert_id': 'ALERT-001',
            'status': 'open'
        }
        
        case_id = repo.store_case(case_data)
        assert case_id == 'CASE-001'

    def test_get_cases(self, temp_db_path):
        """Test retrieving cases"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        for i in range(3):
            case_data = {
                'case_id': f'CASE-{i:03d}',
                'title': f'Test Case {i}',
                'description': 'Test description',
                'severity': 'high',
                'alert_id': f'ALERT-{i:03d}',
                'status': 'open'
            }
            repo.store_case(case_data)
        
        cases = repo.get_cases()
        assert len(cases) == 3

    def test_get_cases_with_status_filter(self, temp_db_path):
        """Test retrieving cases filtered by status"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        repo.store_case({
            'case_id': 'CASE-001',
            'title': 'Test Case 1',
            'description': 'Test description',
            'severity': 'high',
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
        
        open_cases = repo.get_cases(status='open')
        assert len(open_cases) == 1
        assert open_cases[0]['case_id'] == 'CASE-001'

    def test_count_cases_by_status(self, temp_db_path):
        """Test counting cases by status"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        for i in range(3):
            repo.store_case({
                'case_id': f'CASE-{i:03d}',
                'title': f'Test Case {i}',
                'description': 'Test description',
                'severity': 'high',
                'alert_id': f'ALERT-{i:03d}',
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
        
        assert repo.count_cases_by_status('open') == 3
        assert repo.count_cases_by_status('closed') == 1

    def test_store_backup_info(self, temp_db_path):
        """Test storing backup information"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        backup_data = {
            'backup_name': 'backup-2024-01-01.tar.gz',
            'backup_type': 'manual',
            'status': 'completed',
            'file_path': '/backups/backup-2024-01-01.tar.gz',
            'size_bytes': 1024000,
            'checksum': 'abc123',
            'created_by': 'admin'
        }
        
        backup_name = repo.store_backup_info(backup_data)
        assert backup_name == 'backup-2024-01-01.tar.gz'

    def test_get_backups(self, temp_db_path):
        """Test retrieving backup information"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        for i in range(3):
            backup_data = {
                'backup_name': f'backup-{i:03d}.tar.gz',
                'backup_type': 'manual',
                'status': 'completed',
                'file_path': f'/backups/backup-{i:03d}.tar.gz',
                'size_bytes': 1024000,
                'checksum': 'abc123',
                'created_by': 'admin'
            }
            repo.store_backup_info(backup_data)
        
        backups = repo.get_backups()
        assert len(backups) == 3

    def test_store_test_coverage(self, temp_db_path):
        """Test storing test coverage data"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        coverage_data = {
            'test_category': 'unit',
            'coverage_percentage': 85.5,
            'tests_run': 100,
            'tests_passed': 95,
            'tests_failed': 5
        }
        
        repo.store_test_coverage(coverage_data)
        # No assertion needed, just ensure no exception

    def test_get_average_test_coverage(self, temp_db_path):
        """Test retrieving average test coverage"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        repo.store_test_coverage({
            'test_category': 'unit',
            'coverage_percentage': 80.0,
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
        
        avg_coverage = repo.get_average_test_coverage(hours=24)
        assert avg_coverage == 85.0

    def test_get_average_test_coverage_no_data(self, temp_db_path):
        """Test retrieving average coverage with no data returns None"""
        repo = SqliteAlertRepository(db_path=temp_db_path)
        
        avg_coverage = repo.get_average_test_coverage(hours=24)
        assert avg_coverage is None
