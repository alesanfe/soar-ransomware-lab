#!/usr/bin/env python3
"""TEST-005: per-module coverage gate for security-critical webhook code.

Reads ``runtime/coverage/coverage.json`` (produced by ``pytest --cov``)
and fails when any module listed below falls under its threshold. The
global ``--cov-fail-under`` gates the project; this gates the modules
that carry the webhook security/reliability guarantees.

Usage:
    python scripts/quality/check_critical_coverage.py \
        [--coverage runtime/coverage/coverage.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Module path suffix -> minimum required line coverage (%)
CRITICAL_THRESHOLDS: dict[str, float] = {
    "interfaces/api/auth.py": 95.0,
    "application/use_cases/alert_admission.py": 95.0,
    "infrastructure/messaging/admission_worker.py": 95.0,
    "infrastructure/messaging/shuffle_forward.py": 95.0,
    "interfaces/api/routes_ingest.py": 95.0,
    "interfaces/api/routes_grafana_alerts.py": 95.0,
    "interfaces/api/middleware/rate_limit.py": 95.0,
    "interfaces/api/middleware/security_headers.py": 95.0,
    "interfaces/api/middleware/trace_id.py": 95.0,
    "interfaces/api/middleware/body_limit.py": 95.0,
    "security/webhook_signing.py": 95.0,
    "security/redaction.py": 95.0,
}
GLOBAL_THRESHOLD = 90.0

# Per-file floor for EVERY measured module (user requirement: minimum 80 %
# per file, not just aggregate). Files omitted at collection time
# (``[tool.coverage.run] omit``) are not present in the JSON and therefore
# not gated here — the omit list is the documented exemption set.
PER_FILE_FLOOR = 80.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage",
        default="runtime/coverage/coverage.json",
        help="Path to coverage.py JSON report",
    )
    args = parser.parse_args()

    path = Path(args.coverage)
    if not path.exists():
        # Inside the container the project lives at /app
        alt = Path("/app") / args.coverage
        path = alt if alt.exists() else path
    if not path.exists():
        print(f"ERROR: coverage file not found: {args.coverage}")
        return 2

    data = json.loads(path.read_text(encoding="utf-8"))
    files = data.get("files", {})

    failures: list[str] = []
    checked = 0
    for suffix, threshold in CRITICAL_THRESHOLDS.items():
        match = next((f for f in files if f.replace("\\", "/").endswith(suffix)), None)
        if match is None:
            continue  # module may not exist yet (pre-HMAC) — gate only what exists
        checked += 1
        pct = files[match]["summary"]["percent_covered"]
        status = "OK " if pct >= threshold else "LOW"
        print(f"{status} {suffix:60s} {pct:6.2f}%  (>= {threshold}%)")
        if pct < threshold:
            failures.append(f"{suffix}: {pct:.2f}% < {threshold}%")

    total = data.get("totals", {}).get("percent_covered", 0.0)
    print(f"--- global coverage: {total:.2f}% (gate {GLOBAL_THRESHOLD}%) ---")
    if checked and total < GLOBAL_THRESHOLD:
        failures.append(f"global: {total:.2f}% < {GLOBAL_THRESHOLD}%")

    below_floor = sorted(
        (f.replace("\\", "/"), info["summary"]["percent_covered"])
        for f, info in files.items()
        if info["summary"]["percent_covered"] < PER_FILE_FLOOR
    )
    for f, pct in below_floor:
        print(f"LOW {f:70s} {pct:6.2f}%  (>= {PER_FILE_FLOOR}%)")
        failures.append(f"{f}: {pct:.2f}% < per-file floor {PER_FILE_FLOOR}%")
    print(f"--- per-file floor {PER_FILE_FLOOR}%: {len(files) - len(below_floor)}/{len(files)} files pass ---")

    if failures:
        print("COVERAGE GATE FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("Coverage gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
