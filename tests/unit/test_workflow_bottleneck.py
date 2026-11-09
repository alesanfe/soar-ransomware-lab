"""Unit tests for ``scripts/perf/workflow_bottleneck.py`` aggregation logic.

Feeds synthetic OpenSearch execution documents (workflow-level
``started_at``/``completed_at`` in epoch seconds, node-level
``results[].started_at/completed_at`` in epoch milliseconds — the real
Shuffle schema) through ``aggregate_executions`` and asserts the
bottleneck math: per-node shares, percentiles, orchestration overhead and
queue-wait extraction.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.perf import workflow_bottleneck as wb


def _exec(
    exec_id: str,
    wf_start: float,
    nodes: list[tuple[str, float, float]],
    alert_ts: float | None = None,
    status: str = "FINISHED",
) -> dict:
    """Build a synthetic execution doc.

    ``nodes`` = [(label, start_offset_s, duration_s)] relative to
    ``wf_start``; node timestamps are emitted in ms like Shuffle does.
    """
    wf_end = wf_start + max(off + dur for _, off, dur in nodes)
    arg = json.dumps({"timestamp": alert_ts}) if alert_ts is not None else "{}"
    return {
        "execution_id": exec_id,
        "status": status,
        "started_at": wf_start,
        "completed_at": wf_end,
        "execution_argument": arg,
        "results": [
            {
                "action": {"label": label},
                "started_at": int((wf_start + off) * 1000),
                "completed_at": int((wf_start + off + dur) * 1000),
                "status": "SUCCESS",
            }
            for label, off, dur in nodes
        ],
    }


class TestQueueWait:
    def test_queue_wait_from_execution_argument(self):
        ex = _exec("e1", 1000.0, [("n1", 0, 5)], alert_ts=990.0)
        assert wb.extract_queue_wait(ex) == pytest.approx(10.0, abs=0.001)

    def test_queue_wait_none_without_alert_ts(self):
        ex = _exec("e2", 1000.0, [("n1", 0, 5)])
        assert wb.extract_queue_wait(ex) is None

    def test_queue_wait_negative_is_clock_skew(self):
        ex = _exec("e3", 1000.0, [("n1", 0, 5)], alert_ts=2000.0)
        assert wb.extract_queue_wait(ex) is None

    def test_queue_wait_none_without_started(self):
        ex = _exec("e4", 0, [("n1", 0, 5)], alert_ts=100.0)
        ex.pop("started_at")
        assert wb.extract_queue_wait(ex) is None

    def test_queue_wait_from_iso_detection_time(self):
        """Simulator/TC payloads carry ISO-8601 ``detection_time``."""
        from datetime import UTC, datetime

        ex = _exec("iso", 1000.0, [("n1", 0, 5)])
        ex["execution_argument"] = json.dumps(
            {"detection_time": datetime.fromtimestamp(990.0, UTC).isoformat()}
        )
        assert wb.extract_queue_wait(ex) == pytest.approx(10.0, abs=0.01)

    def test_alert_ts_garbage_returns_none(self):
        ex = _exec("bad", 1000.0, [("n1", 0, 5)])
        ex["execution_argument"] = json.dumps({"detection_time": "not-a-date"})
        assert wb.extract_queue_wait(ex) is None


class TestAggregateExecutions:
    def test_node_share_ranks_bottleneck(self):
        """The node consuming most total runtime must rank first."""
        executions = [
            _exec("a", 1000.0, [("fast", 0, 2), ("slow_node", 2, 30)]),
            _exec("b", 2000.0, [("fast", 0, 3), ("slow_node", 3, 40)]),
        ]
        report = wb.aggregate_executions(executions)
        assert report["bottleneck_top5"][0] == "slow_node"
        slow = next(n for n in report["nodes"] if n["label"] == "slow_node")
        assert slow["executions"] == 2
        assert slow["total_s"] == pytest.approx(70.0)
        assert slow["share_of_node_time"] == pytest.approx(70 / 75, abs=0.001)

    def test_percentiles_across_executions(self):
        executions = [
            _exec(f"e{i}", (i + 1) * 1000.0, [("n", 0, dur)])
            for i, dur in enumerate([10, 20, 30, 40])
        ]
        report = wb.aggregate_executions(executions)
        wf = report["workflow_duration_s"]
        assert wf["n"] == 4
        assert wf["min"] == pytest.approx(10.0)
        assert wf["max"] == pytest.approx(40.0)

    def test_orchestration_overhead_is_wall_minus_node_span(self):
        """Gap between workflow end and last node end = dispatch overhead."""
        # Node ends at offset 10; workflow runs to completed_at +5 → 5s overhead
        ex = _exec("ovh", 1000.0, [("n1", 0, 10)])
        ex["completed_at"] = 1000.0 + 15
        report = wb.aggregate_executions([ex])
        ovh = report["orchestration_overhead_s"]
        assert ovh["p50"] == pytest.approx(5.0, abs=0.01)

    def test_queue_wait_distribution(self):
        executions = [
            _exec("q1", 1000.0, [("n", 0, 5)], alert_ts=995.0),
            _exec("q2", 2000.0, [("n", 0, 5)], alert_ts=1980.0),
            _exec("q3", 3000.0, [("n", 0, 5)]),  # no ts → excluded
        ]
        report = wb.aggregate_executions(executions)
        qw = report["queue_wait_s"]
        assert qw["n"] == 2
        assert qw["min"] == pytest.approx(5.0)
        assert qw["max"] == pytest.approx(20.0)

    def test_invalid_node_timings_counted(self):
        ex = _exec("bad", 1000.0, [("n", 0, 5)])
        # Corrupt a node: completed before started
        ex["results"][0]["completed_at"] = ex["results"][0]["started_at"] - 1000
        report = wb.aggregate_executions([ex])
        assert report["data_quality"]["invalid_node_timings_total"] == 1

    def test_statuses_aggregated(self):
        ex = _exec("st", 1000.0, [("n1", 0, 5), ("n2", 5, 3)])
        ex["results"][1]["status"] = "SKIPPED"
        report = wb.aggregate_executions([ex])
        n2 = next(n for n in report["nodes"] if n["label"] == "n2")
        assert n2["statuses"] == {"SKIPPED": 1}

    def test_empty_input(self):
        report = wb.aggregate_executions([])
        assert report["executions_analyzed"] == 0
        assert report["nodes"] == []
        assert report["workflow_duration_s"] is None


def _report(**over):
    base = {
        "nodes": [],
        "workflow_duration_s": None,
        "orchestration_overhead_s": None,
        "queue_wait_s": None,
    }
    return base | over


class TestDetectBottlenecks:
    def test_flat_distribution_no_findings(self):
        report = _report(
            nodes=[
                {"label": f"n{i}", "share_of_node_time": 0.1, "p50_s": 2.0, "p95_s": 5.0}
                for i in range(10)
            ],
            workflow_duration_s={"p50": 130.0, "p95": 400.0},
            queue_wait_s={"p50": 0.01, "p95": 0.5},
            orchestration_overhead_s={"p50": 0.0, "p95": 1.0},
        )
        assert wb.detect_bottlenecks(report) == []

    def test_dominant_node_is_critical(self):
        report = _report(
            nodes=[
                {"label": "hog", "share_of_node_time": 0.55, "p50_s": 60.0, "p95_s": 90.0},
                {"label": "ok", "share_of_node_time": 0.1, "p50_s": 1.0, "p95_s": 2.0},
            ]
        )
        findings = wb.detect_bottlenecks(report)
        assert findings[0]["rule"] == "dominant_node"
        assert findings[0]["severity"] == "critical"
        assert "hog" in findings[0]["detail"]

    def test_slow_tail_below_dominance_is_warning(self):
        report = _report(
            nodes=[{"label": "spiky", "share_of_node_time": 0.2, "p50_s": 2.0, "p95_s": 45.0}]
        )
        findings = wb.detect_bottlenecks(report)
        assert [f["severity"] for f in findings] == ["warning"]
        assert findings[0]["rule"] == "slow_node_tail"

    def test_queue_wait_finding(self):
        report = _report(queue_wait_s={"p50": 2.0, "p95": 9.0})
        findings = wb.detect_bottlenecks(report)
        assert findings[0]["rule"] == "queue_wait"
        assert findings[0]["severity"] == "critical"

    def test_orchestration_overhead_finding(self):
        report = _report(orchestration_overhead_s={"p50": 3.0, "p95": 25.0})
        findings = wb.detect_bottlenecks(report)
        assert findings[0]["rule"] == "orchestration_overhead"
        assert findings[0]["severity"] == "warning"

    def test_workflow_p95_over_timeout_is_critical(self):
        report = _report(workflow_duration_s={"p50": 300.0, "p95": 700.0})
        findings = wb.detect_bottlenecks(report)
        assert findings[0]["rule"] == "workflow_p95_over_timeout"
        assert findings[0]["severity"] == "critical"

    def test_missing_distributions_safe(self):
        assert wb.detect_bottlenecks(_report()) == []

    def test_end_to_end_aggregation_flags_dominant(self):
        """Full pipeline: synthetic executions → report → findings."""
        executions = [
            _exec("x", 1000.0, [("tiny", 0, 1), ("mega", 1, 100)]),
            _exec("y", 2000.0, [("tiny", 0, 1), ("mega", 1, 90)]),
        ]
        report = wb.aggregate_executions(executions)
        findings = wb.detect_bottlenecks(report)
        rules = {f["rule"] for f in findings}
        assert "dominant_node" in rules
        # wf P95 ~191s < 600 → no timeout finding
        assert "workflow_p95_over_timeout" not in rules


class TestSchedulingGap:
    def test_empty(self):
        assert wb.scheduling_gap([]) == (0.0, 0.0)

    def test_fully_covered_span(self):
        # overlapping intervals — union covers the whole span → gap 0
        gap, ratio = wb.scheduling_gap([(0, 10), (5, 15), (10, 20)])
        assert gap == 0.0 and ratio == 0.0

    def test_dead_gap_measured(self):
        # sequential nodes with dead time between them: span 0..30,
        # coverage 10+10=20 → gap 10
        gap, ratio = wb.scheduling_gap([(0, 10), (20, 30)])
        assert gap == 10.0
        assert ratio == round(10 / 30, 4)

    def test_touching_intervals_not_gap(self):
        gap, _ = wb.scheduling_gap([(0, 5), (5, 10)])
        assert gap == 0.0

    def test_detect_rule_fires_on_idle_span(self):
        report = _report()
        report["scheduling_gap_s"] = {"p50": 12.0, "p95": 20.0}
        report["scheduling_gap_ratio"] = {"p50": 0.2, "p95": 0.4}
        findings = wb.detect_bottlenecks(report)
        assert any(f["rule"] == "scheduling_gap" for f in findings)

    def test_detect_rule_quiet_when_busy(self):
        report = _report()
        report["scheduling_gap_s"] = {"p50": 1.0, "p95": 3.0}
        report["scheduling_gap_ratio"] = {"p50": 0.05, "p95": 0.1}
        findings = wb.detect_bottlenecks(report)
        assert not any(f["rule"] == "scheduling_gap" for f in findings)

    def test_aggregate_populates_scheduling_fields(self):
        executions = [_exec("x", 1000.0, [("a", 0, 5), ("b", 15, 5)])]
        report = wb.aggregate_executions(executions)
        assert report["scheduling_gap_s"]["n"] == 1
        assert report["scheduling_gap_s"]["p50"] == 10.0
        assert report["per_execution"][0]["scheduling_gap_s"] == 10.0
