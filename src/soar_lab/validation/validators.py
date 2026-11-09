#!/usr/bin/env python3
"""SOAR Ransomware Lab - Centralized Validators.

Single source of truth for IP, hash, alert and path validation.
"""

import ipaddress
import re
from pathlib import Path
from typing import Any

from soar_lab.common.exceptions import ValidationError
from soar_lab.domain.models import AlertSeverity

__all__ = [
    "IPValidator",
    "HashValidator",
    "AlertValidator",
    "PathValidator",
]


class IPValidator:
    """Validates IPv4 and IPv6 addresses (CFG-048).

    Uses the stdlib ``ipaddress`` module instead of a regex — zone IDs
    (``fe80::1%eth0``) and compressed forms are handled correctly.
    """

    @staticmethod
    def validate(ip: Any) -> bool:
        """Return True if *ip* is a valid IPv4 or IPv6 address string."""
        if not ip or not isinstance(ip, str):
            return False
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return False
        return True

    @classmethod
    def assert_valid(cls, ip: str) -> None:
        if not cls.validate(ip):
            raise ValidationError(f"Invalid IP address: {ip!r}")


class HashValidator:
    """Validates MD5 / SHA-1 / SHA-256 hex digest strings."""

    _HASH_RE = re.compile(r"^(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{40}|[a-fA-F0-9]{64})$")

    @staticmethod
    def validate(hash_value: Any) -> bool:
        """Return True for valid MD5 (32), SHA-1 (40) or SHA-256 (64) hex.

        strings.
        """
        # An all-decimal string is a perfectly valid hex digest — the old
        # ``isdigit()`` exclusion rejected real hashes.
        return (
            hash_value is not None
            and isinstance(hash_value, str)
            and bool(HashValidator._HASH_RE.match(hash_value))
        )

    @classmethod
    def assert_valid(cls, hash_value: str) -> None:
        if not cls.validate(hash_value):
            raise ValidationError(f"Invalid hash: {hash_value!r}")


class AlertValidator:
    """Validates alert payloads."""

    REQUIRED_FIELDS = ("alert_id", "hostname", "hash", "src_ip", "timestamp")
    FULL_REQUIRED_FIELDS = ("alert_id", "hostname", "src_ip", "hash", "severity", "event_type")
    # CFG-002: derive from the canonical domain enum — the old tuple
    # accepted 0 (contract violation) and rejected 4 (CRITICAL).
    VALID_SEVERITIES = tuple(s.value for s in AlertSeverity)
    HOSTNAME_RE = re.compile(r"^.{1,255}$", re.UNICODE)

    @classmethod
    def _is_valid_hostname(cls, hostname: Any) -> bool:
        """Return True for a non-empty hostname up to 255 chars."""
        return (
            bool(hostname)
            and isinstance(hostname, str)
            and len(hostname) <= 255
            and cls.HOSTNAME_RE.match(hostname) is not None
        )

    @classmethod
    def validate(cls, alert: Any) -> bool:
        """Basic validation: required fields, valid IP and hash."""
        return (
            bool(alert)
            and isinstance(alert, dict)
            and all(alert.get(field) for field in cls.REQUIRED_FIELDS)
            and IPValidator.validate(alert["src_ip"])
            and HashValidator.validate(alert["hash"])
        )

    @classmethod
    def _check_required_fields(cls, alert: Any) -> bool:
        """Return True if all FULL_REQUIRED_FIELDS are present and non-empty."""
        return all(alert.get(field) not in (None, "") for field in cls.FULL_REQUIRED_FIELDS)

    @classmethod
    def _check_severity(cls, alert: Any) -> bool:
        """Return True if the alert's severity is a valid integer value."""
        try:
            return int(alert["severity"]) in cls.VALID_SEVERITIES
        except (ValueError, TypeError):
            return False

    @classmethod
    def validate_structure(cls, alert: Any) -> bool:
        """Full structural validation including severity and hostname."""
        return (
            bool(alert)
            and isinstance(alert, dict)
            and cls._check_required_fields(alert)
            and cls._is_valid_hostname(alert.get("hostname"))
            and cls._check_severity(alert)
            and IPValidator.validate(alert["src_ip"])
            and HashValidator.validate(alert["hash"])
        )

    @classmethod
    def assert_valid(cls, alert: dict) -> None:
        if not cls.validate(alert):
            raise ValidationError("Alert failed validation")


class PathValidator:
    """Validates file-system paths to prevent traversal attacks."""

    FORBIDDEN_PREFIXES = ("/etc/", "/usr/", "/bin/", "/sbin/", "c:/windows/")

    @staticmethod
    def validate(path: Any) -> bool:
        """Return True if path is safe (no traversal, not in system dirs)."""
        if path is None or ".." in (p := Path(str(path))).parts:
            return False
        resolved = str(p.resolve()).replace("\\", "/").lower()
        return not any(resolved.startswith(f) for f in PathValidator.FORBIDDEN_PREFIXES)

    @classmethod
    def assert_valid(cls, path: Any) -> None:
        if not cls.validate(path):
            raise ValidationError(f"Invalid or unsafe path: {path!r}")
