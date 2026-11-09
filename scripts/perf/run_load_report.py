#!/usr/bin/env python3
"""Locust headless runner producing a structured load-report artifact (PERF).

Wraps ``locust -f scripts/perf/locustfile.py --headless --csv ...``, then
post-processes the stats CSV into ``reports/perf/load_report.json`` with
percentiles, RPS, failure ratio and a PASS/WARN/FAIL verdict against the
admission SLO (default: P95 <= 1000 ms, failure ratio <= 1 %, excluding
the controlled rejections 429/503 which the locustfile marks success).

Usage::

    python scripts/perf/run_load_report.py \
        --host http://localhost:8000 --users 60 --spawn-rate 10 \
        --duration 5m [--token $INTERNAL_SERVICE_TOKEN]

Exit code is 0 when the verdict is PASS/WARN, 1 on FAIL or runner error.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "reports" / "perf"
LOCUSTFILE = ROOT / "scripts" / "perf" / "locustfile.py"

# Admission SLO (aligned with tests/e2e/base/timeouts.py admission P95
# measurement): P95 under 1 s inside the docker network; host-side runs
# traverse the Docker Desktop proxy and are expected ~6x slower.
SLO_P95_MS = 1000.0
SLO_FAIL_RATIO = 0.01
WARN_P95_MS = 3000.0

_DURATION_RE = re.compile(r"^(\d+)(s|m|h)?$")


def _parse_duration(value: str) -> int:
    """Parse ``300s``/``5m``/``1h``/plain seconds into seconds."""
    m = _DURATION_RE.match(value.strip())
    if not m:
        raise ValueError(f"invalid duration {value!r} (use e.g. 60s, 5m, 1h)")
    n = int(m.group(1))
    return n * {"s": 1, "m": 60, "h": 3600}[m.group(2) or "s"]


def parse_stats_csv(csv_path: Path) -> dict:
    """Aggregate the locust ``*_stats.csv`` into headline metrics."""
    rows = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("Name") == "Aggregated":
                continue
            rows.append(row)
    total_req = sum(int(float(r.get("Request Count", 0) or 0)) for r in rows)
    total_fail = sum(int(float(r.get("Failure Count", 0) or 0)) for r in rows)
    # Weighted averages across endpoints; worst-of percentiles.

    def weighted(key: str) -> float:
        if not total_req:
            return 0.0
        return (
            sum(
                float(r.get(key, 0) or 0) * int(float(r.get("Request Count", 0) or 0)) for r in rows
            )
            / total_req
        )

    def pct(key: str) -> float:
        return max((float(r.get(key, 0) or 0) for r in rows), default=0.0)

    rps = sum(float(r.get("Requests/s", 0) or 0) for r in rows)
    endpoints = [
        {
            "name": r.get("Name", "?"),
            "requests": int(float(r.get("Request Count", 0) or 0)),
            "failures": int(float(r.get("Failure Count", 0) or 0)),
            "p50_ms": float(r.get("50%", 0) or 0),
            "p95_ms": float(r.get("95%", 0) or 0),
            "p99_ms": float(r.get("99%", 0) or 0),
            "rps": float(r.get("Requests/s", 0) or 0),
        }
        for r in rows
    ]
    return {
        "requests": total_req,
        "failures": total_fail,
        "failure_ratio": (total_fail / total_req) if total_req else 0.0,
        "mean_ms": weighted("Average Response Time"),
        "p50_ms": pct("50%"),
        "p95_ms": pct("95%"),
        "p99_ms": pct("99%"),
        "rps": rps,
        "endpoints": endpoints,
    }


def verdict(stats: dict) -> tuple[str, list[str]]:
    """PASS/WARN/FAIL vs the admission SLO; reasons list is machine-readable."""
    reasons: list[str] = []
    if stats["requests"] == 0:
        return "FAIL", ["no requests executed — locust produced zero load"]
    if stats["failure_ratio"] > SLO_FAIL_RATIO:
        reasons.append(f"failure_ratio {stats['failure_ratio']:.3%} > {SLO_FAIL_RATIO:.0%}")
    p95 = stats["p95_ms"]
    if p95 > WARN_P95_MS:
        reasons.append(f"p95 {p95:.0f}ms > warn ceiling {WARN_P95_MS:.0f}ms")
    elif p95 > SLO_P95_MS:
        return "WARN", reasons + [f"p95 {p95:.0f}ms > SLO {SLO_P95_MS:.0f}ms"]
    return ("FAIL" if reasons else "PASS"), reasons


def build_report(stats: dict, meta: dict) -> dict:
    v, reasons = verdict(stats)
    return {
        "schema": "soar.load-report.v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "meta": meta,
        "slo": {"p95_ms": SLO_P95_MS, "warn_p95_ms": WARN_P95_MS, "fail_ratio": SLO_FAIL_RATIO},
        "stats": stats,
        "verdict": v,
        "verdict_reasons": reasons,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default=os.environ.get("LOCUST_HOST", "http://localhost:8000"))
    ap.add_argument("--users", "-u", type=int, default=60)
    ap.add_argument("--spawn-rate", "-r", type=float, default=10)
    ap.add_argument("--duration", "-t", default="5m", help="e.g. 60s, 5m, 1h")
    ap.add_argument("--token", default=os.environ.get("INTERNAL_SERVICE_TOKEN", ""))
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true", help="print command, do not run")
    ap.add_argument(
        "--from-csv",
        type=Path,
        metavar="PREFIX",
        help="skip the locust run — post-process existing <PREFIX>_stats.csv "
        "(e.g. captured by a locust container inside the docker network)",
    )
    args = ap.parse_args(argv)

    if not args.token:
        print("WARNING: INTERNAL_SERVICE_TOKEN empty — requests will be 401/429", file=sys.stderr)
    seconds = _parse_duration(args.duration)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    csv_prefix = str(args.from_csv) if args.from_csv else str(out / "locust_run")

    locust = shutil.which("locust")
    if locust is not None:
        locust_cmd = [locust]
    else:
        locust_cmd = [sys.executable, "-m", "locust"]

    cmd = [
        *locust_cmd,
        "-f",
        str(LOCUSTFILE),
        "--host",
        args.host,
        "-u",
        str(args.users),
        "-r",
        str(args.spawn_rate),
        "-t",
        f"{seconds}s",
        "--headless",
        "--csv",
        csv_prefix,
        "--csv-full-history",
        "--html",
        str(out / "locust_report.html"),
        "--only-summary",
    ]
    env = dict(os.environ, INTERNAL_SERVICE_TOKEN=args.token)
    meta = {
        "host": args.host,
        "users": args.users,
        "spawn_rate": args.spawn_rate,
        "duration_s": seconds,
        "locustfile": str(LOCUSTFILE.relative_to(ROOT)),
        "command": " ".join(cmd),
    }
    if args.dry_run:
        print(json.dumps(meta, indent=2))
        return 0

    if args.from_csv:
        meta["command"] = f"external locust run (csv source: {args.from_csv}_stats.csv)"
        meta["from_csv"] = True
    elif locust is None:
        try:
            import locust as _l  # noqa: F401
        except ImportError:
            print("ERROR: locust not installed (pip install locust)", file=sys.stderr)
            return 1

    if not args.from_csv:
        print(f"[load] {' '.join(cmd)}")
        proc = subprocess.run(cmd, env=env, timeout=seconds + 300)
        if proc.returncode != 0:
            print(f"[load] WARNING: locust exited rc={proc.returncode}", file=sys.stderr)
    stats_csv = Path(f"{csv_prefix}_stats.csv")
    if not stats_csv.exists():
        print(f"ERROR: locust stats CSV missing ({stats_csv})", file=sys.stderr)
        return 1

    stats = parse_stats_csv(stats_csv)
    report = build_report(stats, meta)
    report_path = out / "load_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"[load] verdict={report['verdict']} requests={stats['requests']} "
        f"failures={stats['failures']} p95={stats['p95_ms']:.0f}ms rps={stats['rps']:.1f}"
    )
    for r in report["verdict_reasons"]:
        print(f"[load]   - {r}")
    print(f"[load] report -> {report_path}")
    return 1 if report["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
