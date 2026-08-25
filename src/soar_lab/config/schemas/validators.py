"""Standalone validation helper functions."""

import re
from typing import Any

from pydantic import ValidationError
from pydantic.networks import IPv4Address

from soar_lab.common.constants import ALERT_ID_PATTERN
from soar_lab.config.schemas.alerts import RansomwareAlert
from soar_lab.config.schemas.hashes import FileHash
from soar_lab.config.schemas.kpi import KPIReport
from soar_lab.config.schemas.webhook import WebhookPayload

__all__ = [
    "validate_alert_data",
    "validate_webhook_payload",
    "validate_kpi_report",
    "is_valid_sha256",
    "is_valid_ip_address",
    "is_valid_alert_id",
]


def validate_alert_data(alert_data: dict[str, Any]) -> tuple[bool, list]:
    """Validate alert data and return (is_valid, errors)."""
    try:
        RansomwareAlert(**alert_data)
        return True, []
    except ValidationError as e:
        return False, [str(err) for err in e.errors()]
    except Exception as e:
        return False, [str(e)]


def validate_webhook_payload(payload_data: dict[str, Any]) -> WebhookPayload:
    """Validate webhook payload and return validated model."""
    return WebhookPayload(**payload_data)


def validate_kpi_report(kpi_data: dict[str, Any]) -> KPIReport:
    """Validate KPI report data and return validated model."""
    return KPIReport(**kpi_data)


def is_valid_sha256(hash_value: str) -> bool:
    """Check if SHA256 hash is valid."""
    try:
        FileHash(sha256=hash_value)
        return True
    except Exception:
        return False


def is_valid_ip_address(ip_address: str) -> bool:
    """Check if IP address is valid."""
    try:
        IPv4Address(ip_address)
        return True
    except Exception:
        return False


def is_valid_alert_id(alert_id: str) -> bool:
    """Check if alert ID is valid."""
    return bool(re.match(ALERT_ID_PATTERN, alert_id))
