#!/usr/bin/env python3
"""Chaos campaign runner (RES-02 formal): multi-fault injection with evidence.

Runs a sequence of bounded faults through ``chaos_lite.py`` (one alert +
workflow per scenario), verifies the injected service recovers before the
next scenario (no compounding failures), and emits an aggregate campaign
report — per-scenario pass, recovery time (RTO), and overall verdict.

Honest criteria: a campaign PASSES only when every scenario passes
chaos_lite's own oracle (FINISHED + fault overlapped execution) AND the
target returns to healthy within ``recovery_slo_s``.

    python scripts/perf/chaos_campaign.py                # default suite
    python scripts/perf/chaos_campaign.py --scenario cortex --pause 45
    python scripts/perf/chaos_campaign.py --dry-run      # health checks only

Report -> reports/perf/chaos-campaign-<ts>.json ; exit 1 on FAIL.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "reports" / "perf"
CHAOS_LITE = ROOT / "scripts" / "perf" / "chaos_lite.py"
RECOVERY_POLL_S = 10

# Default campaign: one fault per critical backend.  Pause is bounded and
# non-destructive; containers resume on unpause.
DEFAULT_SCENARIOS = [
    {"name": "cortex-pause", "target": "soar_cortex", "pause": 30},
    {"name": "thehive-pause", "target": "soar_thehive", "pause": 30},
    {"name": "misp-pause", "target": "soar_misp", "pause": 30},
]


def _sh(cmd: list[str], timeout: int = 60) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    return out.stdout


def container_health(name: str) -> str:
    """docker inspect health state — 'healthy'|'unhealthy'|'running'|''."""
    fmt = "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}"
    return _sh(["docker", "inspect", "--format", fmt, name]).strip()


def wait_healthy(name: str, timeout_s: int) -> tuple[bool, float]:
    """Poll until healthy/running; returns (recovered, seconds)."""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        h = container_health(name)
        if h in ("healthy", "running"):
            return True, round(time.time() - t0, 1)
        time.sleep(RECOVERY_POLL_S)
    return False, float(timeout_s)


def run_scenario(scenario: dict, dry_run: bool) -> dict:
    """Execute one chaos_lite run + post-fault recovery check."""
    name = scenario["name"]
    target = scenario["target"]
    print(f"[campaign] === {name}: pause {target} {scenario['pause']}s ===")
    started = time.time()
    result = {
        "scenario": name,
        "target": target,
        "pause_s": scenario["pause"],
        "dry_run": dry_run,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
    }

    if dry_run:
        ok, secs = wait_healthy(target, 30)
        result.update(
            scenario_pass=True,
            recovery_s=0.0,
            recovery_ok=ok,
            recovery_ok_detail=f"baseline health={ok}",
            evidence_file=None,
        )
        return result

    before = set(OUT_DIR.glob("chaos-*.json")) if OUT_DIR.exists() else set()
    proc = subprocess.run(
        [
            sys.executable,
            str(CHAOS_LITE),
            "--target",
            target,
            "--pause",
            str(scenario["pause"]),
        ],
        capture_output=True,
        text=True,
        timeout=900,
        cwd=str(ROOT),
    )
    for line in proc.stdout.splitlines():
        print(f"  [lite] {line}")
    if proc.stderr.strip():
        print(f"  [lite:stderr] {proc.stderr.strip()[:300]}")

    # Recovery: target must come back healthy (no compounded state).
    recovered, recovery_secs = wait_healthy(target, scenario.get("recovery_slo_s", 120))

    new_files = set(OUT_DIR.glob("chaos-*.json")) - before
    scenario_pass = proc.returncode == 0
    evidence = None
    for f in new_files:
        evidence = str(f.relative_to(ROOT))
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            scenario_pass = scenario_pass and bool(data.get("pass"))
            result["workflow_status"] = data.get("status")
            result["fault_overlapped"] = data.get("fault_overlapped_execution")
            result["failed_nodes"] = data.get("failed_nodes", [])
        except (json.JSONDecodeError, OSError):
            scenario_pass = False

    result.update(
        scenario_pass=bool(scenario_pass and recovered),
        chaos_lite_rc=proc.returncode,
        recovery_s=recovery_secs,
        recovery_ok=recovered,
        evidence_file=evidence,
        wall_s=round(time.time() - started, 1),
    )
    return result


def campaign_verdict(scenarios: list[dict]) -> tuple[str, list[str]]:
    """PASS only when every scenario passes and recovers within SLO."""
    reasons = []
    failed = [s for s in scenarios if not s.get("scenario_pass")]
    for s in failed:
        detail = []
        if s.get("chaos_lite_rc", 0) != 0:
            detail.append(f"chaos_lite rc={s.get('chaos_lite_rc')}")
        if s.get("recovery_ok") is False:
            detail.append(f"recovery>{s.get('recovery_s')}s")
        if s.get("workflow_status") and s["workflow_status"] != "FINISHED":
            detail.append(f"status={s['workflow_status']}")
        reasons.append(f"{s['scenario']}: {'; '.join(detail) or 'failed'}")
    return ("FAIL" if failed else "PASS"), reasons


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", help="run only the scenario with this name")
    ap.add_argument("--pause", type=int, help="override pause seconds")
    ap.add_argument("--recovery-slo", type=int, default=120)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    scenarios = [dict(s, recovery_slo_s=args.recovery_slo) for s in DEFAULT_SCENARIOS]
    if args.scenario:
        scenarios = [s for s in scenarios if s["name"] == args.scenario]
        if not scenarios:
            known = [s["name"] for s in DEFAULT_SCENARIOS]
            sys.exit(f"unknown scenario {args.scenario!r}; known: {known}")
    if args.pause:
        for s in scenarios:
            s["pause"] = args.pause

    t0 = time.time()
    results = [run_scenario(s, args.dry_run) for s in scenarios]
    verdict, reasons = campaign_verdict(results)

    report = {
        "schema": "soar.chaos-campaign.v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dry_run": args.dry_run,
        "scenarios": results,
        "passed": sum(1 for s in results if s["scenario_pass"]),
        "total": len(results),
        "max_recovery_s": max((s.get("recovery_s", 0) for s in results), default=0),
        "verdict": verdict,
        "verdict_reasons": reasons,
        "wall_s": round(time.time() - t0, 1),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"chaos-campaign-{int(t0)}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[campaign] verdict={verdict} ({report['passed']}/{report['total']})")
    for r in reasons:
        print(f"[campaign]   - {r}")
    print(f"[campaign] report -> {out}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
