#!/usr/bin/env python3
"""Execute atomic-style test techniques inside the victim container (F2).

Each technique runs a *bounded, non-destructive* command inside
``victim_sim`` and emits a telemetry line tagged ``[atomic:<tid>]`` to
the container's stdout — the detection path sees real process telemetry
(Promtail → Loki → the alert pipeline), closing the realism gap between
"synthetic webhook alert" and "executed technique".

Honest scope: this is an atomic-test *harness*, not a real Atomic Red
Team install — the commands simulate each technique's observable
behavior (file writes, suspicious process names, shadow-copy-like
commands) without destructive payloads. Extend ``TECHNIQUES`` to add
coverage.

Usage:
    python scripts/maintenance/run_atomic.py [--technique T1486] [--container victim_sim]
"""

import argparse
import subprocess
import sys
from typing import NamedTuple

TECHNIQUES: dict[str, "Technique"] = {}


class Technique(NamedTuple):
    tid: str
    name: str
    commands: list[str]


TECHNIQUES.update(
    {
        "T1059": Technique(
            "T1059",
            "Command and scripting interpreter",
            ["python -c \"print('[atomic:T1059] suspicious shell exec')\""],
        ),
        "T1486": Technique(
            "T1486",
            "Data encrypted for impact",
            [
                "python -c \"open('/tmp/enc_sim.crypt','w').write('simulated-encrypted')\"",
                "python -c \"print('[atomic:T1486] mass file encryption simulated')\"",
            ],
        ),
        "T1490": Technique(
            "T1490",
            "Inhibit system recovery",
            [
                "python -c \"print('[atomic:T1490] vssadmin delete shadows simulated')\"",
            ],
        ),
        "T1003": Technique(
            "T1003",
            "OS credential dumping",
            [
                "python -c \"open('/tmp/lsass_dump_sim.dmp','w').write('sim')\"",
                "python -c \"print('[atomic:T1003] credential dump simulated')\"",
            ],
        ),
    }
)


def run_technique(container: str, tech: Technique) -> dict:
    """Run one technique's commands in the victim; return evidence."""
    results = []
    for cmd in tech.commands:
        proc = subprocess.run(
            ["docker", "exec", container, "sh", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=30,
        )
        results.append({"command": cmd, "rc": proc.returncode, "out": proc.stdout.strip()})
    ok = all(r["rc"] == 0 for r in results)
    return {"technique": tech.tid, "name": tech.name, "ok": ok, "steps": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--technique", "-t", help="Run one technique id (default: all)")
    parser.add_argument("--container", "-c", default="victim_sim")
    args = parser.parse_args()

    wanted = [args.technique] if args.technique else list(TECHNIQUES)
    failures = 0
    for tid in wanted:
        tech = TECHNIQUES.get(tid)
        if tech is None:
            print(f"unknown technique: {tid} (known: {sorted(TECHNIQUES)})")
            return 2
        result = run_technique(args.container, tech)
        status = "OK" if result["ok"] else "FAIL"
        print(f"[{status}] {tech.tid} — {tech.name}")
        for step in result["steps"]:
            print(f"    rc={step['rc']} {step['command'][:60]}")
        if not result["ok"]:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
