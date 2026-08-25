"""KPI report Pydantic model."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator

__all__ = ["KPIReport"]


class KPIReport(BaseModel):
    """KPI report model."""

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Report timestamp"
    )
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

    @model_validator(mode="after")
    def compute_threshold_compliance(self) -> "KPIReport":
        """Compute whether P50 and P90 MTTR values are within their thresholds."""
        self.p50_within_threshold = self.p50_mttr <= self.threshold_p50
        self.p90_within_threshold = self.p90_mttr <= self.threshold_p90
        return self
