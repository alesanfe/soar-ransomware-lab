#!/usr/bin/env python3
"""SOAR Ransomware Lab - Centralized Exception Hierarchy.

All custom exceptions used across the project.
"""

__all__ = [
    "SOARError",
    "ConfigurationError",
    "ValidationError",
    "IntegrationError",
    "IntegrationTimeoutError",
    "IntegrationAuthError",
    "IntegrationAuthorizationError",
    "IntegrationUnavailableError",
    "IntegrationRateLimitError",
    "IntegrationPayloadError",
    "RetryableError",
    "BackupError",
    "KPIError",
    "AuthError",
    "SubprocessError",
]


class SOARError(Exception):
    """Base exception for all SOAR Lab errors."""


class ConfigurationError(SOARError):
    """Raised when required configuration is missing or invalid."""


class ValidationError(SOARError):
    """Raised when input data fails validation."""


class IntegrationError(SOARError):
    """Raised when communication with an external SOAR tool fails."""

    def __init__(self, service: str, message: str) -> None:
        self.service = service
        super().__init__(f"[{service}] {message}")


class IntegrationTimeoutError(IntegrationError):
    """The integration did not answer within the configured timeout."""


class IntegrationAuthError(IntegrationError):
    """The integration rejected credentials (HTTP 401)."""


class IntegrationAuthorizationError(IntegrationError):
    """Credentials are valid but lack permission (HTTP 403)."""


class RetryableError(IntegrationError):
    """Transient failure that is safe to retry (5xx, throttling).

    Marker subclass: callers with a retry policy can check
    ``isinstance(exc, RetryableError)`` instead of guessing from status
    codes. Non-retryable failures (auth, payload) must NOT inherit this.
    """


class IntegrationUnavailableError(RetryableError):
    """The integration cannot be reached (connection/DNS refused)."""


class IntegrationRateLimitError(RetryableError):
    """The integration throttled the request (HTTP 429)."""


class IntegrationPayloadError(IntegrationError):
    """The integration answered but the payload is not usable."""


class BackupError(SOARError):
    """Raised for backup/restore operation failures."""


class KPIError(SOARError):
    """Raised for KPI calculation errors."""


class AuthError(SOARError):
    """Raised for authentication/authorisation errors."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        self.status_code = status_code
        super().__init__(message)


class SubprocessError(SOARError):
    """Raised when a subprocess command fails."""

    def __init__(self, cmd: list[str], returncode: int, stderr: str = "") -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Command {cmd[0]!r} exited with code {returncode}: {stderr}")
