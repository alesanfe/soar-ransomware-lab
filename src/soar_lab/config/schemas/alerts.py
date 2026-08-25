"""Ransomware alert Pydantic model."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic.networks import IPv4Address

from soar_lab.common.constants import ALERT_ID_PATTERN
from soar_lab.config.schemas.enums import SeverityLevel
from soar_lab.config.schemas.files import AffectedFile
from soar_lab.config.schemas.hashes import FileHash, NetworkEvent

__all__ = ["RansomwareAlert"]


class RansomwareAlert(BaseModel):
    """Ransomware detection alert model."""

    alert_id: str = Field(
        ..., pattern=ALERT_ID_PATTERN, description="Alert ID format: ALERT-timestamp-sequence"
    )
    hostname: str = Field(
        ..., min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9\-]+$", description="Hostname"
    )
    src_ip: IPv4Address = Field(..., description="Source IP address")
    hash: FileHash = Field(..., description="File hash information")
    severity: SeverityLevel = Field(..., description="Alert severity")
    source: str = Field(..., min_length=1, max_length=100, description="Alert source")
    detection_time: datetime = Field(..., description="Detection timestamp")
    event_type: str = Field(..., pattern=r"^ransomware_detection$", description="Event type")
    description: str = Field(..., min_length=1, max_length=1000, description="Alert description")
    affected_files: list[AffectedFile] = Field(default_factory=list, description="Affected files")
    mitre_tactics: list[str] = Field(default_factory=list, description="MITRE tactics")
    mitre_techniques: list[str] = Field(default_factory=list, description="MITRE techniques")
    network_events: list[NetworkEvent] = Field(default_factory=list, description="Network events")
    user_context: dict[str, Any] | None = Field(None, description="User context information")
    process_info: dict[str, Any] | None = Field(None, description="Process information")

    @field_validator("detection_time")
    @classmethod
    def validate_detection_time(cls, v: datetime) -> datetime:
        """Validate that the detection time is not in the future."""
        now = datetime.now(UTC)
        v_aware = v if v.tzinfo is not None else v.replace(tzinfo=UTC)
        if v_aware > now:
            raise ValueError("Detection time cannot be in the future")
        return v
