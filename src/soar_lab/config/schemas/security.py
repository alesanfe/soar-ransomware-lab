"""Security scan Pydantic model."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

__all__ = ["SecurityScan"]

_VALID_SEVERITIES = frozenset({"critical", "high", "medium", "low", "info"})


class SecurityScan(BaseModel):
    """Security scan report model."""

    scan_id: str = Field(..., pattern=r"^SCAN-\d{8}_\d{6}$", description="Scan ID")
    timestamp: datetime = Field(..., description="Scan timestamp")
    scanner: str = Field(..., description="Scanner name")
    target: str = Field(..., description="Scan target")
    vulnerabilities: dict[str, int] = Field(..., description="Vulnerability counts by severity")
    total_vulnerabilities: int = Field(..., ge=0, description="Total vulnerabilities found")
    scan_duration_seconds: float = Field(..., ge=0, description="Scan duration in seconds")
    success: bool = Field(..., description="Scan success status")
    recommendations: list[str] = Field(default_factory=list, description="Security recommendations")

    @field_validator("vulnerabilities")
    @classmethod
    def validate_vulnerabilities(cls, v: dict[str, int]) -> dict[str, int]:
        """Validate vulnerability severity keys and non-negative counts."""
        for severity, count in v.items():
            if severity not in _VALID_SEVERITIES:
                raise ValueError(f"Invalid vulnerability severity: {severity}")
            if count < 0:
                raise ValueError(f"Vulnerability count cannot be negative for {severity}")
        return v
