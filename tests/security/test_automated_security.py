#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Automated Security Tests
Comprehensive security testing for SOAR components
Refactored to be compatible with pytest
"""

import pytest
from datetime import datetime, timezone

from soar_lab.config.schemas import validate_alert_data


class TestSecurityInputValidation:
    """Test input validation security"""

    def test_malformed_alert_id_rejected(self):
        """Test that malformed alert IDs are rejected"""
        alert = {
            "alert_id": "INVALID-ID",
            "hostname": "test-host",
            "src_ip": "192.168.1.1",
            "hash": {"sha256": "a" * 64},
            "severity": "2",
            "source": "test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "description": "Test alert"
        }
        is_valid, errors = validate_alert_data(alert)
        assert not is_valid, "Malformed alert ID should be rejected"
        assert errors, "Should return validation errors"

    def test_invalid_ip_address_rejected(self):
        """Test that invalid IP addresses are rejected"""
        alert = {
            "alert_id": "ALERT-1234567890-0001",
            "hostname": "test-host",
            "src_ip": "999.999.999.999",
            "hash": {"sha256": "a" * 64},
            "severity": "2",
            "source": "test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "description": "Test alert"
        }
        is_valid, errors = validate_alert_data(alert)
        assert not is_valid, "Invalid IP address should be rejected"
        assert errors, "Should return validation errors"

    def test_invalid_hash_format_rejected(self):
        """Test that invalid hash formats are rejected"""
        alert = {
            "alert_id": "ALERT-1234567890-0002",
            "hostname": "test-host",
            "src_ip": "192.168.1.1",
            "hash": {"sha256": "invalid_hash"},
            "severity": "2",
            "source": "test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "description": "Test alert"
        }
        is_valid, errors = validate_alert_data(alert)
        assert not is_valid, "Invalid hash format should be rejected"
        assert errors, "Should return validation errors"

    def test_missing_required_fields_rejected(self):
        """Test that missing required fields are rejected"""
        alert = {
            "alert_id": "ALERT-1234567890-0003",
            "hostname": "test-host",
            # Missing src_ip, hash, etc.
            "severity": "2",
            "source": "test"
        }
        is_valid, errors = validate_alert_data(alert)
        assert not is_valid, "Missing required fields should be rejected"
        assert errors, "Should return validation errors"

    def test_valid_alert_accepted(self):
        """Test that valid alerts are accepted"""
        alert = {
            "alert_id": "ALERT-1234567890-0001",
            "hostname": "test-host",
            "src_ip": "192.168.1.1",
            "hash": {"sha256": "a" * 64},
            "severity": "2",
            "source": "test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "description": "Test alert"
        }
        is_valid, errors = validate_alert_data(alert)
        assert is_valid, "Valid alert should be accepted"
        assert not errors, "Should not return validation errors"
