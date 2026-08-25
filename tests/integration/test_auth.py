#!/usr/bin/env python3
"""Unit tests for auth.py Tests authentication adapter."""

from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from soar_lab.application.use_cases.auth_service import AuthService
from soar_lab.common.exceptions import AuthError
from soar_lab.interfaces.api.auth import create_get_current_user


class TestAuthAdapter:
    """Test auth adapter functions."""

    def test_create_get_current_user_requires_auth_service(self):
        """Test that create_get_current_user requires auth_service."""
        with pytest.raises(ValueError, match="auth_service is required"):
            create_get_current_user(None)

    def test_create_get_current_user_returns_dependency(self):
        """Test that create_get_current_user returns a callable dependency."""
        mock_auth_service = Mock()
        dependency = create_get_current_user(mock_auth_service)
        assert callable(dependency)

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """Test successful authentication via get_current_user."""
        mock_auth_service = Mock()
        mock_auth_service.verify_jwt_token.return_value = {"user": "testuser", "method": "jwt"}

        dependency = create_get_current_user(mock_auth_service)

        # Mock the credentials
        mock_credentials = Mock()
        mock_credentials.credentials = "valid-token"

        # Call the dependency (it's not async, but we need to handle the Depends)
        result = dependency(mock_credentials)

        assert result == {"user": "testuser", "method": "jwt"}
        mock_auth_service.verify_jwt_token.assert_called_once_with("valid-token")

    @pytest.mark.asyncio
    async def test_get_current_user_auth_error(self):
        """Test get_current_user raises HTTPException on AuthError."""
        mock_auth_service = Mock()
        mock_auth_service.verify_jwt_token.side_effect = AuthError("Invalid token", status_code=401)

        dependency = create_get_current_user(mock_auth_service)

        mock_credentials = Mock()
        mock_credentials.credentials = "invalid-token"

        with pytest.raises(HTTPException) as exc_info:
            dependency(mock_credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)

    def test_auth_service_requires_config_provider(self):
        """Test that AuthService requires config_provider."""
        with pytest.raises(ValueError, match="config_provider is required"):
            AuthService(None, Mock())

    def test_auth_service_requires_token_provider(self):
        """Test that AuthService requires token_provider."""
        with pytest.raises(ValueError, match="token_provider is required"):
            AuthService(Mock(), None)

    def test_auth_service_verify_credentials_success(self):
        """Test successful credential verification."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "web_ui_user": "admin",
            "web_ui_password": "password",
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        result = service.verify_credentials("admin", "password")
        assert result is True

    def test_auth_service_verify_credentials_failure(self):
        """Test failed credential verification."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "web_ui_user": "admin",
            "web_ui_password": "password",
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        result = service.verify_credentials("admin", "wrong")
        assert result is False

    def test_auth_service_verify_credentials_not_configured(self):
        """Test credential verification when not configured."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: None
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        result = service.verify_credentials("admin", "password")
        assert result is False

    def test_auth_service_create_token_uses_provider(self):
        """Test that create_token delegates to token provider."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "jwt_secret_key": "test-secret-key-min-32-chars-long",
            "api_auth_secret": "",
            "JWT_EXPIRATION_MINUTES": 60,
            "JWT_ALGORITHM": "HS256",
        }.get(key, default)
        mock_token_provider = Mock()
        mock_token_provider.create_token.return_value = "test-token"

        service = AuthService(mock_config, mock_token_provider)
        token = service.create_jwt_token("testuser")

        mock_token_provider.create_token.assert_called_once_with(
            "testuser", "test-secret-key-min-32-chars-long", 60, "HS256"
        )
        assert token == "test-token"

    def test_auth_service_verify_token_uses_provider(self):
        """Test that verify_token delegates to token provider."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "jwt_secret_key": "test-secret-key-min-32-chars-long",
            "api_auth_secret": "",
            "JWT_ALGORITHM": "HS256",
        }.get(key, default)
        mock_token_provider = Mock()
        mock_token_provider.verify_token.return_value = {"user": "testuser", "method": "jwt"}

        service = AuthService(mock_config, mock_token_provider)
        payload = service.verify_jwt_token("test-token")

        mock_token_provider.verify_token.assert_called_once_with(
            "test-token", "test-secret-key-min-32-chars-long", "HS256"
        )
        assert payload == {"user": "testuser", "method": "jwt"}
