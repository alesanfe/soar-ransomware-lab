#!/usr/bin/env python3
"""SOAR Ransomware Lab - Centralized Exception Hierarchy.

All custom exceptions used across the project.
"""

__all__ = [
    "SOARError",
    "ConfigurationError",
    "ValidationError",
    "IntegrationError",
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

    def __init__(self, cmd: list, returncode: int, stderr: str = "") -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Command {cmd[0]!r} exited with code {returncode}: {stderr}")
