#!/usr/bin/env python3
"""
Unit tests for api/models.py
Tests Pydantic models for SOAR Lab API
"""

import pytest
from datetime import datetime
from fastapi import Response
import json

from soar_lab.api.models import (
    LoginRequest,
    LoginResponse,
    VerifyAuthResponse,
    TestRequest,
    BackupRequest,
    ServiceStatus,
    Metrics,
    TestResults,
    CoverageData,
    BackupInfo,
    BackupListResponse,
    CreateBackupResponse,
    RestoreBackupResponse,
    ErrorResponse,
    HealthResponse
)


class TestLoginRequest:
    """Test LoginRequest model"""

    def test_valid_login_request(self):
        """Test valid login request"""
        request = LoginRequest(username="admin", password="password")
        assert request.username == "admin"
        assert request.password == "password"

    def test_login_request_required_fields(self):
        """Test that username and password are required"""
        with pytest.raises(Exception):
            LoginRequest(username="admin")
        with pytest.raises(Exception):
            LoginRequest(password="password")


class TestLoginResponse:
    """Test LoginResponse model"""

    def test_valid_login_response(self):
        """Test valid login response"""
        response = LoginResponse(token="test-token", message="Login successful")
        assert response.token == "test-token"
        assert response.message == "Login successful"
        assert response.token_type == "Bearer"

    def test_login_response_custom_token_type(self):
        """Test login response with custom token type"""
        response = LoginResponse(token="test-token", message="Login successful", token_type="Custom")
        assert response.token_type == "Custom"


class TestVerifyAuthResponse:
    """Test VerifyAuthResponse model"""

    def test_valid_verify_auth_response(self):
        """Test valid verify auth response"""
        response = VerifyAuthResponse(valid=True, user={"username": "admin"})
        assert response.valid == True
        assert response.user == {"username": "admin"}


class TestTestRequest:
    """Test TestRequest model"""

    def test_valid_test_request(self):
        """Test valid test request"""
        request = TestRequest(category="unit")
        assert request.category == "unit"

    def test_test_request_all_categories(self):
        """Test all allowed categories"""
        for category in ['unit', 'integration', 'e2e', 'all']:
            request = TestRequest(category=category)
            assert request.category == category

    def test_test_request_invalid_category(self):
        """Test invalid category raises validation error"""
        with pytest.raises(ValueError, match="Category must be one of"):
            TestRequest(category="invalid")


class TestBackupRequest:
    """Test BackupRequest model"""

    def test_valid_backup_request(self):
        """Test valid backup request"""
        request = BackupRequest(backup_name="backup.tar.gz")
        assert request.backup_name == "backup.tar.gz"

    def test_backup_request_path_traversal(self):
        """Test backup request with path traversal raises error"""
        with pytest.raises(ValueError, match="path traversal not allowed"):
            BackupRequest(backup_name="../backup.tar.gz")
        with pytest.raises(ValueError, match="path traversal not allowed"):
            BackupRequest(backup_name="sub/backup.tar.gz")
        with pytest.raises(ValueError, match="path traversal not allowed"):
            BackupRequest(backup_name="sub\\backup.tar.gz")

    def test_backup_request_invalid_extension(self):
        """Test backup request without .tar.gz extension raises error"""
        with pytest.raises(ValueError, match="must end with .tar.gz"):
            BackupRequest(backup_name="backup.zip")
        with pytest.raises(ValueError, match="must end with .tar.gz"):
            BackupRequest(backup_name="backup.tar")


class TestServiceStatus:
    """Test ServiceStatus model"""

    def test_valid_service_status(self):
        """Test valid service status"""
        status = ServiceStatus(service="thehive", status=True, url="http://localhost:9000")
        assert status.service == "thehive"
        assert status.status == True
        assert status.url == "http://localhost:9000"


class TestMetrics:
    """Test Metrics model"""

    def test_valid_metrics(self):
        """Test valid metrics"""
        metrics = Metrics(
            cpu=50.5,
            memory=60.0,
            disk=70.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        assert metrics.cpu == 50.5
        assert metrics.memory == 60.0
        assert metrics.disk == 70.0
        assert metrics.timestamp == datetime(2024, 1, 1, 12, 0, 0)


class TestTestResults:
    """Test TestResults model"""

    def test_valid_test_results(self):
        """Test valid test results"""
        results = TestResults(
            category="unit",
            passed=10,
            failed=2,
            skipped=1,
            coverage=85.5,
            output="Test output",
            duration=5.5
        )
        assert results.category == "unit"
        assert results.passed == 10
        assert results.failed == 2
        assert results.skipped == 1
        assert results.coverage == 85.5
        assert results.output == "Test output"
        assert results.duration == 5.5


class TestCoverageData:
    """Test CoverageData model"""

    def test_valid_coverage_data(self):
        """Test valid coverage data"""
        coverage = CoverageData(unit=85.0, integration=75.0, overall=80.0)
        assert coverage.unit == 85.0
        assert coverage.integration == 75.0
        assert coverage.overall == 80.0

    def test_coverage_data_defaults(self):
        """Test coverage data with default values"""
        coverage = CoverageData()
        assert coverage.unit == 0.0
        assert coverage.integration == 0.0
        assert coverage.overall == 0.0


class TestBackupInfo:
    """Test BackupInfo model"""

    def test_valid_backup_info(self):
        """Test valid backup info"""
        info = BackupInfo(name="backup.tar.gz", size="10MB", date="2024-01-01")
        assert info.name == "backup.tar.gz"
        assert info.size == "10MB"
        assert info.date == "2024-01-01"


class TestBackupListResponse:
    """Test BackupListResponse model"""

    def test_valid_backup_list_response(self):
        """Test valid backup list response"""
        backups = [
            BackupInfo(name="backup1.tar.gz", size="10MB", date="2024-01-01"),
            BackupInfo(name="backup2.tar.gz", size="15MB", date="2024-01-02")
        ]
        response = BackupListResponse(backups=backups)
        assert len(response.backups) == 2
        assert response.backups[0].name == "backup1.tar.gz"

    def test_backup_list_response_default(self):
        """Test backup list response with default empty list"""
        response = BackupListResponse()
        assert response.backups == []


class TestCreateBackupResponse:
    """Test CreateBackupResponse model"""

    def test_valid_create_backup_response(self):
        """Test valid create backup response"""
        response = CreateBackupResponse(filename="backup.tar.gz", message="Backup created")
        assert response.filename == "backup.tar.gz"
        assert response.message == "Backup created"


class TestRestoreBackupResponse:
    """Test RestoreBackupResponse model"""

    def test_valid_restore_backup_response(self):
        """Test valid restore backup response"""
        response = RestoreBackupResponse(message="Backup restored")
        assert response.message == "Backup restored"


class TestErrorResponse:
    """Test ErrorResponse model"""

    def test_valid_error_response(self):
        """Test valid error response"""
        response = ErrorResponse(error={"code": "ERR001", "message": "Error occurred"})
        assert response.error == {"code": "ERR001", "message": "Error occurred"}

    def test_error_response_create(self):
        """Test ErrorResponse.create class method"""
        response = ErrorResponse.create(code="ERR001", message="Error occurred", status_code=400)
        assert isinstance(response, Response)
        assert response.status_code == 400
        content = json.loads(response.body.decode())
        assert content["error"]["code"] == "ERR001"
        assert content["error"]["message"] == "Error occurred"

    def test_error_response_create_default_status(self):
        """Test ErrorResponse.create with default status code"""
        response = ErrorResponse.create(code="ERR001", message="Error occurred")
        assert response.status_code == 500


class TestHealthResponse:
    """Test HealthResponse model"""

    def test_valid_health_response(self):
        """Test valid health response"""
        response = HealthResponse(
            status="healthy",
            timestamp="2024-01-01T12:00:00",
            version="1.0.0"
        )
        assert response.status == "healthy"
        assert response.timestamp == "2024-01-01T12:00:00"
        assert response.version == "1.0.0"
