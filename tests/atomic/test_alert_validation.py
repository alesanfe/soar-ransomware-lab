#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Atomic Tests for Alert Validation
Tests individual validation functions in isolation
"""

import unittest
import json
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from send_alert import SIEMSimulator


class TestAlertValidationAtomic(unittest.TestCase):
    """Atomic tests for individual alert validation functions"""

    def setUp(self):
        """Set up test fixtures"""
        self.simulator = SIEMSimulator(
            webhook_url="http://localhost:5001/webhook",
            api_token="test_token"
        )

    def test_validate_hash_valid_sha256(self):
        """Test SHA256 hash validation with valid hash"""
        valid_hash = "d41d8cd98f00b204e9800998ecf8427e"
        result = self.simulator.validate_hash(valid_hash)
        self.assertTrue(result)

    def test_validate_hash_invalid_length(self):
        """Test SHA256 hash validation with invalid length"""
        invalid_hash = "d41d8cd98f00b204e9800998ecf8427"  # Too short
        result = self.simulator.validate_hash(invalid_hash)
        self.assertFalse(result)

    def test_validate_hash_invalid_characters(self):
        """Test SHA256 hash validation with invalid characters"""
        invalid_hash = "z41d8cd98f00b204e9800998ecf8427e"  # Contains 'z'
        result = self.simulator.validate_hash(invalid_hash)
        self.assertFalse(result)

    def test_validate_hash_empty_string(self):
        """Test SHA256 hash validation with empty string"""
        result = self.simulator.validate_hash("")
        self.assertFalse(result)

    def test_validate_hash_none(self):
        """Test SHA256 hash validation with None"""
        result = self.simulator.validate_hash(None)
        self.assertFalse(result)

    def test_validate_ip_address_valid_ipv4(self):
        """Test IP validation with valid IPv4 address"""
        valid_ip = "192.168.1.100"
        result = self.simulator.validate_ip_address(valid_ip)
        self.assertTrue(result)

    def test_validate_ip_address_valid_localhost(self):
        """Test IP validation with localhost"""
        valid_ip = "127.0.0.1"
        result = self.simulator.validate_ip_address(valid_ip)
        self.assertTrue(result)

    def test_validate_ip_address_invalid_octet_range(self):
        """Test IP validation with octet out of range"""
        invalid_ip = "192.168.1.300"  # 300 is invalid
        result = self.simulator.validate_ip_address(invalid_ip)
        self.assertFalse(result)

    def test_validate_ip_address_invalid_format(self):
        """Test IP validation with invalid format"""
        invalid_ip = "192.168.1"  # Missing octet
        result = self.simulator.validate_ip_address(invalid_ip)
        self.assertFalse(result)

    def test_validate_ip_address_non_numeric(self):
        """Test IP validation with non-numeric characters"""
        invalid_ip = "192.168.1.abc"
        result = self.simulator.validate_ip_address(invalid_ip)
        self.assertFalse(result)

    def test_validate_ip_address_empty(self):
        """Test IP validation with empty string"""
        result = self.simulator.validate_ip_address("")
        self.assertFalse(result)

    def test_validate_alert_structure_complete(self):
        """Test alert structure validation with complete alert"""
        complete_alert = {
            "alert_id": "ALERT-2025-001",
            "hostname": "web-server-01",
            "src_ip": "192.168.1.100",
            "hash": "d41d8cd98f00b204e9800998ecf8427e" * 2,
            "severity": 2,
            "event_type": "ransomware_detection"
        }
        
        result = self.simulator.validate_alert_structure(complete_alert)
        self.assertTrue(result)

    def test_validate_alert_structure_missing_required(self):
        """Test alert structure validation with missing required fields"""
        incomplete_alert = {
            "id": "ALERT-2025-001",
            "timestamp": "2025-01-01T12:00:00Z"
            # Missing other required fields
        }
        
        result = self.simulator.validate_alert_structure(incomplete_alert)
        self.assertFalse(result)

    def test_validate_alert_structure_empty_dict(self):
        """Test alert structure validation with empty dictionary"""
        result = self.simulator.validate_alert_structure({})
        self.assertFalse(result)

    def test_validate_alert_structure_none(self):
        """Test alert structure validation with None"""
        result = self.simulator.validate_alert_structure(None)
        self.assertFalse(result)

    def test_validate_alert_structure_invalid_severity(self):
        """Test alert structure validation with invalid severity"""
        alert = {
            "id": "ALERT-2025-001",
            "timestamp": "2025-01-01T12:00:00Z",
            "severity": "critical",  # Invalid severity
            "source_ip": "192.168.1.100",
            "target_host": "web-server-01",
            "file_hash": "d41d8cd98f00b204e9800998ecf8427e",
            "description": "Test alert"
        }
        
        result = self.simulator.validate_alert_structure(alert)
        self.assertFalse(result)

    def test_validate_alert_structure_valid_severities(self):
        """Test alert structure validation with all valid severities"""
        base_alert = {
            "alert_id": "ALERT-2025-001",
            "hostname": "web-server-01",
            "src_ip": "192.168.1.100",
            "hash": "d41d8cd98f00b204e9800998ecf8427e" * 2,
            "event_type": "ransomware_detection"
        }
        
        valid_severities = [0, 1, 2, 3]  # Low, Medium, High, Critical
        for severity in valid_severities:
            alert = base_alert.copy()
            alert["severity"] = severity
            result = self.simulator.validate_alert_structure(alert)
            self.assertTrue(result, f"Failed for severity: {severity}")

    def test_mitre_attack_tactics_presence(self):
        """Test that MITRE ATT&CK tactics are available"""
        tactics = self.simulator.mitre_attack_tactics
        
        # Should be a dictionary
        self.assertIsInstance(tactics, dict)
        
        # Should have common tactics
        expected_tactics = ["TA0001", "TA0002", "TA0003", "TA0004"]
        for tactic in expected_tactics:
            self.assertIn(tactic, tactics)

    def test_mitre_attack_tactics_format(self):
        """Test MITRE ATT&CK tactics format"""
        tactics = self.simulator.mitre_attack_tactics
        
        # All tactics values should be strings
        for tactic_id, tactic_name in tactics.items():
            self.assertIsInstance(tactic_id, str)
            self.assertIsInstance(tactic_name, str)
            self.assertGreater(len(tactic_name), 0)

    def test_malicious_hashes_presence(self):
        """Test that malicious hashes are available"""
        hashes = self.simulator.malicious_hashes
        
        # Should be a list
        self.assertIsInstance(hashes, list)
        
        # Should have hashes
        self.assertGreater(len(hashes), 0)
        
        # All should be valid SHA256
        for hash_val in hashes:
            self.assertEqual(len(hash_val), 64)
            self.assertTrue(all(c in '0123456789abcdef' for c in hash_val))

    def test_benign_hashes_presence(self):
        """Test that benign hashes are available"""
        hashes = self.simulator.benign_hashes
        
        # Should be a list
        self.assertIsInstance(hashes, list)
        
        # Should have hashes
        self.assertGreater(len(hashes), 0)
        
        # All should be valid SHA256
        for hash_val in hashes:
            self.assertEqual(len(hash_val), 64)
            self.assertTrue(all(c in '0123456789abcdef' for c in hash_val))

    def test_headers_initialization(self):
        """Test that headers are properly initialized"""
        expected_headers = {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json'
        }
        
        self.assertEqual(self.simulator.headers, expected_headers)

    def test_webhook_url_storage(self):
        """Test that webhook URL is properly stored"""
        self.assertEqual(self.simulator.webhook_url, "http://localhost:5001/webhook")

    def test_api_token_storage(self):
        """Test that API token is properly stored"""
        self.assertEqual(self.simulator.api_token, "test_token")


if __name__ == '__main__':
    unittest.main()
