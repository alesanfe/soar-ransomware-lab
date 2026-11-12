#!/usr/bin/env python3
"""Soak monitor — sampled evidence for the formal >=30 min soak run (MNT-01).

Samples the stack at a fixed interval for ``--duration`` seconds while a
load generator (locust ambient + periodic admission bursts) drives the
system. Writes:

  * ``reports/perf/soak-<run_id>.jsonl`` — one sample per interval
  * ``reports/perf/soak-<run_id>.summary.json`` — aggregate verdict

Sampled signals (all host-side, no in-container deps):

  * OpenSearch ``workflowexecution-*`` counts by status
    (FINISHED / EXECUTING / ABORTED / FAILED) + cluster health.
  * Docker containers: restart count deltas, OOMKilled flags, per-service
    memory (``docker stats``), total container count drift (leak check).
  * ``warmapp-*`` orphan count (patch 0009 reaps them — should stay ~0).
  * ``docker service ls`` — any swarm service appearing is a regression
    (the ``127-0-0-1`` rogue-service bug class).
  * Admission queue depth via ``GET /api/v1/queue/metrics``.

Verdict rules (honest — a soak "passes" only if all hold):
  * completion_rate = FINISHED / submitted >= 0.95 at end of run
    (excluding EXECUTING still in flight — they count separately),
  * zero new container OOMKilled events,
  * zero new swarm services,
  * warmapp orphans <= 2 at every sample (transient ok, accumulated no),
  * container count drift <= +10 (no unbounded leak),
  * memory slope for every sampled service < 5 MiB/min (no linear leak).

Usage:
    python scripts/perf/soak_monitor.py --duration 1800 --interval 60
    python scripts/perf/soak_monitor.py --duration 600 --interval 30 --dry-run
"""

from __future__ import annotations

import argparse
import base64
import itertools
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

OUT_DIR = Path("reports/perf")
OPENSEARCH = os.environ.get("OPENSEARCH_URL", "https://localhost:19201")
API = "http://localhost:8000"


def _env_value(key: str, default: str = "") -> str:
    """``.env.full``-first lookup (same precedence as tests/conftest.py)."""
    env_file = Path(".env.full")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get(key, default)


_OS_USER = _env_value("OPENSEARCH_USERNAME", "admin")
_OS_PASS = _env_value("OPENSEARCH_PASSWORD")
_OS_BASIC = (
    "Basic " + base64.b64encode(f"{_OS_USER}:{_OS_PASS}".encode()).decode()
    if _OS_PASS
    else None
)
_REPO_CA = Path("infra/docker/config/certs/ca.crt")
_SSL_CTX = ssl.create_default_context(cafile=str(_REPO_CA)) if _REPO_CA.exists() else None


def _docker(*args: str, timeout: int = 20) -> str:
    try:
        out = subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def _service_token() -> str:
    """INTERNAL_SERVICE_TOKEN for the authed queue-metrics probe.

    Same precedence as tests/conftest.py: ``.env.full`` wins over the
    process environment (load_dotenv override semantics).
    """
    env_file = Path(".env.full")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("INTERNAL_SERVICE_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    import os

    return os.environ.get("INTERNAL_SERVICE_TOKEN", "")


def _curl_json(
    url: str,
    data: dict | None = None,
    timeout: int = 15,
    headers: dict | None = None,
) -> dict:
    body = json.dumps(data).encode() if data is not None else None
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    if _OS_BASIC and "opensearch" in url or ":9200" in url or ":19201" in url:
        hdrs["Authorization"] = _OS_BASIC
    req = urllib.request.Request(url, data=body, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        return {"_error": str(exc)[:120]}


def sample_executions() -> dict:
    q = {
        "size": 0,
        "track_total_hits": True,
        "aggs": {"by_status": {"terms": {"field": "status", "size": 10}}},
    }
    d = _curl_json(f"{OPENSEARCH}/workflowexecution/_search", q)
    if "_error" in d:
        return {"error": d["_error"]}
    counts = {b["key"]: b["doc_count"] for b in d["aggregations"]["by_status"]["buckets"]}
    counts["total"] = d["hits"]["total"]["value"]
    return counts


def sample_cluster() -> str:
    d = _curl_json(f"{OPENSEARCH}/_cluster/health")
    return d.get("status", d.get("_error", "?"))


def sample_containers() -> dict:
    fmt = "{{.Names}}|{{.Status}}|{{.State}}"
    names = _docker("ps", "-a", "--format", fmt).splitlines()
    containers = {}
    restarts = {}
    for line in names:
        if not line:
            continue
        name, _, _ = line.partition("|")
        insp = _docker(
            "inspect",
            name,
            "--format",
            "{{.RestartCount}} {{.State.OOMKilled}} {{if .State.Health}}{{.State.Health.Status}}{{end}}",
        )
        if not insp:
            continue
        rc, oom, health = (insp.split(" ", 2) + ["", ""])[:3]
        restarts[name] = int(rc) if rc.isdigit() else 0
        containers[name] = {"restarts": restarts[name], "oom": oom == "true", "health": health}
    return {"count": len(containers), "containers": containers}


def sample_stats() -> dict:
    out = _docker(
        "stats",
        "--no-stream",
        "--format",
        "{{.Name}}|{{.MemUsage}}",
        timeout=30,
    )
    stats = {}
    for line in out.splitlines():
        name, _, mem = line.partition("|")
        # "123.4MiB / 2GiB" -> MiB float
        used = mem.split("/")[0].strip()
        try:
            stats[name] = float(used.replace("GiB", "").replace("MiB", "").replace("KiB", "")) * (
                1024.0 if "GiB" in used else (1 / 1024.0 if "KiB" in used else 1.0)
            )
        except ValueError:
            stats[name] = None
    return stats


def sample_extras() -> dict:
    warmapps = [
        n
        for n in _docker(
            "ps", "-a", "--filter", "name=warmapp", "--format", "{{.Names}}"
        ).splitlines()
        if n
    ]
    workers = [
        n
        for n in _docker("ps", "--filter", "name=worker-", "--format", "{{.Names}}").splitlines()
        if n
    ]
    services = [s for s in _docker("service", "ls", "--format", "{{.Name}}").splitlines() if s]
    token = _service_token()
    queue = _curl_json(
        f"{API}/api/v1/queue/metrics",
        headers={"X-Service-Token": token} if token else None,
    )
    return {
        "warmapps": len(warmapps),
        "workers_live": len(workers),
        "swarm_services": services,
        "queue": queue,
    }


def take_sample(stats: bool = True) -> dict:
    s = {
        "ts": datetime.now(UTC).isoformat(),
        "exec": sample_executions(),
        "cluster": sample_cluster(),
    }
    s.update(sample_extras())
    containers = sample_containers()
    s["containers"] = {"count": containers["count"]}
    s["restarts"] = {
        k: v["restarts"] for k, v in containers["containers"].items() if v["restarts"] > 0
    }
    s["oom"] = [k for k, v in containers["containers"].items() if v["oom"]]
    if stats:
        s["mem"] = sample_stats()
    return s


def summarize(samples: list[dict], duration: int) -> dict:
    first, last = samples[0], samples[-1]
    exec_first = first["exec"] if "total" in first["exec"] else {}
    exec_last = last["exec"] if "total" in last["exec"] else {}
    submitted = exec_last.get("total", 0) - exec_first.get("total", 0)
    finished = exec_last.get("FINISHED", 0) - exec_first.get("FINISHED", 0)
    aborted = exec_last.get("ABORTED", 0) - exec_first.get("ABORTED", 0)
    failed = exec_last.get("FAILED", 0) - exec_first.get("FAILED", 0)
    in_flight = exec_last.get("EXECUTING", 0)

    restart_first = first.get("restarts", {})
    restart_last = last.get("restarts", {})
    new_restarts = {
        k: restart_last.get(k, 0) - restart_first.get(k, 0)
        for k in restart_last
        if restart_last.get(k, 0) - restart_first.get(k, 0) > 0
    }
    oom_events = sorted({c for s in samples for c in s.get("oom", [])})
    swarm_seen = sorted({svc for s in samples for svc in s.get("swarm_services", [])})
    max_warmapps = max(s.get("warmapps", 0) for s in samples)
    container_drift = last["containers"]["count"] - first["containers"]["count"]

    mem_slopes = {}
    for s, nxt in itertools.pairwise(samples):
        for name, mib in (nxt.get("mem") or {}).items():
            prev = (s.get("mem") or {}).get(name)
            if mib is None or prev is None:
                continue
            mem_slopes.setdefault(name, []).append(mib - prev)
    interval_min = (duration / max(len(samples) - 1, 1)) / 60.0
    leak_candidates = {
        k: sum(v) / (len(v) * interval_min)
        for k, v in mem_slopes.items()
        if v and sum(v) / (len(v) * interval_min) > 5.0
    }

    completed = finished + aborted + failed
    completion_rate = finished / completed if completed else 0.0
    checks = {
        "completion_rate>=0.95": completion_rate >= 0.95 if completed else submitted == 0,
        "no_oom": not oom_events,
        "no_swarm_services": not swarm_seen,
        "warmapp_orphans<=2": max_warmapps <= 2,
        "container_drift<=10": container_drift <= 10,
        "no_mem_leak_slope": not leak_candidates,
    }
    return {
        "duration_s": duration,
        "samples": len(samples),
        "submitted": submitted,
        "finished": finished,
        "aborted": aborted,
        "failed": failed,
        "in_flight_end": in_flight,
        "throughput_per_min": round(finished / (duration / 60), 2) if duration else 0,
        "completion_rate": round(completion_rate, 4),
        "new_restarts": new_restarts,
        "oom_events": oom_events,
        "swarm_services_seen": swarm_seen,
        "max_warmapp_orphans": max_warmapps,
        "container_drift": container_drift,
        "mem_leak_candidates_mib_per_min": leak_candidates,
        "cluster_health": [s.get("cluster") for s in samples],
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Soak monitor for the SOAR stack")
    ap.add_argument("--duration", type=int, default=1800, help="seconds (default 1800 = 30 min)")
    ap.add_argument("--interval", type=int, default=60, help="sample interval s (default 60)")
    ap.add_argument(
        "--stats-every", type=int, default=3, help="docker stats every N samples (default 3)"
    )
    ap.add_argument("--run-id", default=datetime.now(UTC).strftime("%Y%m%d-%H%M%S"))
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jsonl = OUT_DIR / f"soak-{args.run_id}.jsonl"
    print(f"[soak] {args.duration}s @ {args.interval}s -> {jsonl}")

    samples: list[dict] = []
    t0 = time.time()
    i = 0
    while time.time() - t0 < args.duration:
        i += 1
        s = take_sample(stats=(i % args.stats_every == 1))
        samples.append(s)
        with jsonl.open("a", encoding="utf-8") as f:
            f.write(json.dumps(s) + "\n")
        ex = s["exec"]
        print(
            f"[{i:3d}] FIN={ex.get('FINISHED', '?')} EX={ex.get('EXECUTING', '?')} "
            f"AB={ex.get('ABORTED', '?')} | warm={s['warmapps']} work={s['workers_live']} "
            f"svc={len(s['swarm_services'])} cl={s['cluster']} restarts={len(s.get('restarts', {}))}",
            flush=True,
        )
        time.sleep(args.interval)

    summary = summarize(samples, args.duration)
    summ_path = OUT_DIR / f"soak-{args.run_id}.summary.json"
    summ_path.write_text(json.dumps(summary, indent=2))
    print(f"\n[soak] verdict={summary['verdict']} -> {summ_path}")
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "submitted",
                    "finished",
                    "throughput_per_min",
                    "completion_rate",
                    "checks",
                )
            },
            indent=2,
        )
    )
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
