"""Pydantic request and response models for the SOAR management API."""

import json
from datetime import datetime
from typing import Any

from fastapi import Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from soar_lab.common.constants import AUTH_BEARER_PREFIX, CONTENT_TYPE_JSON

__all__ = [
    "LoginRequest",
    "LoginResponse",
    "VerifyAuthResponse",
    "RunRequest",
    "BackupRequest",
    "ServiceStatus",
    "Metrics",
    "RunResults",
    "CoverageData",
    "BackupInfo",
    "BackupListResponse",
    "CreateBackupResponse",
    "RestoreBackupResponse",
    "ErrorResponse",
    "HealthResponse",
    "ContainmentRequest",
    "ContainmentResponse",
    "IocCacheRequest",
    "IocCacheResponse",
]

_ALLOWED_CATEGORIES = frozenset(
    {"unit", "integration", "e2e", "atomic", "performance", "security", "smoke", "all"}
)

_OptionalStr = str | None
_OptionalStatusField = Field(default=None, description="Operation status")
_MessageField = Field(..., description="Response message")


class LoginRequest(BaseModel):
    """Login request model.

    Contains username and password fields for authentication.
    """

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """Login response model.

    Contains the JWT token and related metadata.
    """

    token: str = Field(..., description="Authentication token")
    message: str = _MessageField
    token_type: str = Field(default=AUTH_BEARER_PREFIX, description="Token type")


class VerifyAuthResponse(BaseModel):
    """Verify authentication response model.

    Indicates whether a token is valid and includes user info.
    """

    valid: bool = Field(..., description="Whether the token is valid")
    user: dict[str, Any] = Field(..., description="User information")


class RunRequest(BaseModel):
    """Test execution request model.

    Specifies the test category to run.
    """

    category: str = Field(..., description="Test category (e.g., 'unit', 'integration', 'all')")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate that the category is one of the allowed values."""
        if v not in _ALLOWED_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(sorted(_ALLOWED_CATEGORIES))}")
        return v


class BackupRequest(BaseModel):
    """Backup request model.

    Specifies the backup file name for create or restore operations.
    """

    backup_name: str = Field(..., description="Name of the backup file to restore")

    @field_validator("backup_name")
    @classmethod
    def validate_backup_name(cls, v: str) -> str:
        """Validate the backup name against path traversal and extension rules."""
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Invalid backup name: path traversal not allowed")
        if not v.endswith(".tar.gz"):
            raise ValueError("Backup name must end with .tar.gz")
        return v


class ServiceStatus(BaseModel):
    """Service status model.

    Represents the running state of a service.
    """

    service: str = Field(..., description="Service name")
    status: bool = Field(..., description="Whether the service is running")
    url: str = Field(..., description="Service health check URL")


class Metrics(BaseModel):
    """System metrics model.

    Contains CPU, memory, and disk usage percentages.
    """

    cpu: float = Field(..., description="CPU usage percentage")
    memory: float = Field(..., description="Memory usage percentage")
    disk: float = Field(..., description="Disk usage percentage")
    timestamp: datetime = Field(..., description="Timestamp of metrics collection")


class RunResults(BaseModel):
    """Test results model.

    Contains pass/fail/skip counts and coverage info.
    """

    category: str = Field(..., description="Test category")
    passed: int = Field(..., description="Number of passed tests")
    failed: int = Field(..., description="Number of failed tests")
    skipped: int = Field(..., description="Number of skipped tests")
    coverage: float = Field(..., description="Test coverage percentage")
    output: str = Field(..., description="Test output")
    duration: float = Field(..., description="Test execution duration in seconds")


class CoverageData(BaseModel):
    """Coverage data model.

    Contains coverage percentages for different test types.
    """

    unit: float = Field(default=0.0, description="Unit test coverage")
    integration: float = Field(default=0.0, description="Integration test coverage")
    overall: float = Field(default=0.0, description="Overall coverage")


class BackupInfo(BaseModel):
    """Backup information model.

    Contains metadata about a backup file.
    """

    name: str = Field(..., description="Backup file name")
    size: str = Field(..., description="Backup file size")
    date: str = Field(..., description="Backup creation date")


class BackupListResponse(BaseModel):
    """Backup list response model.

    Contains a list of available backups.
    """

    backups: list[BackupInfo] = Field(default_factory=list, description="List of available backups")


class CreateBackupResponse(BaseModel):
    """Create backup response model.

    Contains the result of a backup creation operation.
    """

    backup_name: str = Field(..., description="Created backup name")
    status: _OptionalStr = _OptionalStatusField
    message: str = _MessageField


class RestoreBackupResponse(BaseModel):
    """Restore backup response model.

    Contains the result of a backup restore operation.
    """

    backup_name: _OptionalStr = Field(default=None, description="Restored backup name")
    status: _OptionalStr = _OptionalStatusField
    message: str = _MessageField


class ErrorResponse(BaseModel):
    """Standard error response model.

    Contains error details with code and message.
    """

    error: dict[str, str] = Field(..., description="Error details")

    @classmethod
    def create(cls, code: str, message: str, status_code: int = 500) -> JSONResponse:
        """Create a JSON error response with the given code and message.

        Args:
            code: Error code string.
            message: Human-readable error message.
            status_code: HTTP status code for the response.

        Returns:
            A FastAPI Response with JSON error content.
        """
        return Response(
            status_code=status_code,
            content=json.dumps({"error": {"code": code, "message": message}}),
            media_type=CONTENT_TYPE_JSON,
        )


class HealthResponse(BaseModel):
    """Health check response model.

    Contains service health status and version info.
    """

    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="ISO format timestamp")
    version: str = Field(..., description="API version")


class ContainmentRequest(BaseModel):
    """Request model for the simulated containment endpoint."""

    alert_id: str = Field(..., description="Alert identifier")
    case_id: str = Field(..., description="TheHive case identifier")
    hostname: str = Field(..., description="Target hostname to contain")
    mode: str = Field(default="simulated", description="Containment mode")


class ContainmentResponse(BaseModel):
    """Response model for the simulated containment endpoint."""

    status: str = Field(..., description="Containment status")
    alert_id: str = Field(..., description="Alert identifier")
    case_id: str = Field(..., description="TheHive case identifier")
    hostname: str = Field(..., description="Target hostname")
    actions: list[str] = Field(default_factory=list, description="Actions performed")
    timestamp: str = Field(..., description="ISO format timestamp")


class IocCacheRequest(BaseModel):
    """Request model for the IoC cache endpoint."""

    key: str = Field(..., description="Cache key")
    value: str = Field(..., description="Cache value")
    ttl_seconds: int | None = Field(None, description="Optional TTL in seconds")


class IocCacheResponse(BaseModel):
    """Response model for the IoC cache endpoint."""

    success: bool = Field(..., description="Whether the cache operation succeeded")
    key: str = Field(..., description="Cache key")
    message: str = Field(default="", description="Status message")
