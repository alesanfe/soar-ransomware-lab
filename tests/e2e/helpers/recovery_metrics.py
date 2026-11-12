"""E8-04 — historical recovery metrics.

Appends one JSONL record per observed outage/recovery to
``reports/validation/results/recovery-metrics.jsonl`` so regressions in
recovery time become visible across runs. Correlates each observation with
a reconciliation-storm marker when ``churn_at`` is supplied.
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

METRICS_PATH = Path(os.environ.get(
    "E2E_RECOVERY_METRICS",
    "/app/reports/validation/results/recovery-metrics.jsonl"
    if Path("/app").exists() else
    "reports/validation/results/recovery-metrics.jsonl",
))


def record_recovery(component: str, disruption: str, down_s: float,
                    recovery_s: float | None, extra: dict | None = None) -> dict:
    """Append a recovery observation. ``recovery_s=None`` => timed out."""
    rec = {
        "ts_utc": datetime.now(UTC).isoformat(),
        "component": component,
        "disruption": disruption,          # e.g. "stop", "kill-9", "pause"
        "down_detected_s": round(down_s, 2),
        "recovery_s": round(recovery_s, 2) if recovery_s is not None else None,
        "recovered": recovery_s is not None,
    }
    if extra:
        rec.update(extra)
    try:
        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with METRICS_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError:
        pass
    return rec


def recent_recovery_stats(component: str, limit: int = 20) -> dict:
    """Return {n, mean_s, max_s} for the last ``limit`` recovered runs."""
    if not METRICS_PATH.exists():
        return {"n": 0}
    vals = []
    try:
        for line in METRICS_PATH.read_text(encoding="utf-8").splitlines()[-500:]:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("component") == component and rec.get("recovered"):
                vals.append(rec["recovery_s"])
    except OSError:
        return {"n": 0}
    vals = vals[-limit:]
    if not vals:
        return {"n": 0}
    return {"n": len(vals), "mean_s": round(sum(vals) / len(vals), 2),
            "max_s": round(max(vals), 2)}


def docker_start_churn(window_s: int = 120) -> int:
    """Count container starts in the last ``window_s`` (storm correlation)."""
    import subprocess
    try:
        out = subprocess.run(
            ["docker", "events", "--since", f"{window_s}s",
             "--filter", "event=start", "--format", "{{.Actor.Attributes.name}}"],
            capture_output=True, text=True, timeout=window_s + 10,
        )
    except (OSError, subprocess.SubprocessError):
        return -1
    return len([l for l in out.stdout.splitlines() if l.strip()])
