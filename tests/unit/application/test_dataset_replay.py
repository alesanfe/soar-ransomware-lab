"""Unit tests for dataset replay (F3 — benchmark mode)."""

import json

import pytest

from soar_lab.simulator.dataset_replay import load_dataset, replay_dataset


@pytest.fixture
def jsonl_file(tmp_path):
    p = tmp_path / "data.jsonl"
    p.write_text(
        '{"alert_id": "a1", "techniques": ["T1486"]}\n' "\n" "# comment\n" '{"alert_id": "a2"}\n',
        encoding="utf-8",
    )
    return p


class TestLoadDataset:
    def test_jsonl_skips_blanks_and_comments(self, jsonl_file):
        alerts = list(load_dataset(jsonl_file))
        assert [a["alert_id"] for a in alerts] == ["a1", "a2"]

    def test_json_array(self, tmp_path):
        p = tmp_path / "d.json"
        p.write_text(json.dumps([{"x": 1}, {"x": 2}]), encoding="utf-8")
        assert len(list(load_dataset(p))) == 2

    def test_json_object_with_alerts_key(self, tmp_path):
        p = tmp_path / "d.json"
        p.write_text(json.dumps({"alerts": [{"x": 1}]}), encoding="utf-8")
        assert len(list(load_dataset(p))) == 1

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            list(load_dataset(tmp_path / "nope.jsonl"))

    def test_bad_extension(self, tmp_path):
        p = tmp_path / "d.csv"
        p.write_text("a,b", encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported"):
            list(load_dataset(p))

    def test_malformed_jsonl(self, tmp_path):
        p = tmp_path / "bad.jsonl"
        p.write_text("{not json}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid JSONL"):
            list(load_dataset(p))

    def test_non_object_entry_rejected(self, tmp_path):
        p = tmp_path / "bad.jsonl"
        p.write_text("[1,2,3]\n", encoding="utf-8")
        with pytest.raises(ValueError, match="not a JSON object"):
            list(load_dataset(p))


class TestReplayDataset:
    def test_counts_successes_and_failures(self):
        alerts = iter([{"n": i} for i in range(5)])
        outcomes = iter([True, True, False, True, False])
        result = replay_dataset(alerts, send=lambda _a: next(outcomes))
        assert result == {"total": 5, "sent": 3, "failed": 2, "success_rate": 60.0}

    def test_send_exception_counts_as_failure(self):
        def boom(_a):
            raise RuntimeError("net down")

        result = replay_dataset(iter([{"x": 1}]), send=boom)
        assert result["failed"] == 1

    def test_limit_respected(self):
        seen = []
        replay_dataset(
            iter([{"n": i} for i in range(10)]),
            send=lambda a: seen.append(a) or True,
            limit=3,
        )
        assert len(seen) == 3

    def test_on_result_called(self):
        calls = []
        replay_dataset(
            iter([{"x": 1}]),
            send=lambda _a: True,
            on_result=lambda i, a, ok: calls.append((i, ok)),
        )
        assert calls == [(0, True)]

    def test_empty_dataset(self):
        result = replay_dataset(iter([]), send=lambda _a: True)
        assert result["total"] == 0 and result["success_rate"] == 0.0

    def test_delay_uses_injected_sleep(self):
        slept = []
        replay_dataset(
            iter([{"x": 1}, {"x": 2}]),
            send=lambda _a: True,
            delay=0.5,
            sleep=slept.append,
        )
        assert slept == [0.5, 0.5]
