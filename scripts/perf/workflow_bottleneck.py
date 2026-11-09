#!/usr/bin/env python3
"""Workflow bottleneck detector — aggregates per-node timings across recent
Shuffle executions and ranks the nodes that dominate workflow latency.

Queries OpenSearch ``workflowexecution-*`` for the last N FINISHED
executions, reuses ``NodeTimingExtractor.extract_timings`` (pure function —
no HTTP) per document, and produces:

- ``nodes``: per-label stats (n, mean/P50/P95/max duration, share of total
  node time) — the bottleneck ranking.
- ``workflow``: duration percentiles across executions.
- ``orchestration_overhead``: per-execution gap between the workflow wall
  clock and the first-node-start→last-node-end span (scheduling/dispatch
  overhead outside node runtime).
- ``queue_wait_s``: ``execution.started_at - alert.timestamp`` when the
  execution args carry the alert ``timestamp`` field — measures the
  admission→dispatch path (queue wait + webhook forward + Shuffle
  scheduling) that node timings cannot see.

Run inside the ``soar_api`` container::

    docker exec soar_api python3 /app/scripts/perf/workflow_bottleneck.py \
        --size 30 --out /app/reports/perf/bottleneck.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from soar_lab.application.use_cases.node_timing_extractor import NodeTimingExtractor

OPENSEARCH_URL = os.environ.get("OPENSEARCH_URL", "http://opensearch:9200")
EXECUTION_INDEX = os.environ.get("SHUFFLE_EXECUTION_INDEX", "workflowexecution")


def _pct(sorted_vals: list[float], q: float) -> float:
    return sorted_vals[min(int(q * len(sorted_vals)), len(sorted_vals) - 1)]


def fetch_finished_executions(size: int, os_url: str = OPENSEARCH_URL) -> list[dict[str, Any]]:
    """Fetch the ``size`` most recent FINISHED workflow executions."""
    body = json.dumps(
        {
            "size": size,
            "sort": [{"started_at": {"order": "desc"}}],
            "query": {"term": {"status": "FINISHED"}},
        }
    ).encode()
    req = urllib.request.Request(
        f"{os_url.rstrip('/')}/{EXECUTION_INDEX}/_search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return [h["_source"] for h in data.get("hits", {}).get("hits", [])]


def _alert_timestamp(execution: dict[str, Any]) -> float | None:
    """Best-effort extraction of the alert submission timestamp.

    Shuffle echoes the webhook payload in ``execution_argument``; the
    simulator/e2e payloads carry a ``timestamp`` (epoch seconds) field.
    Returns None when unavailable — queue wait is then not measurable.
    """
    raw = execution.get("execution_argument") or ""
    if isinstance(raw, dict):
        arg = raw
    else:
        try:
            arg = json.loads(raw)
        except (TypeError, ValueError):
            return None
    ts = arg.get("timestamp") or arg.get("detection_time")
    if ts is None:
        return None
    try:
        return float(ts)  # epoch seconds (e2e/load payloads)
    except (TypeError, ValueError):
        pass
    # ISO-8601 ``detection_time`` (simulator/TC payloads)
    if isinstance(ts, str):
        try:
            from datetime import datetime

            return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except (TypeError, ValueError):
            return None
    return None


def extract_queue_wait(execution: dict[str, Any]) -> float | None:
    """Seconds between alert submission and workflow start (dispatch path)."""
    alert_ts = _alert_timestamp(execution)
    started = execution.get("started_at")
    if alert_ts is None or not started:
        return None
    try:
        wait = float(started) - alert_ts
    except (TypeError, ValueError):
        return None
    # Negative waits mean clock skew between alert source and Shuffle — the
    # measurement is meaningless, not a negative queue.
    return wait if wait >= 0 else None


def scheduling_gap(node_intervals: list[tuple[float, float]]) -> tuple[float, float]:
    """Dead wall-clock time inside the node span — union-complement metric.

    The old ``orchestration_overhead`` (wall minus first-start→last-end)
    stays ~0 whenever any node runs, which masks the real loss: *inside*
    the span there are dead gaps where NO node runs (worker→backend
    scheduling latency between dependent branches — measured ~3 s per
    transition in the sequential tail, ~25 % of workflow wall time).

    Returns ``(gap_seconds, gap_ratio)`` = span − union coverage and its
    fraction of the node span. Works with overlapping (parallel) nodes —
    only truly idle time counts.
    """
    if not node_intervals:
        return 0.0, 0.0
    ivs = sorted(node_intervals)
    span_start, span_end = ivs[0][0], max(e for _, e in ivs)
    coverage = 0.0
    cur_s, cur_e = ivs[0]
    for s, e in ivs[1:]:
        if s <= cur_e:  # overlap/touch — extend current union segment
            cur_e = max(cur_e, e)
        else:
            coverage += cur_e - cur_s
            cur_s, cur_e = s, e
    coverage += cur_e - cur_s
    span = span_end - span_start
    gap = max(0.0, span - coverage)
    return round(gap, 3), round(gap / span, 4) if span > 0 else 0.0


def aggregate_executions(executions: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-node + per-workflow timings into a bottleneck report."""
    extractor = NodeTimingExtractor()
    node_durations: dict[str, list[float]] = {}
    node_statuses: dict[str, dict[str, int]] = {}
    wf_durations: list[float] = []
    overheads: list[float] = []
    sched_gaps: list[float] = []
    sched_ratios: list[float] = []
    queue_waits: list[float] = []
    per_execution: list[dict[str, Any]] = []
    invalid_total = 0

    for ex in executions:
        t = extractor.extract_timings(ex)
        invalid_total += t["data_quality"]["invalid_node_timings"]
        gap_s = gap_ratio = None

        if t["workflow_duration_s"] > 0:
            wf_durations.append(t["workflow_duration_s"])

        # Orchestration overhead: wall clock minus first-start→last-end span
        if t["nodes"] and t["workflow_duration_s"] > 0:
            spans = [info["start_offset_s"] + info["duration_s"] for info in t["nodes"].values()]
            node_span = max(spans) if spans else 0.0
            overheads.append(round(t["workflow_duration_s"] - node_span, 3))

            # Scheduling gap: idle wall-clock inside the span (union
            # complement) — catches the dead ~3s transitions between
            # dependent nodes that overhead-per-execution cannot see.
            intervals = [
                (info["start_offset_s"], info["start_offset_s"] + info["duration_s"])
                for info in t["nodes"].values()
            ]
            gap_s, gap_ratio = scheduling_gap(intervals)
            sched_gaps.append(gap_s)
            sched_ratios.append(gap_ratio)

        qw = extract_queue_wait(ex)
        if qw is not None:
            queue_waits.append(round(qw, 3))

        for label, info in t["nodes"].items():
            node_durations.setdefault(label, []).append(info["duration_s"])
            st = node_statuses.setdefault(label, {})
            for s in info["statuses"]:
                st[s] = st.get(s, 0) + 1

        per_execution.append(
            {
                "execution_id": t["execution_id"],
                "workflow_duration_s": t["workflow_duration_s"],
                "total_nodes": t["total_nodes"],
                "top3": [n["label"] for n in t["slowest_nodes"][:3]],
                "invalid_node_timings": t["data_quality"]["invalid_node_timings"],
                "scheduling_gap_s": gap_s,
                "scheduling_gap_ratio": gap_ratio,
            }
        )

    total_node_time = sum(sum(v) for v in node_durations.values())
    node_stats = []
    for label, durs in node_durations.items():
        d = sorted(durs)
        agg = sum(d)
        node_stats.append(
            {
                "label": label,
                "executions": len(d),
                "mean_s": round(agg / len(d), 3),
                "p50_s": round(_pct(d, 0.5), 3),
                "p95_s": round(_pct(d, 0.95), 3),
                "max_s": round(d[-1], 3),
                "total_s": round(agg, 3),
                "share_of_node_time": (
                    round(agg / total_node_time, 4) if total_node_time > 0 else 0.0
                ),
                "statuses": node_statuses.get(label, {}),
            }
        )
    node_stats.sort(key=lambda n: n["total_s"], reverse=True)

    def _dist(vals: list[float]) -> dict[str, float] | None:
        if not vals:
            return None
        s = sorted(vals)
        return {
            "n": len(s),
            "p50": round(_pct(s, 0.5), 3),
            "p95": round(_pct(s, 0.95), 3),
            "max": round(s[-1], 3),
            "min": round(s[0], 3),
        }

    return {
        "generated_at": time.time(),
        "executions_analyzed": len(executions),
        "nodes": node_stats,
        "bottleneck_top5": [n["label"] for n in node_stats[:5]],
        "workflow_duration_s": _dist(wf_durations),
        "orchestration_overhead_s": _dist(overheads),
        "scheduling_gap_s": _dist(sched_gaps),
        "scheduling_gap_ratio": _dist(sched_ratios),
        "queue_wait_s": _dist(queue_waits),
        "data_quality": {"invalid_node_timings_total": invalid_total},
        "per_execution": per_execution,
    }


# ── Bottleneck detection rules ───────────────────────────────────────────────
# Thresholds tuned from the measured baseline (40 executions):
#   queue_wait P50=0.007s, orchestration_overhead≈0, top node share≈10%.
DOMINANT_NODE_SHARE = 0.40  # one node eating >40% of node time = hotspot
SLOW_NODE_P95_S = 30.0  # node-level tail latency worth investigating
QUEUE_WAIT_P95_S = 5.0  # admission→start should stay sub-second
ORCHESTRATION_OVERHEAD_P95_S = 15.0  # Shuffle dispatch overhead should be ~0
WORKFLOW_P95_S = 600.0  # e2e wait timeout — P95 above it means timing failures
SCHEDULING_GAP_P95_S = 15.0  # dead time inside the node span (measured ~14s)
SCHEDULING_GAP_RATIO = 0.25  # >25% of node span idle = orchestration bottleneck


def detect_bottlenecks(report: dict[str, Any]) -> list[dict[str, str]]:
    """Turn an aggregate report into actionable bottleneck findings.

    Each finding is ``{rule, severity, detail}`` — machine-readable so e2e
    tests and CI can gate on ``severity == "critical"`` or just record the
    list as regression evidence.
    """
    findings: list[dict[str, str]] = []

    for node in report.get("nodes", []):
        share = node.get("share_of_node_time", 0.0)
        if share >= DOMINANT_NODE_SHARE:
            findings.append(
                {
                    "rule": "dominant_node",
                    "severity": "critical",
                    "detail": (
                        f"{node['label']} consumes {share:.0%} of node time "
                        f"(P50={node['p50_s']}s) — single-node bottleneck"
                    ),
                }
            )
        elif node.get("p95_s", 0.0) >= SLOW_NODE_P95_S:
            findings.append(
                {
                    "rule": "slow_node_tail",
                    "severity": "warning",
                    "detail": (
                        f"{node['label']} P95={node['p95_s']}s "
                        f"(share={share:.0%}) — tail latency outlier"
                    ),
                }
            )

    qw = report.get("queue_wait_s")
    if qw and qw.get("p95", 0.0) >= QUEUE_WAIT_P95_S:
        findings.append(
            {
                "rule": "queue_wait",
                "severity": "critical",
                "detail": (
                    f"admission→workflow-start P95={qw['p95']}s — queue/dispatch path is saturating"
                ),
            }
        )

    sg = report.get("scheduling_gap_s")
    sgr = report.get("scheduling_gap_ratio")
    if sg and (
        sg.get("p95", 0.0) >= SCHEDULING_GAP_P95_S
        or (sgr or {}).get("p95", 0.0) >= SCHEDULING_GAP_RATIO
    ):
        findings.append(
            {
                "rule": "scheduling_gap",
                "severity": "warning",
                "detail": (
                    f"idle time inside node span: P95={sg.get('p95')}s "
                    f"(ratio={(sgr or {}).get('p95')}) — dead transitions between "
                    "dependent nodes dominate wall time, not node runtimes"
                ),
            }
        )

    oh = report.get("orchestration_overhead_s")
    if oh and oh.get("p95", 0.0) >= ORCHESTRATION_OVERHEAD_P95_S:
        findings.append(
            {
                "rule": "orchestration_overhead",
                "severity": "warning",
                "detail": (
                    f"workflow wall minus node-span P95={oh['p95']}s — "
                    "time is spent outside node runtimes (scheduling gaps)"
                ),
            }
        )

    wf = report.get("workflow_duration_s")
    if wf and wf.get("p95", 0.0) >= WORKFLOW_P95_S:
        findings.append(
            {
                "rule": "workflow_p95_over_timeout",
                "severity": "critical",
                "detail": (
                    f"workflow P95={wf['p95']}s exceeds the e2e wait timeout "
                    f"({WORKFLOW_P95_S}s) — suites will fail on timing, not defects"
                ),
            }
        )

    return findings


def print_gantt(execution: dict[str, Any]) -> None:
    """ASCII timeline of one execution — makes parallel bursts and dead
    scheduling gaps visible at a glance."""
    t = NodeTimingExtractor().extract_timings(execution)
    rows = sorted(
        (
            (info["start_offset_s"], info["start_offset_s"] + info["duration_s"], label)
            for label, info in t["nodes"].items()
        ),
        key=lambda r: r[0],
    )
    if not rows:
        print("no node timings")
        return
    print(f"execution {t['execution_id'][:12]} — {len(rows)} nodes")
    prev_end = 0.0
    for s, e, label in rows:
        bar = "#" * max(1, int(e - s))
        gap = "  <GAP>" if s - prev_end >= 1.5 else ""
        print(f"  {s:6.1f}->{e:6.1f} {bar:<18} {label}{gap}")
        prev_end = max(prev_end, e)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=30, help="executions to analyze")
    ap.add_argument("--out", type=str, default="", help="JSON report path")
    ap.add_argument("--os-url", type=str, default=OPENSEARCH_URL)
    ap.add_argument(
        "--gantt",
        action="store_true",
        help="also print an ASCII timeline of the most recent execution",
    )
    args = ap.parse_args()

    # Windows consoles default to cp1252 and crash on box-drawing/arrow
    # glyphs; force UTF-8 output so gantt and arrows print everywhere.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    executions = fetch_finished_executions(args.size, args.os_url)
    if not executions:
        print("No FINISHED executions found", file=sys.stderr)
        return 1

    report = aggregate_executions(executions)
    report["opensearch_url"] = args.os_url
    report["bottleneck_findings"] = detect_bottlenecks(report)

    out = args.out or f"/app/reports/perf/bottleneck-{int(time.time())}.json"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Human-readable bottleneck table
    print(f"Analyzed {report['executions_analyzed']} FINISHED executions")
    wf = report["workflow_duration_s"] or {}
    print(f"Workflow duration: P50={wf.get('p50')}s P95={wf.get('p95')}s max={wf.get('max')}s")
    oh = report["orchestration_overhead_s"] or {}
    print(f"Orchestration overhead: P50={oh.get('p50')}s P95={oh.get('p95')}s")
    sg = report["scheduling_gap_s"] or {}
    sgr = report["scheduling_gap_ratio"] or {}
    print(
        f"Scheduling gap (idle inside span): P50={sg.get('p50')}s "
        f"P95={sg.get('p95')}s ratio-P50={sgr.get('p50')}"
    )
    qw = report["queue_wait_s"] or {}
    print(f"Queue wait (submission→start): n={qw.get('n', 0)} P50={qw.get('p50')}s")
    print("\nTop bottlenecks (share of total node time):")
    for n in report["nodes"][:10]:
        print(
            f"  {n['label']:<30} {n['share_of_node_time']:>6.1%}  "
            f"P50={n['p50_s']:>7.1f}s P95={n['p95_s']:>7.1f}s max={n['max_s']:>7.1f}s"
        )
    if report["bottleneck_findings"]:
        print("\nFindings:")
        for f in report["bottleneck_findings"]:
            print(f"  [{f['severity'].upper():>8}] {f['rule']}: {f['detail']}")
    else:
        print("\nNo bottleneck findings — distribution is flat and within budget.")
    print(f"\nReport: {out}")
    if args.gantt:
        print()
        print_gantt(executions[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
