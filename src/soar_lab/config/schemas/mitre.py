"""MITRE ATT&CK information Pydantic model."""

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

__all__ = ["MITREInfo"]

_VALID_MITRE_TACTICS = frozenset(
    {
        "TA0001",
        "TA0002",
        "TA0003",
        "TA0004",
        "TA0005",
        "TA0006",
        "TA0007",
        "TA0008",
        "TA0009",
        "TA0010",
        "TA0011",
        "TA0040",
        "TA0042",
        "TA0043",
    }
)
_MITRE_TECHNIQUE_RE = r"^T\d{4}(\.\d{3})?$"


def _normalize_technique(item: Any) -> Any:
    """Normalize a single MITRE technique entry (string or dict)."""
    if isinstance(item, dict):
        tech_id = item.get("id", "")
        if not re.match(_MITRE_TECHNIQUE_RE, tech_id):
            raise ValueError(f"Invalid MITRE technique ID: {tech_id}")
        return item
    if isinstance(item, str):
        if not re.match(_MITRE_TECHNIQUE_RE, item):
            raise ValueError(f"Invalid MITRE technique ID: {item}")
        return item
    raise ValueError(f"MITRE technique must be string or dict, got {type(item)}")


class MITREInfo(BaseModel):
    """MITRE ATT&CK information."""

    tactics: list[str] = Field(default_factory=list, description="MITRE tactics")
    techniques: list[Any] = Field(default_factory=list, description="MITRE techniques")
    sub_techniques: list[str] = Field(default_factory=list, description="MITRE sub-techniques")

    @field_validator("tactics")
    @classmethod
    def validate_tactics(cls, v: list[str]) -> list[str]:
        """Validate that all tactics are recognized MITRE ATT&CK tactic IDs."""
        for tactic in v:
            if tactic not in _VALID_MITRE_TACTICS:
                raise ValueError(f"Invalid MITRE tactic: {tactic}")
        return v

    @field_validator("techniques")
    @classmethod
    def validate_techniques(cls, v: list[Any]) -> list[Any]:
        """Validate and normalize MITRE technique entries (string or dict)."""
        return [_normalize_technique(item) for item in v]
