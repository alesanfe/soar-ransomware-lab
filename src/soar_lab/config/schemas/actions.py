"""Containment action Pydantic model."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from soar_lab.common.constants import ALERT_ID_PATTERN

__all__ = ["ContainmentAction"]


class ContainmentAction(BaseModel):
    """Containment action model."""

    action_id: str = Field(..., pattern=r"^ACTION-\d{10}-\d{4}$", description="Action ID")
    alert_id: str = Field(..., pattern=ALERT_ID_PATTERN, description="Related alert ID")
    hostname: str = Field(..., description="Target hostname")
    action_type: str = Field(
        ...,
        pattern=r"^(network_isolation|process_termination|account_lockdown)$",
        description="Action type",
    )
    status: str = Field(
        ..., pattern=r"^(pending|executed|failed|completed)$", description="Action status"
    )
    execution_time: datetime | None = Field(None, description="Execution timestamp")
    details: dict[str, Any] = Field(default_factory=dict, description="Action details")
    error_message: str | None = Field(None, description="Error message if failed")
