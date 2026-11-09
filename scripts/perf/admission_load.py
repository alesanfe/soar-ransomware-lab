#!/usr/bin/env python3
"""PERF-001 admission-path load evidence.

Fires N concurrent ``POST /api/v1/alerts`` requests against the SOAR API,
measures per-request latency (P50/P95/P99/max), response status codes, and
samples queue metrics before/after the burst. Writes a JSON evidence file.

Run inside the ``soar_api`` container (aiohttp is available there):

    docker exec -e INTERNAL_SERVICE_TOKEN="$INTERNAL_SERVICE_TOKEN" soar_api \
        python3 /app/scripts/perf/admission_load.py --concurrency 60

Caution: every admission is forwarded to the Shuffle webhook, so each burst
creates real workflow executions. Run when the stack is idle — not during
e2e suites — and expect dead-letter entries if the downstream 500s.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import aiohttp

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
TOKEN = os.environ.get("INTERNAL_SERVICE_TOKEN", "")
OUT_DIR = Path("/app/reports/perf")


def _pct(sorted_lat: list[float], q: float) -> float:
    return sorted_lat[min(int(q * len(sorted_lat)), len(sorted_lat) - 1)]


async def _queue_metrics(session: aiohttp.ClientSession) -> dict:
    try:
        async with session.get(
            f"{API_URL}/api/v1/queue/metrics",
            headers={"X-Service-Token": TOKEN},
        ) as resp:
            return await resp.json() if resp.status == 200 else {"error": resp.status}
    except Exception as exc:
        return {"error": str(exc)[:80]}


async def _post(session: aiohttp.ClientSession, i: int, run_id: str) -> tuple[float, int | str]:
    # Full workflow payload — fields the downstream workflow requires
    # (alert_type/src_ip/hash); payloads without them dead-letter at Shuffle.
    body = {
        "alert_id": f"load-{run_id}-{i}",
        "alert_type": "ransomware",
        "event_type": "ransomware_detection",
        "hostname": f"perf-host-{i % 10}",
        "src_ip": f"192.168.99.{i % 250 + 1}",
        "hash": f"{i:064x}",
        "severity": 2,
        "source": "admission-load-probe",
        "description": "PERF-001 load evidence — synthetic, harmless",
        "idempotency_key": f"load-{run_id}-{i}",
    }
    t0 = time.perf_counter()
    try:
        async with session.post(
            f"{API_URL}/api/v1/alerts",
            json=body,
            headers={"X-Service-Token": TOKEN},
        ) as resp:
            await resp.read()
            return time.perf_counter() - t0, resp.status
    except Exception as exc:
        return time.perf_counter() - t0, str(exc)[:60]


async def _single_warmup(session: aiohttp.ClientSession) -> dict:
    t0 = time.perf_counter()
    async with session.get(f"{API_URL}/health") as resp:
        await resp.read()
        health_ms = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    async with session.post(
        f"{API_URL}/api/v1/alerts",
        json={
            "alert_id": f"load-warmup-{uuid.uuid4().hex[:8]}",
            "alert_type": "ransomware",
            "event_type": "ransomware_detection",
            "hostname": "perf-warmup",
            "src_ip": "192.168.99.250",
            "hash": "0" * 64,
            "severity": 2,
            "source": "admission-load-probe",
            "idempotency_key": f"warmup-{time.time_ns()}",
        },
        headers={"X-Service-Token": TOKEN},
    ) as resp:
        await resp.read()
        single_ms = (time.perf_counter() - t0) * 1000
        single_status = resp.status
    return {
        "health_ms": round(health_ms, 1),
        "single_ms": round(single_ms, 1),
        "single_status": single_status,
    }


async def _soak(
    session: aiohttp.ClientSession, duration_s: int, rate: float, run_id: str
) -> list[tuple[int, float, int | str]]:
    """Sustained-rate soak: schedule `rate` posts/s for `duration_s`.

    Returns (minute_bucket, latency_s, status) tuples — bucketing enables
    per-minute percentile drift detection (memory leaks, index growth,
    queue accumulation surface as rising late-bucket percentiles).
    """
    out: list[tuple[int, float, int | str]] = []
    t0 = time.perf_counter()
    seq = 0
    while True:
        now = time.perf_counter() - t0
        if now >= duration_s:
            break
        target = seq / rate
        if now < target:
            await asyncio.sleep(target - now)
        bucket = int(now // 60)
        lat, code = await _post(session, seq, run_id)
        out.append((bucket, lat, code))
        seq += 1
    return out


async def main(concurrency: int, waves: int, duration: int, rate: float) -> int:
    run_id = uuid.uuid4().hex[:8]
    conn = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=conn) as session:
        warmup = await _single_warmup(session)
        q_before = await _queue_metrics(session)

        soak_rows: list[tuple[int, float, int | str]] = []
        all_results: list[tuple[float, int | str]] = []
        wall = 0.0
        if duration > 0:
            t0 = time.perf_counter()
            soak_rows = await _soak(session, duration, rate, run_id)
            wall = time.perf_counter() - t0
            all_results = [(lat, code) for _, lat, code in soak_rows]
        else:
            for _ in range(waves):
                t0 = time.perf_counter()
                res = await asyncio.gather(*[_post(session, i, run_id) for i in range(concurrency)])
                wall += time.perf_counter() - t0
                all_results.extend(res)

        await asyncio.sleep(2)
        q_after = await _queue_metrics(session)

    lat_ms = sorted(r[0] * 1000 for r in all_results)
    codes: dict[str, int] = {}
    for _, c in all_results:
        codes[str(c)] = codes.get(str(c), 0) + 1

    evidence = {
        "run_id": run_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "api_url": API_URL,
        "concurrency": concurrency,
        "waves": waves,
        "total_requests": len(all_results),
        "wall_seconds": round(wall, 2),
        "latency_ms": {
            "p50": round(_pct(lat_ms, 0.5), 1),
            "p95": round(_pct(lat_ms, 0.95), 1),
            "p99": round(_pct(lat_ms, 0.99), 1),
            "max": round(lat_ms[-1], 1),
        },
        "status_codes": codes,
        "warmup": warmup,
        "queue_before": q_before,
        "queue_after": q_after,
        "soak": _soak_report(soak_rows) if soak_rows else None,
        "acceptance": {
            "all_202": codes == {"202": len(all_results)},
            "p95_under_500ms": _pct(lat_ms, 0.95) < 500,
            **({"concurrency_at_least_50": concurrency >= 50} if duration == 0 else {}),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"admission-load-{run_id}.json"
    out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence["latency_ms"], indent=0))
    print(f"codes={codes} wall={evidence['wall_seconds']}s -> {out}")
    print(f"acceptance={evidence['acceptance']}")
    return 0 if all(evidence["acceptance"].values()) else 1


def _soak_report(rows: list[tuple[int, float, int | str]]) -> dict:
    """Per-minute percentile buckets + drift between first/last bucket."""
    buckets: dict[int, list[float]] = {}
    codes: dict[str, int] = {}
    for b, lat, code in rows:
        buckets.setdefault(b, []).append(lat * 1000)
        codes[str(code)] = codes.get(str(code), 0) + 1
    per_minute = [
        {
            "minute": b,
            "n": len(lats),
            "p50_ms": round(_pct(sorted(lats), 0.5), 1),
            "p95_ms": round(_pct(sorted(lats), 0.95), 1),
        }
        for b, lats in sorted(buckets.items())
    ]
    drift = None
    if len(per_minute) >= 2:
        drift = round(per_minute[-1]["p50_ms"] - per_minute[0]["p50_ms"], 1)
    return {"per_minute": per_minute, "p50_drift_ms": drift, "status_codes": codes}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=60)
    ap.add_argument("--waves", type=int, default=1)
    ap.add_argument(
        "--duration",
        type=int,
        default=0,
        help="Soak mode: sustain --rate req/s for N seconds (disables waves)",
    )
    ap.add_argument("--rate", type=float, default=2.0, help="soak requests/second")
    args = ap.parse_args()
    if not TOKEN:
        sys.exit("INTERNAL_SERVICE_TOKEN env var required")
    sys.exit(asyncio.run(main(args.concurrency, args.waves, args.duration, args.rate)))
