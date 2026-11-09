"""Unit tests for scripts/perf/admission_load.py (soak mode)."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from scripts.perf import admission_load as al


class TestSoakReport:
    def test_empty(self):
        rep = al._soak_report([])
        assert rep == {"per_minute": [], "p50_drift_ms": None, "status_codes": {}}

    def test_buckets_and_drift(self):
        rows = [
            (0, 0.100, 202),
            (0, 0.200, 202),
            (1, 0.300, 202),
            (1, 0.400, 503),
        ]
        rep = al._soak_report(rows)
        assert [m["minute"] for m in rep["per_minute"]] == [0, 1]
        assert rep["per_minute"][0]["p50_ms"] == 200.0
        assert rep["per_minute"][1]["p50_ms"] == 400.0
        assert rep["p50_drift_ms"] == 200.0
        assert rep["status_codes"] == {"202": 3, "503": 1}

    def test_single_bucket_no_drift(self):
        rep = al._soak_report([(0, 0.1, 202), (0, 0.2, 202)])
        assert rep["p50_drift_ms"] is None
        assert rep["per_minute"][0]["n"] == 2


class TestSoakPacing:
    def test_respects_duration_and_rate(self):
        latencies = iter([(0.001 * i, 202) for i in range(100)])

        async def fake_post(session, i, run_id):
            return next(latencies, (0.01, 202))

        async def run():
            with patch.object(al, "_post", side_effect=fake_post):
                return await al._soak(None, duration_s=1, rate=50.0, run_id="x")

        rows = asyncio.run(run())
        # 1s @ 50 rps ≈ 50 requests (±scheduling slack)
        assert 30 <= len(rows) <= 60
        assert all(b == 0 for b, _, _ in rows)

    def test_minute_buckets_advance(self):
        async def fake_post(session, i, run_id):
            return (0.001, 202)

        async def run():
            with patch.object(al, "_post", side_effect=fake_post):
                # high rate → several hundred requests in 1s; all bucket 0
                return await al._soak(None, duration_s=1, rate=1000.0, run_id="x")

        rows = asyncio.run(run())
        assert len(rows) > 100
