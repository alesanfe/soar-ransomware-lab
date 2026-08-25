"""Alert severity and type enumerations."""

from enum import Enum

__all__ = ["SeverityLevel", "AlertType"]


class SeverityLevel(str, Enum):
    """Alert severity levels."""

    LOW = "0"
    MEDIUM = "1"
    HIGH = "2"
    CRITICAL = "3"


class AlertType(str, Enum):
    """Alert types."""

    MALICIOUS = "malicious"
    BENIGN = "benign"
    SUSPICIOUS = "suspicious"
