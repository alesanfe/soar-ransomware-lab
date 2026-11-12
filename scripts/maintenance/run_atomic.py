#!/usr/bin/env python3
"""Execute atomic-style test techniques inside the victim container (F2).

Each technique runs *bounded, non-destructive* commands inside
``victim_sim`` and emits a telemetry line tagged ``[atomic:<tid>]`` —
written to ``/proc/1/fd/1``, the container PID-1 stdout, so the
json-file log driver captures it and Promtail ships it to Loki. A
plain ``docker exec`` only prints to the caller's TTY and the
detection path would see **nothing** (VICTIM-EVAL-006).

Coverage model (MITRE ATT&CK / CALDERA / Atomic Red Team):

- Each :class:`Technique` is an *ability*: ordered ``commands``,
  a ``tactic``, and ``cleanup`` commands (CALDERA-style) that remove
  the artifacts so runs are repeatable/idempotent.
- ``PROFILES`` are CALDERA-style adversary profiles: an ordered
  kill-chain executed end-to-end.

Honest scope: this is an atomic-test *harness*, not a real Atomic Red
Team install — commands simulate each technique's observable
behavior without destructive payloads. Extend ``TECHNIQUES`` to add
coverage.

Usage:
    python scripts/maintenance/run_atomic.py                  # all techniques
    python scripts/maintenance/run_atomic.py -t T1486         # one technique
    python scripts/maintenance/run_atomic.py -p ransomware    # kill-chain profile
    python scripts/maintenance/run_atomic.py --no-cleanup     # leave artifacts
"""

import argparse
import subprocess
import sys
from typing import NamedTuple

# Telemetry sink: PID-1 stdout — the only path Promtail actually sees.
SINK = "/proc/1/fd/1"


class Technique(NamedTuple):
    tid: str
    name: str
    tactic: str
    commands: list[str]
    cleanup: list[str] = []


def _t(tid: str, *lines: str) -> list[str]:
    """Telemetry lines for a technique, tagged and sunk to PID-1 stdout."""
    return [f'echo "[atomic:{tid}] {line}" >> {SINK}' for line in lines]


TECHNIQUES: dict[str, Technique] = {
    "T1059": Technique(
        "T1059", "Command and scripting interpreter", "execution",
        _t("T1059", "suspicious shell exec: python -c spawned"),
    ),
    "T1082": Technique(
        "T1082", "System information discovery", "discovery",
        _t("T1082", "system info discovery: uname -a; cat /etc/os-release")
        + ["uname -a", "cat /etc/os-release"],
    ),
    "T1083": Technique(
        "T1083", "File and directory discovery", "discovery",
        _t("T1083", "file discovery sweep: find / -name '*.doc*'")
        + ["find /tmp -type f 2>/dev/null | head -5"],
    ),
    "T1053": Technique(
        "T1053", "Scheduled task/job (persistence)", "persistence",
        _t("T1053", "cron persistence simulated: wrote /tmp/cron_persist")
        + ["echo '* * * * * /tmp/x' > /tmp/cron_persist"],
        ["rm -f /tmp/cron_persist"],
    ),
    "T1070": Technique(
        "T1070", "Indicator removal (defense evasion)", "defense-evasion",
        _t("T1070", "log tampering simulated: history delete")
        + ["echo hist > /tmp/fake_history && rm -f /tmp/fake_history"],
    ),
    "T1003": Technique(
        "T1003", "OS credential dumping", "credential-access",
        _t("T1003", "credential dump simulated: /tmp/lsass_dump_sim.dmp")
        + ["python3 -c \"open('/tmp/lsass_dump_sim.dmp','w').write('sim')\""],
        ["rm -f /tmp/lsass_dump_sim.dmp"],
    ),
    "T1005": Technique(
        "T1005", "Data from local system", "collection",
        _t("T1005", "sensitive file access simulated: /etc/shadow read attempt")
        + ["cat /etc/passwd | head -3"],
    ),
    "T1560": Technique(
        "T1560", "Archive collected data", "collection",
        _t("T1560", "archive staged: /tmp/loot_sim.tar")
        + ["tar -cf /tmp/loot_sim.tar /tmp 2>/dev/null || true"],
        ["rm -f /tmp/loot_sim.tar"],
    ),
    "T1071": Technique(
        "T1071", "Application layer protocol (C2)", "command-and-control",
        _t("T1071", "C2 beacon simulated: periodic HTTPS check-in pattern"),
    ),
    "T1490": Technique(
        "T1490", "Inhibit system recovery", "impact",
        _t("T1490", "vssadmin delete shadows simulated"),
    ),
    "T1486": Technique(
        "T1486", "Data encrypted for impact", "impact",
        _t("T1486", "mass file encryption simulated: wrote /tmp/enc_sim.crypt")
        + ["python3 -c \"open('/tmp/enc_sim.crypt','w').write('simulated-encrypted')\""],
        ["rm -f /tmp/enc_sim.crypt"],
    ),
}

# CALDERA-style adversary profiles: ordered kill-chains.
PROFILES: dict[str, list[str]] = {
    "ransomware": [
        "T1082", "T1083", "T1053", "T1070", "T1003",
        "T1005", "T1560", "T1071", "T1490", "T1486",
    ],
}


def run_technique(container: str, tech: Technique, cleanup: bool = True) -> dict:
    """Run one technique's commands in the victim; return evidence."""
    results = []
    for cmd in [*tech.commands, *(tech.cleanup if cleanup else [])]:
        proc = subprocess.run(
            ["docker", "exec", container, "sh", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=30,
        )
        results.append({"command": cmd, "rc": proc.returncode, "out": proc.stdout.strip()})
    ok = all(r["rc"] == 0 for r in results)
    return {"technique": tech.tid, "name": tech.name, "tactic": tech.tactic,
            "ok": ok, "steps": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--technique", "-t", help="Run one technique id")
    parser.add_argument("--profile", "-p", choices=sorted(PROFILES),
                        help="Run a kill-chain profile")
    parser.add_argument("--container", "-c", default="victim_sim")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Leave technique artifacts in place")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List techniques, tactics and profiles")
    args = parser.parse_args()

    if args.list:
        for tid, tech in sorted(TECHNIQUES.items()):
            print(f"{tid} [{tech.tactic}] {tech.name}")
        print(f"profiles: {', '.join(sorted(PROFILES))}")
        return 0

    if args.profile:
        wanted = PROFILES[args.profile]
    elif args.technique:
        wanted = [args.technique]
    else:
        wanted = list(TECHNIQUES)

    failures = 0
    for tid in wanted:
        tech = TECHNIQUES.get(tid)
        if tech is None:
            print(f"unknown technique: {tid} (known: {sorted(TECHNIQUES)})")
            return 2
        result = run_technique(args.container, tech, cleanup=not args.no_cleanup)
        status = "OK" if result["ok"] else "FAIL"
        print(f"[{status}] {tech.tid} [{tech.tactic}] {tech.name}")
        for step in result["steps"]:
            print(f"    rc={step['rc']} {step['command'][:60]}")
        if not result["ok"]:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
