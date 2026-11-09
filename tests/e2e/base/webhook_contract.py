"""Webhook contractual matrix (E2E-HTTP-001).

Single source of truth for the ``POST /api/v1/alerts`` contract. Every
negative/positive ingestion test should consume these rows instead of
ad-hoc status comparisons — per the backlog, ``status < 500``-style bounds
are forbidden: each row names its precise expectation and the effect that
must (not) follow.

Deviations from the aspirational doc-matrix (docs/18 §9) are documented in
each row's ``note`` — the matrix encodes the *observed* OpenAPI contract,
not wishful thinking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ContractRow:
    """One row of the webhook contract matrix."""

    id: str
    description: str
    expect_status: int
    effect: str  # admission_created | none | idempotent_no_dup
    auth: str  # service | none | invalid
    note: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


# Baseline payload builders — tests override alert_id/idempotency_key.
def _valid_payload() -> dict[str, Any]:
    return {
        "alert_id": "MATRIX-VALID",
        "alert_type": "ransomware",
        "hostname": "MATRIX-HOST",
        "src_ip": "10.0.0.99",
        "hash": "0" * 64,
        "severity": 2,
        "source": "contract-matrix",
        "event_type": "ransomware_detection",
    }


WEBHOOK_CONTRACT: tuple[ContractRow, ...] = (
    ContractRow(
        id="valid",
        description="Valid alert with service auth",
        expect_status=202,
        effect="admission_created",
        auth="service",
        payload=_valid_payload(),
    ),
    ContractRow(
        id="malformed_json",
        description="Body is not parseable JSON",
        expect_status=422,
        effect="none",
        auth="service",
        # Doc-matrix said 400; FastAPI's RequestValidationError maps to 422.
        note="FastAPI returns 422 for unparsable bodies (not 400)",
    ),
    ContractRow(
        id="schema_invalid",
        description="JSON object but not a dict payload / missing fields",
        expect_status=422,
        effect="none",
        auth="service",
        payload={"definitely": "not-an-alert-shape", "severity": "high"},
    ),
    ContractRow(
        id="oversized",
        description="Payload larger than max_payload_bytes (256KiB)",
        expect_status=422,
        effect="none",
        auth="service",
        # The API maps oversize to 422 (AdmissionValidationError), not 413.
        note="API maps oversize to 422, not 413",
    ),
    ContractRow(
        id="no_auth",
        description="No credentials at all",
        expect_status=401,
        effect="none",
        auth="none",
    ),
    ContractRow(
        id="bad_token",
        description="Invalid Bearer credential",
        expect_status=401,
        effect="none",
        auth="invalid",
        # There is no 403 tier: AuthError surfaces as 401 either way.
        note="API has no 403 tier; invalid credential maps to 401",
    ),
    ContractRow(
        id="replay",
        description="Same idempotency_key submitted twice",
        expect_status=202,
        effect="idempotent_no_dup",
        auth="service",
        payload=_valid_payload() | {"alert_id": "MATRIX-REPLAY"},
    ),
    ContractRow(
        id="secret_canary",
        description="Valid alert carrying a credential-like field — the "
        "canary must reach the domain store but never the log pipeline",
        expect_status=202,
        effect="admission_created",
        auth="service",
        payload=_valid_payload() | {"alert_id": "MATRIX-SECRET"},
    ),
    ContractRow(
        id="rate_limited",
        description="Burst beyond the per-minute budget",
        expect_status=429,
        effect="none",
        auth="service",
        note="Requires RATE_LIMIT_PER_MINUTE budget+1 requests; "
        "asserts Retry-After header per HTTP-002",
    ),
)


def expected_effects(effect: str) -> str:
    """Human description of the expected post-condition for a matrix row."""
    return {
        "admission_created": "an admission_id is returned and the record is queryable",
        "none": "no admission, no ES document, no TheHive case",
        "idempotent_no_dup": "the replay returns the SAME admission_id; no second document",
    }[effect]
