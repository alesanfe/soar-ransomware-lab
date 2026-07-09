#!/usr/bin/env python3
"""
Unit tests for soar_lab.infrastructure.jwt_token_provider
"""

import pytest
from unittest.mock import Mock

from soar_lab.exceptions import AuthError
from soar_lab.infrastructure.jwt_token_provider import JWTTokenProvider


class TestJWTTokenProvider:
    """Test JWTTokenProvider infrastructure adapter"""

    def test_create_token_success(self):
        """Test successful token creation"""
        provider = JWTTokenProvider()
        token = provider.create_token("testuser", "test-secret-key-min-32-chars-long", 60, "HS256")

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_short_secret(self):
        """Test token creation with short secret - provider allows it, jose handles validation"""
        provider = JWTTokenProvider()
        # The provider doesn't validate secret length, jose library does
        token = provider.create_token("testuser", "short", 60, "HS256")
        assert token is not None

    def test_verify_token_success(self):
        """Test successful token verification"""
        provider = JWTTokenProvider()
        secret = "test-secret-key-min-32-chars-long"

        token = provider.create_token("testuser", secret, 60, "HS256")
        payload = provider.verify_token(token, secret, "HS256")

        assert payload is not None
        assert payload["user"] == "testuser"
        assert payload["method"] == "jwt"

    def test_verify_token_invalid(self):
        """Test token verification with invalid token"""
        provider = JWTTokenProvider()

        with pytest.raises(AuthError) as exc_info:
            provider.verify_token("invalid_token", "test-secret-key-min-32-chars-long", "HS256")

        assert "Invalid authentication credentials" in str(exc_info.value)

    def test_verify_token_wrong_secret(self):
        """Test token verification with wrong secret"""
        provider = JWTTokenProvider()
        secret1 = "test-secret-key-min-32-chars-long"
        secret2 = "different-secret-key-min-32-chars-long"

        token = provider.create_token("testuser", secret1, 60, "HS256")

        with pytest.raises(AuthError):
            provider.verify_token(token, secret2, "HS256")

    def test_create_token_custom_expiration(self):
        """Test token creation with custom expiration"""
        provider = JWTTokenProvider()
        token = provider.create_token("testuser", "test-secret-key-min-32-chars-long", 120, "HS256")

        assert token is not None
        payload = provider.verify_token(token, "test-secret-key-min-32-chars-long", "HS256")
        assert payload["user"] == "testuser"

    def test_create_token_exception(self):
        """Test token creation raises AuthError on exception"""
        provider = JWTTokenProvider()

        with pytest.raises(AuthError) as exc_info:
            provider.create_token("testuser", "secret", 60, "INVALID_ALGORITHM")

        assert "Failed to create authentication token" in str(exc_info.value)

    def test_verify_token_missing_username(self):
        """Test token verification when payload has no username"""
        from jose import jwt

        provider = JWTTokenProvider()
        secret = "test-secret-key-min-32-chars-long"

        # Create a token without 'sub' field
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        payload = {
            "iat": now,
            "exp": now + timedelta(minutes=60),
            "scope": "access"
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

        with pytest.raises(AuthError) as exc_info:
            provider.verify_token(token, secret, "HS256")

        assert "Invalid token payload" in str(exc_info.value)

    def test_verify_token_expired(self):
        """Test token verification with expired token"""
        from jose import jwt
        from datetime import datetime, timedelta, timezone

        provider = JWTTokenProvider()
        secret = "test-secret-key-min-32-chars-long"

        # Create an expired token
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "testuser",
            "iat": now - timedelta(days=2),
            "exp": now - timedelta(days=1),
            "scope": "access"
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

        with pytest.raises(AuthError) as exc_info:
            provider.verify_token(token, secret, "HS256")

        assert "Invalid authentication credentials" in str(exc_info.value)
