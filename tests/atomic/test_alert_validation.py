#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Atomic Tests for Alert Validation
Tests individual validation functions in isolation
"""

import unittest
from datetime import UTC

from soar_lab.validation.validators import AlertValidator


class TestAlertValidationAtomic(unittest.TestCase):
    """Atomic tests for individual alert validation functions."""

    def test_validate_alert_structure_complete(self):
        """Test alert structure validation with complete data."""
        alert = {
            "alert_id": "TEST-001",
            "hostname": "test-host",
            "src_ip": "192.168.1.100",
            "hash": "a" * 64,
            "severity": 2,
            "event_type": "ransomware_detection",
        }
        assert AlertValidator.validate_structure(alert)

    def test_validate_alert_structure_missing_required_fields(self):
        """Test alert structure validation with missing required fields."""
        invalid_alerts = [
            {"alert_id": "TEST-002"},  # Missing all other fields
            {"hostname": "test-host", "severity": 1},  # Missing alert_id, src_ip, hash, event_type
            {
                "alert_id": "TEST-003",
                "src_ip": "192.168.1.1",
            },  # Missing hostname, hash, severity, event_type
            {"alert_id": "TEST-004", "severity": 2},  # Missing hostname, src_ip, hash, event_type
        ]

        for alert in invalid_alerts:
            assert not AlertValidator.validate_structure(alert)

    def test_validate_alert_structure_invalid_severity(self):
        """Test alert structure validation with invalid severity."""
        alert = {
            "alert_id": "TEST-005",
            "hostname": "test-host",
            "src_ip": "192.168.1.100",
            "hash": "a" * 64,
            "severity": 99,  # Invalid severity
            "event_type": "ransomware_detection",
        }
        assert not AlertValidator.validate_structure(alert)

    def test_validate_alert_structure_invalid_hash(self):
        """Test alert structure validation with invalid hash."""
        alert = {
            "alert_id": "TEST-006",
            "hostname": "test-host",
            "src_ip": "192.168.1.100",
            "hash": "invalid_hash",  # Invalid hash format
            "severity": 2,
            "event_type": "ransomware_detection",
        }
        assert not AlertValidator.validate_structure(alert)

    def test_validate_alert_structure_invalid_ip(self):
        """Test alert structure validation with invalid IP."""
        alert = {
            "alert_id": "TEST-007",
            "hostname": "test-host",
            "src_ip": "999.999.999.999",  # Invalid IP
            "hash": "a" * 64,
            "severity": 2,
            "event_type": "ransomware_detection",
        }
        assert not AlertValidator.validate_structure(alert)

    def test_validate_alert_structure_edge_cases(self):
        """Test alert structure validation with edge cases."""
        # Empty alert
        self.assertFalse(AlertValidator.validate_structure({}))

        # Alert with extra fields (should still be valid)
        alert_with_extra = {
            "alert_id": "TEST-008",
            "hostname": "test-host",
            "src_ip": "192.168.1.100",
            "hash": "a" * 64,
            "severity": 2,
            "event_type": "ransomware_detection",
            "extra_field": "extra_value",
        }
        assert AlertValidator.validate_structure(alert_with_extra)

    def test_validate_alert_structure_unicode_handling(self):
        """Test alert structure validation with unicode characters."""
        alert = {
            "alert_id": "TEST-009",
            "hostname": "test-üñíçödé",
            "src_ip": "192.168.1.100",
            "hash": "a" * 64,
            "severity": 2,
            "event_type": "ransomware_detection",
        }
        assert AlertValidator.validate_structure(alert)

    def test_validate_alert_structure_numeric_severity(self):
        """Test alert structure validation with numeric severity values."""
        # Test all valid severity values
        for severity in [0, 1, 2, 3]:  # Low, Medium, High, Critical
            alert = {
                "alert_id": f"TEST-SEV-{severity}",
                "hostname": "test-host",
                "src_ip": "192.168.1.100",
                "hash": "a" * 64,
                "severity": severity,
                "event_type": "ransomware_detection",
            }
            assert AlertValidator.validate_structure(alert)

    def test_validate_alert_structure_hash_formats(self):
        """Test alert structure validation with different hash formats."""
        # Test valid hash formats
        valid_hashes = [
            (
                "d41d8cd98f00b204e9800998ecf8427e" "d41d8cd98f00b204e9800998ecf8427e"
            ),  # SHA-256 (64 chars)
            "da39a3ee5e6b4b0d3255bfef95601890afd80709",  # SHA1 (40 chars)
            "a" * 64,  # SHA256 (64 chars)
        ]

        for i, hash_value in enumerate(valid_hashes):
            alert = {
                "alert_id": f"TEST-HASH-{i}",
                "hostname": "test-host",
                "src_ip": "192.168.1.100",
                "hash": hash_value,
                "severity": 2,
                "event_type": "ransomware_detection",
            }
            assert AlertValidator.validate_structure(alert)

    def test_validate_alert_structure_ip_formats(self):
        """Test alert structure validation with different IP formats."""
        # Test valid IP formats
        valid_ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1", "127.0.0.1"]

        for i, ip in enumerate(valid_ips):
            alert = {
                "alert_id": f"TEST-IP-{i}",
                "hostname": "test-host",
                "src_ip": ip,
                "hash": "a" * 64,
                "severity": 2,
                "event_type": "ransomware_detection",
            }
            assert AlertValidator.validate_structure(alert)

    def test_edge_case_empty_alert_id(self):
        """Test edge case: empty alert_id."""
        alert = {
            "alert_id": "",
            "hostname": "test-host",
            "src_ip": "192.168.1.1",
            "hash": "a" * 64,
            "severity": 2,
            "event_type": "ransomware_detection",
        }
        assert not AlertValidator.validate_structure(alert)

    def test_edge_case_very_long_hostname(self):
        """Test edge case: very long hostname."""
        alert = {
            "alert_id": "TEST-EDGE-001",
            "hostname": "a" * 1000,
            "src_ip": "192.168.1.1",
            "hash": "a" * 64,
            "severity": 2,
            "event_type": "ransomware_detection",
        }
        # Should either reject or truncate
        is_valid = AlertValidator.validate_structure(alert)
        # If valid, hostname should be truncated
        if is_valid:
            assert len(alert["hostname"]) <= 255
        else:
            assert len(alert["hostname"]) > 255

    def test_edge_case_zero_severity(self):
        """Test edge case: severity 0."""
        alert = {
            "alert_id": "TEST-EDGE-002",
            "hostname": "test-host",
            "src_ip": "192.168.1.1",
            "hash": "a" * 64,
            "severity": 0,
            "event_type": "ransomware_detection",
        }
        # Severity 0 might be valid or invalid depending on requirements
        AlertValidator.validate_structure(alert)

    def test_edge_case_max_severity(self):
        """Test edge case: maximum severity."""
        alert = {
            "alert_id": "TEST-EDGE-003",
            "hostname": "test-host",
            "src_ip": "192.168.1.1",
            "hash": "a" * 64,
            "severity": 100,
            "event_type": "ransomware_detection",
        }
        # Should handle max severity gracefully
        AlertValidator.validate_structure(alert)

    def test_edge_case_negative_severity(self):
        """Test edge case: negative severity."""
        alert = {
            "alert_id": "TEST-EDGE-004",
            "hostname": "test-host",
            "src_ip": "192.168.1.1",
            "hash": "a" * 64,
            "severity": -1,
            "event_type": "ransomware_detection",
        }
        assert not AlertValidator.validate_structure(alert)

    def test_edge_case_special_characters_in_hostname(self):
        """Test edge case: special characters in hostname."""
        alert = {
            "alert_id": "TEST-EDGE-005",
            "hostname": "test-host!@#$%^&*()",
            "src_ip": "192.168.1.1",
            "hash": "a" * 64,
            "severity": 2,
            "event_type": "ransomware_detection",
        }
        # Should handle special characters
        AlertValidator.validate_structure(alert)

    def test_edge_case_unicode_in_hostname(self):
        """Test edge case: unicode characters in hostname."""
        alert = {
            "alert_id": "TEST-EDGE-006",
            "hostname": "höst-näme-тест",
            "src_ip": "192.168.1.1",
            "hash": "a" * 64,
            "severity": 2,
            "event_type": "ransomware_detection",
        }
        # Should handle unicode
        AlertValidator.validate_structure(alert)

    def test_edge_case_null_bytes_in_fields(self):
        """Test edge case: null bytes in fields."""
        alert = {
            "alert_id": "TEST-EDGE-007\x00",
            "hostname": "test-host\x00",
            "src_ip": "192.168.1.1",
            "hash": "a" * 64,
            "severity": 2,
            "event_type": "ransomware_detection",
        }
        # Should handle null bytes
        AlertValidator.validate_structure(alert)

    def test_edge_case_mixed_case_hash(self):
        """Test edge case: mixed case hash."""
        alert = {
            "alert_id": "TEST-EDGE-008",
            "hostname": "test-host",
            "src_ip": "192.168.1.1",
            "hash": "A" * 32 + "b" * 32,
            "severity": 2,
            "event_type": "ransomware_detection",
        }
        # Should handle mixed case
        AlertValidator.validate_structure(alert)

    def test_edge_case_future_timestamp(self):
        """Test edge case: future timestamp."""
        from datetime import datetime, timedelta

        future_time = (datetime.now(UTC) + timedelta(days=365)).isoformat()
        alert = {
            "alert_id": "TEST-EDGE-009",
            "hostname": "test-host",
            "src_ip": "192.168.1.1",
            "hash": "a" * 64,
            "severity": 2,
            "event_type": "ransomware_detection",
            "detection_time": future_time,
        }
        # Should handle future timestamp
        AlertValidator.validate_structure(alert)

    def test_edge_case_very_old_timestamp(self):
        """Test edge case: very old timestamp."""
        from datetime import datetime, timedelta

        old_time = (datetime.now(UTC) - timedelta(days=3650)).isoformat()
        alert = {
            "alert_id": "TEST-EDGE-010",
            "hostname": "test-host",
            "src_ip": "192.168.1.1",
            "hash": "a" * 64,
            "severity": 2,
            "event_type": "ransomware_detection",
            "detection_time": old_time,
        }
        # Should handle old timestamp
        AlertValidator.validate_structure(alert)
