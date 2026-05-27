#!/usr/bin/env python3
"""
Unit tests for auth_service.py
Tests authentication service with mocked dependencies
"""

import pytest
from unittest.mock import Mock

from soar_lab.services.auth_service import AuthService
from soar_lab.exceptions import AuthError


class TestAuthService:
    """Test AuthService"""

    def test_initialization_success(self):
        """Test successful initialization"""
        mock_config = Mock()
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)

        assert service.config_provider == mock_config
        assert service.token_provider == mock_token_provider

    def test_requires_config_provider(self):
        """Test that config_provider is required"""
        mock_token_provider = Mock()
        with pytest.raises(ValueError, match="config_provider is required"):
            AuthService(None, mock_token_provider)

    def test_requires_token_provider(self):
        """Test that token_provider is required"""
        mock_config = Mock()
        with pytest.raises(ValueError, match="token_provider is required"):
            AuthService(mock_config, None)

    def test_verify_credentials_success(self):
        """Test successful credential verification"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'web_ui_user': 'admin',
            'web_ui_password': 'password'
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        result = service.verify_credentials("admin", "password")

        assert result is True

    def test_verify_credentials_failure(self):
        """Test failed credential verification"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'web_ui_user': 'admin',
            'web_ui_password': 'password'
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        result = service.verify_credentials("admin", "wrong")

        assert result is False

    def test_verify_credentials_not_configured(self):
        """Test credential verification when not configured"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: None
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        result = service.verify_credentials("admin", "password")

        assert result is False

    def test_create_jwt_token_success(self):
        """Test successful JWT token creation"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'jwt_secret_key': 'test-secret-key-min-32-chars-long',
            'api_auth_secret': '',
            'JWT_EXPIRATION_MINUTES': 60,
            'JWT_ALGORITHM': 'HS256'
        }.get(key, default)
        mock_token_provider = Mock()
        mock_token_provider.create_token.return_value = "test-token"

        service = AuthService(mock_config, mock_token_provider)
        token = service.create_jwt_token("testuser")

        assert token == "test-token"
        mock_token_provider.create_token.assert_called_once_with(
            "testuser", "test-secret-key-min-32-chars-long", 60, "HS256"
        )

    def test_create_jwt_token_no_secret(self):
        """Test JWT token creation when secret is not configured"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: None
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)

        with pytest.raises(AuthError, match="Authentication system not properly configured"):
            service.create_jwt_token("testuser")

    def test_create_jwt_token_short_secret(self):
        """Test JWT token creation with short secret (non-legacy)"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'jwt_secret_key': 'short',
            'api_auth_secret': '',
            'JWT_EXPIRATION_MINUTES': 60,
            'JWT_ALGORITHM': 'HS256'
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)

        with pytest.raises(AuthError, match="Authentication system not properly configured"):
            service.create_jwt_token("testuser")

    def test_create_jwt_token_short_secret_legacy(self):
        """Test JWT token creation with short secret but legacy API_AUTH_SECRET"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'jwt_secret_key': 'short',
            'api_auth_secret': 'legacy-secret',
            'JWT_EXPIRATION_MINUTES': 60,
            'JWT_ALGORITHM': 'HS256'
        }.get(key, default)
        mock_token_provider = Mock()
        mock_token_provider.create_token.return_value = "test-token"

        service = AuthService(mock_config, mock_token_provider)
        token = service.create_jwt_token("testuser")

        # Should succeed because legacy secret is set
        assert token == "test-token"

    def test_verify_jwt_token_success(self):
        """Test successful JWT token verification"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'jwt_secret_key': 'test-secret-key-min-32-chars-long',
            'api_auth_secret': '',
            'JWT_ALGORITHM': 'HS256'
        }.get(key, default)
        mock_token_provider = Mock()
        mock_token_provider.verify_token.return_value = {"user": "testuser", "method": "jwt"}

        service = AuthService(mock_config, mock_token_provider)
        payload = service.verify_jwt_token("test-token")

        assert payload == {"user": "testuser", "method": "jwt"}
        mock_token_provider.verify_token.assert_called_once_with(
            "test-token", "test-secret-key-min-32-chars-long", "HS256"
        )

    def test_verify_jwt_token_no_secret(self):
        """Test JWT token verification when secret is not configured"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: None
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)

        with pytest.raises(AuthError, match="Authentication system not properly configured"):
            service.verify_jwt_token("test-token")

    def test_verify_jwt_token_short_secret(self):
        """Test JWT token verification with short secret (non-legacy)"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'jwt_secret_key': 'short',
            'api_auth_secret': '',
            'JWT_ALGORITHM': 'HS256'
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)

        with pytest.raises(AuthError, match="Authentication system not properly configured"):
            service.verify_jwt_token("test-token")

    def test_get_auth_secret_uses_jwt_secret(self):
        """Test _get_auth_secret uses jwt_secret_key"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'jwt_secret_key': 'jwt-secret',
            'api_auth_secret': 'api-secret'
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        secret = service._get_auth_secret()

        assert secret == 'jwt-secret'

    def test_get_auth_secret_fallback_to_api_auth(self):
        """Test _get_auth_secret falls back to api_auth_secret"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'jwt_secret_key': None,
            'api_auth_secret': 'api-secret'
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        secret = service._get_auth_secret()

        assert secret == 'api-secret'

    def test_get_auth_secret_empty_when_none(self):
        """Test _get_auth_secret returns empty string when neither is set"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: None
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        secret = service._get_auth_secret()

        assert secret == ""
