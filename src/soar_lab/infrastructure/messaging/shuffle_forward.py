"""PERF-001 + HMAC-002: forward admitted alerts to the Shuffle webhook.

Resolves the downstream webhook URL (config > webhook_info.json > default),
wraps the alert in the CONTRACT-003 envelope (schema_version, event_id,
delivery_id, attempt, payload) and embeds an HMAC-SHA256 ``security``
block (body-level signature — Shuffle hooks do not expose HTTP headers
to the workflow, so the signature travels inside the JSON itself).

Errors are STRUCTURED (``error_code``/``retryable``) — the raw exception
text never leaves this module, so the capability URL can no longer leak
into ``last_error``, metrics or logs (ERROR-001/B6).
"""

from __future__ import annotations

import ipaddress
import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests

from soar_lab.common.constants import SHUFFLE_WEBHOOK_DEFAULT, WEBHOOK_INFO_PATHS
from soar_lab.common.ids import new_id
from soar_lab.infrastructure.http_client import AioHTTPClient
from soar_lab.security.redaction import redact_url
from soar_lab.security.webhook_signing import sign_envelope

logger = logging.getLogger(__name__)

CONTRACT_VERSION = "1.0"

# INPUT-005: destination allowlist — only these schemes are ever valid.
_ALLOWED_SCHEMES = {"http", "https"}


class DestinationPolicyError(ValueError):
    """Forward target violates the egress policy (INPUT-005)."""


def _validate_target(url: str, allowed_hosts: set[str] | None) -> str:
    """Egress policy: scheme allowlist + optional host allowlist.

    ``allowed_hosts`` empty/None = lab default (any resolvable host,
    still no credentials-in-URL). In hardened deployments set
    ``ALERT_INGEST_ALLOWED_HOSTS=shuffle-backend``.
    """
    try:
        parts = urlsplit(url)
    except ValueError as exc:
        raise DestinationPolicyError(f"malformed forward URL: {exc}") from exc
    if parts.scheme not in _ALLOWED_SCHEMES:
        raise DestinationPolicyError(f"scheme {parts.scheme!r} not allowed")
    if parts.username or parts.password:
        raise DestinationPolicyError("credentials in forward URL are forbidden")
    host = parts.hostname or ""
    if allowed_hosts and host not in allowed_hosts:
        raise DestinationPolicyError(f"host {host!r} not in forward allowlist")
    return url


def resolve_target_url(config_provider: Any) -> str:
    """Resolve the Shuffle webhook URL for the in-container context."""
    url = config_provider.get("ALERT_INGEST_TARGET_URL") or config_provider.get(
        "SHUFFLE_WEBHOOK_URL"
    )
    if url:
        return url
    for candidate in WEBHOOK_INFO_PATHS:
        path = Path(candidate)
        if path.exists():
            try:
                info = json.loads(path.read_text(encoding="utf-8"))
                url = info.get("webhook_url") or info.get("webhook_url_host")
                if url:
                    return url
            except Exception:
                continue
    logger.warning("No webhook_info.json found — falling back to default webhook URL")
    return SHUFFLE_WEBHOOK_DEFAULT


def _classify(status: int | None, exc: BaseException | None) -> dict[str, Any]:
    """WORKER-004 retry policy by error class — no secrets, no URLs."""
    if exc is not None:
        if isinstance(exc, (requests.Timeout,)):
            return {"error_code": "DOWNSTREAM_TIMEOUT", "retryable": True}
        if isinstance(exc, (requests.ConnectionError,)):
            return {"error_code": "DOWNSTREAM_UNAVAILABLE", "retryable": True}
        return {"error_code": "FORWARD_ERROR", "retryable": True}
    if status is None:
        return {"error_code": "FORWARD_ERROR", "retryable": True}
    if status == 429:
        return {"error_code": "DOWNSTREAM_RATE_LIMITED", "retryable": True}
    if status >= 500:
        return {"error_code": "DOWNSTREAM_5XX", "retryable": True}
    if status in (400, 401, 403, 404, 422):
        return {"error_code": "DOWNSTREAM_REJECTED", "retryable": False}
    if 200 <= status < 300:
        return {"error_code": None, "retryable": False}
    return {"error_code": f"DOWNSTREAM_HTTP_{status}", "retryable": False}


def make_shuffle_forward(
    config_provider: Any,
    timeout_s: float = 30.0,
    http_client: Any = None,
):
    """Build an async ``forward(alert) -> {ok, exec_id, status_code, ...}``.

    Signs each delivery with ``ALERT_SIGNING_KEY`` (envelope HMAC); when
    unset the alert is forwarded unsigned and the workflow falls back to
    its documented no-signature mode (lab transition compatibility —
    set the key to close it).
    """
    raw_hosts = str(config_provider.get("ALERT_INGEST_ALLOWED_HOSTS") or "").strip()
    allowed_hosts = {h.strip() for h in raw_hosts.split(",") if h.strip()} or None
    target = _validate_target(resolve_target_url(config_provider), allowed_hosts)
    signing_key = str(config_provider.get("ALERT_SIGNING_KEY") or "")
    key_id = str(config_provider.get("ALERT_SIGNING_KEY_ID") or "api-forward-1")
    logger.info("Admission worker forwards alerts to %s", redact_url(target))
    owned = http_client is None
    state: dict[str, Any] = {"client": http_client, "closed": False}

    async def _client() -> Any:
        client = state["client"]
        if client is None or (owned and state["closed"]):
            client = AioHTTPClient(default_timeout=int(timeout_s))
            state["client"] = client
            state["closed"] = False
        return client

    async def aclose() -> None:
        if state["closed"]:
            return
        state["closed"] = True
        client = state["client"]
        if client is not None:
            await client.close()

    async def forward(alert: dict[str, Any]) -> dict[str, Any]:
        # CONTRACT-003 + IDEMP-001: versioned envelope carrying logical
        # identity (event_id), transport attempt (delivery_id/attempt)
        # and the dedup key inside the BODY (Shuffle ignores headers).
        envelope: dict[str, Any] = {
            "schema_version": CONTRACT_VERSION,
            "event_id": str(alert.get("alert_id") or new_id("evt")),
            "delivery_id": str(alert.get("delivery_id") or new_id("dlv")),
            "attempt": int(alert.get("attempt") or 1),
            # fallback to alert_id — the dedup identity must exist even
            # for direct forward() calls that bypass the admission layer.
            "idempotency_key": alert.get("idempotency_key") or alert.get("alert_id"),
        }
        envelope.update(alert)  # alert fields stay at top level for $exec.*
        if signing_key:
            envelope = sign_envelope(envelope, signing_key, key_id=key_id)
        try:
            body = json.dumps(envelope, default=str).encode()
            status, resp = await (await _client()).post_json(
                target, payload=json.loads(body), timeout=timeout_s
            )
            ok = 200 <= status < 300
            klass = _classify(status, None)
            return {
                "ok": ok,
                "status_code": status,
                "exec_id": resp.get("execution_id") or resp.get("executionId") or resp.get("id"),
                **klass,
            }
        except Exception as exc:
            logger.warning(
                "forward to %s failed: %s", redact_url(target), type(exc).__name__
            )
            klass = _classify(None, exc)
            return {"ok": False, "status_code": None, "exec_id": None, **klass}

    forward.aclose = aclose
    return forward
