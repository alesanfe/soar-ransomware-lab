"""HMAC-001: versioned message-signature protocol for webhook traffic.

Two layers:

1. **Transport signatures** (Shuffle/workflow -> API callbacks and any
   signed inbound call): ``X-SOAR-*`` headers over a canonical request
   string ``METHOD\nPATH\nTIMESTAMP\nNONCE\nCONTENT_SHA256``.
2. **Envelope signatures** (API -> Shuffle): the Shuffle webhook does
   NOT expose HTTP headers to the workflow, so the signature travels
   inside the JSON body under ``security`` — the embedded
   ``normalize_inputs`` script can verify it before processing.

Both use HMAC-SHA256 with ``hmac.compare_digest``, a timestamp window
and a nonce store (Redis SET NX EX, in-memory fallback for tests).
Keys are selected by ``key_id`` — never tried indiscriminately.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Protocol

__all__ = [
    "SIGNATURE_VERSION",
    "SignatureError",
    "ReplayError",
    "canonical_request",
    "sign_request",
    "verify_request",
    "sign_envelope",
    "verify_envelope",
    "InMemoryNonceStore",
    "RedisNonceStore",
    "body_sha256",
]

SIGNATURE_VERSION = "v1"
DEFAULT_SKEW_S = 300
NONCE_TTL_S = 660  # max skew + margin

HDR_VERSION = "x-soar-signature-version"
HDR_KEY_ID = "x-soar-key-id"
HDR_TIMESTAMP = "x-soar-timestamp"
HDR_NONCE = "x-soar-nonce"
HDR_CONTENT_SHA = "x-soar-content-sha256"
HDR_SIGNATURE = "x-soar-signature"

_ALLOWED_ALGS = {"v1"}  # only HMAC-SHA256/v1 exists — allowlist (HMAC-006)
_MAX_HEADER_LEN = 512


class SignatureError(Exception):
    """Message signature invalid — always a 401-class rejection."""

    def __init__(self, detail: str, code: str = "SIGNATURE_INVALID") -> None:
        super().__init__(detail)
        self.code = code


class ReplayError(SignatureError):
    """Nonce reused inside the acceptance window."""

    def __init__(self) -> None:
        super().__init__("nonce already used", code="REPLAY_DETECTED")


def body_sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def canonical_request(method: str, path: str, timestamp: str, nonce: str, content_sha: str) -> str:
    return "\n".join((method.upper(), path, timestamp, nonce, content_sha))


def _mac(secret: str | bytes, canonical: str) -> str:
    key = secret.encode() if isinstance(secret, str) else secret
    return hmac.new(key, canonical.encode(), hashlib.sha256).hexdigest()


def sign_request(
    secret: str,
    *,
    method: str,
    path: str,
    body: bytes,
    key_id: str,
    now: float | None = None,
) -> dict[str, str]:
    """Produce the ``X-SOAR-*`` header set for an outbound signed call."""
    ts = str(int(now if now is not None else time.time()))
    nonce = uuid.uuid4().hex
    csha = body_sha256(body)
    canonical = canonical_request(method, path, ts, nonce, csha)
    return {
        "X-SOAR-Signature-Version": SIGNATURE_VERSION,
        "X-SOAR-Key-Id": key_id,
        "X-SOAR-Timestamp": ts,
        "X-SOAR-Nonce": nonce,
        "X-SOAR-Content-SHA256": csha,
        "X-SOAR-Signature": f"v1={_mac(secret, canonical)}",
    }


def _bounded(value: str | None, name: str) -> str:
    if not value:
        raise SignatureError(f"missing {name}", code="SIGNATURE_MISSING")
    if len(value) > _MAX_HEADER_LEN:
        raise SignatureError(f"{name} too long", code="SIGNATURE_MALFORMED")
    return value


def _check_freshness(ts_raw: str, skew_s: int, now: float) -> None:
    try:
        ts = int(ts_raw)
    except ValueError as exc:
        raise SignatureError("timestamp malformed", code="SIGNATURE_MALFORMED") from exc
    if abs(now - ts) > skew_s:
        raise SignatureError("timestamp outside acceptance window", code="SIGNATURE_STALE")


class InMemoryNonceStore:
    """Nonce registry for tests/single-process (SET NX EX semantics)."""

    def __init__(self) -> None:
        self._nonces: dict[str, float] = {}

    async def claim(self, nonce: str, ttl_s: int = NONCE_TTL_S) -> bool:
        now = time.time()
        expired = [k for k, t in self._nonces.items() if t <= now]
        for k in expired:
            del self._nonces[k]
        if nonce in self._nonces:
            return False
        self._nonces[nonce] = now + ttl_s
        return True


class RedisNonceStore:
    """Redis-backed nonce registry — shared across replicas.

    Fail-closed: a Redis error raises ``SignatureError`` rather than
    silently disabling replay protection (DOS-003 policy).
    """

    KEY_PREFIX = "soar:nonce:"

    def __init__(self, client: Any) -> None:
        self._client = client

    async def claim(self, nonce: str, ttl_s: int = NONCE_TTL_S) -> bool:
        try:
            won = await self._client.set(
                f"{self.KEY_PREFIX}{nonce}", "1", nx=True, ex=ttl_s
            )
        except Exception as exc:
            raise SignatureError(
                "nonce store unavailable", code="NONCE_STORE_DOWN"
            ) from exc
        return bool(won)


def _verify_common(
    secret_resolver: Any,
    *,
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    content_sha: str,
    signature: str,
    body: bytes,
    nonce_store: Any | None,
    skew_s: int,
    now: float | None = None,
) -> dict[str, Any]:
    now = now if now is not None else time.time()
    scheme, _, sig_hex = signature.partition("=")
    if scheme not in _ALLOWED_ALGS:
        raise SignatureError("signature version/alg not allowed", code="SIGNATURE_ALG")
    _check_freshness(timestamp, skew_s, now)
    if not hmac.compare_digest(body_sha256(body), content_sha):
        raise SignatureError("content digest mismatch", code="SIGNATURE_BODY")
    canonical = canonical_request(method, path, timestamp, nonce, content_sha)
    return {
        "canonical": canonical,
        "sig_hex": sig_hex,
        "now": now,
        "secret_resolver": secret_resolver,
        "nonce_store": nonce_store,
        "nonce": nonce,
    }


async def verify_request(
    secret_resolver: Any,
    *,
    method: str,
    path: str,
    headers: Any,
    body: bytes,
    nonce_store: Any | None = None,
    skew_s: int = DEFAULT_SKEW_S,
) -> dict[str, str]:
    """Verify ``X-SOAR-*`` transport signature headers.

    ``secret_resolver`` is called with ``key_id`` and must return the
    current (or previous, grace) secret or ``None`` for unknown ids.
    Returns ``{"key_id": ..., "rotation_grace": bool}`` on success.
    """
    if hasattr(headers, "items"):
        _h = {str(k).lower(): v for k, v in headers.items()}
    else:
        _h = {}
    def get(n: str) -> Any:
        return _h.get(n)
    version = _bounded(get(HDR_VERSION), "signature version")
    if version not in _ALLOWED_ALGS:
        raise SignatureError("signature version not allowed", code="SIGNATURE_ALG")
    key_id = _bounded(get(HDR_KEY_ID), "key id")
    timestamp = _bounded(get(HDR_TIMESTAMP), "timestamp")
    nonce = _bounded(get(HDR_NONCE), "nonce")
    content_sha = _bounded(get(HDR_CONTENT_SHA), "content sha")
    signature = _bounded(get(HDR_SIGNATURE), "signature")

    resolved = secret_resolver(key_id)
    if isinstance(resolved, tuple):
        secret, grace = resolved
    else:
        secret, grace = resolved, False
    if not secret:
        raise SignatureError("unknown key id", code="SIGNATURE_UNKNOWN_KEY")

    common = _verify_common(
        secret_resolver,
        method=method,
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        content_sha=content_sha,
        signature=signature,
        body=body,
        nonce_store=nonce_store,
        skew_s=skew_s,
    )
    expected = _mac(secret, common["canonical"])
    if not hmac.compare_digest(expected, common["sig_hex"]):
        raise SignatureError("signature mismatch")
    if nonce_store is not None and not await nonce_store.claim(nonce):
        raise ReplayError()
    return {"key_id": key_id, "rotation_grace": grace}


# ── Envelope (body-embedded) signatures — API -> Shuffle ──────────────────────

_ENVELOPE_KEY = "security"


def _canonical_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload, sort_keys=True, default=str, separators=(",", ":")
    ).encode()


def sign_envelope(
    payload: dict[str, Any],
    secret: str,
    *,
    key_id: str,
    now: float | None = None,
) -> dict[str, Any]:
    """Embed a ``security`` block inside the JSON body for Shuffle.

    Signature covers the canonical JSON of ``payload`` (minus any prior
    ``security`` block): ``v1|timestamp|nonce|sha256(payload)``.
    """
    clean = {k: v for k, v in payload.items() if k != _ENVELOPE_KEY}
    ts = int(now if now is not None else time.time())
    nonce = uuid.uuid4().hex
    digest = body_sha256(_canonical_payload(clean))
    sig = _mac(secret, f"v1|{ts}|{nonce}|{digest}")
    out = dict(clean)
    out[_ENVELOPE_KEY] = {
        "alg": SIGNATURE_VERSION,
        "key_id": key_id,
        "timestamp": ts,
        "nonce": nonce,
        "payload_sha256": digest,
        "signature": sig,
    }
    return out


def verify_envelope(
    message: dict[str, Any],
    secret_resolver: Any,
    *,
    skew_s: int = DEFAULT_SKEW_S,
    now: float | None = None,
) -> dict[str, Any]:
    """Verify the embedded ``security`` block (Shuffle side mirror)."""
    sec = message.get(_ENVELOPE_KEY)
    if not isinstance(sec, dict):
        raise SignatureError("missing security envelope", code="SIGNATURE_MISSING")
    if sec.get("alg") not in _ALLOWED_ALGS:
        raise SignatureError("envelope alg not allowed", code="SIGNATURE_ALG")
    key_id = sec.get("key_id")
    if not key_id:
        raise SignatureError("missing key id", code="SIGNATURE_MALFORMED")
    resolved = secret_resolver(key_id)
    if isinstance(resolved, tuple):
        secret, _grace = resolved
    else:
        secret = resolved
    if not secret:
        raise SignatureError("unknown key id", code="SIGNATURE_UNKNOWN_KEY")
    now = now if now is not None else time.time()
    ts = sec.get("timestamp")
    try:
        if abs(now - int(ts)) > skew_s:
            raise SignatureError("envelope timestamp stale", code="SIGNATURE_STALE")
    except (TypeError, ValueError) as exc:
        raise SignatureError("envelope timestamp malformed", code="SIGNATURE_MALFORMED") from exc
    clean = {k: v for k, v in message.items() if k != _ENVELOPE_KEY}
    digest = body_sha256(_canonical_payload(clean))
    if not hmac.compare_digest(digest, str(sec.get("payload_sha256", ""))):
        raise SignatureError("payload digest mismatch", code="SIGNATURE_BODY")
    expected = _mac(secret, f"v1|{int(ts)}|{sec.get('nonce')}|{digest}")
    if not hmac.compare_digest(expected, str(sec.get("signature", ""))):
        raise SignatureError("envelope signature mismatch")
    return {"key_id": key_id, "nonce": sec.get("nonce")}
