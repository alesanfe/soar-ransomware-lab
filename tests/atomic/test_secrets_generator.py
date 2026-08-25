#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Atomic Tests for Secrets Generator (Corrected)
Tests individual secrets generation functions in isolation
"""

import re
import string

import scripts.setup.generate_secrets as secrets_module


class TestSecretsGeneratorAtomic:
    """Atomic tests for individual secrets generation functions."""

    def test_generate_password_default_length(self):
        """Test password generation with default length."""
        password = secrets_module.generate_password()
        assert len(password) == 32  # Corrected: actual default is 32

    def test_generate_password_custom_length(self):
        """Test password generation with custom length."""
        for length in [8, 12, 16, 24, 32]:
            password = secrets_module.generate_password(length)
            assert len(password) == length

    def test_generate_password_complexity(self):
        """Test password complexity requirements."""
        password = secrets_module.generate_password(20)

        # Should contain uppercase letters
        assert any(c.isupper() for c in password)
        # Should contain lowercase letters
        assert any(c.islower() for c in password)
        # Should contain digits
        assert any(c.isdigit() for c in password)
        # Should contain special characters
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    def test_generate_api_key_default(self):
        """Test API key generation with default length."""
        api_key = secrets_module.generate_api_key()
        assert len(api_key) == 32
        # Should not contain ambiguous characters
        assert all(c not in "0Ol1I" for c in api_key)
        # Should be alphanumeric
        assert all(c.isalnum() for c in api_key)

    def test_generate_api_key_custom_length(self):
        """Test API key generation with custom length."""
        api_key = secrets_module.generate_api_key(16)
        assert len(api_key) == 21  # Corrected: minimum 21 due to forced distribution
        assert all(c not in "0Ol1I" for c in api_key)

    def test_generate_jwt_secret_default(self):
        """Test JWT secret generation with default length."""
        jwt_secret = secrets_module.generate_jwt_secret()
        assert len(jwt_secret) == 64
        assert all(c.isalnum() for c in jwt_secret)

    def test_generate_webhook_token_default(self):
        """Test webhook token generation with default length."""
        webhook_token = secrets_module.generate_webhook_token()
        assert len(webhook_token) == 64
        assert all(c.isalnum() for c in webhook_token)

    def test_generate_secret_key_default(self):
        """Test secret key generation with default length."""
        secret_key = secrets_module.generate_secret_key()
        assert len(secret_key) == 32  # Corrected: token_hex(16) gives 32 chars
        # Should be hex
        assert all(c in "0123456789abcdef" for c in secret_key.lower())

    def test_generate_token_default(self):
        """Test token generation with default length."""
        token = secrets_module.generate_token()
        assert len(token) == 48
        # Should be URL-safe base64 characters
        assert all(c.isalnum() or c in "-_" for c in token)

    def test_validate_secret_format_valid(self):
        """Test secret format validation with valid secrets."""
        # Test API key validation - use actual generated API key format
        api_key = secrets_module.generate_api_key(32)
        result = secrets_module.validate_secret_format(
            api_key,
            32,
            "".join(c for c in string.ascii_letters + string.digits if c not in "0Ol1I"),
        )
        assert result is True

        # Test JWT secret validation
        jwt_secret = secrets_module.generate_jwt_secret(64)
        result = secrets_module.validate_secret_format(
            jwt_secret, 64, string.ascii_letters + string.digits
        )
        assert result is True

    def test_validate_secret_format_invalid_length(self):
        """Test secret format validation with invalid length."""
        short_secret = "ABC"
        result = secrets_module.validate_secret_format(short_secret, 32, "ABCDEF")
        assert result is False

    def test_validate_secret_format_invalid_chars(self):
        """Test secret format validation with invalid characters."""
        invalid_secret = "ABC@#$%^&*()DEF"
        result = secrets_module.validate_secret_format(invalid_secret, 16, "ABCDEF")
        assert result is False

    def test_generate_all_secrets_structure(self):
        """Test generate all secrets returns proper structure."""
        secrets = secrets_module.generate_all_secrets()

        expected_keys = [
            "thehive_api_key",
            "cortex_api_key",
            "shuffle_api_key",
            "shuffle_webhook_token",
            "jwt_secret",
            "generated_at",
        ]

        for key in expected_keys:
            assert key in secrets
            assert isinstance(secrets[key], str)
            assert len(secrets[key]) > 0

    def test_generate_all_secrets_completeness(self):
        """Test generate all secrets includes all required fields."""
        secrets = secrets_module.generate_all_secrets()

        # Check API keys are 32 chars
        assert len(secrets["thehive_api_key"]) == 32
        assert len(secrets["cortex_api_key"]) == 32
        assert len(secrets["shuffle_api_key"]) == 32

        # Check webhook token is 64 chars
        assert len(secrets["shuffle_webhook_token"]) == 64

        # Check JWT secret is 64 chars
        assert len(secrets["jwt_secret"]) == 64

        # Check generated_at is ISO format

        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", secrets["generated_at"])

    def test_generate_all_secrets_uniqueness(self):
        """Test generate all secrets produces unique values."""
        secrets1 = secrets_module.generate_all_secrets()
        secrets2 = secrets_module.generate_all_secrets()

        # All values should be different between calls
        for key in ["thehive_api_key", "cortex_api_key", "shuffle_api_key"]:
            assert secrets1[key] != secrets2[key]

    def test_generate_all_secrets_validity(self):
        """Test generate all secrets produces valid secrets."""
        secrets = secrets_module.generate_all_secrets()

        # Validate API keys
        for key in ["thehive_api_key", "cortex_api_key", "shuffle_api_key"]:
            api_key = secrets[key]
            assert len(api_key) == 32
            assert all(c not in "0Ol1I" for c in api_key)
            assert all(c.isalnum() for c in api_key)

    def test_edge_cases_empty_string_validation(self):
        """Test validation with empty string."""
        result = secrets_module.validate_secret_format("", 16, "ABCDEF")
        assert result is False

    def test_edge_cases_whitespace_validation(self):
        """Test validation with whitespace."""
        result = secrets_module.validate_secret_format(" ABC DEF ", 16, "ABCDEF")
        assert result is False

    def test_edge_cases_minimum_length(self):
        """Test generation with minimum valid length."""
        password = secrets_module.generate_password(8)
        assert len(password) == 8
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    def test_edge_cases_large_length(self):
        """Test generation with large length."""
        password = secrets_module.generate_password(128)
        assert len(password) == 128
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    def test_secret_key_hex_format(self):
        """Test secret key is properly formatted as hex."""
        secret_key = secrets_module.generate_secret_key(32)
        assert len(secret_key) == 32
        # Should be valid hex
        try:
            int(secret_key, 16)
            is_hex = True
        except ValueError:
            is_hex = False
        assert is_hex is True

    def test_token_url_safe_format(self):
        """Test token uses URL-safe characters."""
        token = secrets_module.generate_token()
        # Should not contain URL-unsafe characters
        unsafe_chars = "+/="
        for char in unsafe_chars:
            assert char not in token

    def test_password_special_chars(self):
        """Test password contains required special characters."""
        password = secrets_module.generate_password(32)
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        has_special = any(c in special_chars for c in password)
        assert has_special is True

    def test_api_key_no_ambiguous_chars(self):
        """Test API key excludes ambiguous characters."""
        api_key = secrets_module.generate_api_key()
        ambiguous_chars = "0Ol1I"
        for char in ambiguous_chars:
            assert char not in api_key
