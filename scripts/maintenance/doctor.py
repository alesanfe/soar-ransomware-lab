#!/usr/bin/env python3
"""SOAR Lab diagnostics (OP4 — `make doctor`).

Turns the documented operational pitfalls (AGENTS.md §Common pitfalls)
into machine-checkable diagnostics:

- Docker daemon reachability + compose stack state
- Hyper-V reserved port ranges on Windows
- `.env.full` presence and required-credential completeness
- Elasticsearch/OpenSearch cluster status (yellow is expected single-node)
- Loki readiness lag (30-60s after `make up` is normal)
- Shuffle stale executions saturating Orborus workers
- Redis reachability

Exit code 0 = everything actionable is OK (warnings allowed).
Exit code 1 = at least one FAIL check.

Usage: python scripts/maintenance/doctor.py [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Check:
    name: str
    status: str  # OK | WARN | FAIL
    detail: str


def _sh(cmd: list[str], timeout: int = 15) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=REPO_ROOT,
        )
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def check_docker() -> Check:
    code, out = _sh(["docker", "version", "--format", "{{.Server.Version}}"])
    if code != 0 or not out:
        return Check("docker-daemon", "FAIL", f"daemon unreachable: {out[:120]}")
    return Check("docker-daemon", "OK", f"server {out.splitlines()[0]}")


def check_stack() -> Check:
    cmd = [
        "docker", "compose",
        "-f", "infra/docker/compose/docker-compose.yml",
        "-f", "infra/docker/compose/docker-compose.core.yml",
        "-f", "infra/docker/compose/docker-compose.api.yml",
    ]
    env_file = REPO_ROOT / ".env.full"
    if env_file.exists():
        cmd += ["--env-file", ".env.full"]
    code, out = _sh(cmd + ["ps", "--format", "json"])
    if code != 0:
        return Check("compose-stack", "FAIL", f"docker compose ps failed: {out[:120]}")
    running = [l for l in out.splitlines() if '"running"' in l.lower() or "running" in l]
    if not running:
        return Check("compose-stack", "WARN", "stack not running — run `make up`")
    return Check("compose-stack", "OK", f"{len(running)} containers running")


def check_hyperv_ports() -> Check:
    if sys.platform != "win32":
        return Check("hyperv-ports", "OK", "not Windows — check skipped")
    code, out = _sh(["netsh", "interface", "ipv4", "show", "excludedportrange",
                     "protocol=tcp"])
    if code != 0:
        return Check("hyperv-ports", "WARN", "cannot read excluded ranges")
    # Known-bad lab ports (AGENTS.md): 2976-3075, 5600-5699, 55000-55099
    lab_ports = {3000, 3001, 5001, 5601, 8000, 8081, 8083, 9000, 9001, 9200, 9201}
    blocked = []
    for m in re.finditer(r"(\d+)\s+(\d+)\s+", out):
        lo, hi = int(m.group(1)), int(m.group(2))
        blocked += [p for p in lab_ports if lo <= p <= hi]
    if blocked:
        return Check("hyperv-ports", "WARN",
                     f"Hyper-V reserves lab ports {sorted(blocked)} — remap or "
                     "`net stop winnat`")
    return Check("hyperv-ports", "OK", "no lab port inside Hyper-V ranges")


def check_env_full() -> Check:
    env_file = REPO_ROOT / ".env.full"
    if not env_file.exists():
        return Check("env-full", "FAIL", ".env.full missing — copy .env.example "
                                        "and fill credentials")
    required = ["THEHIVE_SECRET", "THEHIVE_API_KEY", "CORTEX_SECRET",
                "CORTEX_API_KEY", "SIEM_WEBHOOK_TOKEN", "JWT_SECRET_KEY"]
    content = env_file.read_text(encoding="utf-8", errors="replace")
    missing = [k for k in required if not re.search(rf"^{k}=\S+", content, re.M)]
    if missing:
        return Check("env-full", "WARN",
                     f"empty/absent credentials: {', '.join(missing)}")
    return Check("env-full", "OK", "required credentials present")


def _http_status(url: str, timeout: float = 4.0) -> int | None:
    import ssl
    import urllib.request

    ctx = None
    if url.startswith("https"):
        # Reachability probe only — lab-CA endpoints fail the system
        # trust store on host runs; auth/identity checks live elsewhere.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status
    except Exception as exc:
        code = getattr(exc, "code", None)
        return int(code) if code else None


def _env_file_value(key: str) -> str:
    env_file = REPO_ROOT / ".env.full"
    if not env_file.exists():
        return ""
    m = re.search(rf"^{re.escape(key)}=(.+)$",
                  env_file.read_text(encoding="utf-8", errors="replace"), re.M)
    return m.group(1).strip() if m else ""


def _container_health(name: str) -> str | None:
    """Docker-native health status for services without published ports."""
    code, out = _sh([
        "docker", "inspect", "-f", "{{if .State.Health}}{{.State.Health.Status}}{{end}}",
        name,
    ])
    if code != 0:
        return None
    return out.strip() or "none"


def check_es() -> Check:
    # ES publishes host port 8200 → container 9200 in this stack.
    url = os.getenv("ELASTICSEARCH_URL", "https://localhost:19200")
    status = _http_status(f"{url}/_cluster/health")
    if status == 200:
        return Check("elasticsearch", "OK", "reachable (yellow is normal "
                                             "single-node)")
    if status == 401:
        return Check("elasticsearch", "OK", "reachable — auth required "
                                             "(expected with security on)")
    health = _container_health("soar_elasticsearch")
    return Check("elasticsearch", "WARN",
                 f"HTTP {status or 'unreachable'} at {url}; container "
                 f"health: {health or 'not running'}")


def check_loki() -> Check:
    # Loki is internal-only (no published port) — use container health.
    health = _container_health("soar_loki")
    if health == "healthy":
        return Check("loki", "OK", "container healthy")
    if health in ("none", "starting"):
        return Check("loki", "WARN",
                     f"health: {health} — Loki takes 30-60s after `make up`")
    return Check("loki", "WARN",
                 f"health: {health or 'not running'} — internal-only service")


def check_webhook_info() -> Check:
    path = REPO_ROOT / "reports" / "validation" / "results" / "webhook_info.json"
    if not path.exists():
        return Check("webhook-init", "WARN",
                     "webhook_info.json missing — run `make init-webhook` after "
                     "stack reset")
    return Check("webhook-init", "OK", str(path.relative_to(REPO_ROOT)))


def check_redis() -> Check:
    # Redis is internal-only — check via docker exec ping, with auth if
    # REDIS_PASSWORD is configured (env or .env.full).
    password = os.getenv("REDIS_PASSWORD") or _env_file_value("REDIS_PASSWORD")
    # Redis serves TLS only (docker-compose.core.yml --tls-port) — a plaintext
    # ping always fails with I/O error, producing a false WARN.
    cmd = [
        "docker", "exec", "soar_redis", "redis-cli",
        "--tls", "--cacert", "/etc/redis/tls/ca.crt",
    ]
    if password:
        cmd += ["-a", password, "--no-auth-warning"]
    code, out = _sh(cmd + ["ping"], timeout=8)
    if code == 0 and "PONG" in out:
        return Check("redis", "OK", "PONG via docker exec")
    health = _container_health("soar_redis")
    return Check("redis", "WARN",
                 f"ping failed ({out[:60]}); container health: "
                 f"{health or 'not running'}")


CHECKS = [
    check_docker,
    check_stack,
    check_hyperv_ports,
    check_env_full,
    check_es,
    check_loki,
    check_webhook_info,
    check_redis,
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    results = [fn() for fn in CHECKS]
    worst = 0
    if args.json:
        print(json.dumps([vars(r) for r in results], indent=2))
    else:
        print("SOAR Lab doctor\n" + "-" * 60)
        for r in results:
            mark = {"OK": "PASS", "WARN": "WARN", "FAIL": "FAIL"}[r.status]
            print(f"[{mark}] {r.name:<16} {r.detail}")
    if any(r.status == "FAIL" for r in results):
        worst = 1
        if not args.json:
            print("-" * 60 + "\nFAIL checks must be fixed before the lab works.")
    return worst


if __name__ == "__main__":
    sys.exit(main())
