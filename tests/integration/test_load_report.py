"""Tests for the locust load-report runner (scripts/perf/run_load_report.py)."""

import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "run_load_report", ROOT / "scripts" / "perf" / "run_load_report.py"
)
mod = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault("run_load_report", mod)
_SPEC.loader.exec_module(mod)


def _write_stats(path: Path, rows: list[dict]) -> None:
    fields = [
        "Name",
        "Request Count",
        "Failure Count",
        "Average Response Time",
        "50%",
        "95%",
        "99%",
        "Requests/s",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


class TestParseDuration:
    def test_seconds_minutes_hours(self):
        assert mod._parse_duration("60s") == 60
        assert mod._parse_duration("5m") == 300
        assert mod._parse_duration("1h") == 3600
        assert mod._parse_duration("120") == 120

    def test_invalid(self):
        try:
            mod._parse_duration("soon")
        except ValueError:
            return
        raise AssertionError("expected ValueError")


class TestParseStats:
    def test_aggregates_rows(self, tmp_path):
        csv_path = tmp_path / "s_stats.csv"
        _write_stats(
            csv_path,
            [
                {
                    "Name": "POST /api/v1/alerts",
                    "Request Count": "100",
                    "Failure Count": "1",
                    "Average Response Time": "150",
                    "50%": "120",
                    "95%": "400",
                    "99%": "800",
                    "Requests/s": "20",
                },
                {
                    "Name": "Aggregated",
                    "Request Count": "100",
                    "Failure Count": "1",
                    "Average Response Time": "150",
                    "50%": "120",
                    "95%": "400",
                    "99%": "800",
                    "Requests/s": "20",
                },
            ],
        )
        stats = mod.parse_stats_csv(csv_path)
        assert stats["requests"] == 100
        assert stats["failures"] == 1
        assert stats["failure_ratio"] == 0.01
        assert stats["p95_ms"] == 400
        assert stats["endpoints"][0]["name"] == "POST /api/v1/alerts"

    def test_worst_of_percentiles_across_endpoints(self, tmp_path):
        csv_path = tmp_path / "s_stats.csv"
        _write_stats(
            csv_path,
            [
                {"Name": "A", "Request Count": "10", "95%": "100", "50%": "50", "99%": "200"},
                {"Name": "B", "Request Count": "10", "95%": "900", "50%": "80", "99%": "1500"},
            ],
        )
        stats = mod.parse_stats_csv(csv_path)
        assert stats["p95_ms"] == 900
        assert stats["p99_ms"] == 1500


class TestVerdict:
    def test_pass(self):
        v, reasons = mod.verdict({"requests": 100, "failure_ratio": 0.0, "p95_ms": 200})
        assert v == "PASS"
        assert reasons == []

    def test_fail_on_failures(self):
        v, reasons = mod.verdict({"requests": 100, "failure_ratio": 0.05, "p95_ms": 200})
        assert v == "FAIL"
        assert any("failure_ratio" in r for r in reasons)

    def test_fail_on_zero_requests(self):
        v, reasons = mod.verdict({"requests": 0, "failure_ratio": 0.0, "p95_ms": 0})
        assert v == "FAIL"

    def test_warn_between_slo_and_ceiling(self):
        v, _ = mod.verdict({"requests": 100, "failure_ratio": 0.0, "p95_ms": 2000})
        assert v == "WARN"

    def test_fail_over_ceiling(self):
        v, _ = mod.verdict({"requests": 100, "failure_ratio": 0.0, "p95_ms": 4000})
        assert v == "FAIL"


class TestDryRun:
    def test_dry_run_prints_command(self, tmp_path, capsys):
        rc = mod.main(
            ["--host", "http://x:8000", "--token", "t", "--dry-run", "--out-dir", str(tmp_path)]
        )
        out = capsys.readouterr().out
        meta = json.loads(out)
        assert rc == 0
        assert meta["users"] == 60
        assert "locust" in meta["command"]
