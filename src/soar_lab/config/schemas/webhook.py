"""Webhook payload Pydantic model."""

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from soar_lab.config.schemas.alerts import RansomwareAlert

__all__ = ["WebhookPayload"]

_VERSION_PATTERN = re.compile(r"^\d+\.\d+$")


class WebhookPayload(BaseModel):
    """Webhook payload model."""

    alert: RansomwareAlert = Field(..., description="Ransomware alert")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Payload timestamp"
    )
    version: str = Field(default="1.0", description="Payload version")

    @field_validator("version")
    @classmethod
    def _validate_version(cls, v: str) -> str:
        if not _VERSION_PATTERN.match(v):
            raise ValueError("Version must be in format 'X.Y' (e.g. '1.0')")
        return v
