"""Alert type enumeration.

CFG-001: ``SeverityLevel`` (base-0 strings) was removed — the canonical
severity enum is ``soar_lab.domain.models.AlertSeverity`` (IntEnum 1-4,
TheHive/MISP scale). Import it from there.
"""

from enum import Enum

__all__ = ["AlertType"]


class AlertType(str, Enum):
    """Alert types."""

    MALICIOUS = "malicious"
    BENIGN = "benign"
    SUSPICIOUS = "suspicious"
