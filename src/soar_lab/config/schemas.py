#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Pydantic Schemas
Data validation models using Pydantic for type safety and validation
"""

import re
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
from pydantic.networks import IPv4Address
from typing import Any, Dict, List, Optional

# Constants
ALERT_ID_PATTERN = r"^ALERT-\d{10}-\d{4}$"


class SeverityLevel(str, Enum):
    """Alert severity levels"""
    LOW = "0"
    MEDIUM = "1"
    HIGH = "2"
    CRITICAL = "3"


class AlertType(str, Enum):
    """Alert types"""
    MALICIOUS = "malicious"
    BENIGN = "benign"
    SUSPICIOUS = "suspicious"


class NetworkEvent(BaseModel):
    """Network event model"""
    src_ip: IPv4Address = Field(..., description="Source IP address")
    dst_ip: Optional[IPv4Address] = Field(None, description="Destination IP address")
    src_port: Optional[int] = Field(None, ge=1, le=65535, description="Source port")
    dst_port: Optional[int] = Field(None, ge=1, le=65535, description="Destination port")
    protocol: Optional[str] = Field(None, pattern=r"^(TCP|UDP|ICMP)$", description="Network protocol")

    @field_validator('src_ip')
    @classmethod
    def validate_src_ip(cls, v: IPv4Address) -> IPv4Address:
        return v


class FileHash(BaseModel):
    """File hash model"""
    sha256: str = Field(..., min_length=64, max_length=64, pattern=r"^[a-fA-F0-9]{64}$", description="SHA256 hash")
    md5: Optional[str] = Field(None, min_length=32, max_length=32, pattern=r"^[a-fA-F0-9]{32}$", description="MD5 hash")
    sha1: Optional[str] = Field(None, min_length=40, max_length=40, pattern=r"^[a-fA-F0-9]{40}$",
                                description="SHA1 hash")


class MITREInfo(BaseModel):
    """MITRE ATT&CK information"""
    tactics: List[str] = Field(default_factory=list, description="MITRE tactics")
    techniques: List[str] = Field(default_factory=list, description="MITRE techniques")
    sub_techniques: List[str] = Field(default_factory=list, description="MITRE sub-techniques")

    @field_validator('tactics')
    @classmethod
    def validate_tactics(cls, v: List[str]) -> List[str]:
        valid_tactics = {
            "TA0001", "TA0002", "TA0003", "TA0004", "TA0005", "TA0006", "TA0007", "TA0008", "TA0009",
            "TA0010", "TA0011", "TA0040", "TA0042", "TA0043"
        }
        for tactic in v:
            if tactic not in valid_tactics:
                raise ValueError(f"Invalid MITRE tactic: {tactic}")
        return v


class AffectedFile(BaseModel):
    """Affected file information"""
    path: str = Field(..., description="File path")
    name: str = Field(..., description="File name")
    size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    extension: Optional[str] = Field(None, description="File extension")
    encrypted: Optional[bool] = Field(None, description="Whether file is encrypted")

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v:
            raise ValueError("File path cannot be empty")
        return v


class RansomwareAlert(BaseModel):
    """Ransomware detection alert model"""
    alert_id: str = Field(..., pattern=ALERT_ID_PATTERN, description="Alert ID format: ALERT-timestamp-sequence")
    hostname: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9\-]+$", description="Hostname")
    src_ip: IPv4Address = Field(..., description="Source IP address")
    hash: FileHash = Field(..., description="File hash information")
    severity: SeverityLevel = Field(..., description="Alert severity")
    source: str = Field(..., min_length=1, max_length=100, description="Alert source")
    detection_time: datetime = Field(..., description="Detection timestamp")
    event_type: str = Field(..., pattern=r"^ransomware_detection$", description="Event type")
    description: str = Field(..., min_length=1, max_length=1000, description="Alert description")
    affected_files: List[AffectedFile] = Field(default_factory=list, description="Affected files")
    mitre_tactics: List[str] = Field(default_factory=list, description="MITRE tactics")
    mitre_techniques: List[str] = Field(default_factory=list, description="MITRE techniques")
    network_events: List[NetworkEvent] = Field(default_factory=list, description="Network events")
    user_context: Optional[Dict[str, Any]] = Field(None, description="User context information")
    process_info: Optional[Dict[str, Any]] = Field(None, description="Process information")

    @field_validator('alert_id')
    @classmethod
    def validate_alert_id(cls, v: str) -> str:
        if not re.match(ALERT_ID_PATTERN, v):
            raise ValueError("Alert ID must be in format: ALERT-timestamp-sequence")
        return v

    @field_validator('hostname')
    @classmethod
    def validate_hostname(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9\-]{1,255}$", v):
            raise ValueError("Hostname can only contain alphanumeric characters and hyphens")
        return v

    @field_validator('detection_time')
    @classmethod
    def validate_detection_time(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc)
        v_aware = v if v.tzinfo is not None else v.replace(tzinfo=timezone.utc)
        if v_aware > now:
            raise ValueError("Detection time cannot be in the future")
        return v


class WebhookPayload(BaseModel):
    """Webhook payload model"""
    alert: RansomwareAlert = Field(..., description="Ransomware alert")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Payload timestamp")
    version: str = Field(default="1.0", description="Payload version")

    @field_validator('version')
    @classmethod
    def validate_version(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+(\.\d+)?$", v):
            raise ValueError("Version must be in format: x.y or x.y.z")
        return v


class ContainmentAction(BaseModel):
    """Containment action model"""
    action_id: str = Field(..., pattern=r"^ACTION-\d{10}-\d{4}$", description="Action ID")
    alert_id: str = Field(..., pattern=ALERT_ID_PATTERN, description="Related alert ID")
    hostname: str = Field(..., description="Target hostname")
    action_type: str = Field(..., pattern=r"^(network_isolation|process_termination|account_lockdown)$",
                             description="Action type")
    status: str = Field(..., pattern=r"^(pending|executed|failed|completed)$", description="Action status")
    execution_time: Optional[datetime] = Field(None, description="Execution timestamp")
    details: Dict[str, Any] = Field(default_factory=dict, description="Action details")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    @field_validator('action_id')
    @classmethod
    def validate_action_id(cls, v: str) -> str:
        if not re.match(r"^ACTION-\d{10}-\d{4}$", v):
            raise ValueError("Action ID must be in format: ACTION-timestamp-sequence")
        return v


class KPIReport(BaseModel):
    """KPI report model"""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Report timestamp")
    total_executions: int = Field(..., ge=0, description="Total number of executions")
    mean_mttr: float = Field(..., ge=0, description="Mean MTTR in seconds")
    median_mttr: float = Field(..., ge=0, description="Median MTTR in seconds")
    p50_mttr: float = Field(..., ge=0, description="50th percentile MTTR in seconds")
    p90_mttr: float = Field(..., ge=0, description="90th percentile MTTR in seconds")
    min_mttr: float = Field(..., ge=0, description="Minimum MTTR in seconds")
    max_mttr: float = Field(..., ge=0, description="Maximum MTTR in seconds")
    std_deviation: float = Field(..., ge=0, description="Standard deviation of MTTR")
    threshold_p50: float = Field(default=120.0, description="P50 threshold in seconds")
    threshold_p90: float = Field(default=180.0, description="P90 threshold in seconds")
    p50_within_threshold: bool = Field(..., description="Whether P50 is within threshold")
    p90_within_threshold: bool = Field(..., description="Whether P90 is within threshold")

    @model_validator(mode='after')
    def compute_threshold_compliance(self) -> 'KPIReport':
        self.p50_within_threshold = self.p50_mttr <= self.threshold_p50
        self.p90_within_threshold = self.p90_mttr <= self.threshold_p90
        return self


class HealthCheck(BaseModel):
    """Health check model"""
    service_name: str = Field(..., description="Service name")
    status: str = Field(..., pattern=r"^(healthy|unhealthy|degraded)$", description="Health status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Check timestamp")
    response_time_ms: Optional[float] = Field(None, ge=0, description="Response time in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('response_time_ms')
    @classmethod
    def validate_response_time(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v > 30000:
            raise ValueError("Response time exceeds 30 seconds")
        return v


class BackupReport(BaseModel):
    """Backup report model"""
    backup_id: str = Field(..., pattern=r"^BACKUP-\d{8}_\d{6}$", description="Backup ID")
    timestamp: datetime = Field(..., description="Backup timestamp")
    backup_type: str = Field(..., pattern=r"^(manual|scheduled|auto)$", description="Backup type")
    components: Dict[str, bool] = Field(..., description="Backup components status")
    total_size_mb: float = Field(..., ge=0, description="Total backup size in MB")
    compression_ratio: Optional[float] = Field(None, ge=0, le=1, description="Compression ratio")
    success: bool = Field(..., description="Backup success status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retention_days: int = Field(default=7, ge=1, description="Retention period in days")

    @field_validator('backup_id')
    @classmethod
    def validate_backup_id(cls, v: str) -> str:
        if not re.match(r"^BACKUP-\d{8}_\d{6}$", v):
            raise ValueError("Backup ID must be in format: BACKUP-YYYYMMDD_HHMMSS")
        return v


class SecurityScan(BaseModel):
    """Security scan report model"""
    scan_id: str = Field(..., pattern=r"^SCAN-\d{8}_\d{6}$", description="Scan ID")
    timestamp: datetime = Field(..., description="Scan timestamp")
    scanner: str = Field(..., description="Scanner name")
    target: str = Field(..., description="Scan target")
    vulnerabilities: Dict[str, int] = Field(..., description="Vulnerability counts by severity")
    total_vulnerabilities: int = Field(..., ge=0, description="Total vulnerabilities found")
    scan_duration_seconds: float = Field(..., ge=0, description="Scan duration in seconds")
    success: bool = Field(..., description="Scan success status")
    recommendations: List[str] = Field(default_factory=list, description="Security recommendations")

    @field_validator('vulnerabilities')
    @classmethod
    def validate_vulnerabilities(cls, v: Dict[str, int]) -> Dict[str, int]:
        valid_severities = {'critical', 'high', 'medium', 'low', 'info'}
        for severity, count in v.items():
            if severity not in valid_severities:
                raise ValueError(f"Invalid vulnerability severity: {severity}")
            if count < 0:
                raise ValueError(f"Vulnerability count cannot be negative for {severity}")
        return v


# Validation functions
def validate_alert_data(alert_data: Dict[str, Any]) -> tuple[bool, list]:
    """Validate alert data and return (is_valid, errors)"""
    try:
        RansomwareAlert(**alert_data)
        return True, []
    except Exception as e:
        # Extract validation errors from pydantic exception
        if hasattr(e, 'errors'):
            errors = [str(error) for error in e.errors()]
        else:
            errors = [str(e)]
        return False, errors


def validate_webhook_payload(payload_data: Dict[str, Any]) -> WebhookPayload:
    """Validate webhook payload and return validated model"""
    return WebhookPayload(**payload_data)


def validate_kpi_report(kpi_data: Dict[str, Any]) -> KPIReport:
    """Validate KPI report data and return validated model"""
    return KPIReport(**kpi_data)


def is_valid_sha256(hash_value: str) -> bool:
    """Check if SHA256 hash is valid"""
    try:
        FileHash(sha256=hash_value)
        return True
    except Exception:
        return False


def is_valid_ip_address(ip_address: str) -> bool:
    """Check if IP address is valid"""
    try:
        IPv4Address(ip_address)
        return True
    except Exception:
        return False


def is_valid_alert_id(alert_id: str) -> bool:
    """Check if alert ID is valid"""
    return bool(re.match(ALERT_ID_PATTERN, alert_id))
