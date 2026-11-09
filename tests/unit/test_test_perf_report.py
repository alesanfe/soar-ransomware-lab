"""Tests for scripts/perf/test_perf_report.py aggregation and findings."""

import json
from pathlib import Path

from scripts.perf import test_perf_report as tpr


def _rec(nodeid: str, phase: str, dur: float, outcome: str = "passed") -> dict:
    return {"nodeid": nodeid, "phase": phase, "duration_s": dur, "outcome": outcome}


def _full(nodeid: str, setup: float, call: float, teardown: float, outcome="passed"):
    return [
        _rec(nodeid, "setup", setup),
        _rec(nodeid, "call", call, outcome),
        _rec(nodeid, "teardown", teardown),
    ]


class TestAggregate:
    def test_phase_breakdown_per_test(self):
        report = tpr.aggregate(_full("t/unit/a.py::x", 1.0, 2.0, 0.5))
        t = report["tests"]["t/unit/a.py::x"]
        assert t["setup_s"] == 1.0 and t["call_s"] == 2.0 and t["teardown_s"] == 0.5
        assert t["total_s"] == 3.5

    def test_failed_outcome_propagates(self):
        report = tpr.aggregate(_full("t/a.py::x", 0, 1, 0, outcome="failed"))
        assert report["tests"]["t/a.py::x"]["outcome"] == "failed"

    def test_suite_grouping_e2e(self):
        recs = _full("tests/e2e/TC-04/a.py::x", 0, 5, 0) + _full("tests/e2e/TC-05/b.py::y", 0, 3, 0)
        report = tpr.aggregate(recs)
        assert report["suites"]["e2e/TC-04"]["total_s"] == 5
        assert report["suites"]["e2e/TC-05"]["total_s"] == 3

    def test_phase_share_sums_to_one(self):
        recs = _full("t/unit/a.py::x", 1, 3, 1) + _full("t/unit/b.py::y", 1, 4, 0)
        report = tpr.aggregate(recs)
        assert abs(sum(report["phase_share"].values()) - 1.0) < 0.01

    def test_sorted_by_total_desc(self):
        recs = _full("t/a.py::slow", 0, 10, 0) + _full("t/b.py::fast", 0, 1, 0)
        report = tpr.aggregate(recs)
        assert list(report["tests"])[0] == "t/a.py::slow"


class TestFindings:
    def test_dominant_test_flagged(self):
        recs = _full("t/a.py::big", 0, 90, 0) + [
            _full_rec for i in range(5) for _full_rec in _full(f"t/b.py::t{i}", 0, 10, 0)
        ]
        findings = tpr.detect_findings(tpr.aggregate(recs))
        rules = {f["rule"] for f in findings}
        assert "dominant_test" in rules

    def test_slow_failure_flagged(self):
        report = tpr.aggregate(_full("t/a.py::x", 0, 120, 0, outcome="failed"))
        rules = {f["rule"] for f in tpr.detect_findings(report)}
        assert "slow_failure" in rules

    def test_fixture_overhead_flagged(self):
        # suite where setup+teardown dominates: 60 of 100s
        recs = _full("t/a.py::x", 40, 40, 20)
        report = tpr.aggregate(recs)
        rules = {f["rule"] for f in tpr.detect_findings(report)}
        assert "fixture_overhead" in rules

    def test_healthy_suite_no_findings(self):
        recs = _full("t/a.py::x", 0.1, 2.0, 0.1) + _full("t/b.py::y", 0.1, 3.0, 0.1)
        findings = tpr.detect_findings(tpr.aggregate(recs))
        assert findings == []


class TestLoadRecords:
    def test_merges_multiple_files(self, tmp_path: Path):
        p1 = tmp_path / "d1.json"
        p2 = tmp_path / "d2.json"
        p1.write_text(json.dumps({"records": [_rec("a", "call", 1.0)]}))
        p2.write_text(json.dumps({"records": [_rec("b", "call", 2.0)]}))
        recs = tpr.load_records([str(p1), str(p2)])
        assert len(recs) == 2
