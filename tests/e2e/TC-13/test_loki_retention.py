"""TC-13 — Loki retention / ingestion boundaries against the live config.

Real assertions against loki-config.yml semantics: retention_period=720h,
compactor with retention_enabled, default reject_old_samples_max_age and
creation_grace_period. Probes push/query the HTTPS API with the lab CA.
"""

from __future__ import annotations

import time

import pytest
import requests

CA = "/app/certs/ca.crt"
LOKI = "https://loki:3100"
STREAM = {"e2e_tc13": "retention_probe", "source": "e2e"}


def _push(ts_ns: int, line: str) -> requests.Response:
    body = {
        "streams": [
            {
                "stream": STREAM,
                "values": [[str(ts_ns), line]],
            }
        ]
    }
    return requests.post(
        f"{LOKI}/loki/api/v1/push", json=body, verify=CA, timeout=15
    )


def _query(label: str, start_ns: int, end_ns: int) -> list:
    r = requests.get(
        f"{LOKI}/loki/api/v1/query_range",
        params={
            "query": f'{{e2e_tc13="{label}"}}',
            "start": start_ns,
            "end": end_ns,
            "limit": 100,
        },
        verify=CA,
        timeout=15,
    )
    r.raise_for_status()
    out = []
    for stream in r.json().get("data", {}).get("result", []):
        out.extend(stream.get("values", []))
    return out


@pytest.mark.e2e
class TestLokiRetention:
    tc_id = "TC-13"

    def test_retention_policy_configured(self):
        """/config exposes retention_period=720h and compactor retention
        enabled — the policy exists and is the documented one."""
        r = requests.get(f"{LOKI}/config", verify=CA, timeout=15)
        assert r.status_code == 200
        cfg = r.text
        # loki-config.yml sets 720h; the runtime serializes it as 30d.
        assert "retention_period: 30d" in cfg or "retention_period: 720h" in cfg, (
            "retention period not configured"
        )
        assert "retention_enabled: true" in cfg, "compactor retention off"
        assert "delete_request_store: s3" in cfg, "delete store missing"

    def test_out_of_order_log_accepted(self):
        """A log entry stamped 1h in the past is accepted and queryable —
        within reject_old_samples_max_age, out-of-order tolerated."""
        now = time.time_ns()
        old = now - 3600 * 10**9
        tag = f"ooo-{now}"
        r = _push(old, tag)
        assert r.status_code == 204, f"out-of-order rejected: {r.status_code} {r.text[:120]}"
        time.sleep(3)
        vals = _query("retention_probe", old - 60 * 10**9, now)
        assert any(tag in v[1] for v in vals), "out-of-order log not queryable"

    def test_future_timestamp_rejected(self):
        """A log entry stamped 1h in the FUTURE exceeds creation_grace_period
        (default 10m) — Loki must reject it, not silently accept."""
        now = time.time_ns()
        future = now + 3600 * 10**9
        r = _push(future, f"future-{now}")
        assert r.status_code == 400, (
            f"future log accepted (grace window not enforced): {r.status_code}"
        )

    def test_ingest_boundary_rejects_too_old(self):
        """Entries older than reject_old_samples_max_age (default 168h) are
        rejected at ingest — the boundary is enforced before retention."""
        now = time.time_ns()
        ancient = now - 9 * 24 * 3600 * 10**9  # 9 days > 168h default
        r = _push(ancient, f"ancient-{now}")
        assert r.status_code == 400, (
            f"9d-old log accepted: {r.status_code} — ingest bound missing"
        )

    def test_compactor_metrics_present(self):
        """/metrics exposes compactor activity — retention machinery is
        actually running, not just configured."""
        r = requests.get(f"{LOKI}/metrics", verify=CA, timeout=15)
        assert r.status_code == 200
        metrics = r.text
        assert "loki_compactor" in metrics, "no compactor metrics — not running"
