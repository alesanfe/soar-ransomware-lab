"""Health check Pydantic model."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

__all__ = ["HealthCheck"]


class HealthCheck(BaseModel):
    """Health check model."""

    service_name: str = Field(..., description="Service name")
    status: str = Field(..., pattern=r"^(healthy|unhealthy|degraded)$", description="Health status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Check timestamp"
    )
    response_time_ms: float | None = Field(None, ge=0, description="Response time in milliseconds")
    error_message: str | None = Field(None, description="Error message if unhealthy")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("response_time_ms")
    @classmethod
    def validate_response_time(cls, v: float | None) -> float | None:
        """Validate that the response time does not exceed 30 seconds."""
        if v is not None and v > 30000:
            raise ValueError("Response time exceeds 30 seconds")
        return v
