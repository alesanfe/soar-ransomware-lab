#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Atomic Tests for Schema Validation
Tests individual schema validation functions in isolation
"""

import unittest
import json
import sys
from pathlib import Path

# Add config directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'config'))

from schemas import (
    RansomwareAlert,
    NetworkEvent,
    FileHash,
    SeverityLevel,
    AlertType,
    MITREInfo,
    AffectedFile
)


class TestSchemaValidationAtomic(unittest.TestCase):
    """Atomic tests for individual schema validation functions"""

    def test_severity_level_enum_values(self):
        """Test SeverityLevel enum has correct values"""
        self.assertEqual(SeverityLevel.LOW.value, "0")
        self.assertEqual(SeverityLevel.MEDIUM.value, "1")
        self.assertEqual(SeverityLevel.HIGH.value, "2")
        self.assertEqual(SeverityLevel.CRITICAL.value, "3")

    def test_severity_level_enum_comparison(self):
        """Test SeverityLevel enum comparisons"""
        self.assertEqual(SeverityLevel.LOW, SeverityLevel("0"))
        self.assertNotEqual(SeverityLevel.LOW, SeverityLevel.HIGH)
        self.assertIn(SeverityLevel.MEDIUM, [SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH])

    def test_alert_type_enum_values(self):
        """Test AlertType enum has correct values"""
        self.assertEqual(AlertType.MALICIOUS.value, "malicious")
        self.assertEqual(AlertType.BENIGN.value, "benign")
        self.assertEqual(AlertType.SUSPICIOUS.value, "suspicious")

    def test_alert_type_enum_comparison(self):
        """Test AlertType enum comparisons"""
        self.assertEqual(AlertType.MALICIOUS, AlertType("malicious"))
        self.assertNotEqual(AlertType.MALICIOUS, AlertType.BENIGN)

    def test_file_hash_valid_sha256(self):
        """Test FileHash with valid SHA256"""
        file_hash = FileHash(sha256="d41d8cd98f00b204e9800998ecf8427e" * 2)
        self.assertEqual(file_hash.sha256, "d41d8cd98f00b204e9800998ecf8427e" * 2)

    def test_file_hash_invalid_sha256_length(self):
        """Test FileHash with invalid SHA256 length"""
        with self.assertRaises(Exception):  # Pydantic validation error
            FileHash(sha256="d41d8cd98f00b204e9800998ecf8427")  # Too short

    def test_file_hash_invalid_sha256_chars(self):
        """Test FileHash with invalid SHA256 characters"""
        with self.assertRaises(Exception):  # Pydantic validation error
            FileHash(sha256="g41d8cd98f00b204e9800998ecf8427e" * 2)  # Contains 'g'

    def test_file_hash_with_optional_md5(self):
        """Test FileHash with optional MD5"""
        file_hash = FileHash(
            sha256="d41d8cd98f00b204e9800998ecf8427e" * 2,
            md5="d41d8cd98f00b204e9800998ecf8427e"
        )
        self.assertEqual(file_hash.md5, "d41d8cd98f00b204e9800998ecf8427e")

    def test_file_hash_invalid_md5_length(self):
        """Test FileHash with invalid MD5 length"""
        with self.assertRaises(Exception):
            FileHash(
                sha256="d41d8cd98f00b204e9800998ecf8427e" * 2,
                md5="d41d8cd98f00b204e9800998ecf8427"  # Too short
            )

    def test_network_event_valid_minimal(self):
        """Test NetworkEvent with minimal valid data"""
        event = NetworkEvent(src_ip="192.168.1.100")
        self.assertEqual(str(event.src_ip), "192.168.1.100")
        self.assertIsNone(event.dst_ip)
        self.assertIsNone(event.src_port)
        self.assertIsNone(event.dst_port)
        self.assertIsNone(event.protocol)

    def test_network_event_valid_complete(self):
        """Test NetworkEvent with complete valid data"""
        event = NetworkEvent(
            src_ip="192.168.1.100",
            dst_ip="10.0.0.50",
            src_port=12345,
            dst_port=443,
            protocol="TCP"
        )
        self.assertEqual(str(event.src_ip), "192.168.1.100")
        self.assertEqual(str(event.dst_ip), "10.0.0.50")
        self.assertEqual(event.src_port, 12345)
        self.assertEqual(event.dst_port, 443)
        self.assertEqual(event.protocol, "TCP")

    def test_network_event_invalid_src_ip(self):
        """Test NetworkEvent with invalid source IP"""
        with self.assertRaises(Exception):
            NetworkEvent(src_ip="192.168.1.300")  # Invalid octet

    def test_network_event_invalid_dst_ip(self):
        """Test NetworkEvent with invalid destination IP"""
        with self.assertRaises(Exception):
            NetworkEvent(
                src_ip="192.168.1.100",
                dst_ip="10.0.0.300"  # Invalid octet
            )

    def test_network_event_invalid_port_range(self):
        """Test NetworkEvent with invalid port range"""
        with self.assertRaises(Exception):
            NetworkEvent(
                src_ip="192.168.1.100",
                src_port=70000  # Invalid port (> 65535)
            )

    def test_network_event_invalid_port_zero(self):
        """Test NetworkEvent with invalid port zero"""
        with self.assertRaises(Exception):
            NetworkEvent(
                src_ip="192.168.1.100",
                src_port=0  # Invalid port (< 1)
            )

    def test_network_event_invalid_protocol(self):
        """Test NetworkEvent with invalid protocol"""
        with self.assertRaises(Exception):
            NetworkEvent(
                src_ip="192.168.1.100",
                protocol="HTTP"  # Not in TCP|UDP|ICMP
            )

    def test_network_event_valid_protocols(self):
        """Test NetworkEvent with all valid protocols"""
        valid_protocols = ["TCP", "UDP", "ICMP"]
        for protocol in valid_protocols:
            event = NetworkEvent(src_ip="192.168.1.100", protocol=protocol)
            self.assertEqual(event.protocol, protocol)

    def test_file_hash_with_sha1(self):
        """Test FileHash with SHA1"""
        file_hash = FileHash(
            sha256="d41d8cd98f00b204e9800998ecf8427e" * 2,
            sha1="da39a3ee5e6b4b0d3255bfef95601890afd80709"
        )
        self.assertEqual(file_hash.sha1, "da39a3ee5e6b4b0d3255bfef95601890afd80709")

    def test_file_hash_invalid_sha1_length(self):
        """Test FileHash with invalid SHA1 length"""
        with self.assertRaises(Exception):
            FileHash(
                sha256="d41d8cd98f00b204e9800998ecf8427e" * 2,
                sha1="d41d8cd98f00b204e9800998ecf8427e"  # Too short
            )

    def test_file_hash_all_hashes(self):
        """Test FileHash with all hash types"""
        file_hash = FileHash(
            sha256="d41d8cd98f00b204e9800998ecf8427e" * 2,
            md5="d41d8cd98f00b204e9800998ecf8427e",
            sha1="da39a3ee5e6b4b0d3255bfef95601890afd80709"
        )
        self.assertIsNotNone(file_hash.sha256)
        self.assertIsNotNone(file_hash.md5)
        self.assertIsNotNone(file_hash.sha1)

    def test_network_event_port_boundary_values(self):
        """Test NetworkEvent with port boundary values"""
        # Test minimum valid port
        event1 = NetworkEvent(src_ip="192.168.1.100", src_port=1)
        self.assertEqual(event1.src_port, 1)
        
        # Test maximum valid port
        event2 = NetworkEvent(src_ip="192.168.1.100", dst_port=65535)
        self.assertEqual(event2.dst_port, 65535)

    def test_file_hash_case_insensitive(self):
        """Test FileHash accepts both uppercase and lowercase hex"""
        # Should accept uppercase
        file_hash1 = FileHash(sha256="D41D8CD98F00B204E9800998ECF8427E" * 2)
        self.assertIsNotNone(file_hash1.sha256)
        
        # Should accept lowercase
        file_hash2 = FileHash(sha256="d41d8cd98f00b204e9800998ecf8427e" * 2)
        self.assertIsNotNone(file_hash2.sha256)
        
        # Should accept mixed case
        file_hash3 = FileHash(sha256="D41d8CD9" * 8)
        self.assertIsNotNone(file_hash3.sha256)

    def test_mitre_info_valid_tactics(self):
        """Test MITREInfo with valid tactics"""
        mitre = MITREInfo(tactics=["TA0001", "TA0002"])
        self.assertEqual(len(mitre.tactics), 2)
        self.assertIn("TA0001", mitre.tactics)
        self.assertIn("TA0002", mitre.tactics)

    def test_mitre_info_invalid_tactics(self):
        """Test MITREInfo with invalid tactics"""
        with self.assertRaises(Exception):
            MITREInfo(tactics=["INVALID_TACTIC"])

    def test_mitre_info_with_techniques(self):
        """Test MITREInfo with techniques"""
        mitre = MITREInfo(
            tactics=["TA0001"],
            techniques=["T1059", "T1055"],
            sub_techniques=["T1059.001", "T1055.001"]
        )
        self.assertEqual(len(mitre.techniques), 2)
        self.assertEqual(len(mitre.sub_techniques), 2)

    def test_affected_file_valid_minimal(self):
        """Test AffectedFile with minimal valid data"""
        file = AffectedFile(path="/tmp/test.txt", name="test.txt")
        self.assertEqual(file.path, "/tmp/test.txt")
        self.assertEqual(file.name, "test.txt")
        self.assertIsNone(file.size)
        self.assertIsNone(file.extension)
        self.assertIsNone(file.encrypted)

    def test_affected_file_valid_complete(self):
        """Test AffectedFile with complete valid data"""
        file = AffectedFile(
            path="/tmp/test.txt",
            name="test.txt",
            size=1024,
            extension="txt",
            encrypted=True
        )
        self.assertEqual(file.size, 1024)
        self.assertEqual(file.extension, "txt")
        self.assertTrue(file.encrypted)

    def test_affected_file_invalid_size(self):
        """Test AffectedFile with invalid size"""
        with self.assertRaises(Exception):
            AffectedFile(
                path="/tmp/test.txt",
                name="test.txt",
                size=-1  # Negative size not allowed
            )

    def test_affected_file_empty_path(self):
        """Test AffectedFile with empty path"""
        with self.assertRaises(Exception):
            AffectedFile(path="", name="test.txt")

    def test_ransomware_alert_valid_minimal(self):
        """Test RansomwareAlert with minimal valid data"""
        file_hash = FileHash(sha256="d41d8cd98f00b204e9800998ecf8427e" * 2)
        alert = RansomwareAlert(
            alert_id="ALERT-1234567890-1234",
            hostname="server-01",
            src_ip="192.168.1.100",
            hash=file_hash,
            severity="2",
            source="siem-detection",
            detection_time="2025-01-15T10:30:00",
            event_type="ransomware_detection",
            description="Ransomware activity detected"
        )
        self.assertEqual(alert.alert_id, "ALERT-1234567890-1234")
        self.assertEqual(alert.hostname, "server-01")
        self.assertEqual(str(alert.src_ip), "192.168.1.100")
        self.assertEqual(alert.hash.sha256, file_hash.sha256)

    def test_ransomware_alert_invalid_alert_id(self):
        """Test RansomwareAlert with invalid alert ID"""
        file_hash = FileHash(sha256="d41d8cd98f00b204e9800998ecf8427e" * 2)
        with self.assertRaises(Exception):
            RansomwareAlert(
                alert_id="INVALID-ID",  # Invalid format
                hostname="server-01",
                src_ip="192.168.1.100",
                hash=file_hash
            )

    def test_ransomware_alert_invalid_hostname(self):
        """Test RansomwareAlert with invalid hostname"""
        file_hash = FileHash(sha256="d41d8cd98f00b204e9800998ecf8427e" * 2)
        with self.assertRaises(Exception):
            RansomwareAlert(
                alert_id="ALERT-1234567890-1234",
                hostname="server@01",  # Invalid character
                src_ip="192.168.1.100",
                hash=file_hash
            )


if __name__ == '__main__':
    unittest.main()
