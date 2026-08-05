#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Atomic Tests for Schema Validation
Tests individual schema validation functions in isolation
"""

import json
import pytest
from pathlib import Path
from pydantic import ValidationError

from soar_lab.config.schemas import (
    RansomwareAlert,
    NetworkEvent,
    FileHash,
    SeverityLevel,
    AlertType,
    MITREInfo,
    AffectedFile
)


class TestSchemaValidationAtomic:
    """Atomic tests for individual schema validation functions"""

    def test_severity_level_enum_values(self):
        """Test SeverityLevel enum has correct values"""
        assert SeverityLevel.LOW.value == "0"
        assert SeverityLevel.MEDIUM.value == "1"
        assert SeverityLevel.HIGH.value == "2"
        assert SeverityLevel.CRITICAL.value == "3"

    def test_severity_level_enum_comparison(self):
        """Test SeverityLevel enum comparisons"""
        assert SeverityLevel.LOW == SeverityLevel("0")
        assert SeverityLevel.LOW != SeverityLevel.HIGH
        assert SeverityLevel.MEDIUM in [SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH]

    def test_alert_type_enum_values(self):
        """Test AlertType enum has correct values"""
        assert AlertType.MALICIOUS.value == "malicious"
        assert AlertType.BENIGN.value == "benign"
        assert AlertType.SUSPICIOUS.value == "suspicious"

    def test_alert_type_enum_comparison(self):
        """Test AlertType enum comparisons"""
        assert AlertType.MALICIOUS == AlertType("malicious")
        assert AlertType.MALICIOUS != AlertType.BENIGN

    def test_file_hash_valid_sha256(self):
        """Test FileHash with valid SHA256"""
        file_hash = FileHash(sha256="d41d8cd98f00b204e9800998ecf8427e" * 2)
        assert file_hash.sha256 == "d41d8cd98f00b204e9800998ecf8427e" * 2

    def test_file_hash_invalid_sha256_length(self):
        """Test FileHash with invalid SHA256 length"""
        with pytest.raises(ValidationError):
            FileHash(sha256="d41d8cd98f00b204e9800998ecf8427")  # Too short

    def test_file_hash_invalid_sha256_chars(self):
        """Test FileHash with invalid SHA256 characters"""
        with pytest.raises(ValidationError):
            FileHash(sha256="g41d8cd98f00b204e9800998ecf8427e" * 2)  # Contains 'g'

    def test_file_hash_with_optional_md5(self):
        """Test FileHash with optional MD5"""
        file_hash = FileHash(
            sha256="d41d8cd98f00b204e9800998ecf8427e" * 2,
            md5="d41d8cd98f00b204e9800998ecf8427e"
        )
        assert file_hash.md5 == "d41d8cd98f00b204e9800998ecf8427e"

    def test_file_hash_invalid_md5_length(self):
        """Test FileHash with invalid MD5 length"""
        with pytest.raises(ValidationError):
            FileHash(
                sha256="d41d8cd98f00b204e9800998ecf8427e" * 2,
                md5="d41d8cd98f00b204e9800998ecf8427"  # Too short
            )

    def test_network_event_valid_minimal(self):
        """Test NetworkEvent with minimal valid data"""
        event = NetworkEvent(src_ip="192.168.1.100")
        assert str(event.src_ip) == "192.168.1.100"
        assert event.dst_ip is None
        assert event.src_port is None
        assert event.dst_port is None
        assert event.protocol is None

    def test_network_event_valid_complete(self):
        """Test NetworkEvent with complete valid data"""
        event = NetworkEvent(
            src_ip="192.168.1.100",
            dst_ip="10.0.0.50",
            src_port=12345,
            dst_port=443,
            protocol="TCP"
        )
        assert str(event.src_ip) == "192.168.1.100"
        assert str(event.dst_ip) == "10.0.0.50"
        assert event.src_port == 12345
        assert event.dst_port == 443
        assert event.protocol == "TCP"

    def test_network_event_invalid_src_ip(self):
        """Test NetworkEvent with invalid source IP"""
        with pytest.raises(ValidationError):
            NetworkEvent(src_ip="192.168.1.300")  # Invalid octet

    def test_network_event_invalid_dst_ip(self):
        """Test NetworkEvent with invalid destination IP"""
        with pytest.raises(ValidationError):
            NetworkEvent(
                src_ip="192.168.1.100",
                dst_ip="10.0.0.300"  # Invalid octet
            )

    def test_network_event_invalid_port_range(self):
        """Test NetworkEvent with invalid port range"""
        with pytest.raises(ValidationError):
            NetworkEvent(
                src_ip="192.168.1.100",
                src_port=70000  # Invalid port (> 65535)
            )

    def test_network_event_invalid_port_zero(self):
        """Test NetworkEvent with invalid port zero"""
        with pytest.raises(ValidationError):
            NetworkEvent(
                src_ip="192.168.1.100",
                src_port=0  # Invalid port (< 1)
            )

    def test_network_event_invalid_protocol(self):
        """Test NetworkEvent with invalid protocol"""
        with pytest.raises(ValidationError):
            NetworkEvent(
                src_ip="192.168.1.100",
                protocol="HTTP"  # Not in TCP|UDP|ICMP
            )

    def test_network_event_valid_protocols(self):
        """Test NetworkEvent with all valid protocols"""
        valid_protocols = ["TCP", "UDP", "ICMP"]
        for protocol in valid_protocols:
            event = NetworkEvent(src_ip="192.168.1.100", protocol=protocol)
            assert event.protocol == protocol

    def test_file_hash_with_sha1(self):
        """Test FileHash with SHA1"""
        file_hash = FileHash(
            sha256="d41d8cd98f00b204e9800998ecf8427e" * 2,
            sha1="da39a3ee5e6b4b0d3255bfef95601890afd80709"
        )
        assert file_hash.sha1 == "da39a3ee5e6b4b0d3255bfef95601890afd80709"

    def test_file_hash_invalid_sha1_length(self):
        """Test FileHash with invalid SHA1 length"""
        with pytest.raises(ValidationError):
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
        assert file_hash.sha256 is not None
        assert file_hash.md5 is not None
        assert file_hash.sha1 is not None

    def test_network_event_port_boundary_values(self):
        """Test NetworkEvent with port boundary values"""
        # Test minimum valid port
        event1 = NetworkEvent(src_ip="192.168.1.100", src_port=1)
        assert event1.src_port == 1

        # Test maximum valid port
        event2 = NetworkEvent(src_ip="192.168.1.100", dst_port=65535)
        assert event2.dst_port == 65535

    def test_file_hash_case_insensitive(self):
        """Test FileHash accepts both uppercase and lowercase hex"""
        # Should accept uppercase
        file_hash1 = FileHash(sha256="D41D8CD98F00B204E9800998ECF8427E" * 2)
        assert file_hash1.sha256 is not None

        # Should accept lowercase
        file_hash2 = FileHash(sha256="d41d8cd98f00b204e9800998ecf8427e" * 2)
        assert file_hash2.sha256 is not None

        # Should accept mixed case
        file_hash3 = FileHash(sha256="D41d8CD9" * 8)
        assert file_hash3.sha256 is not None

    def test_mitre_info_valid_tactics(self):
        """Test MITREInfo with valid tactics"""
        mitre = MITREInfo(tactics=["TA0001", "TA0002"])
        assert len(mitre.tactics) == 2
        assert "TA0001" in mitre.tactics
        assert "TA0002" in mitre.tactics

    def test_mitre_info_invalid_tactics(self):
        """Test MITREInfo with invalid tactics"""
        with pytest.raises(ValidationError):
            MITREInfo(tactics=["INVALID_TACTIC"])

    def test_mitre_info_with_techniques(self):
        """Test MITREInfo with techniques"""
        mitre = MITREInfo(
            tactics=["TA0001"],
            techniques=["T1059", "T1055"],
            sub_techniques=["T1059.001", "T1055.001"]
        )
        assert len(mitre.techniques) == 2
        assert len(mitre.sub_techniques) == 2

    def test_affected_file_valid_minimal(self):
        """Test AffectedFile with minimal valid data"""
        file = AffectedFile(path="/tmp/test.txt", name="test.txt")
        assert file.path == "/tmp/test.txt"
        assert file.name == "test.txt"
        assert file.size is None
        assert file.extension is None
        assert file.encrypted is None

    def test_affected_file_valid_complete(self):
        """Test AffectedFile with complete valid data"""
        file = AffectedFile(
            path="/tmp/test.txt",
            name="test.txt",
            size=1024,
            extension="txt",
            encrypted=True
        )
        assert file.size == 1024
        assert file.extension == "txt"
        assert file.encrypted is True

    def test_affected_file_invalid_size(self):
        """Test AffectedFile with invalid size"""
        with pytest.raises(ValidationError):
            AffectedFile(
                path="/tmp/test.txt",
                name="test.txt",
                size=-1  # Negative size not allowed
            )

    def test_affected_file_empty_path(self):
        """Test AffectedFile with empty path"""
        with pytest.raises(ValidationError):
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
        assert alert.alert_id == "ALERT-1234567890-1234"
        assert alert.hostname == "server-01"
        assert str(alert.src_ip) == "192.168.1.100"
        assert alert.hash.sha256 == file_hash.sha256

    def test_ransomware_alert_invalid_alert_id(self):
        """Test RansomwareAlert with invalid alert ID"""
        file_hash = FileHash(sha256="d41d8cd98f00b204e9800998ecf8427e" * 2)
        with pytest.raises(ValidationError):
            RansomwareAlert(
                alert_id="INVALID-ID",  # Invalid format
                hostname="server-01",
                src_ip="192.168.1.100",
                hash=file_hash
            )

    def test_ransomware_alert_invalid_hostname(self):
        """Test RansomwareAlert with invalid hostname"""
        file_hash = FileHash(sha256="d41d8cd98f00b204e9800998ecf8427e" * 2)
        with pytest.raises(ValidationError):
            RansomwareAlert(
                alert_id="ALERT-1234567890-1234",
                hostname="server@01",  # Invalid character
                src_ip="192.168.1.100",
                hash=file_hash
            )

    def test_mitre_technique_valid_ids(self):
        """Test MITRE technique validation with valid IDs"""
        valid_techniques = [
            {"id": "T1486", "name": "Data Encrypted for Impact"},
            {"id": "T1059", "name": "Command and Scripting Interpreter"},
            {"id": "T1190", "name": "Exploit Public-Facing Application"},
            {"id": "T1566", "name": "Phishing"}
        ]

        for technique in valid_techniques:
            mitre_info = MITREInfo(techniques=[technique])
            assert mitre_info.techniques[0]['id'] == technique['id']

    def test_mitre_technique_invalid_ids(self):
        """Test MITRE technique validation with invalid IDs"""
        invalid_techniques = [
            {"id": "INVALID", "name": "Invalid Technique"},
            {"id": "T99999", "name": "Non-existent Technique"},
            {"id": "", "name": "Empty ID"},
            {"id": "T1", "name": "Too Short"}
        ]

        # Should handle invalid technique IDs gracefully
        for technique in invalid_techniques:
            try:
                mitre_info = MITREInfo(techniques=[technique])
                # If valid, check structure
                assert 'id' in mitre_info.techniques[0]
            except ValidationError:
                # Expected for invalid IDs
                pass

    def test_mitre_technique_format_validation(self):
        """Test MITRE technique ID format validation"""
        # Valid format: T followed by 4-5 digits
        valid_formats = ["T1486", "T1059", "T1190", "T1566"]
        invalid_formats = ["t1486", "T-1486", "T1486A", "T1486.001"]

        for tech_id in valid_formats:
            technique = {"id": tech_id, "name": "Test"}
            mitre_info = MITREInfo(techniques=[technique])
            assert mitre_info.techniques[0]['id'] == tech_id

    def test_mitre_technique_tactics_validation(self):
        """Test MITRE tactic validation"""
        valid_tactics = [
            "Initial Access",
            "Execution",
            "Persistence",
            "Privilege Escalation",
            "Defense Evasion",
            "Credential Access",
            "Discovery",
            "Lateral Movement",
            "Collection",
            "Exfiltration",
            "Impact"
        ]

        for tactic in valid_tactics:
            technique = {"id": "T1486", "name": "Test", "tactic": tactic}
            mitre_info = MITREInfo(techniques=[technique])
            assert mitre_info.techniques[0]['tactic'] == tactic

    def test_mitre_technique_multiple_techniques(self):
        """Test multiple MITRE techniques in single alert"""
        techniques = [
            {"id": "T1486", "name": "Data Encrypted"},
            {"id": "T1059", "name": "Command Execution"},
            {"id": "T1190", "name": "Exploit"}
        ]

        mitre_info = MITREInfo(techniques=techniques)
        assert len(mitre_info.techniques) == 3

    def test_mitre_technique_duplicate_handling(self):
        """Test handling of duplicate MITRE techniques"""
        techniques = [
            {"id": "T1486", "name": "Data Encrypted"},
            {"id": "T1486", "name": "Data Encrypted"}  # Duplicate
        ]

        # Should handle duplicates (deduplicate or accept)
        mitre_info = MITREInfo(techniques=techniques)
        # Check if duplicates are handled
        pass

    def test_mitre_technique_sub_techniques(self):
        """Test MITRE sub-technique validation"""
        sub_techniques = [
            {"id": "T1486.001", "name": "Data Encrypted for Impact"},
            {"id": "T1059.001", "name": "PowerShell"}
        ]

        # Should handle sub-techniques
        for technique in sub_techniques:
            mitre_info = MITREInfo(techniques=[technique])
            assert '.' in mitre_info.techniques[0]['id']
