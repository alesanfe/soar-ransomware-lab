"""Per-test performance recorder for pytest.

Collects (nodeid, phase, duration, outcome) from pytest's own phase reports
(setup/call/teardown) and persists a JSON artifact at session end so tests
can be ranked and bottlenecked by measured time instead of guesswork.

Enable with ``PERF_REPORT=1`` (default on) and override the output path with
``PERF_REPORT_PATH``. Inside the e2e container the default resolves to
``/app/reports/perf/``; on the host it resolves to ``reports/perf/`` under the
repo root.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

_RECORDS: list[dict] = []

_CONTAINER_ROOT = Path("/app")


def _default_report_path() -> Path:
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    name = f"test-durations-{ts}.json"
    if _CONTAINER_ROOT.exists() and os.environ.get("SOAR_IN_CONTAINER", "0") == "1":
        return _CONTAINER_ROOT / "reports" / "perf" / name
    # tests/ -> repo root
    return Path(__file__).resolve().parent.parent / "reports" / "perf" / name


def record(item, rep) -> None:
    """Store one phase report from ``pytest_runtest_makereport``."""
    if os.environ.get("PERF_REPORT", "1") in ("0", "false", "False"):
        return
    _RECORDS.append(
        {
            "nodeid": item.nodeid,
            "phase": rep.when,
            "duration_s": round(float(rep.duration), 3),
            "outcome": rep.outcome,
        }
    )


def finish() -> Path | None:
    """Flush collected records to JSON; returns the written path or None."""
    if not _RECORDS or os.environ.get("PERF_REPORT", "1") in ("0", "false", "False"):
        return None
    path = Path(os.environ.get("PERF_REPORT_PATH", "") or _default_report_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "test_count": len({r["nodeid"] for r in _RECORDS}),
        "records": _RECORDS,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path
