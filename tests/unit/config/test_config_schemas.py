#!/usr/bin/env python3
"""
Unit tests for config/schemas.py
Tests Pydantic schemas for data validation
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from soar_lab.config.schemas import (
    SeverityLevel,
    AlertType,
    NetworkEvent,
    FileHash,
    MITREInfo,
    AffectedFile,
    RansomwareAlert,
    WebhookPayload,
    ContainmentAction,
    KPIReport,
    HealthCheck,
    BackupReport,
    SecurityScan,
    validate_alert_data,
    validate_webhook_payload,
    validate_kpi_report,
    is_valid_sha256,
    is_valid_ip_address,
    is_valid_alert_id
)


class TestSeverityLevel:
    """Test SeverityLevel enum"""

    def test_severity_levels(self):
        """Test all severity level values"""
        assert SeverityLevel.LOW.value == "0"
        assert SeverityLevel.MEDIUM.value == "1"
        assert SeverityLevel.HIGH.value == "2"
        assert SeverityLevel.CRITICAL.value == "3"


class TestAlertType:
    """Test AlertType enum"""

    def test_alert_types(self):
        """Test all alert type values"""
        assert AlertType.MALICIOUS.value == "malicious"
        assert AlertType.BENIGN.value == "benign"
        assert AlertType.SUSPICIOUS.value == "suspicious"


class TestNetworkEvent:
    """Test NetworkEvent model"""

    def test_network_event_valid(self):
        """Test valid network event"""
        event = NetworkEvent(
            src_ip="192.168.1.1",
            dst_ip="10.0.0.1",
            src_port=443,
            dst_port=80,
            protocol="TCP"
        )
        assert str(event.src_ip) == "192.168.1.1"
        assert str(event.dst_ip) == "10.0.0.1"
        assert event.src_port == 443
        assert event.dst_port == 80
        assert event.protocol == "TCP"

    def test_network_event_minimal(self):
        """Test network event with only required fields"""
        event = NetworkEvent(src_ip="192.168.1.1")
        assert str(event.src_ip) == "192.168.1.1"
        assert event.dst_ip is None
        assert event.src_port is None
        assert event.dst_port is None
        assert event.protocol is None

    def test_network_event_invalid_port_too_low(self):
        """Test network event with port too low"""
        with pytest.raises(ValidationError):
            NetworkEvent(src_ip="192.168.1.1", src_port=0)

    def test_network_event_invalid_port_too_high(self):
        """Test network event with port too high"""
        with pytest.raises(ValidationError):
            NetworkEvent(src_ip="192.168.1.1", src_port=65536)

    def test_network_event_invalid_protocol(self):
        """Test network event with invalid protocol"""
        with pytest.raises(ValidationError):
            NetworkEvent(src_ip="192.168.1.1", protocol="HTTP")


class TestFileHash:
    """Test FileHash model"""

    def test_file_hash_valid_sha256(self):
        """Test valid SHA256 hash"""
        hash_obj = FileHash(
            sha256="a" * 64,
            md5="b" * 32,
            sha1="c" * 40
        )
        assert hash_obj.sha256 == "a" * 64
        assert hash_obj.md5 == "b" * 32
        assert hash_obj.sha1 == "c" * 40

    def test_file_hash_minimal(self):
        """Test file hash with only required SHA256"""
        hash_obj = FileHash(sha256="a" * 64)
        assert hash_obj.sha256 == "a" * 64
        assert hash_obj.md5 is None
        assert hash_obj.sha1 is None

    def test_file_hash_invalid_sha256_length(self):
        """Test file hash with invalid SHA256 length"""
        with pytest.raises(ValidationError):
            FileHash(sha256="a" * 63)

    def test_file_hash_invalid_sha256_characters(self):
        """Test file hash with invalid SHA256 characters"""
        with pytest.raises(ValidationError):
            FileHash(sha256="g" * 64)

    def test_file_hash_invalid_md5_length(self):
        """Test file hash with invalid MD5 length"""
        with pytest.raises(ValidationError):
            FileHash(sha256="a" * 64, md5="b" * 31)

    def test_file_hash_invalid_sha1_length(self):
        """Test file hash with invalid SHA1 length"""
        with pytest.raises(ValidationError):
            FileHash(sha256="a" * 64, sha1="c" * 39)


class TestMITREInfo:
    """Test MITREInfo model"""

    def test_mitre_info_valid(self):
        """Test valid MITRE info"""
        mitre = MITREInfo(
            tactics=["TA0001", "TA0002"],
            techniques=["T1059", "T1566"],
            sub_techniques=["T1059.001"]
        )
        assert mitre.tactics == ["TA0001", "TA0002"]
        assert mitre.techniques == ["T1059", "T1566"]
        assert mitre.sub_techniques == ["T1059.001"]

    def test_mitre_info_default_empty_lists(self):
        """Test MITRE info with default empty lists"""
        mitre = MITREInfo()
        assert mitre.tactics == []
        assert mitre.techniques == []
        assert mitre.sub_techniques == []

    def test_mitre_info_invalid_tactic(self):
        """Test MITRE info with invalid tactic"""
        with pytest.raises(ValidationError) as exc_info:
            MITREInfo(tactics=["INVALID"])
        assert "Invalid MITRE tactic" in str(exc_info.value)


class TestAffectedFile:
    """Test AffectedFile model"""

    def test_affected_file_valid(self):
        """Test valid affected file"""
        file = AffectedFile(
            path="/path/to/file.txt",
            name="file.txt",
            size=1024,
            extension=".txt",
            encrypted=True
        )
        assert file.path == "/path/to/file.txt"
        assert file.name == "file.txt"
        assert file.size == 1024
        assert file.extension == ".txt"
        assert file.encrypted is True

    def test_affected_file_minimal(self):
        """Test affected file with only required fields"""
        file = AffectedFile(path="/path/to/file.txt", name="file.txt")
        assert file.path == "/path/to/file.txt"
        assert file.name == "file.txt"
        assert file.size is None
        assert file.extension is None
        assert file.encrypted is None

    def test_affected_file_empty_path(self):
        """Test affected file with empty path"""
        with pytest.raises(ValidationError) as exc_info:
            AffectedFile(path="", name="file.txt")
        assert "File path cannot be empty" in str(exc_info.value)

    def test_affected_file_negative_size(self):
        """Test affected file with negative size"""
        with pytest.raises(ValidationError):
            AffectedFile(path="/path/to/file.txt", name="file.txt", size=-1)


class TestRansomwareAlert:
    """Test RansomwareAlert model"""

    def test_ransomware_alert_valid(self):
        """Test valid ransomware alert"""
        now = datetime.now(timezone.utc)
        alert = RansomwareAlert(
            alert_id="ALERT-1234567890-0001",
            hostname="test-host",
            src_ip="192.168.1.1",
            hash=FileHash(sha256="a" * 64),
            severity=SeverityLevel.HIGH,
            source="endpoint",
            detection_time=now,
            event_type="ransomware_detection",
            description="Test alert"
        )
        assert alert.alert_id == "ALERT-1234567890-0001"
        assert alert.hostname == "test-host"
        assert alert.severity == SeverityLevel.HIGH

    def test_ransomware_alert_with_optional_fields(self):
        """Test ransomware alert with optional fields"""
        now = datetime.now(timezone.utc)
        alert = RansomwareAlert(
            alert_id="ALERT-1234567890-0001",
            hostname="test-host",
            src_ip="192.168.1.1",
            hash=FileHash(sha256="a" * 64),
            severity=SeverityLevel.HIGH,
            source="endpoint",
            detection_time=now,
            event_type="ransomware_detection",
            description="Test alert",
            affected_files=[AffectedFile(path="/path/to/file.txt", name="file.txt")],
            mitre_tactics=["TA0001"],
            mitre_techniques=["T1059"],
            network_events=[NetworkEvent(src_ip="192.168.1.1")],
            user_context={"username": "test"},
            process_info={"pid": 1234}
        )
        assert len(alert.affected_files) == 1
        assert len(alert.mitre_tactics) == 1
        assert len(alert.network_events) == 1
        assert alert.user_context == {"username": "test"}

    def test_ransomware_alert_invalid_alert_id(self):
        """Test ransomware alert with invalid alert ID"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            RansomwareAlert(
                alert_id="INVALID",
                hostname="test-host",
                src_ip="192.168.1.1",
                hash=FileHash(sha256="a" * 64),
                severity=SeverityLevel.HIGH,
                source="endpoint",
                detection_time=now,
                event_type="ransomware_detection",
                description="Test alert"
            )

    def test_ransomware_alert_invalid_hostname(self):
        """Test ransomware alert with invalid hostname"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            RansomwareAlert(
                alert_id="ALERT-1234567890-0001",
                hostname="invalid_hostname!",
                src_ip="192.168.1.1",
                hash=FileHash(sha256="a" * 64),
                severity=SeverityLevel.HIGH,
                source="endpoint",
                detection_time=now,
                event_type="ransomware_detection",
                description="Test alert"
            )

    def test_ransomware_alert_future_detection_time(self):
        """Test ransomware alert with future detection time"""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        with pytest.raises(ValidationError) as exc_info:
            RansomwareAlert(
                alert_id="ALERT-1234567890-0001",
                hostname="test-host",
                src_ip="192.168.1.1",
                hash=FileHash(sha256="a" * 64),
                severity=SeverityLevel.HIGH,
                source="endpoint",
                detection_time=future,
                event_type="ransomware_detection",
                description="Test alert"
            )
        assert "Detection time cannot be in the future" in str(exc_info.value)

    def test_ransomware_alert_invalid_event_type(self):
        """Test ransomware alert with invalid event type"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            RansomwareAlert(
                alert_id="ALERT-1234567890-0001",
                hostname="test-host",
                src_ip="192.168.1.1",
                hash=FileHash(sha256="a" * 64),
                severity=SeverityLevel.HIGH,
                source="endpoint",
                detection_time=now,
                event_type="invalid_event",
                description="Test alert"
            )


class TestWebhookPayload:
    """Test WebhookPayload model"""

    def test_webhook_payload_valid(self):
        """Test valid webhook payload"""
        now = datetime.now(timezone.utc)
        alert = RansomwareAlert(
            alert_id="ALERT-1234567890-0001",
            hostname="test-host",
            src_ip="192.168.1.1",
            hash=FileHash(sha256="a" * 64),
            severity=SeverityLevel.HIGH,
            source="endpoint",
            detection_time=now,
            event_type="ransomware_detection",
            description="Test alert"
        )
        payload = WebhookPayload(
            alert=alert,
            metadata={"key": "value"},
            version="1.0"
        )
        assert payload.alert.alert_id == "ALERT-1234567890-0001"
        assert payload.metadata == {"key": "value"}
        assert payload.version == "1.0"

    def test_webhook_payload_defaults(self):
        """Test webhook payload with defaults"""
        now = datetime.now(timezone.utc)
        alert = RansomwareAlert(
            alert_id="ALERT-1234567890-0001",
            hostname="test-host",
            src_ip="192.168.1.1",
            hash=FileHash(sha256="a" * 64),
            severity=SeverityLevel.HIGH,
            source="endpoint",
            detection_time=now,
            event_type="ransomware_detection",
            description="Test alert"
        )
        payload = WebhookPayload(alert=alert)
        assert payload.metadata == {}
        assert payload.version == "1.0"
        assert payload.timestamp is not None

    def test_webhook_payload_invalid_version(self):
        """Test webhook payload with invalid version"""
        now = datetime.now(timezone.utc)
        alert = RansomwareAlert(
            alert_id="ALERT-1234567890-0001",
            hostname="test-host",
            src_ip="192.168.1.1",
            hash=FileHash(sha256="a" * 64),
            severity=SeverityLevel.HIGH,
            source="endpoint",
            detection_time=now,
            event_type="ransomware_detection",
            description="Test alert"
        )
        with pytest.raises(ValidationError) as exc_info:
            WebhookPayload(alert=alert, version="invalid")
        assert "Version must be in format" in str(exc_info.value)


class TestContainmentAction:
    """Test ContainmentAction model"""

    def test_containment_action_valid(self):
        """Test valid containment action"""
        action = ContainmentAction(
            action_id="ACTION-1234567890-0001",
            alert_id="ALERT-1234567890-0001",
            hostname="test-host",
            action_type="network_isolation",
            status="pending"
        )
        assert action.action_id == "ACTION-1234567890-0001"
        assert action.alert_id == "ALERT-1234567890-0001"
        assert action.action_type == "network_isolation"
        assert action.status == "pending"

    def test_containment_action_with_optional_fields(self):
        """Test containment action with optional fields"""
        now = datetime.now(timezone.utc)
        action = ContainmentAction(
            action_id="ACTION-1234567890-0001",
            alert_id="ALERT-1234567890-0001",
            hostname="test-host",
            action_type="network_isolation",
            status="executed",
            execution_time=now,
            details={"reason": "test"},
            error_message=None
        )
        assert action.execution_time == now
        assert action.details == {"reason": "test"}

    def test_containment_action_invalid_action_id(self):
        """Test containment action with invalid action ID"""
        with pytest.raises(ValidationError):
            ContainmentAction(
                action_id="INVALID",
                alert_id="ALERT-1234567890-0001",
                hostname="test-host",
                action_type="network_isolation",
                status="pending"
            )

    def test_containment_action_invalid_action_type(self):
        """Test containment action with invalid action type"""
        with pytest.raises(ValidationError):
            ContainmentAction(
                action_id="ACTION-1234567890-0001",
                alert_id="ALERT-1234567890-0001",
                hostname="test-host",
                action_type="invalid_action",
                status="pending"
            )

    def test_containment_action_invalid_status(self):
        """Test containment action with invalid status"""
        with pytest.raises(ValidationError):
            ContainmentAction(
                action_id="ACTION-1234567890-0001",
                alert_id="ALERT-1234567890-0001",
                hostname="test-host",
                action_type="network_isolation",
                status="invalid_status"
            )


class TestKPIReport:
    """Test KPIReport model"""

    def test_kpi_report_valid(self):
        """Test valid KPI report"""
        report = KPIReport(
            total_executions=100,
            mean_mttr=120.0,
            median_mttr=110.0,
            p50_mttr=100.0,
            p90_mttr=150.0,
            min_mttr=50.0,
            max_mttr=200.0,
            std_deviation=30.0,
            p50_within_threshold=True,
            p90_within_threshold=True
        )
        assert report.total_executions == 100
        assert report.mean_mttr == 120.0
        # The model validator computes threshold compliance
        assert report.p50_within_threshold is True
        assert report.p90_within_threshold is True

    def test_kpi_report_threshold_computation(self):
        """Test KPI report threshold computation"""
        report = KPIReport(
            total_executions=100,
            mean_mttr=120.0,
            median_mttr=110.0,
            p50_mttr=100.0,
            p90_mttr=150.0,
            min_mttr=50.0,
            max_mttr=200.0,
            std_deviation=30.0,
            threshold_p50=120.0,
            threshold_p90=180.0,
            p50_within_threshold=True,
            p90_within_threshold=True
        )
        # The model validator should compute threshold compliance
        assert report.p50_within_threshold is True
        assert report.p90_within_threshold is True

    def test_kpi_report_defaults(self):
        """Test KPI report with default thresholds"""
        report = KPIReport(
            total_executions=100,
            mean_mttr=120.0,
            median_mttr=110.0,
            p50_mttr=100.0,
            p90_mttr=150.0,
            min_mttr=50.0,
            max_mttr=200.0,
            std_deviation=30.0,
            p50_within_threshold=True,
            p90_within_threshold=True
        )
        assert report.threshold_p50 == 120.0
        assert report.threshold_p90 == 180.0

    def test_kpi_report_negative_values(self):
        """Test KPI report with negative values"""
        with pytest.raises(ValidationError):
            KPIReport(
                total_executions=-1,
                mean_mttr=120.0,
                median_mttr=110.0,
                p50_mttr=100.0,
                p90_mttr=150.0,
                min_mttr=50.0,
                max_mttr=200.0,
                std_deviation=30.0,
                p50_within_threshold=True,
                p90_within_threshold=True
            )


class TestHealthCheck:
    """Test HealthCheck model"""

    def test_health_check_valid(self):
        """Test valid health check"""
        check = HealthCheck(
            service_name="test-service",
            status="healthy",
            response_time_ms=100.0
        )
        assert check.service_name == "test-service"
        assert check.status == "healthy"
        assert check.response_time_ms == 100.0

    def test_health_check_defaults(self):
        """Test health check with defaults"""
        check = HealthCheck(service_name="test-service", status="healthy")
        assert check.response_time_ms is None
        assert check.metadata == {}
        assert check.timestamp is not None

    def test_health_check_invalid_status(self):
        """Test health check with invalid status"""
        with pytest.raises(ValidationError):
            HealthCheck(service_name="test-service", status="invalid")

    def test_health_check_response_time_too_high(self):
        """Test health check with response time exceeding 30 seconds"""
        with pytest.raises(ValidationError) as exc_info:
            HealthCheck(
                service_name="test-service",
                status="healthy",
                response_time_ms=35000.0
            )
        assert "Response time exceeds 30 seconds" in str(exc_info.value)

    def test_health_check_negative_response_time(self):
        """Test health check with negative response time"""
        with pytest.raises(ValidationError):
            HealthCheck(
                service_name="test-service",
                status="healthy",
                response_time_ms=-1.0
            )


class TestBackupReport:
    """Test BackupReport model"""

    def test_backup_report_valid(self):
        """Test valid backup report"""
        now = datetime.now(timezone.utc)
        report = BackupReport(
            backup_id="BACKUP-20240101_120000",
            timestamp=now,
            backup_type="manual",
            components={"database": True, "files": True},
            total_size_mb=1024.0,
            compression_ratio=0.5,
            success=True
        )
        assert report.backup_id == "BACKUP-20240101_120000"
        assert report.backup_type == "manual"
        assert report.success is True

    def test_backup_report_defaults(self):
        """Test backup report with defaults"""
        now = datetime.now(timezone.utc)
        report = BackupReport(
            backup_id="BACKUP-20240101_120000",
            timestamp=now,
            backup_type="manual",
            components={"database": True},
            total_size_mb=1024.0,
            success=True
        )
        assert report.retention_days == 7
        assert report.compression_ratio is None

    def test_backup_report_invalid_backup_id(self):
        """Test backup report with invalid backup ID"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            BackupReport(
                backup_id="INVALID",
                timestamp=now,
                backup_type="manual",
                components={"database": True},
                total_size_mb=1024.0,
                success=True
            )

    def test_backup_report_invalid_backup_type(self):
        """Test backup report with invalid backup type"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            BackupReport(
                backup_id="BACKUP-20240101_120000",
                timestamp=now,
                backup_type="invalid",
                components={"database": True},
                total_size_mb=1024.0,
                success=True
            )

    def test_backup_report_compression_ratio_out_of_range(self):
        """Test backup report with compression ratio out of range"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            BackupReport(
                backup_id="BACKUP-20240101_120000",
                timestamp=now,
                backup_type="manual",
                components={"database": True},
                total_size_mb=1024.0,
                compression_ratio=1.5,
                success=True
            )

    def test_backup_report_negative_size(self):
        """Test backup report with negative size"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            BackupReport(
                backup_id="BACKUP-20240101_120000",
                timestamp=now,
                backup_type="manual",
                components={"database": True},
                total_size_mb=-1.0,
                success=True
            )


class TestSecurityScan:
    """Test SecurityScan model"""

    def test_security_scan_valid(self):
        """Test valid security scan"""
        now = datetime.now(timezone.utc)
        scan = SecurityScan(
            scan_id="SCAN-20240101_120000",
            timestamp=now,
            scanner="nessus",
            target="192.168.1.0/24",
            vulnerabilities={"critical": 1, "high": 2, "medium": 3, "low": 4, "info": 5},
            total_vulnerabilities=15,
            scan_duration_seconds=300.0,
            success=True
        )
        assert scan.scan_id == "SCAN-20240101_120000"
        assert scan.scanner == "nessus"
        assert scan.total_vulnerabilities == 15

    def test_security_scan_defaults(self):
        """Test security scan with defaults"""
        now = datetime.now(timezone.utc)
        scan = SecurityScan(
            scan_id="SCAN-20240101_120000",
            timestamp=now,
            scanner="nessus",
            target="192.168.1.0/24",
            vulnerabilities={"critical": 1},
            total_vulnerabilities=1,
            scan_duration_seconds=300.0,
            success=True
        )
        assert scan.recommendations == []

    def test_security_scan_invalid_severity(self):
        """Test security scan with invalid severity"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError) as exc_info:
            SecurityScan(
                scan_id="SCAN-20240101_120000",
                timestamp=now,
                scanner="nessus",
                target="192.168.1.0/24",
                vulnerabilities={"invalid_severity": 1},
                total_vulnerabilities=1,
                scan_duration_seconds=300.0,
                success=True
            )
        assert "Invalid vulnerability severity" in str(exc_info.value)

    def test_security_scan_negative_vulnerability_count(self):
        """Test security scan with negative vulnerability count"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError) as exc_info:
            SecurityScan(
                scan_id="SCAN-20240101_120000",
                timestamp=now,
                scanner="nessus",
                target="192.168.1.0/24",
                vulnerabilities={"critical": -1},
                total_vulnerabilities=-1,
                scan_duration_seconds=300.0,
                success=True
            )
        assert "cannot be negative" in str(exc_info.value)

    def test_security_scan_negative_duration(self):
        """Test security scan with negative duration"""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            SecurityScan(
                scan_id="SCAN-20240101_120000",
                timestamp=now,
                scanner="nessus",
                target="192.168.1.0/24",
                vulnerabilities={"critical": 1},
                total_vulnerabilities=1,
                scan_duration_seconds=-1.0,
                success=True
            )


class TestValidationFunctions:
    """Test validation functions"""

    def test_validate_alert_data_valid(self):
        """Test validate_alert_data with valid data"""
        now = datetime.now(timezone.utc)
        alert_data = {
            "alert_id": "ALERT-1234567890-0001",
            "hostname": "test-host",
            "src_ip": "192.168.1.1",
            "hash": {"sha256": "a" * 64},
            "severity": "2",
            "source": "endpoint",
            "detection_time": now.isoformat(),
            "event_type": "ransomware_detection",
            "description": "Test alert"
        }
        is_valid, errors = validate_alert_data(alert_data)
        assert is_valid is True
        assert errors == []

    def test_validate_alert_data_invalid(self):
        """Test validate_alert_data with invalid data"""
        alert_data = {
            "alert_id": "INVALID",
            "hostname": "test-host",
            "src_ip": "192.168.1.1",
            "hash": {"sha256": "a" * 64},
            "severity": "2",
            "source": "endpoint",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "description": "Test alert"
        }
        is_valid, errors = validate_alert_data(alert_data)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_webhook_payload_valid(self):
        """Test validate_webhook_payload with valid data"""
        now = datetime.now(timezone.utc)
        payload_data = {
            "alert": {
                "alert_id": "ALERT-1234567890-0001",
                "hostname": "test-host",
                "src_ip": "192.168.1.1",
                "hash": {"sha256": "a" * 64},
                "severity": "2",
                "source": "endpoint",
                "detection_time": now.isoformat(),
                "event_type": "ransomware_detection",
                "description": "Test alert"
            },
            "metadata": {"key": "value"},
            "version": "1.0"
        }
        payload = validate_webhook_payload(payload_data)
        assert payload.alert.alert_id == "ALERT-1234567890-0001"

    def test_validate_kpi_report_valid(self):
        """Test validate_kpi_report with valid data"""
        kpi_data = {
            "total_executions": 100,
            "mean_mttr": 120.0,
            "median_mttr": 110.0,
            "p50_mttr": 100.0,
            "p90_mttr": 150.0,
            "min_mttr": 50.0,
            "max_mttr": 200.0,
            "std_deviation": 30.0,
            "p50_within_threshold": True,
            "p90_within_threshold": True
        }
        report = validate_kpi_report(kpi_data)
        assert report.total_executions == 100

    def test_is_valid_sha256_valid(self):
        """Test is_valid_sha256 with valid hash"""
        assert is_valid_sha256("a" * 64) is True

    def test_is_valid_sha256_invalid_length(self):
        """Test is_valid_sha256 with invalid length"""
        assert is_valid_sha256("a" * 63) is False

    def test_is_valid_sha256_invalid_characters(self):
        """Test is_valid_sha256 with invalid characters"""
        assert is_valid_sha256("g" * 64) is False

    def test_is_valid_ip_address_valid(self):
        """Test is_valid_ip_address with valid IP"""
        assert is_valid_ip_address("192.168.1.1") is True
        assert is_valid_ip_address("10.0.0.1") is True
        assert is_valid_ip_address("127.0.0.1") is True

    def test_is_valid_ip_address_invalid(self):
        """Test is_valid_ip_address with invalid IP"""
        assert is_valid_ip_address("256.256.256.256") is False
        assert is_valid_ip_address("invalid") is False
        assert is_valid_ip_address("") is False

    def test_is_valid_alert_id_valid(self):
        """Test is_valid_alert_id with valid alert ID"""
        assert is_valid_alert_id("ALERT-1234567890-0001") is True
        assert is_valid_alert_id("ALERT-9999999999-9999") is True

    def test_is_valid_alert_id_invalid(self):
        """Test is_valid_alert_id with invalid alert ID"""
        assert is_valid_alert_id("INVALID") is False
        assert is_valid_alert_id("ALERT-123") is False
        assert is_valid_alert_id("") is False
