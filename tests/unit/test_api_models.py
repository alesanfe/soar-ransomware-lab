"""Unit tests for api.models module."""

import pytest
from datetime import datetime
from fastapi import Response

from soar_lab.api.models import (
    LoginRequest,
    LoginResponse,
    VerifyAuthResponse,
    RunRequest,
    BackupRequest,
    ServiceStatus,
    Metrics,
    RunResults,
    CoverageData,
    BackupInfo,
    BackupListResponse,
    CreateBackupResponse,
    RestoreBackupResponse,
    ErrorResponse,
    HealthResponse,
)


class TestLoginRequest:
    """Tests for LoginRequest model."""

    def test_login_request_valid(self):
        """Test valid LoginRequest creation."""
        request = LoginRequest(username="testuser", password="testpass")
        assert request.username == "testuser"
        assert request.password == "testpass"


class TestLoginResponse:
    """Tests for LoginResponse model."""

    def test_login_response_valid(self):
        """Test valid LoginResponse creation."""
        response = LoginResponse(token="test_token", message="Login successful")
        assert response.token == "test_token"
        assert response.message == "Login successful"
        assert response.token_type == "Bearer"

    def test_login_response_custom_token_type(self):
        """Test LoginResponse with custom token type."""
        response = LoginResponse(token="test_token", message="Login successful", token_type="Custom")
        assert response.token_type == "Custom"


class TestVerifyAuthResponse:
    """Tests for VerifyAuthResponse model."""

    def test_verify_auth_response_valid(self):
        """Test valid VerifyAuthResponse creation."""
        response = VerifyAuthResponse(valid=True, user={"username": "testuser"})
        assert response.valid is True
        assert response.user == {"username": "testuser"}


class TestRunRequest:
    """Tests for RunRequest model."""

    def test_run_request_valid_category(self):
        """Test RunRequest with valid category."""
        for category in ['unit', 'integration', 'e2e', 'atomic', 'performance', 'security', 'smoke', 'all']:
            request = RunRequest(category=category)
            assert request.category == category

    def test_run_request_invalid_category(self):
        """Test RunRequest with invalid category raises ValueError."""
        with pytest.raises(ValueError, match="Category must be one of"):
            RunRequest(category="invalid")


class TestBackupRequest:
    """Tests for BackupRequest model."""

    def test_backup_request_valid(self):
        """Test valid BackupRequest creation."""
        request = BackupRequest(backup_name="backup.tar.gz")
        assert request.backup_name == "backup.tar.gz"

    def test_backup_request_path_traversal(self):
        """Test BackupRequest with path traversal raises ValueError."""
        with pytest.raises(ValueError, match="path traversal not allowed"):
            BackupRequest(backup_name="../backup.tar.gz")

    def test_backup_request_invalid_extension(self):
        """Test BackupRequest with invalid extension raises ValueError."""
        with pytest.raises(ValueError, match="must end with .tar.gz"):
            BackupRequest(backup_name="backup.zip")


class TestServiceStatus:
    """Tests for ServiceStatus model."""

    def test_service_status_valid(self):
        """Test valid ServiceStatus creation."""
        status = ServiceStatus(service="grafana", status=True, url="http://localhost:8084")
        assert status.service == "grafana"
        assert status.status is True
        assert status.url == "http://localhost:8084"


class TestMetrics:
    """Tests for Metrics model."""

    def test_metrics_valid(self):
        """Test valid Metrics creation."""
        metrics = Metrics(
            cpu=50.5,
            memory=60.3,
            disk=70.2,
            timestamp=datetime.now()
        )
        assert metrics.cpu == 50.5
        assert metrics.memory == 60.3
        assert metrics.disk == 70.2


class TestRunResults:
    """Tests for RunResults model."""

    def test_run_results_valid(self):
        """Test valid RunResults creation."""
        results = RunResults(
            category="unit",
            passed=100,
            failed=0,
            skipped=5,
            coverage=85.5,
            output="All tests passed",
            duration=10.5
        )
        assert results.category == "unit"
        assert results.passed == 100
        assert results.failed == 0
        assert results.skipped == 5
        assert results.coverage == 85.5


class TestCoverageData:
    """Tests for CoverageData model."""

    def test_coverage_data_valid(self):
        """Test valid CoverageData creation."""
        coverage = CoverageData(unit=80.0, integration=70.0, overall=75.0)
        assert coverage.unit == 80.0
        assert coverage.integration == 70.0
        assert coverage.overall == 75.0

    def test_coverage_data_defaults(self):
        """Test CoverageData with default values."""
        coverage = CoverageData()
        assert coverage.unit == 0.0
        assert coverage.integration == 0.0
        assert coverage.overall == 0.0


class TestBackupInfo:
    """Tests for BackupInfo model."""

    def test_backup_info_valid(self):
        """Test valid BackupInfo creation."""
        info = BackupInfo(name="backup.tar.gz", size="10MB", date="2026-06-29")
        assert info.name == "backup.tar.gz"
        assert info.size == "10MB"
        assert info.date == "2026-06-29"


class TestBackupListResponse:
    """Tests for BackupListResponse model."""

    def test_backup_list_response_valid(self):
        """Test valid BackupListResponse creation."""
        backups = [
            BackupInfo(name="backup1.tar.gz", size="10MB", date="2026-06-29"),
            BackupInfo(name="backup2.tar.gz", size="15MB", date="2026-06-30")
        ]
        response = BackupListResponse(backups=backups)
        assert len(response.backups) == 2

    def test_backup_list_response_defaults(self):
        """Test BackupListResponse with default empty list."""
        response = BackupListResponse()
        assert response.backups == []


class TestCreateBackupResponse:
    """Tests for CreateBackupResponse model."""

    def test_create_backup_response_valid(self):
        """Test valid CreateBackupResponse creation."""
        response = CreateBackupResponse(
            backup_name="backup.tar.gz",
            status="success",
            message="Backup created successfully"
        )
        assert response.backup_name == "backup.tar.gz"
        assert response.status == "success"
        assert response.message == "Backup created successfully"


class TestRestoreBackupResponse:
    """Tests for RestoreBackupResponse model."""

    def test_restore_backup_response_valid(self):
        """Test valid RestoreBackupResponse creation."""
        response = RestoreBackupResponse(
            backup_name="backup.tar.gz",
            status="success",
            message="Backup restored successfully"
        )
        assert response.backup_name == "backup.tar.gz"
        assert response.status == "success"
        assert response.message == "Backup restored successfully"


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_error_response_create(self):
        """Test ErrorResponse.create class method."""
        response = ErrorResponse.create(
            code="test_error",
            message="Test error message",
            status_code=400
        )
        assert isinstance(response, Response)
        assert response.status_code == 400


class TestHealthResponse:
    """Tests for HealthResponse model."""

    def test_health_response_valid(self):
        """Test valid HealthResponse creation."""
        response = HealthResponse(
            status="healthy",
            timestamp="2026-06-29T10:00:00Z",
            version="1.0.0"
        )
        assert response.status == "healthy"
        assert response.timestamp == "2026-06-29T10:00:00Z"
        assert response.version == "1.0.0"
