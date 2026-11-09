"""PERF-001: forward admitted alerts to the Shuffle webhook.

Resolves the downstream webhook URL (config > webhook_info.json > default)
and returns an async ``forward(alert)`` callable compatible with
``AdmissionWorker``. A 2xx response is success and captures the Shuffle
execution id when present in the JSON body.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from soar_lab.common.constants import SHUFFLE_WEBHOOK_DEFAULT, WEBHOOK_INFO_PATHS
from soar_lab.infrastructure.http_client import AioHTTPClient

logger = logging.getLogger(__name__)


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


def make_shuffle_forward(
    config_provider: Any,
    timeout_s: float = 30.0,
    http_client: Any = None,
):
    """Build an async ``forward(alert) -> {ok, exec_id, status_code, error}``.

    BL-HTTP-003: forwarding shares the project's single HTTP stack — the
    async :class:`AioHTTPClient` facade over the pooled ``requests``
    transport — instead of paying a fresh TCP(+TLS) handshake per alert
    or carrying a second async stack. Pass ``http_client`` to share a
    caller-managed one; otherwise a lazily-created client is reused and
    MUST be released via ``forward.aclose()`` at shutdown (the API wires
    this into its shutdown hook).
    """
    target = resolve_target_url(config_provider)
    logger.info("Admission worker forwards alerts to %s", target)
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
        headers: dict[str, str] = {}
        idem = alert.get("idempotency_key") or alert.get("alert_id")
        if idem:
            # IDEMP-003: downstream dedupe — Shuffle can correlate a
            # retried delivery of the SAME admission with a replay.
            headers["X-Idempotency-Key"] = str(idem)
        try:
            status, body = await (await _client()).post_json(
                target, payload=alert, headers=headers, timeout=timeout_s
            )
            ok = 200 <= status < 300
            return {
                "ok": ok,
                "status_code": status,
                "exec_id": body.get("execution_id") or body.get("executionId") or body.get("id"),
                "error": None if ok else f"HTTP {status}",
            }
        except Exception as exc:
            return {"ok": False, "status_code": None, "exec_id": None, "error": str(exc)}

    forward.aclose = aclose
    return forward
