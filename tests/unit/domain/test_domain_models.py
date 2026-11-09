#!/usr/bin/env python3
"""Unit tests for soar_lab.domain.models."""

from datetime import UTC, datetime

import pytest

from soar_lab.domain.models import IOC, Alert, AlertSeverity, AlertStatus, Case


class TestIOC:
    """Test IOC domain model."""

    def test_ioc_creation(self):
        """Test IOC creation with valid data."""
        ioc = IOC(ioc_type="hash", value="5d41402abc4b2a76b9719d911017c592", source="test")
        assert ioc.ioc_type == "hash"
        assert ioc.value == "5d41402abc4b2a76b9719d911017c592"
        assert ioc.source == "test"

    def test_ioc_validation_empty_type(self):
        """Test IOC validation with empty type."""
        with pytest.raises(ValueError, match=r"^IOC\ type\ is\ required$"):
            IOC(ioc_type="", value="test")

    def test_ioc_validation_empty_value(self):
        """Test IOC validation with empty value."""
        with pytest.raises(ValueError, match=r"^IOC\ value\ is\ required$"):
            IOC(ioc_type="hash", value="")

    def test_ioc_validation_confidence_range(self):
        """Test IOC validation with invalid confidence."""
        with pytest.raises(ValueError, match=r"^Confidence\ must\ be\ between\ 0\.0\ and\ 1\.0$"):
            IOC(ioc_type="hash", value="test", confidence=1.5)


class TestAlert:
    """Test Alert domain model."""

    def test_alert_creation(self):
        """Test Alert creation with valid data."""
        alert = Alert(
            alert_id="ALERT-001",
            hostname="test-host",
            src_ip="192.168.1.100",
            hash="5d41402abc4b2a76b9719d911017c592",
            severity=AlertSeverity.HIGH,
            event_type="ransomware",
            description="Test alert",
            timestamp=datetime.now(UTC),
        )
        assert alert.alert_id == "ALERT-001"
        assert alert.hostname == "test-host"
        assert alert.severity == AlertSeverity.HIGH

    def test_alert_with_iocs(self):
        """Test Alert with IOCs."""
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
            timestamp=datetime.now(UTC),
            iocs=[ioc1, ioc2],
        )
        assert len(alert.iocs) == 2
        assert alert.iocs[0].value == "abc123"

    def test_alert_to_dict(self):
        """Test Alert serialization to dict."""
        alert = Alert(
            alert_id="ALERT-003",
            hostname="test-host",
            src_ip="192.168.1.100",
            hash="5d41402abc4b2a76b9719d911017c592",
            severity=AlertSeverity.MEDIUM,
            event_type="ransomware",
            description="Test alert",
            timestamp=datetime.now(UTC),
        )
        data = alert.to_dict()
        assert data["alert_id"] == "ALERT-003"
        assert data["severity"] == AlertSeverity.MEDIUM.value

    def test_alert_from_dict(self):
        """Test Alert deserialization from dict."""
        data = {
            "alert_id": "ALERT-004",
            "hostname": "test-host",
            "src_ip": "192.168.1.100",
            "hash": "5d41402abc4b2a76b9719d911017c592",
            "severity": AlertSeverity.LOW.value,
            "event_type": "ransomware",
            "description": "Test alert",
            "timestamp": datetime.now(UTC).isoformat(),
            "mitre_techniques": ["T1059"],
        }
        alert = Alert.from_dict(data)
        assert alert.alert_id == "ALERT-004"
        assert alert.severity == AlertSeverity.LOW
        assert "T1059" in alert.mitre_techniques

    def test_alert_add_ioc(self):
        """Test adding IOC to alert."""
        alert = Alert(
            alert_id="ALERT-005",
            hostname="test-host",
            src_ip="192.168.1.100",
            hash="5d41402abc4b2a76b9719d911017c592",
            severity=AlertSeverity.HIGH,
            event_type="ransomware",
            description="Test alert",
        )
        ioc = IOC(ioc_type="hash", value="abc123", source="test")
        alert.add_ioc(ioc)
        assert len(alert.iocs) == 1
        assert alert.iocs[0].value == "abc123"

    def test_alert_get_critical_iocs(self):
        """Test getting critical IOCs."""
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
            iocs=[ioc1, ioc2],
        )
        critical = alert.get_critical_iocs()
        assert len(critical) == 1
        assert critical[0].value == "abc123"

    def test_alert_validation_empty_alert_id(self):
        """Test Alert validation with empty alert ID."""
        with pytest.raises(ValueError, match=r"^Alert\ ID\ is\ required$"):
            Alert(
                alert_id="",
                hostname="test-host",
                src_ip="192.168.1.100",
                severity=AlertSeverity.HIGH,
                event_type="ransomware",
                description="Test alert",
            )

    def test_alert_validation_empty_hostname(self):
        """Test Alert validation with empty hostname."""
        with pytest.raises(ValueError, match=r"^Hostname\ is\ required$"):
            Alert(
                alert_id="ALERT-001",
                hostname="",
                src_ip="192.168.1.100",
                severity=AlertSeverity.HIGH,
                event_type="ransomware",
                description="Test alert",
            )

    def test_alert_validation_empty_src_ip(self):
        """Test Alert validation with empty src_ip."""
        with pytest.raises(ValueError, match=r"^Source\ IP\ is\ required$"):
            Alert(
                alert_id="ALERT-001",
                hostname="test-host",
                src_ip="",
                severity=AlertSeverity.HIGH,
                event_type="ransomware",
                description="Test alert",
            )


class TestAlertSeverity:
    """Test AlertSeverity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert AlertSeverity.LOW.value == 1
        assert AlertSeverity.MEDIUM.value == 2
        assert AlertSeverity.HIGH.value == 3
        assert AlertSeverity.CRITICAL.value == 4


class TestAlertStatus:
    """Test AlertStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert AlertStatus.NEW.value == "new"
        assert AlertStatus.IN_PROGRESS.value == "in_progress"
        assert AlertStatus.RESOLVED.value == "resolved"
        assert AlertStatus.CLOSED.value == "closed"


class TestCase:
    """Test Case domain model."""

    def test_case_creation(self):
        """Test Case creation with valid data."""
        case = Case(
            case_id="CASE-001",
            title="Test Case",
            description="Test case description",
            severity=AlertSeverity.HIGH,
        )
        assert case.case_id == "CASE-001"
        assert case.title == "Test Case"
        assert case.severity == AlertSeverity.HIGH
        assert case.status == AlertStatus.NEW

    def test_case_with_alerts(self):
        """Test Case with alerts."""
        case = Case(
            case_id="CASE-002",
            title="Test Case",
            description="Test case description",
            severity=AlertSeverity.CRITICAL,
            alerts=["ALERT-001", "ALERT-002"],
        )
        assert len(case.alerts) == 2
        assert "ALERT-001" in case.alerts

    def test_case_add_alert(self):
        """Test adding alert to case."""
        case = Case(
            case_id="CASE-003",
            title="Test Case",
            description="Test case description",
            severity=AlertSeverity.HIGH,
        )
        case.add_alert("ALERT-001")
        assert len(case.alerts) == 1
        assert "ALERT-001" in case.alerts

    def test_case_add_alert_duplicate(self):
        """Test adding duplicate alert doesn't duplicate."""
        case = Case(
            case_id="CASE-004",
            title="Test Case",
            description="Test case description",
            severity=AlertSeverity.HIGH,
        )
        case.add_alert("ALERT-001")
        case.add_alert("ALERT-001")
        assert len(case.alerts) == 1

    def test_case_update_status(self):
        """Test updating case status."""
        case = Case(
            case_id="CASE-005",
            title="Test Case",
            description="Test case description",
            severity=AlertSeverity.HIGH,
        )
        case.update_status(AlertStatus.IN_PROGRESS)
        assert case.status == AlertStatus.IN_PROGRESS
        assert case.updated_at is not None

    def test_case_to_dict(self):
        """Test Case serialization to dict."""
        case = Case(
            case_id="CASE-006",
            title="Test Case",
            description="Test case description",
            severity=AlertSeverity.MEDIUM,
        )
        data = case.to_dict()
        assert data["case_id"] == "CASE-006"
        assert data["severity"] == AlertSeverity.MEDIUM.value
        assert data["status"] == AlertStatus.NEW.value

    def test_case_from_dict(self):
        """Test Case deserialization from dict."""
        data = {
            "case_id": "CASE-007",
            "title": "Test Case",
            "description": "Test case description",
            "severity": AlertSeverity.LOW.value,
            "status": AlertStatus.IN_PROGRESS.value,
            "tags": ["malware", "ransomware"],
        }
        case = Case.from_dict(data)
        assert case.case_id == "CASE-007"
        assert case.severity == AlertSeverity.LOW
        assert case.status == AlertStatus.IN_PROGRESS
        assert "malware" in case.tags

    def test_case_validation_empty_case_id(self):
        """Test Case validation with empty case ID."""
        with pytest.raises(ValueError, match=r"^Case\ ID\ is\ required$"):
            Case(case_id="", title="Test", description="Test", severity=AlertSeverity.HIGH)

    def test_case_validation_empty_title(self):
        """Test Case validation with empty title."""
        with pytest.raises(ValueError, match=r"^Title\ is\ required$"):
            Case(case_id="CASE-001", title="", description="Test", severity=AlertSeverity.HIGH)

    def test_case_validation_tlp_range(self):
        """Test Case validation with invalid TLP."""
        with pytest.raises(ValueError, match=r"^TLP\ must\ be\ between\ 0\ and\ 4$"):
            Case(
                case_id="CASE-001",
                title="Test",
                description="Test",
                severity=AlertSeverity.HIGH,
                tlp=5,
            )


class TestModelsMutationHardening:
    """Exact-value assertions killing to_dict/message/boundary survivors."""

    def _alert(self, **kw):
        from datetime import UTC, datetime

        base = {
            "alert_id": "a1",
            "hostname": "h1",
            "src_ip": "1.2.3.4",
            "severity": AlertSeverity.HIGH,
            "event_type": "ransomware_detection",
            "description": "desc",
            "timestamp": datetime(2024, 1, 1, tzinfo=UTC),
        }
        base.update(kw)
        return Alert(**base)

    def test_alert_to_dict_exact(self):
        a = self._alert(
            process_name="p.exe",
            hash="abc",
            mitre_techniques=["T1486"],
            metadata={"k": "v"},
        )
        a.add_ioc(IOC(ioc_type="ip", value="9.9.9.9", confidence=0.9, tags=["c2"]))
        d = a.to_dict()
        assert d == {
            "alert_id": "a1",
            "hostname": "h1",
            "src_ip": "1.2.3.4",
            "severity": 3,
            "event_type": "ransomware_detection",
            "description": "desc",
            "process_name": "p.exe",
            "hash": "abc",
            "mitre_techniques": ["T1486"],
            "status": "new",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "iocs": [
                {
                    "ioc_type": "ip",
                    "value": "9.9.9.9",
                    "description": None,
                    "source": None,
                    "confidence": 0.9,
                    "tags": ["c2"],
                }
            ],
            "metadata": {"k": "v"},
        }

    def test_alert_from_dict_defaults(self):
        a = Alert.from_dict(
            {
                "alert_id": "a1",
                "hostname": "h",
                "src_ip": "1.1.1.1",
                "event_type": "e",
                "description": "d",
            }
        )
        assert a.severity == AlertSeverity.MEDIUM
        assert a.status == AlertStatus.NEW
        assert a.mitre_techniques == [] and a.iocs == [] and a.metadata == {}

    def test_alert_from_dict_round_trip(self):
        a = self._alert()
        a.add_ioc(IOC(ioc_type="hash", value="deadbeef"))
        a2 = Alert.from_dict(a.to_dict())
        assert a2.alert_id == "a1" and a2.severity == AlertSeverity.HIGH
        assert a2.iocs[0].value == "deadbeef"

    def test_critical_iocs_boundary_08_included(self):
        a = self._alert()
        a.add_ioc(IOC(ioc_type="ip", value="1.1.1.1", confidence=0.8))
        a.add_ioc(IOC(ioc_type="ip", value="2.2.2.2", confidence=0.79))
        crit = a.get_critical_iocs()
        assert len(crit) == 1 and crit[0].value == "1.1.1.1"

    def test_ioc_confidence_zero_is_valid(self):
        ioc = IOC(ioc_type="ip", value="1.1.1.1", confidence=0.0)
        assert ioc.confidence == 0.0

    def test_ioc_confidence_boundaries(self):
        import pytest

        IOC(ioc_type="ip", value="v", confidence=1.0)
        with pytest.raises(ValueError, match=r"^Confidence must be between 0.0 and 1.0$"):
            IOC(ioc_type="ip", value="v", confidence=1.01)
        with pytest.raises(ValueError, match=r"^Confidence must be between 0.0 and 1.0$"):
            IOC(ioc_type="ip", value="v", confidence=-0.01)

    def test_ioc_required_messages(self):
        import pytest

        with pytest.raises(ValueError, match=r"^IOC\ type\ is\ required$"):
            IOC(ioc_type="", value="v")
        with pytest.raises(ValueError, match=r"^IOC\ value\ is\ required$"):
            IOC(ioc_type="ip", value="")

    def test_alert_required_messages(self):
        import pytest

        with pytest.raises(ValueError, match=r"^Alert\ ID\ is\ required$"):
            self._alert(alert_id="")
        with pytest.raises(ValueError, match=r"^Hostname\ is\ required$"):
            self._alert(hostname="")
        with pytest.raises(ValueError, match=r"^Source\ IP\ is\ required$"):
            self._alert(src_ip="")

    def test_case_to_dict_exact(self):
        from datetime import UTC, datetime

        c = Case(
            case_id="c1",
            title="T",
            description="d",
            severity=AlertSeverity.CRITICAL,
            tags=["t1"],
            tlp=3,
            created_at=datetime(2024, 2, 1, tzinfo=UTC),
            assigned_to="analyst",
            metadata={"m": 1},
        )
        c.add_alert("a1")
        assert c.to_dict() == {
            "case_id": "c1",
            "title": "T",
            "description": "d",
            "severity": 4,
            "status": "new",
            "tags": ["t1"],
            "tlp": 3,
            "created_at": "2024-02-01T00:00:00+00:00",
            "updated_at": None,
            "assigned_to": "analyst",
            "alerts": ["a1"],
            "metadata": {"m": 1},
        }

    def test_case_tlp_boundaries(self):
        import pytest

        Case(case_id="c", title="t", description="d", severity=AlertSeverity.LOW, tlp=0)
        Case(case_id="c", title="t", description="d", severity=AlertSeverity.LOW, tlp=4)
        with pytest.raises(ValueError, match=r"^TLP must be between 0 and 4$"):
            Case(case_id="c", title="t", description="d", severity=AlertSeverity.LOW, tlp=5)
        with pytest.raises(ValueError, match=r"^TLP must be between 0 and 4$"):
            Case(case_id="c", title="t", description="d", severity=AlertSeverity.LOW, tlp=-1)

    def test_case_required_messages(self):
        import pytest

        with pytest.raises(ValueError, match=r"^Case\ ID\ is\ required$"):
            Case(case_id="", title="t", description="d", severity=AlertSeverity.LOW)
        with pytest.raises(ValueError, match=r"^Title\ is\ required$"):
            Case(case_id="c", title="", description="d", severity=AlertSeverity.LOW)

    def test_add_alert_dedup(self):
        c = Case(case_id="c", title="t", description="d", severity=AlertSeverity.LOW)
        c.add_alert("a1")
        c.add_alert("a1")
        assert c.alerts == ["a1"]

    def test_update_status_sets_updated_at(self):
        c = Case(case_id="c", title="t", description="d", severity=AlertSeverity.LOW)
        assert c.updated_at is None
        c.update_status(AlertStatus.IN_PROGRESS)
        assert c.status == AlertStatus.IN_PROGRESS
        assert c.updated_at is not None

    def test_case_from_dict_defaults_and_round_trip(self):
        c = Case.from_dict({"case_id": "c1", "title": "t", "description": "d"})
        assert c.severity == AlertSeverity.MEDIUM and c.tlp == 2
        assert c.status == AlertStatus.NEW and c.updated_at is None
        c.add_alert("a1")
        c2 = Case.from_dict(c.to_dict())
        assert c2.case_id == "c1" and c2.alerts == ["a1"]

    def test_alert_from_dict_all_fields(self):
        a = Alert.from_dict(
            {
                "alert_id": "a9",
                "hostname": "web-01",
                "src_ip": "10.0.0.9",
                "severity": 4,
                "status": "in_progress",
                "event_type": "lateral_movement",
                "description": "desc-x",
                "process_name": "w.exe",
                "hash": "feed",
                "mitre_techniques": ["T1021"],
                "timestamp": "2024-03-01T12:30:00+00:00",
                "iocs": [{"ioc_type": "ip", "value": "8.8.8.8", "confidence": 0.5}],
                "metadata": {"src": "siem"},
            }
        )
        assert a.alert_id == "a9" and a.hostname == "web-01" and a.src_ip == "10.0.0.9"
        assert a.severity == AlertSeverity.CRITICAL
        assert a.status == AlertStatus.IN_PROGRESS
        assert a.event_type == "lateral_movement" and a.description == "desc-x"
        assert a.process_name == "w.exe" and a.hash == "feed"
        assert a.mitre_techniques == ["T1021"]
        assert a.timestamp.year == 2024 and a.timestamp.month == 3
        assert a.metadata == {"src": "siem"}
        assert a.iocs[0].ioc_type == "ip" and a.iocs[0].confidence == 0.5

    def test_alert_to_dict_updated_status_value(self):
        a = self._alert(status=AlertStatus.CLOSED)
        assert a.to_dict()["status"] == "closed"

    def test_case_from_dict_all_fields(self):
        c = Case.from_dict(
            {
                "case_id": "c9",
                "title": "Ransom",
                "description": "desc",
                "severity": 3,
                "status": "resolved",
                "tags": ["urgent"],
                "tlp": 3,
                "created_at": "2024-01-15T08:00:00+00:00",
                "updated_at": "2024-01-16T09:00:00+00:00",
                "assigned_to": "soc-lead",
                "alerts": ["a1", "a2"],
                "metadata": {"env": "prod"},
            }
        )
        assert c.case_id == "c9" and c.title == "Ransom"
        assert c.severity == AlertSeverity.HIGH and c.status == AlertStatus.RESOLVED
        assert c.tags == ["urgent"] and c.tlp == 3
        assert c.created_at.month == 1 and c.created_at.day == 15
        assert c.updated_at is not None and c.updated_at.day == 16
        assert c.assigned_to == "soc-lead" and c.alerts == ["a1", "a2"]
        assert c.metadata == {"env": "prod"}

    def test_case_to_dict_with_updated_at(self):
        c = Case(case_id="c", title="t", description="d", severity=AlertSeverity.LOW)
        c.update_status(AlertStatus.CLOSED)
        d = c.to_dict()
        assert d["status"] == "closed"
        assert d["updated_at"] is not None
        from datetime import datetime

        parsed = datetime.fromisoformat(d["updated_at"])
        assert parsed.tzinfo is not None  # kills now(UTC)->now(None)

    def test_update_status_timestamp_has_timezone(self):

        c = Case(case_id="c", title="t", description="d", severity=AlertSeverity.LOW)
        c.update_status(AlertStatus.RESOLVED)
        assert c.updated_at.tzinfo is not None
        assert c.updated_at.tzname() == "UTC"

    def test_case_from_dict_requires_description_key(self):
        with pytest.raises(KeyError):
            Case.from_dict({"case_id": "c", "title": "t", "severity": 1})

    def test_case_from_dict_defaults_tags_metadata(self):
        c = Case.from_dict(
            {
                "case_id": "c",
                "title": "t",
                "description": "d",
                "severity": 1,
                "status": "new",
                "created_at": "2024-01-01T00:00:00+00:00",
            }
        )
        assert c.tags == [] and c.metadata == {}
        assert c.created_at.tzinfo is not None  # kills now(UTC)->now(None)

    def test_alert_from_dict_default_timestamp_is_utc(self):
        a = Alert.from_dict(
            {
                "alert_id": "a",
                "hostname": "h",
                "src_ip": "1.2.3.4",
                "severity": 1,
                "status": "new",
                "event_type": "e",
                "description": "d",
            }
        )
        assert a.timestamp.tzinfo is not None
