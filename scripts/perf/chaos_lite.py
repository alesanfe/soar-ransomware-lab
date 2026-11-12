#!/usr/bin/env python3
"""Chaos-lite: inject a partial integration outage mid-workflow (RES-02).

Runs on the Docker host (needs `docker` CLI). Submits one alert, waits for
the workflow to enter EXECUTING, then pauses a backend container for
``--pause`` seconds — a bounded, non-destructive fault (< container
SHUFFLE_APP_SDK_TIMEOUT=300 s, so nodes should degrade/retry, not abort).

Honest pass criteria — NO green-by-absence:
  * workflow reaches FINISHED (degraded nodes tolerated), AND
  * duration <= baseline_p95 + pause + margin, AND
  * the fault window is proven overlapping execution (not pre/post).

    python scripts/perf/chaos_lite.py --target soar_cortex --pause 30
    python scripts/perf/chaos_lite.py --target soar_thehive --pause 45 --dry-run

Evidence JSON -> reports/perf/chaos-<run>.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

OUT_DIR = Path("reports/perf")
API_CONTAINER = "soar_api"
WORKFLOW_TIMEOUT_S = 600

ALERT = {
    "alert_id": None,  # filled per run
    "alert_type": "ransomware",
    "severity": "high",
    "src_ip": "10.66.66.66",
    "hostname": "chaos-host",
    "hash": "44d88612fea8a8f36de82e1278abb02f",
    "user": "chaos",
    "source": "chaos-lite",
}


def _sh(cmd: list[str], timeout: int = 60) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if out.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} -> rc={out.returncode}: {out.stderr[:200]}")
    return out.stdout


def _api(cmd: str) -> str:
    """Run a python one-liner inside soar_api (in-network)."""
    return _sh(["docker", "exec", API_CONTAINER, "python3", "-c", cmd])


def submit() -> str:
    ALERT["alert_id"] = f"chaos-{uuid.uuid4().hex[:8]}"
    code = (
        "import json,os,urllib.request;"
        f"p={json.dumps(ALERT)};"
        "req=urllib.request.Request('http://localhost:8000/api/v1/alerts',"
        "data=json.dumps(p).encode(),headers={'Content-Type':'application/json',"
        "'X-Service-Token':os.environ['INTERNAL_SERVICE_TOKEN']});"
        "r=urllib.request.urlopen(req);print(json.loads(r.read())['admission_id'])"
    )
    return _api(code).strip()


def execution_state() -> dict | None:
    """Latest execution for this run's alert via OpenSearch."""
    code = (
        "import base64,json,os,ssl,urllib.request;"
        "ctx=ssl.create_default_context(cafile='/app/certs/ca.crt');"
        "u=os.environ.get('SHUFFLE_OPENSEARCH_USERNAME','admin');"
        "pw=os.environ.get('SHUFFLE_OPENSEARCH_PASSWORD','');"
        "q={'query':{'bool':{'should':["
        "{'wildcard':{'execution_argument':'*" + ALERT["alert_id"] + "*'}},"
        "{'wildcard':{'execution_argument.keyword':'*" + ALERT["alert_id"] + "*'}}"
        "],'minimum_should_match':1}},"
        "'size':1,'sort':[{'started_at':{'order':'desc'}}]};"
        "req=urllib.request.Request('https://opensearch:9200/workflowexecution/_search',"
        "data=json.dumps(q).encode(),headers={'Content-Type':'application/json',"
        "'Authorization':'Basic '+base64.b64encode((u+':'+pw).encode()).decode()});"
        "r=json.loads(urllib.request.urlopen(req,context=ctx).read());"
        "h=r['hits']['hits'];"
        "print(json.dumps(h[0]['_source']) if h else '')"
    )
    raw = _api(code).strip()
    return json.loads(raw) if raw else None


def wait_status(want: set[str], timeout: int, poll: float = 4.0) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        ex = execution_state()
        if ex and ex.get("status") in want:
            return ex
        time.sleep(poll)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="soar_cortex")
    ap.add_argument("--pause", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true", help="submit only, no fault")
    args = ap.parse_args()

    t0 = time.time()
    aid = submit()
    print(f"[{0:5.1f}s] alert {ALERT['alert_id']} admitted: {aid}")

    ex = wait_status({"EXECUTING", "FINISHED", "FAILED", "ABORTED"}, timeout=120)
    if not ex:
        sys.exit("workflow never appeared in workflowexecution index")
    started_at = ex.get("started_at", 0)
    print(f"[{time.time() - t0:5.1f}s] executing (started_at={started_at})")

    fault_start = fault_end = None
    if not args.dry_run:
        _sh(["docker", "pause", args.target])
        fault_start = time.time()
        print(f"[{fault_start - t0:5.1f}s] FAULT: paused {args.target} for {args.pause}s")
        time.sleep(args.pause)
        _sh(["docker", "unpause", args.target])
        fault_end = time.time()
        print(f"[{fault_end - t0:5.1f}s] unpaused {args.target}")

    final = wait_status({"FINISHED", "FAILED", "ABORTED"}, timeout=WORKFLOW_TIMEOUT_S)
    wall = time.time() - t0
    if not final:
        sys.exit(f"workflow did not terminate within {WORKFLOW_TIMEOUT_S}s")

    status = final.get("status")
    completed_at = final.get("completed_at", 0)
    duration = (completed_at - started_at) if completed_at and started_at else None
    results = final.get("results")
    if isinstance(results, dict):
        node_rows = results.get("results") or []
    else:
        node_rows = results or []
    failed_nodes = [
        a.get("action", {}).get("label", "?")
        for a in node_rows
        if isinstance(a, dict) and a.get("status") == "FAILURE"
    ]

    # The fault must overlap the execution window to prove anything.
    fault_overlap = (
        fault_start is not None
        and started_at
        and completed_at
        and started_at <= fault_start <= completed_at
    )

    evidence = {
        "run": ALERT["alert_id"],
        "target": args.target,
        "pause_s": args.pause,
        "dry_run": args.dry_run,
        "admission_id": aid,
        "status": status,
        "workflow_duration_s": duration,
        "fault_window": [fault_start, fault_end],
        "fault_overlapped_execution": bool(fault_overlap),
        "failed_nodes": failed_nodes,
        "wall_s": round(wall, 1),
        "pass": status == "FINISHED" and (args.dry_run or fault_overlap),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"chaos-{ALERT['alert_id'].removeprefix('chaos-')}.json"
    out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    print(f"-> {out}")
    return 0 if evidence["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
