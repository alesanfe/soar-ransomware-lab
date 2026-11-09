#!/usr/bin/env python3
"""Unit tests for generate_secrets.py."""

import string
from unittest.mock import Mock

from scripts.setup.generate_secrets import SecretGeneratorService


class TestSecretGeneratorService:
    """Test SecretGeneratorService."""

    def test_initialization(self):
        """Test successful initialization."""
        service = SecretGeneratorService()

        assert service.file_system is None

    def test_initialization_with_filesystem(self):
        """Test initialization with file_system."""
        mock_filesystem = Mock()

        service = SecretGeneratorService(file_system=mock_filesystem)

        assert service.file_system == mock_filesystem

    def test_generate_password_default_length(self):
        """Test generating password with default length."""
        service = SecretGeneratorService()
        password = service.generate_password()

        assert len(password) == 32
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    def test_generate_password_custom_length(self):
        """Test generating password with custom length."""
        service = SecretGeneratorService()
        password = service.generate_password(length=16)

        assert len(password) == 16

    def test_generate_password_minimum_length(self):
        """Test generating password with length below minimum."""
        service = SecretGeneratorService()
        password = service.generate_password(length=4)

        assert len(password) == 8  # Should enforce minimum of 8

    def test_generate_api_key_default_length(self):
        """Test generating API key with default length."""
        service = SecretGeneratorService()
        api_key = service.generate_api_key()

        assert len(api_key) == 32
        assert "0" not in api_key
        assert "O" not in api_key
        assert "l" not in api_key
        assert "I" not in api_key

    def test_generate_api_key_custom_length(self):
        """Test generating API key with custom length."""
        service = SecretGeneratorService()
        api_key = service.generate_api_key(length=24)

        assert len(api_key) == 24

    def test_generate_api_key_distribution(self):
        """Test API key has good character distribution."""
        service = SecretGeneratorService()
        api_key = service.generate_api_key()

        upper_count = sum(1 for c in api_key if c.isupper())
        lower_count = sum(1 for c in api_key if c.islower())
        digit_count = sum(1 for c in api_key if c.isdigit())

        # Should have at least some of each type
        assert upper_count > 0
        assert lower_count > 0
        assert digit_count > 0

    def test_generate_webhook_token_default_length(self):
        """Test generating webhook token with default length."""
        service = SecretGeneratorService()
        token = service.generate_webhook_token()

        assert len(token) == 64
        assert all(c in string.ascii_letters + string.digits for c in token)

    def test_generate_webhook_token_custom_length(self):
        """Test generating webhook token with custom length."""
        service = SecretGeneratorService()
        token = service.generate_webhook_token(length=32)

        assert len(token) == 32

    def test_generate_jwt_secret_default_length(self):
        """Test generating JWT secret with default length."""
        service = SecretGeneratorService()
        secret = service.generate_jwt_secret()

        assert len(secret) == 64
        assert all(c in string.ascii_letters + string.digits for c in secret)

    def test_generate_jwt_secret_custom_length(self):
        """Test generating JWT secret with custom length."""
        service = SecretGeneratorService()
        secret = service.generate_jwt_secret(length=32)

        assert len(secret) == 32

    def test_generate_secret_key_default_length(self):
        """Test generating secret key with default length."""
        service = SecretGeneratorService()
        key = service.generate_secret_key()

        # token_hex generates 2 hex chars per byte, so 32//2 = 16 bytes = 32 hex chars
        assert len(key) == 32
        assert all(c in string.hexdigits for c in key)

    def test_generate_secret_key_custom_length(self):
        """Test generating secret key with custom length."""
        service = SecretGeneratorService()
        key = service.generate_secret_key(length=64)

        assert len(key) == 64

    def test_generate_token_default_length(self):
        """Test generating token with default length."""
        service = SecretGeneratorService()
        token = service.generate_token()

        assert len(token) == 48

    def test_generate_token_custom_length(self):
        """Test generating token with custom length."""
        service = SecretGeneratorService()
        token = service.generate_token(length=32)

        assert len(token) == 32

    def test_validate_secret_format_valid(self):
        """Test validating secret format with valid secret."""
        service = SecretGeneratorService()
        secret = "abc123XYZ"
        allowed = string.ascii_letters + string.digits

        result = service.validate_secret_format(secret, 9, allowed)

        assert result

    def test_validate_secret_format_invalid_length(self):
        """Test validating secret format with invalid length."""
        service = SecretGeneratorService()
        secret = "abc123"
        allowed = string.ascii_letters + string.digits

        result = service.validate_secret_format(secret, 9, allowed)

        assert result is False

    def test_validate_secret_format_invalid_chars(self):
        """Test validating secret format with invalid characters."""
        service = SecretGeneratorService()
        secret = "abc123XYZ!"
        allowed = string.ascii_letters + string.digits

        result = service.validate_secret_format(secret, 10, allowed)

        assert result is False

    def test_validate_secret_format_empty(self):
        """Test validating secret format with empty string."""
        service = SecretGeneratorService()

        result = service.validate_secret_format("", 10, string.ascii_letters)

        assert result is False

    def test_generate_all_secrets(self):
        """Test generating all secrets."""
        service = SecretGeneratorService()
        secrets = service.generate_all_secrets()

        assert "thehive_api_key" in secrets
        assert "cortex_api_key" in secrets
        assert "shuffle_api_key" in secrets
        assert "shuffle_webhook_token" in secrets
        assert "jwt_secret" in secrets
        assert "generated_at" in secrets
        assert len(secrets["thehive_api_key"]) == 32
        assert len(secrets["shuffle_webhook_token"]) == 64
        assert len(secrets["jwt_secret"]) == 64

    def test_generate_all_secrets_with_file(self):
        """Test generating all secrets and saving to file."""
        mock_filesystem = Mock()
        service = SecretGeneratorService(file_system=mock_filesystem)

        secrets = service.generate_all_secrets(output_file="/path/to/secrets.json")

        assert "thehive_api_key" in secrets
        mock_filesystem.write_file.assert_called_once()
        call_args = mock_filesystem.write_file.call_args
        assert call_args[0][0] == "/path/to/secrets.json"
        assert "thehive_api_key" in call_args[0][1]

    def test_generate_all_secrets_no_filesystem(self):
        """Test generating all secrets without filesystem when output_file
        specified."""
        service = SecretGeneratorService()

        secrets = service.generate_all_secrets(output_file="/path/to/secrets.json")

        # Should still generate secrets but not write file
        assert "thehive_api_key" in secrets

    def test_password_uniqueness(self):
        """Test that generated passwords are unique."""
        service = SecretGeneratorService()
        passwords = [service.generate_password() for _ in range(10)]

        assert len(set(passwords)) == 10  # All should be unique

    def test_api_key_uniqueness(self):
        """Test that generated API keys are unique."""
        service = SecretGeneratorService()
        keys = [service.generate_api_key() for _ in range(10)]

        assert len(set(keys)) == 10  # All should be unique


class TestSecretMutationHardening:
    """Deterministic kills for alphabet/exclusion/formatting mutants."""

    EXPECTED_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # ascii_uppercase minus 'O','I'
    EXPECTED_LOWER = "abcdefghijkmnopqrstuvwxyz"  # ascii_lowercase minus 'l'
    EXPECTED_DIGITS = "23456789"  # digits minus '0','1'
    EXPECTED_SPECIAL = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    @staticmethod
    def _capture_choices(monkeypatch):
        """Patch secrets.choice to record every alphabet it receives."""
        import soar_lab.security.secret_generator as sg

        captured = []

        def fake_choice(alphabet):
            captured.append(alphabet)
            return alphabet[0]

        monkeypatch.setattr(sg.secrets, "choice", fake_choice)
        return captured

    def test_password_component_alphabets_exact(self, monkeypatch):
        captured = self._capture_choices(monkeypatch)
        service = SecretGeneratorService()
        service.generate_password(8)
        assert captured[0] == string.ascii_uppercase
        assert captured[1] == string.ascii_lowercase
        assert captured[2] == string.digits
        assert captured[3] == self.EXPECTED_SPECIAL
        assert captured[4] == (
            string.ascii_uppercase + string.ascii_lowercase + string.digits + self.EXPECTED_SPECIAL
        )

    def test_api_key_exclusion_alphabets_exact(self, monkeypatch):
        captured = self._capture_choices(monkeypatch)
        service = SecretGeneratorService()
        service.generate_api_key()
        expected_full = (
            "".join(c for c in string.ascii_letters if c not in "0Ol1I") + self.EXPECTED_DIGITS
        )
        for i in range(7):
            assert captured[i * 3] == self.EXPECTED_UPPER
            assert captured[i * 3 + 1] == self.EXPECTED_LOWER
            assert captured[i * 3 + 2] == self.EXPECTED_DIGITS
        assert captured[21] == expected_full

    def test_all_secrets_lengths_and_utc_timestamp(self):
        secrets = SecretGeneratorService().generate_all_secrets()
        assert len(secrets["thehive_api_key"]) == 32
        assert len(secrets["cortex_api_key"]) == 32
        assert len(secrets["shuffle_api_key"]) == 32
        assert secrets["generated_at"].endswith("Z")
        assert "+00:00" not in secrets["generated_at"]

    def test_all_secrets_file_uses_four_space_indent(self):
        mock_filesystem = Mock()
        service = SecretGeneratorService(file_system=mock_filesystem)
        service.generate_all_secrets(output_file="/tmp/secrets.json")
        content = mock_filesystem.write_file.call_args[0][1]
        assert '\n    "thehive_api_key"' in content
