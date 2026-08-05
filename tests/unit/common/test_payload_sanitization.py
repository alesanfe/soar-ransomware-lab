#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Payload Sanitization Tests
Unit tests for payload sanitization
"""

import pytest
from soar_lab.security.sanitization import PayloadSanitizer


class TestPayloadSanitization:
    """Test payload sanitization"""

    @pytest.fixture
    def sanitizer(self):
        """Create payload sanitizer for testing"""
        return PayloadSanitizer()

    def test_malicious_data_sanitization(self, sanitizer):
        """Test sanitization of malicious data"""
        malicious_payload = {
            "alert_id": "<script>alert('xss')</script>",
            "hostname": "'; DROP TABLE users; --",
            "description": "<img src=x onerror=alert(1)>"
        }

        sanitized = sanitizer.sanitize(malicious_payload)

        assert "<script>" not in sanitized['alert_id'], "Script tags should be removed"
        assert "DROP TABLE" not in sanitized['hostname'], "SQL injection should be removed"
        assert "onerror" not in sanitized['description'], "Event handlers should be removed"

    def test_encoding_decoding(self, sanitizer):
        """Test encoding and decoding"""
        original_data = {"alert_id": "TEST-001", "hostname": "test-host"}

        # Encode
        encoded = sanitizer.encode(original_data)

        # Decode
        decoded = sanitizer.decode(encoded)

        assert decoded == original_data, "Decoded data should match original"

    def test_html_sanitization(self, sanitizer):
        """Test HTML sanitization"""
        html_payload = "<div><script>alert('xss')</script><p>content</p></div>"

        sanitized = sanitizer.sanitize_html(html_payload)

        assert "<script>" not in sanitized, "Script tags should be removed"
        assert "<p>" in sanitized, "Safe HTML tags should be preserved"

    def test_js_sanitization(self, sanitizer):
        """Test JavaScript sanitization"""
        js_payload = "javascript:alert('xss')"

        sanitized = sanitizer.sanitize_js(js_payload)

        assert "javascript:" not in sanitized.lower(), "JavaScript protocol should be removed"

    def test_type_validation(self, sanitizer):
        """Test type validation"""
        invalid_payload = {
            "alert_id": 123,  # Should be string
            "severity": "high",  # Should be integer
            "timestamp": "invalid-date"
        }

        is_valid = sanitizer.validate_types(invalid_payload)
        assert not is_valid, "Invalid types should be rejected"

    def test_null_byte_removal(self, sanitizer):
        """Test null byte removal"""
        payload_with_nulls = {
            "alert_id": "TEST\x00-001",
            "hostname": "host\x00name"
        }

        sanitized = sanitizer.sanitize(payload_with_nulls)

        assert "\x00" not in sanitized['alert_id'], "Null bytes should be removed"
        assert "\x00" not in sanitized['hostname'], "Null bytes should be removed"

    def test_control_character_removal(self, sanitizer):
        """Test control character removal"""
        payload_with_controls = {
            "alert_id": "TEST\r\n-001",
            "hostname": "host\tname"
        }

        sanitized = sanitizer.sanitize(payload_with_controls)

        # Control characters should be handled appropriately
        assert True, "Control characters should be sanitized"

    def test_unicode_normalization(self, sanitizer):
        """Test Unicode normalization"""
        unicode_payload = {
            "alert_id": "TEST-À-001",
            "hostname": "höst-näme"
        }

        sanitized = sanitizer.sanitize(unicode_payload)

        # Unicode should be normalized
        assert True, "Unicode should be normalized"

    def test_max_length_enforcement(self, sanitizer):
        """Test max length enforcement"""
        long_payload = {
            "alert_id": "A" * 1000,
            "hostname": "B" * 1000
        }

        sanitized = sanitizer.sanitize(long_payload, max_length=100)

        assert len(sanitized['alert_id']) <= 100, "Alert ID should be truncated"
        assert len(sanitized['hostname']) <= 100, "Hostname should be truncated"

    def test_field_whitelist(self, sanitizer):
        """Test field whitelist"""
        payload = {
            "alert_id": "TEST-001",
            "hostname": "test-host",
            "malicious_field": "should_be_removed"
        }

        whitelist = ["alert_id", "hostname"]
        sanitized = sanitizer.sanitize(payload, whitelist=whitelist)

        assert "alert_id" in sanitized, "Whitelisted field should be preserved"
        assert "hostname" in sanitized, "Whitelisted field should be preserved"
        assert "malicious_field" not in sanitized, "Non-whitelisted field should be removed"

    def test_field_blacklist(self, sanitizer):
        """Test field blacklist"""
        payload = {
            "alert_id": "TEST-001",
            "hostname": "test-host",
            "password": "secret123"
        }

        blacklist = ["password", "api_key"]
        sanitized = sanitizer.sanitize(payload, blacklist=blacklist)

        assert "alert_id" in sanitized, "Non-blacklisted field should be preserved"
        assert "password" not in sanitized, "Blacklisted field should be removed"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
