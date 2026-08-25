"""SOAR Ransomware Lab - Pydantic Schemas package.

Data validation models using Pydantic for type safety and validation.
Re-exports all models and validators from submodules for backward compatibility.
"""

from soar_lab.common.constants import ALERT_ID_PATTERN
from soar_lab.config.schemas.actions import ContainmentAction
from soar_lab.config.schemas.alerts import RansomwareAlert
from soar_lab.config.schemas.backup import BackupReport
from soar_lab.config.schemas.enums import AlertType, SeverityLevel
from soar_lab.config.schemas.files import AffectedFile
from soar_lab.config.schemas.hashes import FileHash, NetworkEvent
from soar_lab.config.schemas.health import HealthCheck
from soar_lab.config.schemas.kpi import KPIReport
from soar_lab.config.schemas.mitre import MITREInfo
from soar_lab.config.schemas.security import SecurityScan
from soar_lab.config.schemas.validators import (
    is_valid_alert_id,
    is_valid_ip_address,
    is_valid_sha256,
    validate_alert_data,
    validate_kpi_report,
    validate_webhook_payload,
)
from soar_lab.config.schemas.webhook import WebhookPayload

__all__ = [
    "ALERT_ID_PATTERN",
    "SeverityLevel",
    "AlertType",
    "NetworkEvent",
    "FileHash",
    "MITREInfo",
    "AffectedFile",
    "RansomwareAlert",
    "WebhookPayload",
    "ContainmentAction",
    "KPIReport",
    "HealthCheck",
    "BackupReport",
    "SecurityScan",
    "validate_alert_data",
    "validate_webhook_payload",
    "validate_kpi_report",
    "is_valid_sha256",
    "is_valid_ip_address",
    "is_valid_alert_id",
]
