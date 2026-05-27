#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Atomic Tests for Alert Validation
Tests individual validation functions in isolation
"""

import json
import unittest

from soar_lab.validation.validators import AlertValidator


class TestAlertValidationAtomic(unittest.TestCase):
    """Atomic tests for individual alert validation functions"""

    def setUp(self):
        """Set up test fixtures"""
        # Use AlertValidator directly instead of SIEMSimulator
        pass

    def test_validate_alert_structure_complete(self):
        """Test alert structure validation with complete data"""
        alert = {
            'alert_id': 'TEST-001',
            'hostname': 'test-host',
            'src_ip': '192.168.1.100',
            'hash': 'a' * 64,
            'severity': 2,
            'event_type': 'ransomware_detection'
        }
        self.assertTrue(AlertValidator.validate_structure(alert))

    def test_validate_alert_structure_missing_required_fields(self):
        """Test alert structure validation with missing required fields"""
        invalid_alerts = [
            {'alert_id': 'TEST-002'},  # Missing all other fields
            {'hostname': 'test-host', 'severity': 1},  # Missing alert_id, src_ip, hash, event_type
            {'alert_id': 'TEST-003', 'src_ip': '192.168.1.1'},  # Missing hostname, hash, severity, event_type
            {'alert_id': 'TEST-004', 'severity': 2},  # Missing hostname, src_ip, hash, event_type
        ]

        for alert in invalid_alerts:
            self.assertFalse(AlertValidator.validate_structure(alert))

    def test_validate_alert_structure_invalid_severity(self):
        """Test alert structure validation with invalid severity"""
        alert = {
            'alert_id': 'TEST-005',
            'hostname': 'test-host',
            'src_ip': '192.168.1.100',
            'hash': 'a' * 64,
            'severity': 99,  # Invalid severity
            'event_type': 'ransomware_detection'
        }
        self.assertFalse(AlertValidator.validate_structure(alert))

    def test_validate_alert_structure_invalid_hash(self):
        """Test alert structure validation with invalid hash"""
        alert = {
            'alert_id': 'TEST-006',
            'hostname': 'test-host',
            'src_ip': '192.168.1.100',
            'hash': 'invalid_hash',  # Invalid hash format
            'severity': 2,
            'event_type': 'ransomware_detection'
        }
        self.assertFalse(AlertValidator.validate_structure(alert))

    def test_validate_alert_structure_invalid_ip(self):
        """Test alert structure validation with invalid IP"""
        alert = {
            'alert_id': 'TEST-007',
            'hostname': 'test-host',
            'src_ip': '999.999.999.999',  # Invalid IP
            'hash': 'a' * 64,
            'severity': 2,
            'event_type': 'ransomware_detection'
        }
        self.assertFalse(AlertValidator.validate_structure(alert))

    def test_validate_alert_structure_edge_cases(self):
        """Test alert structure validation with edge cases"""
        # Empty alert
        self.assertFalse(AlertValidator.validate_structure({}))

        # Alert with extra fields (should still be valid)
        alert_with_extra = {
            'alert_id': 'TEST-008',
            'hostname': 'test-host',
            'src_ip': '192.168.1.100',
            'hash': 'a' * 64,
            'severity': 2,
            'event_type': 'ransomware_detection',
            'extra_field': 'extra_value'
        }
        self.assertTrue(AlertValidator.validate_structure(alert_with_extra))

    def test_validate_alert_structure_unicode_handling(self):
        """Test alert structure validation with unicode characters"""
        alert = {
            'alert_id': 'TEST-009',
            'hostname': 'test-üñíçödé',
            'src_ip': '192.168.1.100',
            'hash': 'a' * 64,
            'severity': 2,
            'event_type': 'ransomware_detection'
        }
        self.assertTrue(AlertValidator.validate_structure(alert))

    def test_validate_alert_structure_numeric_severity(self):
        """Test alert structure validation with numeric severity values"""
        # Test all valid severity values
        for severity in [0, 1, 2, 3]:  # Low, Medium, High, Critical
            alert = {
                'alert_id': f'TEST-SEV-{severity}',
                'hostname': 'test-host',
                'src_ip': '192.168.1.100',
                'hash': 'a' * 64,
                'severity': severity,
                'event_type': 'ransomware_detection'
            }
            self.assertTrue(AlertValidator.validate_structure(alert))

    def test_validate_alert_structure_hash_formats(self):
        """Test alert structure validation with different hash formats"""
        # Test valid hash formats
        valid_hashes = [
            'd41d8cd98f00b204e9800998ecf8427ed41d8cd98f00b204e9800998ecf8427e',  # SHA-256 (64 chars)
            'da39a3ee5e6b4b0d3255bfef95601890afd80709',  # SHA1 (40 chars)
            'a' * 64  # SHA256 (64 chars)
        ]

        for i, hash_value in enumerate(valid_hashes):
            alert = {
                'alert_id': f'TEST-HASH-{i}',
                'hostname': 'test-host',
                'src_ip': '192.168.1.100',
                'hash': hash_value,
                'severity': 2,
                'event_type': 'ransomware_detection'
            }
            self.assertTrue(AlertValidator.validate_structure(alert))

    def test_validate_alert_structure_ip_formats(self):
        """Test alert structure validation with different IP formats"""
        # Test valid IP formats
        valid_ips = [
            '192.168.1.1',
            '10.0.0.1',
            '172.16.0.1',
            '127.0.0.1'
        ]

        for i, ip in enumerate(valid_ips):
            alert = {
                'alert_id': f'TEST-IP-{i}',
                'hostname': 'test-host',
                'src_ip': ip,
                'hash': 'a' * 64,
                'severity': 2,
                'event_type': 'ransomware_detection'
            }
            self.assertTrue(AlertValidator.validate_structure(alert))


if __name__ == '__main__':
    unittest.main()
