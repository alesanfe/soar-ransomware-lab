#!/usr/bin/env python3
"""
Unit tests for SOAR Lab configuration schemas
"""

import json
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from soar_lab.config.schemas import (
    RansomwareAlert,
    WebhookPayload,
    NetworkEvent,
    FileHash,
    MITREInfo,
    AffectedFile,
    SeverityLevel,
    AlertType,
    ContainmentAction
)


class TestRansomwareAlertModel(unittest.TestCase):
    """Test RansomwareAlert model"""

    def test_ransomware_alert_model_valid(self):
        """Test RansomwareAlert model with valid data"""
        alert_data = {
            "alert_id": "ALERT-1701388800-0001",
            "hostname": "test-host",
            "src_ip": "192.168.1.100",
            "hash": {
                "sha256": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
            },
            "severity": SeverityLevel.HIGH,
            "source": "siem",
            "detection_time": datetime.now(),
            "event_type": "ransomware_detection",
            "description": "Test ransomware detection alert"
        }
        
        alert = RansomwareAlert(**alert_data)
        self.assertEqual(alert.alert_id, "ALERT-1701388800-0001")
        self.assertEqual(alert.hostname, "test-host")
        self.assertEqual(alert.severity, SeverityLevel.HIGH)
        self.assertIsInstance(alert.detection_time, datetime)

    def test_ransomware_alert_model_with_optional_fields(self):
        """Test RansomwareAlert model with optional fields"""
        alert_data = {
            "alert_id": "ALERT-1701388800-0001",
            "hostname": "test-host",
            "src_ip": "192.168.1.100",
            "hash": {
                "sha256": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
            },
            "severity": SeverityLevel.HIGH,
            "source": "external",
            "detection_time": datetime.now(),
            "event_type": "ransomware_detection",
            "description": "Test ransomware detection alert",
            "mitre_tactics": ["TA0001"],
            "mitre_techniques": ["T1059"],
            "user_context": {"username": "testuser"},
            "process_info": {"pid": 1234}
        }
        
        alert = RansomwareAlert(**alert_data)
        self.assertEqual(alert.alert_id, "ALERT-1701388800-0001")
        self.assertEqual(len(alert.mitre_tactics), 1)
        self.assertEqual(alert.mitre_tactics[0], "TA0001")
        self.assertIsNotNone(alert.user_context)

    def test_ransomware_alert_invalid_alert_id(self):
        """Test RansomwareAlert with invalid alert ID"""
        alert_data = {
            "alert_id": "INVALID-ID",
            "hostname": "test-host",
            "src_ip": "192.168.1.100",
            "hash": {
                "sha256": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
            },
            "severity": SeverityLevel.HIGH,
            "source": "siem",
            "detection_time": datetime.now(),
            "event_type": "ransomware_detection",
            "description": "Test alert"
        }
        
        with self.assertRaises(Exception):
            RansomwareAlert(**alert_data)

    def test_ransomware_alert_invalid_hostname(self):
        """Test RansomwareAlert with invalid hostname"""
        alert_data = {
            "alert_id": "ALERT-1701388800-0001",
            "hostname": "invalid hostname with spaces",
            "src_ip": "192.168.1.100",
            "hash": {
                "sha256": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
            },
            "severity": SeverityLevel.HIGH,
            "source": "siem",
            "detection_time": datetime.now(),
            "event_type": "ransomware_detection",
            "description": "Test alert"
        }
        
        with self.assertRaises(Exception):
            RansomwareAlert(**alert_data)


class TestFileHashModel(unittest.TestCase):
    """Test FileHash model"""

    def test_file_hash_valid(self):
        """Test FileHash with valid data"""
        hash_data = {
            "sha256": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
            "md5": "5d41402abc4b2a76b9719d911017c592",
            "sha1": "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"
        }
        
        file_hash = FileHash(**hash_data)
        self.assertEqual(file_hash.sha256, hash_data["sha256"])
        self.assertEqual(file_hash.md5, hash_data["md5"])
        self.assertEqual(file_hash.sha1, hash_data["sha1"])

    def test_file_hash_invalid_sha256(self):
        """Test FileHash with invalid SHA256"""
        hash_data = {
            "sha256": "invalid_hash",
            "md5": "5d41402abc4b2a76b9719d911017c592"
        }
        
        with self.assertRaises(Exception):
            FileHash(**hash_data)

    def test_file_hash_invalid_md5(self):
        """Test FileHash with invalid MD5"""
        hash_data = {
            "sha256": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
            "md5": "invalid_md5"
        }
        
        with self.assertRaises(Exception):
            FileHash(**hash_data)


class TestNetworkEventModel(unittest.TestCase):
    """Test NetworkEvent model"""

    def test_network_event_valid(self):
        """Test NetworkEvent with valid data"""
        event_data = {
            "src_ip": "192.168.1.100",
            "dst_ip": "10.0.0.1",
            "src_port": 12345,
            "dst_port": 80,
            "protocol": "TCP"
        }
        
        event = NetworkEvent(**event_data)
        self.assertEqual(str(event.src_ip), "192.168.1.100")
        self.assertEqual(str(event.dst_ip), "10.0.0.1")
        self.assertEqual(event.src_port, 12345)
        self.assertEqual(event.dst_port, 80)
        self.assertEqual(event.protocol, "TCP")

    def test_network_event_invalid_protocol(self):
        """Test NetworkEvent with invalid protocol"""
        event_data = {
            "src_ip": "192.168.1.100",
            "dst_ip": "10.0.0.1",
            "protocol": "INVALID"
        }
        
        with self.assertRaises(Exception):
            NetworkEvent(**event_data)

    def test_network_event_invalid_port(self):
        """Test NetworkEvent with invalid port"""
        event_data = {
            "src_ip": "192.168.1.100",
            "dst_ip": "10.0.0.1",
            "src_port": 99999  # Invalid port number
        }
        
        with self.assertRaises(Exception):
            NetworkEvent(**event_data)


class TestAffectedFileModel(unittest.TestCase):
    """Test AffectedFile model"""

    def test_affected_file_valid(self):
        """Test AffectedFile with valid data"""
        file_data = {
            "path": "/path/to/file.txt",
            "name": "file.txt",
            "size": 1024,
            "extension": "txt",
            "encrypted": True
        }
        
        affected_file = AffectedFile(**file_data)
        self.assertEqual(affected_file.path, "/path/to/file.txt")
        self.assertEqual(affected_file.name, "file.txt")
        self.assertEqual(affected_file.size, 1024)
        self.assertEqual(affected_file.extension, "txt")
        self.assertTrue(affected_file.encrypted)

    def test_affected_file_empty_path(self):
        """Test AffectedFile with empty path"""
        file_data = {
            "path": "",
            "name": "file.txt"
        }
        
        with self.assertRaises(Exception):
            AffectedFile(**file_data)

    def test_affected_file_negative_size(self):
        """Test AffectedFile with negative size"""
        file_data = {
            "path": "/path/to/file.txt",
            "name": "file.txt",
            "size": -100
        }
        
        with self.assertRaises(Exception):
            AffectedFile(**file_data)


class TestWebhookPayloadModel(unittest.TestCase):
    """Test WebhookPayload model"""

    def test_webhook_payload_valid(self):
        """Test WebhookPayload with valid data"""
        payload_data = {
            "alert": {
                "alert_id": "ALERT-1701388800-0001",
                "hostname": "test-host",
                "src_ip": "192.168.1.100",
                "hash": {
                    "sha256": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
                },
                "severity": SeverityLevel.HIGH,
                "source": "siem",
                "detection_time": datetime.now(),
                "event_type": "ransomware_detection",
                "description": "Test alert"
            },
            "metadata": {"key": "value"},
            "version": "1.0"
        }
        
        payload = WebhookPayload(**payload_data)
        self.assertEqual(payload.alert.alert_id, "ALERT-1701388800-0001")
        self.assertEqual(payload.metadata["key"], "value")
        self.assertEqual(payload.version, "1.0")
        self.assertIsInstance(payload.timestamp, datetime)

    def test_webhook_payload_invalid_version(self):
        """Test WebhookPayload with invalid version"""
        payload_data = {
            "alert": {
                "alert_id": "ALERT-1701388800-0001",
                "hostname": "test-host",
                "src_ip": "192.168.1.100",
                "hash": {
                    "sha256": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
                },
                "severity": SeverityLevel.HIGH,
                "source": "siem",
                "detection_time": datetime.now(),
                "event_type": "ransomware_detection",
                "description": "Test alert"
            },
            "version": "invalid_version"
        }
        
        with self.assertRaises(Exception):
            WebhookPayload(**payload_data)


if __name__ == '__main__':
    unittest.main()
