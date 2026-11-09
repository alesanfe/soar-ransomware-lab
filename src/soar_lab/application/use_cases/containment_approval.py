"""Analyst-in-the-loop containment approvals (F4).

When ``SOAR_CONTAIN_REQUIRE_APPROVAL=1`` the containment endpoint does
not act immediately: it records the request as a pending approval and
returns ``status="pending_approval"`` with an ``approval_id``. A human
analyst then calls the approve/reject endpoints — letting the lab
measure manual-vs-automated MTTR by timing the approval gap.

The store is in-memory and bounded (lab scale): approvals expire after
``ttl_seconds`` and the map is capped to avoid unbounded growth from a
malfunctioning workflow loop.
"""

import secrets
import time
from typing import Any

__all__ = ["ContainmentApprovalStore"]

DEFAULT_APPROVAL_TTL_S = 3600
MAX_PENDING_APPROVALS = 500

STATUS_PENDING = "pending_approval"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_EXPIRED = "expired"
STATUS_CONSUMED = "consumed"


def _same_request(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Two containment payloads are equal modulo the ``approval_id`` field.

    The resubmitted request carries the issued ticket in ``approval_id``
    while the parked copy stores ``None`` — that field alone must not
    break the payload binding.
    """
    strip = {"approval_id"}
    return {k: v for k, v in a.items() if k not in strip} == {
        k: v for k, v in b.items() if k not in strip
    }


class ContainmentApprovalStore:
    """Bounded in-memory store of containment approval requests."""

    def __init__(self, ttl_seconds: int = DEFAULT_APPROVAL_TTL_S) -> None:
        self._ttl = ttl_seconds
        self._records: dict[str, dict[str, Any]] = {}

    def create(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Record a pending approval; returns the stored record."""
        self._evict_expired()
        if len(self.pending()) >= MAX_PENDING_APPROVALS:
            raise RuntimeError("containment approval backlog is full")
        approval_id = f"appr-{secrets.token_hex(8)}"
        record = {
            "approval_id": approval_id,
            "status": STATUS_PENDING,
            "created_at": time.time(),
            "decided_at": None,
            "decided_by": None,
            "request": request_data,
        }
        self._records[approval_id] = record
        return record

    def get(self, approval_id: str) -> dict[str, Any] | None:
        """Return the record, marking it expired if past TTL."""
        record = self._records.get(approval_id)
        if record is None:
            return None
        if record["status"] == STATUS_PENDING and self._is_expired(record):
            record["status"] = STATUS_EXPIRED
        return record

    def decide(
        self, approval_id: str, *, approve: bool, decided_by: str | None = None
    ) -> dict[str, Any] | None:
        """Approve or reject a pending record.

        Returns the updated record, or ``None`` when the id is unknown
        or the approval is no longer pending (expired/decided).
        """
        record = self.get(approval_id)
        if record is None or record["status"] != STATUS_PENDING:
            return None
        record["status"] = STATUS_APPROVED if approve else STATUS_REJECTED
        record["decided_at"] = time.time()
        record["decided_by"] = decided_by
        return record

    def consume(self, approval_id: str, request_data: dict[str, Any]) -> dict[str, Any] | None:
        """Burn an APPROVED record — single-use, payload-bound.

        The ticket only authorizes the exact request it was issued for:
        it returns ``None`` when the id is unknown, not in the approved
        state (pending/rejected/expired/already consumed), or when the
        resubmitted payload differs from the stored one — so a ticket
        approved for host A can never contain host B, and a spent ticket
        can never replay.
        """
        record = self.get(approval_id)
        if (
            record is None
            or record["status"] != STATUS_APPROVED
            or not _same_request(record["request"], request_data)
        ):
            return None
        record["status"] = STATUS_CONSUMED
        return record

    def pending(self) -> list[dict[str, Any]]:
        """List records still awaiting a decision."""
        self._evict_expired()
        return [r for r in self._records.values() if r["status"] == STATUS_PENDING]

    def _is_expired(self, record: dict[str, Any]) -> bool:
        return (time.time() - record["created_at"]) > self._ttl

    def _evict_expired(self) -> None:
        for record in self._records.values():
            if record["status"] == STATUS_PENDING and self._is_expired(record):
                record["status"] = STATUS_EXPIRED
