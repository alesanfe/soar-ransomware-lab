"""ERROR-001/002: centralized redaction policy for logs, metrics and state.

One utility applied everywhere a string can escape into logs, metrics,
audit entries, admission ``last_error``, DLQ reasons or HTTP responses.
It strips capability URLs (``webhook_<id>``), bearer/service tokens,
signatures, nonces and query strings — diagnostics keep codes and host
names, never secrets.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = [
    "redact_text",
    "redact_url",
    "safe_error",
    "LOG_SAFE_REPLACEMENT",
]

LOG_SAFE_REPLACEMENT = "[redacted]"

# Shuffle hook capability URL + query strings
_HOOK_PATH_RE = re.compile(r"/api/v1/hooks/webhook_[0-9a-zA-Z_-]+", re.IGNORECASE)
_QUERY_RE = re.compile(r"\?[^\s\"']+")
# Secrets material that must never appear in any text sink
_SECRET_KV_RE = re.compile(
    r"(?i)(authorization|x-service-token|x-soar-signature|x-api-key|api[_-]?key|"
    r"token|secret|password|passwd|nonce|signature|credential)"
    r"([\s\"'=:\[\{]*)([^\s,\"'\]\}]+)"
)
_BEARER_RE = re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]{8,}")
_HEX_BLOB_RE = re.compile(r"\b[0-9a-f]{40,}\b", re.IGNORECASE)


def redact_text(text: Any, max_len: int = 200) -> str:
    """Redact secrets/capability URLs from arbitrary text for safe output."""
    if text is None:
        return ""
    s = str(text)
    s = _HOOK_PATH_RE.sub("/api/v1/hooks/[redacted]", s)
    s = _BEARER_RE.sub("Bearer [redacted]", s)
    s = _SECRET_KV_RE.sub(lambda m: f"{m.group(1)}{m.group(2) or '='}[redacted]", s)
    s = _HEX_BLOB_RE.sub("[redacted-hex]", s)
    s = _QUERY_RE.sub("?[redacted]", s)
    # strip control chars so redacted text cannot smuggle log forging
    s = re.sub(r"[\x00-\x1f\x7f]", " ", s)
    if len(s) > max_len:
        s = s[:max_len] + "…"
    return s


def redact_url(url: str) -> str:
    """Return scheme://host[:port] only — never path/query/capability ids."""
    from urllib.parse import urlsplit

    try:
        parts = urlsplit(url)
        host = parts.hostname or "unknown"
        port = f":{parts.port}" if parts.port else ""
        scheme = parts.scheme or "http"
        return f"{scheme}://{host}{port}"
    except Exception:
        return "[redacted-url]"


def safe_error(
    exc: BaseException | str | None,
    *,
    code: str,
    retryable: bool,
    destination: str = "downstream",
) -> dict[str, Any]:
    """Structured, redacted error payload for admission records/metrics.

    Returns ``{code, destination, retryable, message}`` — ``message``
    is a sanitized short string with no URL/capability material.
    """
    raw = "" if exc is None else str(exc)
    msg = redact_text(raw, max_len=160) or code.lower()
    return {
        "code": code,
        "destination": destination,
        "retryable": retryable,
        "message": msg,
    }
