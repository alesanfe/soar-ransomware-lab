"""TC-34 — Webhook contractual matrix (E2E-HTTP-001).

Executes the shared contract matrix (``tests/e2e/base/webhook_contract.py``)
against the live ``POST /api/v1/alerts`` endpoint.  Every row asserts its
precise status code AND the side effects the contract demands — rejected
inputs must leave no trace, replays must deduplicate, and rate limiting
must surface 429 + Retry-After.

Runs inside the api container (``docker exec soar_api``) where the API is
reachable as ``http://api:8000``.
"""

from __future__ import annotations

import pytest
import requests

from tests.e2e.base import E2EBaseTest
from tests.e2e.base.webhook_contract import WEBHOOK_CONTRACT

ROWS = {row.id: row for row in WEBHOOK_CONTRACT}
REJECTION_IDS = ("malformed_json", "schema_invalid", "oversized", "no_auth", "bad_token")


class TestWebhookContractMatrix(E2EBaseTest):
    """HTTP-001: contract matrix vs the live admission endpoint."""

    tc_id = "TC-34"
    ALERTS_PATH = "/api/v1/alerts"

    # ── request plumbing ────────────────────────────────────────────────

    def _alerts_url(self) -> str:
        return f"{self.get_service_url('api')}{self.ALERTS_PATH}"

    def _auth_headers(self, kind: str) -> dict[str, str]:
        if kind == "service":
            token = self.env.get("INTERNAL_SERVICE_TOKEN", "")
            assert token, "INTERNAL_SERVICE_TOKEN must be configured for service-auth rows"
            return {"X-Service-Token": token}
        if kind == "invalid":
            return {"Authorization": "Bearer invalid.jwt.token"}
        return {}  # "none" — no credentials at all

    def _send(self, row_id: str, alert_id: str | None = None) -> requests.Response:
        """Send one matrix row — deliberately NOT self.s, which always
        carries the service token."""
        row = ROWS[row_id]
        headers = {"Content-Type": "application/json", **self._auth_headers(row.auth)}
        url = self._alerts_url()
        if row_id == "malformed_json":
            return requests.post(url, data="{not json !!!", headers=headers, timeout=30)
        if row_id == "schema_invalid":
            # A JSON array parses fine but is not a dict payload → 422.
            return requests.post(url, data="[1, 2, 3]", headers=headers, timeout=30)
        payload = dict(row.payload)
        if alert_id:
            payload["alert_id"] = alert_id
        if row_id == "oversized":
            payload["evidence_data"] = "X" * 300_000  # > 256KiB serialized
        return requests.post(url, json=payload, headers=headers, timeout=30)

    @staticmethod
    def _es_doc_count(es, alert_id: str) -> int:
        # term/keyword — a `match` query would tokenize "TC34-..." and
        # fuzzy-match unrelated docs carrying the same "tc34" token.
        resp = es.search(
            query={"term": {"alert_id.keyword": alert_id}},
            index="soar-alerts",
            size=10,
        )
        return len(resp.get("hits", {}).get("hits", []))

    # ── matrix rows ─────────────────────────────────────────────────────

    def test_valid_admission(self):
        """Row 'valid': service auth + valid payload → 202 + queryable record."""
        row = ROWS["valid"]
        alert_id = self.uid("TC34-VALID")
        r = self._send("valid", alert_id=alert_id)
        assert (
            r.status_code == row.expect_status
        ), f"valid row: expected {row.expect_status}, got {r.status_code}: {r.text[:300]}"
        assert r.headers.get("Content-Type", "").startswith("application/json")
        body = r.json()
        admission_id = body.get("admission_id", "")
        assert admission_id, f"202 response must carry admission_id, got: {body}"
        assert body.get("status_url"), "202 response must carry status_url"

        # Effect: the admission record is queryable (queued or forwarded).
        status_url = f"{self.get_service_url('api')}{body['status_url']}"
        r2 = self.s.get(status_url, timeout=30)
        assert r2.status_code == 200, f"admission status must be queryable, got {r2.status_code}"
        record = r2.json()
        assert record.get("admission_id") == admission_id
        assert record.get("status") in (
            "queued",
            "forwarded",
            "dead",
        ), f"unexpected admission status: {record.get('status')}"
        self._log(f"+ valid → 202, admission {admission_id} status={record.get('status')}")

    @pytest.mark.parametrize("row_id", REJECTION_IDS)
    def test_rejected_status(self, row_id: str):
        """Rejection rows: precise status code, no admission_id in the body."""
        row = ROWS[row_id]
        marker = self.uid(f"TC34-REJ-{row_id.upper().replace('_', '-')}")
        r = self._send(row_id, alert_id=marker)
        assert r.status_code == row.expect_status, (
            f"row {row_id}: expected {row.expect_status}, got {r.status_code}: " f"{r.text[:300]}"
        )
        if row.expect_status == 401:
            assert r.headers.get(
                "WWW-Authenticate"
            ), "401 responses must carry a WWW-Authenticate challenge"
        # A rejected request never returns an admission handle.
        try:
            body = r.json()
        except ValueError:
            body = None  # non-JSON rejection body — also acceptable
        assert not (body or {}).get(
            "admission_id"
        ), f"row {row_id}: rejected response must not contain admission_id"
        self._log(f"+ {row_id} → {r.status_code} (expected {row.expect_status})")

    def test_rejected_no_side_effects(self):
        """Rejection rows leave no trace: no case, no alert document."""
        marker = self.uid("TC34-NOEFFECT")
        for row_id in ("schema_invalid", "oversized", "no_auth", "bad_token"):
            r = self._send(row_id, alert_id=marker)
            row = ROWS[row_id]
            assert (
                r.status_code == row.expect_status
            ), f"row {row_id}: expected {row.expect_status}, got {r.status_code}"

        # The marker must remain absent while the worker could conceivably
        # have processed any accepted submission.
        def _case_or_doc() -> bool:
            # Query errors propagate: "could not check" is not "is absent".
            cases = self.thehive.search_cases(range_="0-100")
            if any(marker in f"{c.get('title','')}\n{c.get('description','')}" for c in cases):
                return True
            self.es.indices.refresh("soar-alerts")
            return self._es_doc_count(self.es, marker) > 0

        self.assert_remains_absent(_case_or_doc, duration=20.0, description="rejected-alert effect")
        self.assert_no_case_created(marker)
        self._log("+ rejected rows left no TheHive case and no ES document")

    def test_replay_idempotent(self):
        """Row 'replay': same alert twice → 202 + SAME admission_id, no dup."""
        row = ROWS["replay"]
        alert_id = self.uid("TC34-REPLAY")
        r1 = self._send("replay", alert_id=alert_id)
        r2 = self._send("replay", alert_id=alert_id)
        for r in (r1, r2):
            assert (
                r.status_code == row.expect_status
            ), f"replay row: expected {row.expect_status}, got {r.status_code}: {r.text[:300]}"
        adm1 = r1.json().get("admission_id")
        adm2 = r2.json().get("admission_id")
        assert adm1 and adm1 == adm2, (
            f"Idempotent replay must return the same admission_id, " f"got {adm1} then {adm2}"
        )

        # Bounded window: a second document for the alert must never appear.
        def _duplicated() -> bool:
            # Query errors propagate: an unverifiable absence is not proof.
            self.es.indices.refresh("soar-alerts")
            return self._es_doc_count(self.es, alert_id) > 1

        self.assert_remains_absent(_duplicated, duration=20.0, description="duplicate execution")
        self._log(f"+ replay → same admission_id {adm1}, no duplicate document")

    def test_secret_not_leaked_to_logs(self):
        """Row 'secret_canary': credential-looking field is admitted but a
        canary value must never reach the Loki log pipeline."""
        canary = f"{self.uid('CANARY-SECRET')}-x9k2"
        alert_id = self.uid("TC34-SECRET")
        row = ROWS["secret_canary"]
        headers = {"Content-Type": "application/json", **self._auth_headers("service")}
        payload = dict(row.payload)
        payload["alert_id"] = alert_id
        payload["credentials"] = {"password": canary, "user": "canary-user"}
        r = requests.post(self._alerts_url(), json=payload, headers=headers, timeout=30)
        assert (
            r.status_code == row.expect_status
        ), f"secret_canary row: expected {row.expect_status}, got {r.status_code}: {r.text[:300]}"

        # Give promtail a window to ship any leaked log line, then assert.
        def _leaked() -> bool:
            return self._loki_contains_value(canary)

        self.assert_remains_absent(_leaked, duration=20.0, description="secret canary in Loki")
        self._log(f"+ canary {canary[:20]}... never reached Loki")

    @pytest.mark.slow
    def test_rate_limited(self):
        """Row 'rate_limited': burst beyond budget → 429 + Retry-After.

        The limiter keys on Bearer token or client IP; X-Service-Token
        requests fall back to the client-IP bucket, so the burst shares the
        per-minute budget with the rest of this test file — that is fine,
        it only makes the 429 arrive sooner.
        """
        url = self._alerts_url()
        headers = {
            "Content-Type": "application/json",
            **self._auth_headers("service"),
        }
        # The live budget is read from the response headers — env configs
        # drift between compose files, the header is what the API enforces.
        probe = requests.post(url, data="[1, 2, 3]", headers=headers, timeout=15)
        budget = int(
            probe.headers.get("X-RateLimit-Limit") or self.env.get("RATE_LIMIT_PER_MINUTE", "100")
        )
        hit_429 = probe if probe.status_code == 429 else None
        for i in range(budget + 10):
            if hit_429 is not None:
                break
            # A non-dict body is rejected at the route level (422) but still
            # consumes rate-limit budget — ~110 workflow executions are NOT
            # what we want to spawn just to test the limiter.
            r = requests.post(url, data="[1, 2, 3]", headers=headers, timeout=15)
            if r.status_code == 429:
                hit_429 = r
                break
        assert hit_429 is not None, (
            f"No 429 after {budget + 10} requests (budget={budget}/min) — "
            "rate limiting is not enforced on /api/v1/alerts"
        )
        assert hit_429.headers.get(
            "Retry-After"
        ), "429 responses must carry a Retry-After header (HTTP-002)"
        assert hit_429.headers.get(
            "X-RateLimit-Limit"
        ), "429 responses must carry X-RateLimit-Limit"
        self._log(f"+ rate_limited → 429 with Retry-After={hit_429.headers.get('Retry-After')}s")

    def test_matrix_completeness(self):
        """Every documented matrix row is implemented and self-consistent."""
        assert len(ROWS) == len(WEBHOOK_CONTRACT), "row ids must be unique"
        for row in WEBHOOK_CONTRACT:
            assert row.expect_status in (
                200,
                202,
                400,
                401,
                403,
                409,
                413,
                422,
                429,
                503,
            ), f"row {row.id}: implausible status {row.expect_status}"
            assert row.effect in (
                "admission_created",
                "none",
                "idempotent_no_dup",
            ), f"row {row.id}: unknown effect '{row.effect}'"
            assert row.auth in (
                "service",
                "none",
                "invalid",
            ), f"row {row.id}: unknown auth kind '{row.auth}'"
        self._log(f"+ matrix complete: {len(WEBHOOK_CONTRACT)} rows verified")
