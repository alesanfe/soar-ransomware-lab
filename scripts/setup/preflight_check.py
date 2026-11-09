#!/usr/bin/env python3
"""Pre-flight environment diagnostic for the SOAR Ransomware Lab.

Runs before ``make up`` (or standalone via ``make preflight``) to catch the
most common setup failures early: Docker not running, missing compose
plugin, low disk space, busy host ports and missing env files.

Exit code is 0 when every check passes, 1 otherwise. Every failure prints an
actionable hint so the user knows what to fix before retrying.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# Host ports published by the compose stack (see infra/docker/compose/*.yml)
REQUIRED_PORTS = {
    8000: "API",
    8100: "TheHive",
    8101: "Cortex",
    5001: "Shuffle backend API",
    8081: "Shuffle frontend",
    8200: "Elasticsearch",
    8201: "OpenSearch",
    8202: "OpenSearch Dashboards",
    8083: "MISP",
    8084: "Grafana",
    8085: "Web management",
    8086: "Docs site",
    443: "Nginx (HTTPS)",
    15130: "Network Watcher",
    15160: "Tenzir",
}

# Docker Desktop on Windows reserves these ranges for Hyper-V (AGENTS.md)
WINDOWS_RESERVED = [(2976, 3075), (5600, 5699), (55000, 55099)]

MIN_DISK_GB = 20  # full image set is ~15 GB


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def check_docker() -> bool:
    code, out = _run(["docker", "info", "--format", "{{.ServerVersion}}"])
    if code != 0:
        print("FAIL  Docker daemon is not reachable.")
        print("      -> Start Docker Desktop and retry.")
        return False
    print(f"OK    Docker engine {out}")
    return True


COMPOSE_MIN = (2, 24)  # !reset / !override in the hardened overlay (BUG-053)


def check_compose() -> bool:
    code, out = _run(["docker", "compose", "version", "--short"])
    if code != 0:
        print("FAIL  Docker Compose plugin missing.")
        print("      -> Install the compose plugin or Docker Desktop >= 3.x.")
        return False
    try:
        parts = tuple(int(p) for p in out.strip().lstrip("v").split(".")[:2])
    except ValueError:
        parts = (0, 0)
    if parts < COMPOSE_MIN:
        print(f"FAIL  Docker Compose v{out} < {'.'.join(map(str, COMPOSE_MIN))}.")
        print("      -> The hardened overlay needs !reset/!override (BUG-053).")
        print("      -> Upgrade Docker Desktop / the compose plugin.")
        return False
    print(f"OK    Docker Compose v{out}")
    return True


def check_disk() -> bool:
    usage = shutil.disk_usage(ROOT)
    free_gb = usage.free / 2**30
    if free_gb < MIN_DISK_GB:
        print(f"FAIL  Only {free_gb:.1f} GB free on {ROOT.anchor} (need >= {MIN_DISK_GB} GB).")
        print("      -> Free space or run 'docker system prune'.")
        return False
    print(f"OK    {free_gb:.1f} GB free on {ROOT.anchor}")
    return True


def _port_busy(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def check_ports() -> bool:
    busy = [(p, name) for p, name in sorted(REQUIRED_PORTS.items()) if _port_busy(p)]
    if not busy:
        print(f"OK    All {len(REQUIRED_PORTS)} required host ports are free")
        return True
    # If the SOAR stack itself is running, busy ports are expected — a plain
    # restart, not a conflict. Only flag when containers are NOT ours.
    code, out = _run(["docker", "ps", "--filter", "name=soar_", "--format", "{{.Names}}"])
    stack_running = code == 0 and "soar_" in out
    if stack_running:
        print(
            f"INFO  {len(busy)} required ports are in use by the running stack"
            " (restart/update scenario — not a conflict)"
        )
        return True
    for port, name in busy:
        print(f"FAIL  Port {port} ({name}) is already in use")
    print("      -> Stop the conflicting service or remap the port in the compose file.")
    print(
        "      -> On Windows also check 'netsh interface ipv4 show excludedportrange protocol=tcp'"
    )
    return False


def check_reserved_ranges() -> bool:
    hits = [p for p in REQUIRED_PORTS if any(lo <= p <= hi for lo, hi in WINDOWS_RESERVED)]
    if not hits:
        print("OK    No required port falls inside Windows Hyper-V reserved ranges")
        return True
    print(f"WARN  Ports {hits} overlap known Hyper-V reserved ranges on Windows")
    print("      -> If bind failures appear, remap these ports or restart winnat.")
    return True  # warning only


def check_env() -> bool:
    missing = [f for f in (".env.full", ".env.example") if not (ROOT / f).exists()]
    if (ROOT / ".env.full").exists():
        print("OK    .env.full exists (canonical env)")
        if not (ROOT / ".env.container").exists():
            print("INFO  .env.container missing — regenerated by 'make up' (step 3)")
        return True
    if missing == [".env.full"]:
        print("WARN  .env.full missing — will be created from .env.example by 'make up'")
        return True
    print("FAIL  Neither .env.full nor .env.example exists")
    print("      -> Restore .env.example from the repository.")
    return False


def check_insecure_flags() -> bool:
    """Warn when dev-only insecure settings are enabled in .env (SOAR-015/016).

    ``SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY`` and ``TENZIR_WEB_MODE=dev`` are
    accepted for the local lab profile but must be visible — the hardened
    profile turns them off. Warning only; never fails the preflight.
    """
    env_file = ROOT / ".env"
    if not env_file.exists():
        return True
    values = {}
    for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip()
    warned = False
    if values.get("SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY", "").lower() == "true":
        print("WARN  SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY=true — Shuffle will not")
        print("      verify the OpenSearch certificate (lab-only; set 'false' or")
        print("      use 'make up HARDENED=1' for certificate validation).")
        warned = True
    if values.get("TENZIR_WEB_MODE", "dev") == "dev":
        print("INFO  TENZIR_WEB_MODE=dev — Tenzir runs in development mode")
        print("      (set TENZIR_WEB_MODE=server or use HARDENED=1).")
        warned = True
    if not warned:
        print("OK    No insecure dev flags enabled in .env")
    return True


def check_memory() -> bool:
    """Warn when the Docker VM has less than ~10 GB (22+ containers)."""
    code, out = _run(["docker", "info", "--format", "{{.MemTotal}}"])
    if code != 0 or not out.isdigit():
        print("WARN  Could not read Docker memory limit")
        return True
    gb = int(out) / 2**30
    if gb < 10:
        print(f"WARN  Docker reports only {gb:.1f} GB RAM; the full stack needs ~10 GB+")
        print("      -> Increase Docker Desktop memory in Settings > Resources.")
        return True
    print(f"OK    Docker memory limit {gb:.1f} GB")
    return True


CHECKS = [
    ("Docker daemon", check_docker),
    ("Compose plugin", check_compose),
    ("Disk space", check_disk),
    ("Docker memory", check_memory),
    ("Host ports", check_ports),
    ("Windows reserved ranges", check_reserved_ranges),
    ("Environment files", check_env),
    ("Insecure dev flags", check_insecure_flags),
]


def main() -> int:
    print("=== SOAR Lab pre-flight check ===\n")
    failures = 0
    for label, fn in CHECKS:
        try:
            ok = fn()
        except Exception as exc:  # never let a check crash the diagnostic
            print(f"FAIL  {label}: unexpected error: {exc}")
            ok = False
        failures += 0 if ok else 1
        print()
    if failures:
        print(f"=== {failures} check(s) FAILED — fix the hints above and retry ===")
        return 1
    print("=== All checks passed — safe to run 'make up' ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
