"""Tests for malformed payload validation.

Validates rejection of malformed payloads to prevent injection attacks.
"""

import pytest

from soar_lab.validation.validators import AlertValidator, ValidationError


class TestMalformedPayloads:
    """Test suite for malformed payload validation."""

    def test_missing_required_fields(self):
        """Test that payloads missing required fields are rejected."""
        payload = {
            "alert_id": "test-123",
            # Missing: hostname, hash, src_ip, timestamp
        }
        assert AlertValidator.validate(payload) is False

    def test_empty_payload(self):
        """Test that empty payload is rejected."""
        assert AlertValidator.validate({}) is False

    def test_null_values_in_required_fields(self):
        """Test that null values in required fields are rejected."""
        payload = {
            "alert_id": None,
            "hostname": "test-host",
            "hash": "abc123",
            "src_ip": "192.168.1.1",
            "timestamp": "2026-06-05T10:00:00Z",
        }
        assert AlertValidator.validate(payload) is False

    def test_invalid_ip_address(self):
        """Test that invalid IP addresses are rejected."""
        payload = {
            "alert_id": "test-123",
            "hostname": "test-host",
            "hash": "abc123",
            "src_ip": "999.999.999.999",  # Invalid IP
            "timestamp": "2026-06-05T10:00:00Z",
        }
        assert AlertValidator.validate(payload) is False

    def test_invalid_hash_format(self):
        """Test that invalid hash formats are rejected."""
        payload = {
            "alert_id": "test-123",
            "hostname": "test-host",
            "hash": "not-a-hash",  # Should be MD5/SHA1/SHA256
            "src_ip": "192.168.1.1",
            "timestamp": "2026-06-05T10:00:00Z",
        }
        assert AlertValidator.validate(payload) is False

    def test_valid_payload(self):
        """Test that valid payloads are accepted."""
        payload = {
            "alert_id": "test-123",
            "hostname": "test-host",
            "hash": "5d41402abc4b2a76b9719d911017c592",
            "src_ip": "192.168.1.1",
            "timestamp": "2026-06-05T10:00:00Z",
        }
        assert AlertValidator.validate(payload) is True

    def test_assert_valid_raises_on_invalid(self):
        """Test that assert_valid raises ValidationError on invalid payload."""
        payload = {
            "alert_id": "test-123",
            # Missing required fields
        }
        with pytest.raises(ValidationError):
            AlertValidator.assert_valid(payload)
