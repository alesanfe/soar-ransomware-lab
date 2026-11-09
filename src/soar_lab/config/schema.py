"""Typed configuration schema (C2 — pydantic validation at boot).

``Settings._load_config()`` merges per-section fragments into one dict.
This module validates that merged dict once at construction: numeric
fields get range constraints and booleans get real types, so a bad
``API_PORT=99999`` or ``MAX_CONCURRENT_ANALYZERS=-1`` fails at boot with
a field-level error instead of degrading silently at runtime.

Only the risky numeric/boolean keys are modelled — free-form strings,
URLs and secrets stay ``extra='allow'`` passthrough.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConfigSchema(BaseModel):
    """Constraints for the risky numeric/bool keys of the config dict."""

    model_config = ConfigDict(extra="allow")

    api_port: int = Field(ge=1, le=65535)
    thehive_port: int = Field(ge=1, le=65535)
    cortex_port: int = Field(ge=1, le=65535)
    shuffle_ui_port: int = Field(ge=1, le=65535)
    shuffle_api_port: int = Field(ge=1, le=65535)
    elasticsearch_port: int = Field(ge=1, le=65535)
    misp_port: int = Field(ge=1, le=65535)
    http_port: int = Field(ge=1, le=65535)
    jwt_expiration_minutes: int = Field(gt=0)
    decision_score_threshold: int = Field(ge=0, le=100)
    max_concurrent_analyzers: int = Field(gt=0)
    analyzer_timeout: int = Field(gt=0)
    analyzer_retries: int = Field(ge=0)
    webhook_rate_limit: int = Field(gt=0)
    webhook_payload_max_size: int = Field(gt=0)
    health_check_retries: int = Field(ge=0)
    retention_days: int = Field(gt=0)
    compress_backups: bool
    elastic_security_enabled: bool
    environment: str = "development"

    @field_validator("environment")
    @classmethod
    def _known_environment(cls, v: str) -> str:
        allowed = {"development", "dev", "test", "staging", "production", "prod"}
        if v.lower() not in allowed:
            raise ValueError(f"unknown SOAR_ENV {v!r} — expected one of {sorted(allowed)}")
        return v.lower()


def validate_config_dict(config: dict[str, Any]) -> ConfigSchema:
    """Validate the merged config dict; returns the parsed schema."""
    return ConfigSchema.model_validate(config)
