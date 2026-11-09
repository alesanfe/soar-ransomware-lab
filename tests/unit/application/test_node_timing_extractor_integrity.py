#!/usr/bin/env python3
"""M-016/018/019 — node timing integrity: duplicate labels accumulated,
corrupt clocks rejected and counted (never silently merged)."""

from soar_lab.application.use_cases.node_timing_extractor import NodeTimingExtractor

BASE = 1_700_000_000  # wf epoch seconds


def _exec(results, started=BASE, completed=BASE + 60):
    return {
        "execution_id": "e1",
        "started_at": started,
        "completed_at": completed,
        "results": results,
    }


def _node(label, start_off, end_off, status="SUCCESS"):
    """Node starting `start_off` s after wf start, ending at `end_off` s."""
    return {
        "action": {"label": label},
        "started_at": (BASE + start_off) * 1000,  # node timestamps are ms
        "completed_at": (BASE + end_off) * 1000,
        "status": status,
    }


class TestDuplicateLabels:
    def test_duplicate_label_accumulates_not_overwrites(self):
        ex = NodeTimingExtractor()
        r = ex.extract_timings(
            _exec(
                [
                    _node("http", 1, 2),
                    _node("http", 5, 8),  # retry, 3s
                ]
            )
        )
        node = r["nodes"]["http"]
        assert node["occurrences"] == 2
        assert node["durations_s"] == [1.0, 3.0]
        assert node["duration_s"] == 4.0  # total time spent
        assert node["statuses"] == ["SUCCESS", "SUCCESS"]
        assert r["data_quality"]["duplicate_labels"] == 1

    def test_distinct_labels_unaffected(self):
        ex = NodeTimingExtractor()
        r = ex.extract_timings(
            _exec(
                [
                    _node("a", 1, 2),
                    _node("b", 2, 3),
                ]
            )
        )
        assert len(r["nodes"]) == 2
        assert all(n["occurrences"] == 1 for n in r["nodes"].values())


class TestTemporalValidation:
    def test_end_before_start_rejected_and_counted(self):
        ex = NodeTimingExtractor()
        r = ex.extract_timings(
            _exec(
                [
                    _node("bad-clock", 5, 1),  # end < start
                    _node("ok", 1, 2),
                ]
            )
        )
        assert "bad-clock" not in r["nodes"]
        assert r["data_quality"]["invalid_node_timings"] == 1

    def test_zero_duration_kept(self):
        ex = NodeTimingExtractor()
        r = ex.extract_timings(
            _exec(
                [
                    _node("instant", 1, 1),
                ]
            )
        )
        assert r["nodes"]["instant"]["duration_s"] == 0.0
        assert r["data_quality"]["invalid_node_timings"] == 0

    def test_wf_parse_error_flagged(self):
        ex = NodeTimingExtractor()
        r = ex.extract_timings(_exec([], started="garbage", completed="x"))
        assert r["data_quality"]["wf_timestamp_parse_error"] is True
        assert r["nodes"] == {}
