#!/usr/bin/env python3
"""
Unit tests for exceptions.py
"""

import pytest

from soar_lab.common.exceptions import (
    SOARError,
    ConfigurationError,
    ValidationError,
    IntegrationError,
    BackupError,
    KPIError,
    AuthError,
    SubprocessError
)


class TestExceptions:
    """Test custom exceptions"""

    def test_soar_error(self):
        """Test base SOARError"""
        with pytest.raises(SOARError):
            raise SOARError("Test error")

    def test_configuration_error(self):
        """Test ConfigurationError"""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Missing config")

    def test_validation_error(self):
        """Test ValidationError"""
        with pytest.raises(ValidationError):
            raise ValidationError("Invalid input")

    def test_integration_error(self):
        """Test IntegrationError"""
        exc = IntegrationError("TheHive", "Connection failed")
        assert exc.service == "TheHive"
        assert "[TheHive]" in str(exc)
        assert "Connection failed" in str(exc)

    def test_backup_error(self):
        """Test BackupError"""
        with pytest.raises(BackupError):
            raise BackupError("Backup failed")

    def test_kpi_error(self):
        """Test KPIError"""
        with pytest.raises(KPIError):
            raise KPIError("KPI calculation failed")

    def test_auth_error_default_status(self):
        """Test AuthError with default status code"""
        exc = AuthError("Invalid token")
        assert exc.status_code == 401
        assert str(exc) == "Invalid token"

    def test_auth_error_custom_status(self):
        """Test AuthError with custom status code"""
        exc = AuthError("Forbidden", 403)
        assert exc.status_code == 403
        assert str(exc) == "Forbidden"

    def test_subprocess_error(self):
        """Test SubprocessError"""
        exc = SubprocessError(["ls", "-la"], 1, "Permission denied")
        assert exc.cmd == ["ls", "-la"]
        assert exc.returncode == 1
        assert exc.stderr == "Permission denied"
        assert "ls" in str(exc)
        assert "1" in str(exc)
        assert "Permission denied" in str(exc)

    def test_subprocess_error_no_stderr(self):
        """Test SubprocessError without stderr"""
        exc = SubprocessError(["echo", "test"], 0)
        assert exc.cmd == ["echo", "test"]
        assert exc.returncode == 0
        assert exc.stderr == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
