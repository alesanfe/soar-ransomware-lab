#!/usr/bin/env python3
"""
Unit tests for soar_lab.domain.models
"""

import pytest
from datetime import datetime, timezone

from soar_lab.domain.models import IOC, Alert, AlertSeverity, AlertStatus, Case


class TestIOC:
    """Test IOC domain model"""

    def test_ioc_creation(self):
        """Test IOC creation with valid data"""
        ioc = IOC(
            ioc_type="hash",
            value="5d41402abc4b2a76b9719d911017c592",
            source="test"
        )
        assert ioc.ioc_type == "hash"
        assert ioc.value == "5d41402abc4b2a76b9719d911017c592"
        assert ioc.source == "test"

    def test_ioc_validation_empty_type(self):
        """Test IOC validation with empty type"""
        with pytest.raises(ValueError, match="IOC type is required"):
            IOC(ioc_type="", value="test")

    def test_ioc_validation_empty_value(self):
        """Test IOC validation with empty value"""
        with pytest.raises(ValueError, match="IOC value is required"):
            IOC(ioc_type="hash", value="")

    def test_ioc_validation_confidence_range(self):
        """Test IOC validation with invalid confidence"""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            IOC(ioc_type="hash", value="test", confidence=1.5)


class TestAlert:
    """Test Alert domain model"""

    def test_alert_creation(self):
        """Test Alert creation with valid data"""
        alert = Alert(
            alert_id="ALERT-001",
            hostname="test-host",
            src_ip="192.168.1.100",
            hash="5d41402abc4b2a76b9719d911017c592",
            severity=AlertSeverity.HIGH,
            event_type="ransomware",
            description="Test alert",
            timestamp=datetime.now(timezone.utc)
        )
        assert alert.alert_id == "ALERT-001"
        assert alert.hostname == "test-host"
        assert alert.severity == AlertSeverity.HIGH

    def test_alert_with_iocs(self):
        """Test Alert with IOCs"""
        ioc1 = IOC(ioc_type="hash", value="abc123", source="test")
        ioc2 = IOC(ioc_type="ip", value="10.0.0.1", source="test")

        alert = Alert(
            alert_id="ALERT-002",
            hostname="test-host",
            src_ip="192.168.1.100",
            hash="5d41402abc4b2a76b9719d911017c592",
            severity=AlertSeverity.CRITICAL,
            event_type="ransomware",
            description="Test alert with IOCs",
            timestamp=datetime.now(timezone.utc),
            iocs=[ioc1, ioc2]
        )
        assert len(alert.iocs) == 2
        assert alert.iocs[0].value == "abc123"

    def test_alert_to_dict(self):
        """Test Alert serialization to dict"""
        alert = Alert(
            alert_id="ALERT-003",
            hostname="test-host",
            src_ip="192.168.1.100",
            hash="5d41402abc4b2a76b9719d911017c592",
            severity=AlertSeverity.MEDIUM,
            event_type="ransomware",
            description="Test alert",
            timestamp=datetime.now(timezone.utc)
        )
        data = alert.to_dict()
        assert data['alert_id'] == "ALERT-003"
        assert data['severity'] == AlertSeverity.MEDIUM.value

    def test_alert_from_dict(self):
        """Test Alert deserialization from dict"""
        data = {
            'alert_id': 'ALERT-004',
            'hostname': 'test-host',
            'src_ip': '192.168.1.100',
            'hash': '5d41402abc4b2a76b9719d911017c592',
            'severity': AlertSeverity.LOW.value,
            'event_type': 'ransomware',
            'description': 'Test alert',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'mitre_techniques': ['T1059']
        }
        alert = Alert.from_dict(data)
        assert alert.alert_id == "ALERT-004"
        assert alert.severity == AlertSeverity.LOW
        assert 'T1059' in alert.mitre_techniques

    def test_alert_add_ioc(self):
        """Test adding IOC to alert"""
        alert = Alert(
            alert_id="ALERT-005",
            hostname="test-host",
            src_ip="192.168.1.100",
            hash="5d41402abc4b2a76b9719d911017c592",
            severity=AlertSeverity.HIGH,
            event_type="ransomware",
            description="Test alert"
        )
        ioc = IOC(ioc_type="hash", value="abc123", source="test")
        alert.add_ioc(ioc)
        assert len(alert.iocs) == 1
        assert alert.iocs[0].value == "abc123"

    def test_alert_get_critical_iocs(self):
        """Test getting critical IOCs"""
        ioc1 = IOC(ioc_type="hash", value="abc123", confidence=0.9, source="test")
        ioc2 = IOC(ioc_type="ip", value="10.0.0.1", confidence=0.5, source="test")

        alert = Alert(
            alert_id="ALERT-006",
            hostname="test-host",
            src_ip="192.168.1.100",
            hash="5d41402abc4b2a76b9719d911017c592",
            severity=AlertSeverity.HIGH,
            event_type="ransomware",
            description="Test alert",
            iocs=[ioc1, ioc2]
        )
        critical = alert.get_critical_iocs()
        assert len(critical) == 1
        assert critical[0].value == "abc123"

    def test_alert_validation_empty_alert_id(self):
        """Test Alert validation with empty alert ID"""
        with pytest.raises(ValueError, match="Alert ID is required"):
            Alert(
                alert_id="",
                hostname="test-host",
                src_ip="192.168.1.100",
                severity=AlertSeverity.HIGH,
                event_type="ransomware",
                description="Test alert"
            )

    def test_alert_validation_empty_hostname(self):
        """Test Alert validation with empty hostname"""
        with pytest.raises(ValueError, match="Hostname is required"):
            Alert(
                alert_id="ALERT-001",
                hostname="",
                src_ip="192.168.1.100",
                severity=AlertSeverity.HIGH,
                event_type="ransomware",
                description="Test alert"
            )

    def test_alert_validation_empty_src_ip(self):
        """Test Alert validation with empty src_ip"""
        with pytest.raises(ValueError, match="Source IP is required"):
            Alert(
                alert_id="ALERT-001",
                hostname="test-host",
                src_ip="",
                severity=AlertSeverity.HIGH,
                event_type="ransomware",
                description="Test alert"
            )


class TestAlertSeverity:
    """Test AlertSeverity enum"""

    def test_severity_values(self):
        """Test severity enum values"""
        assert AlertSeverity.LOW.value == 1
        assert AlertSeverity.MEDIUM.value == 2
        assert AlertSeverity.HIGH.value == 3
        assert AlertSeverity.CRITICAL.value == 4


class TestAlertStatus:
    """Test AlertStatus enum"""

    def test_status_values(self):
        """Test status enum values"""
        assert AlertStatus.NEW.value == "new"
        assert AlertStatus.IN_PROGRESS.value == "in_progress"
        assert AlertStatus.RESOLVED.value == "resolved"
        assert AlertStatus.CLOSED.value == "closed"


class TestCase:
    """Test Case domain model"""

    def test_case_creation(self):
        """Test Case creation with valid data"""
        case = Case(
            case_id="CASE-001",
            title="Test Case",
            description="Test case description",
            severity=AlertSeverity.HIGH
        )
        assert case.case_id == "CASE-001"
        assert case.title == "Test Case"
        assert case.severity == AlertSeverity.HIGH
        assert case.status == AlertStatus.NEW

    def test_case_with_alerts(self):
        """Test Case with alerts"""
        case = Case(
            case_id="CASE-002",
            title="Test Case",
            description="Test case description",
            severity=AlertSeverity.CRITICAL,
            alerts=["ALERT-001", "ALERT-002"]
        )
        assert len(case.alerts) == 2
        assert "ALERT-001" in case.alerts

    def test_case_add_alert(self):
        """Test adding alert to case"""
        case = Case(
            case_id="CASE-003",
            title="Test Case",
            description="Test case description",
            severity=AlertSeverity.HIGH
        )
        case.add_alert("ALERT-001")
        assert len(case.alerts) == 1
        assert "ALERT-001" in case.alerts

    def test_case_add_alert_duplicate(self):
        """Test adding duplicate alert doesn't duplicate"""
        case = Case(
            case_id="CASE-004",
            title="Test Case",
            description="Test case description",
            severity=AlertSeverity.HIGH
        )
        case.add_alert("ALERT-001")
        case.add_alert("ALERT-001")
        assert len(case.alerts) == 1

    def test_case_update_status(self):
        """Test updating case status"""
        case = Case(
            case_id="CASE-005",
            title="Test Case",
            description="Test case description",
            severity=AlertSeverity.HIGH
        )
        case.update_status(AlertStatus.IN_PROGRESS)
        assert case.status == AlertStatus.IN_PROGRESS
        assert case.updated_at is not None

    def test_case_to_dict(self):
        """Test Case serialization to dict"""
        case = Case(
            case_id="CASE-006",
            title="Test Case",
            description="Test case description",
            severity=AlertSeverity.MEDIUM
        )
        data = case.to_dict()
        assert data['case_id'] == "CASE-006"
        assert data['severity'] == AlertSeverity.MEDIUM.value
        assert data['status'] == AlertStatus.NEW.value

    def test_case_from_dict(self):
        """Test Case deserialization from dict"""
        data = {
            'case_id': 'CASE-007',
            'title': 'Test Case',
            'description': 'Test case description',
            'severity': AlertSeverity.LOW.value,
            'status': AlertStatus.IN_PROGRESS.value,
            'tags': ['malware', 'ransomware']
        }
        case = Case.from_dict(data)
        assert case.case_id == "CASE-007"
        assert case.severity == AlertSeverity.LOW
        assert case.status == AlertStatus.IN_PROGRESS
        assert 'malware' in case.tags

    def test_case_validation_empty_case_id(self):
        """Test Case validation with empty case ID"""
        with pytest.raises(ValueError, match="Case ID is required"):
            Case(case_id="", title="Test", description="Test", severity=AlertSeverity.HIGH)

    def test_case_validation_empty_title(self):
        """Test Case validation with empty title"""
        with pytest.raises(ValueError, match="Title is required"):
            Case(case_id="CASE-001", title="", description="Test", severity=AlertSeverity.HIGH)

    def test_case_validation_tlp_range(self):
        """Test Case validation with invalid TLP"""
        with pytest.raises(ValueError, match="TLP must be between 0 and 4"):
            Case(case_id="CASE-001", title="Test", description="Test", severity=AlertSeverity.HIGH, tlp=5)
