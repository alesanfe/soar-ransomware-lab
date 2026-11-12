#!/usr/bin/env python3
"""Continuous disk guardrail for the SOAR stack (host-side).

Periodic counterpart to ``check_disk_watermarks.py`` (one-shot, in-network).
Runs on the Docker host so it can remediate: when OpenSearch/Elasticsearch
cross the critical watermark — or flood-stage ``read_only_allow_delete``
blocks appear — it prunes stopped containers (the Orborus worker leak was
the observed root cause: ~2370 stopped workers ≈ 10.7 GB).

    python scripts/maintenance/disk_watchdog.py                 # 5-min loop, forever
    python scripts/maintenance/disk_watchdog.py --interval 60 --cycles 4
    python scripts/maintenance/disk_watchdog.py --dry-run       # report only

Thresholds mirror check_disk_watermarks.py (WARN 88 / CRIT 95). Exit code of
``--once`` mirrors it too (0 ok / 1 critical) so it doubles as a CI probe.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
import time

WARN_PCT = 88.0
CRIT_PCT = 95.0

# Containers that expose _cat/allocation — checked via exec so no host port
# mapping is required.
BACKENDS = {
    "elasticsearch": "soar_elasticsearch",
    "opensearch": "soar_opensearch",
}

# Elasticsearch serves HTTPS+basic auth (xpack); curl runs inside the
# backend container where the lab CA is already mounted.
_ES_AUTH = f"elastic:{os.environ.get('ELASTIC_PASSWORD', '')}"
_ES_CACERT = "/usr/share/elasticsearch/config/certs/ca.crt"
_OS_AUTH = f"{os.environ.get('OPENSEARCH_USERNAME', 'admin')}:{os.environ.get('OPENSEARCH_PASSWORD', '')}"
_OS_CACERT = "/usr/share/opensearch/config/certs/ca.crt"


def _cat_cmd(container: str, path: str) -> list[str]:
    """Backend-local _cat/_cluster request honouring each backend's scheme."""
    if container == "soar_elasticsearch":
        return [
            "docker", "exec", container, "curl", "-sf",
            "--cacert", _ES_CACERT, "-u", _ES_AUTH,
            f"https://localhost:9200{path}",
        ]
    return [
        "docker", "exec", container, "curl", "-sf",
        "--cacert", _OS_CACERT, "-u", _OS_AUTH,
        f"https://localhost:9200{path}",
    ]


def _run(cmd: list[str], timeout: int = 30) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    return out.stdout


def check_allocation(name: str, container: str) -> list[dict]:
    raw = _run(_cat_cmd(container, "/_cat/allocation?v&format=json"))
    try:
        nodes = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return [{"backend": name, "node": "?", "disk_pct": -1.0}]
    out = []
    for n in nodes:
        try:
            pct = float(n.get("disk.percent") or 0)
        except (TypeError, ValueError):
            pct = -1.0
        out.append({"backend": name, "node": n.get("node", "?"), "disk_pct": pct})
    return out


def flood_stage_active(container: str) -> bool:
    raw = _run(_cat_cmd(container, "/_cluster/state/blocks"))
    try:
        state = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return False
    return bool(state.get("blocks", {}).get("indices"))


STALE_EXEC_MINUTES = 30


def stale_executions() -> int:
    """Zombie Shuffle executions: EXECUTING docs older than STALE_EXEC_MINUTES.

    Nothing legitimate exceeds WORKFLOW_TIMEOUT (600 s); 30 min is a
    conservative bound. Report-only — auto-abort lives in
    ``make clean-shuffle`` (deliberate op, nukes worker containers too).
    """
    cutoff_s = int(time.time() - STALE_EXEC_MINUTES * 60)
    body = json.dumps(
        {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"status": "EXECUTING"}},
                        {"range": {"started_at": {"lt": cutoff_s}}},
                    ]
                }
            }
        }
    )
    raw = _run(
        [
            "docker",
            "exec",
            "soar_opensearch",
            "curl",
            "-sf",
            "--cacert",
            _OS_CACERT,
            "-u",
            _OS_AUTH,
            "-H",
            "Content-Type: application/json",
            "-d",
            body,
            "https://localhost:9200/workflowexecution/_count",
        ]
    )
    try:
        return int(json.loads(raw or "{}").get("count", 0))
    except (json.JSONDecodeError, TypeError, ValueError):
        return -1


def stopped_worker_containers() -> int:
    """Stopped containers spawned by Orborus (worker/analyzer leak metric)."""
    raw = _run(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            "status=exited",
            "--filter",
            "status=created",
            "--format",
            "{{.Names}}",
        ]
    )
    names = [ln for ln in raw.splitlines() if ln.strip()]
    return len([n for n in names if "worker" in n or "shuffle" in n or "cortex" in n])


def remediate() -> str:
    """Prune stopped containers — same policy as ``make clean-containers``."""
    return _run(["docker", "container", "prune", "-f"], timeout=120)


def _ts() -> str:
    return _dt.datetime.now().strftime("%H:%M:%S")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=300, help="poll seconds (default 300)")
    ap.add_argument("--cycles", type=int, default=0, help="0 = run forever")
    ap.add_argument("--dry-run", action="store_true", help="never remediate")
    ap.add_argument("--once", action="store_true", help="single check, exit 1 if critical")
    args = ap.parse_args()

    worst_rc = 0
    cycle = 0
    while True:
        cycle += 1
        nodes = []
        for name, container in BACKENDS.items():
            nodes += check_allocation(name, container)

        worst = max((n["disk_pct"] for n in nodes), default=-1.0)
        flood = flood_stage_active(BACKENDS["opensearch"])
        stopped = stopped_worker_containers()
        zombies = stale_executions()
        level = "OK"
        if worst >= CRIT_PCT or flood or worst < 0:
            level = "CRITICAL"
        elif worst >= WARN_PCT or zombies > 0:
            level = "WARN"

        detail = " ".join(
            f"{n['backend']}:{n['disk_pct']:.1f}%" if n["disk_pct"] >= 0 else f"{n['backend']}:ERR"
            for n in nodes
        )
        print(
            f"[{_ts()}] {level:<8} disk[{detail}] flood={flood} "
            f"stopped_workers={stopped} stale_execs={zombies}",
            flush=True,
        )

        critical = level == "CRITICAL"
        if critical:
            worst_rc = 1
            if not args.dry_run:
                out = remediate()
                reclaimed = [ln for ln in out.splitlines() if "reclaimed" in ln.lower()]
                print(
                    f"[{_ts()}]   auto-remediation: container prune "
                    f"({reclaimed[-1].strip() if reclaimed else 'done'})",
                    flush=True,
                )

        if args.once or (args.cycles and cycle >= args.cycles):
            break
        time.sleep(args.interval)

    return worst_rc


if __name__ == "__main__":
    sys.exit(main())
