#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Centralized Validators
Single source of truth for IP, hash, alert and path validation.
"""

import re
from pathlib import Path
from typing import Any, Dict

from soar_lab.exceptions import ValidationError


class IPValidator:
    """Validates IPv4 addresses."""

    _IPV4_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")

    @staticmethod
    def validate(ip: Any) -> bool:
        """Return True if *ip* is a valid IPv4 address string."""
        if not ip or not isinstance(ip, str):
            return False
        m = IPValidator._IPV4_RE.match(ip)
        if not m:
            return False
        return all(0 <= int(g) <= 255 for g in m.groups())

    @classmethod
    def assert_valid(cls, ip: str) -> None:
        if not cls.validate(ip):
            raise ValidationError(f"Invalid IPv4 address: {ip!r}")


class HashValidator:
    """Validates MD5 / SHA-1 / SHA-256 hex digest strings."""

    _HASH_RE = re.compile(
        r"^(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{40}|[a-fA-F0-9]{64})$"
    )

    @staticmethod
    def validate(hash_value: Any) -> bool:
        """Return True for valid MD5 (32), SHA-1 (40) or SHA-256 (64) hex strings."""
        if hash_value is None or not isinstance(hash_value, str):
            return False
        if not HashValidator._HASH_RE.match(hash_value):
            return False
        if hash_value.isdigit():
            return False
        return True

    @classmethod
    def assert_valid(cls, hash_value: str) -> None:
        if not cls.validate(hash_value):
            raise ValidationError(f"Invalid hash: {hash_value!r}")


class AlertValidator:
    """Validates alert payloads."""

    REQUIRED_FIELDS = ("alert_id", "hostname", "hash", "src_ip", "timestamp")
    FULL_REQUIRED_FIELDS = (
        "alert_id", "hostname", "src_ip", "hash", "severity", "event_type"
    )
    VALID_SEVERITIES = (0, 1, 2, 3)

    @classmethod
    def validate(cls, alert: Any) -> bool:
        """Basic validation: required fields, valid IP and hash."""
        if not alert or not isinstance(alert, dict):
            return False
        for field in cls.REQUIRED_FIELDS:
            if not alert.get(field):
                return False
        return (
                IPValidator.validate(alert["src_ip"])
                and HashValidator.validate(alert["hash"])
        )

    @classmethod
    def validate_structure(cls, alert: Any) -> bool:
        """Full structural validation including severity."""
        if not alert or not isinstance(alert, dict):
            return False
        for field in cls.FULL_REQUIRED_FIELDS:
            if field not in alert:
                return False
        try:
            severity = int(alert["severity"])
        except (ValueError, TypeError):
            return False
        if severity not in cls.VALID_SEVERITIES:
            return False
        return (
                IPValidator.validate(alert["src_ip"])
                and HashValidator.validate(alert["hash"])
        )

    @classmethod
    def assert_valid(cls, alert: Dict) -> None:
        if not cls.validate(alert):
            raise ValidationError("Alert failed validation")


class PathValidator:
    """Validates file-system paths to prevent traversal attacks."""

    FORBIDDEN_PREFIXES = ("/etc/", "/usr/", "/bin/", "/sbin/", "C:\\Windows\\")

    @staticmethod
    def validate(path: Any) -> bool:
        """Return True if path is safe (no traversal, not in system dirs)."""
        if path is None:
            return False
        p = Path(str(path))
        if ".." in p.parts:
            return False
        resolved = str(p.resolve()).replace("\\", "/").lower()
        forbidden = (
            "/etc/", "/usr/", "/bin/", "/sbin/", "c:/windows/"
        )
        return not any(resolved.startswith(f) for f in forbidden)

    @classmethod
    def assert_valid(cls, path: Any) -> None:
        if not cls.validate(path):
            raise ValidationError(f"Invalid or unsafe path: {path!r}")
