"""Payload sanitization helpers for alert and webhook data."""

import base64
import json
import re
import unicodedata
from datetime import datetime
from typing import Any

from soar_lab.common.constants import DEFAULT_SANITIZATION_MAX_LENGTH

__all__ = ["PayloadSanitizer"]


class PayloadSanitizer:
    """Sanitize alert/webhook payloads before sending them to external.

    systems.
    """

    # Default expected types for validate_types
    EXPECTED_TYPES: dict[str, Any] = {
        "alert_id": str,
        "severity": int,
        "timestamp": str,
    }

    # Substrings/patterns removed by sanitize_string
    _SCRIPT_TAG_RE = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
    _ON_EVENT_RE = re.compile(r"\son\w+\s*=\s*['\"]?[^'\"\s>]+", re.IGNORECASE)
    _DROP_TABLE_RE = re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE)
    _JS_PROTOCOL_RE = re.compile(r"javascript:", re.IGNORECASE)
    _NULL_BYTE_RE = re.compile(r"\x00")
    _CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

    def sanitize(
        self,
        payload: Any,
        whitelist: list[str] | None = None,
        blacklist: list[str] | None = None,
        max_length: int = DEFAULT_SANITIZATION_MAX_LENGTH,
    ) -> Any:
        """Recursively sanitize a payload."""
        if isinstance(payload, dict):
            result: dict[str, Any] = {}
            for key, value in payload.items():
                if whitelist is not None and key not in whitelist:
                    continue
                if blacklist is not None and key in blacklist:
                    continue
                result[key] = self.sanitize(value, whitelist, blacklist, max_length)
            return result
        if isinstance(payload, list):
            return [self.sanitize(item, whitelist, blacklist, max_length) for item in payload]
        if isinstance(payload, str):
            return self._sanitize_string(payload, max_length)
        return payload

    def _sanitize_string(
        self, value: str, max_length: int = DEFAULT_SANITIZATION_MAX_LENGTH
    ) -> str:
        value = self._NULL_BYTE_RE.sub("", value)
        value = self._CONTROL_RE.sub("", value)
        value = unicodedata.normalize("NFKC", value)
        value = self._SCRIPT_TAG_RE.sub("", value)
        value = self._DROP_TABLE_RE.sub("", value)
        value = self._ON_EVENT_RE.sub("", value)
        value = self._JS_PROTOCOL_RE.sub("", value)
        if len(value) > max_length:
            value = value[:max_length]
        return value

    def sanitize_html(self, html: str, max_length: int = DEFAULT_SANITIZATION_MAX_LENGTH) -> str:
        """Remove script tags and dangerous handlers while keeping safe.

        HTML.
        """
        html = self._SCRIPT_TAG_RE.sub("", html)
        html = self._ON_EVENT_RE.sub("", html)
        html = unicodedata.normalize("NFKC", html)
        if len(html) > max_length:
            html = html[:max_length]
        return html

    def sanitize_js(self, value: str, max_length: int = DEFAULT_SANITIZATION_MAX_LENGTH) -> str:
        """Remove javascript: protocol and event handlers."""
        value = self._JS_PROTOCOL_RE.sub("", value)
        value = self._ON_EVENT_RE.sub("", value)
        if len(value) > max_length:
            value = value[:max_length]
        return value

    def encode(self, data: Any) -> str:
        """Encode a payload as a base64 JSON string."""
        return base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")

    def decode(self, encoded: str) -> Any:
        """Decode a base64 JSON string."""
        return json.loads(base64.b64decode(encoded.encode("utf-8")).decode("utf-8"))

    def validate_types(self, payload: dict[str, Any]) -> bool:
        """Validate that payload fields match expected types."""
        if not isinstance(payload, dict):
            return False
        for field, expected in self.EXPECTED_TYPES.items():
            value = payload.get(field)
            if value is None:
                continue
            if expected is int:
                if isinstance(value, bool) or not isinstance(value, int):
                    return False
            elif expected is str:
                if not isinstance(value, str):
                    return False
                if field == "timestamp":
                    try:
                        datetime.fromisoformat(value)
                    except ValueError:
                        return False
        return True
