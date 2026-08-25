"""Unit tests for api.auth module."""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from soar_lab.common.exceptions import AuthError
from soar_lab.interfaces.api.auth import create_get_current_user


class TestCreateGetCurrentUser:
    """Tests for create_get_current_user factory function."""

    def test_create_get_current_user_with_none_auth_service(self):
        """Test that create_get_current_user raises ValueError when
        auth_service is None."""
        with pytest.raises(ValueError, match="auth_service is required"):
            create_get_current_user(None)

    def test_create_get_current_user_returns_dependency(self):
        """Test that create_get_current_user returns a callable dependency."""
        mock_auth_service = MockAuthService()
        dependency = create_get_current_user(mock_auth_service)
        assert callable(dependency)


class TestGetCurrentUser:
    """Tests for the get_current_user dependency function."""

    def test_get_current_user_valid_token(self):
        """Test successful authentication with valid token."""
        mock_auth_service = MockAuthService()
        dependency = create_get_current_user(mock_auth_service)

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")

        user_info = dependency(credentials)
        assert user_info == {"user": "test_user", "role": "admin"}

    def test_get_current_user_invalid_token(self):
        """Test authentication failure with invalid token."""
        mock_auth_service = MockAuthService(should_fail=True)
        dependency = create_get_current_user(mock_auth_service)

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")

        with pytest.raises(HTTPException) as exc_info:
            dependency(credentials)
        assert exc_info.value.detail == "Invalid token"


class MockAuthService:
    """Mock AuthService for testing."""

    def __init__(self, should_fail=False):
        self.should_fail = should_fail

    def verify_jwt_token(self, token):
        """Mock JWT token verification."""
        if self.should_fail:
            raise AuthError("Invalid token", status_code=401)
        return {"user": "test_user", "role": "admin"}
