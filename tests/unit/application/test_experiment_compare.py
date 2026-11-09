"""F1: ExperimentCompareUseCase — tagged variant latency comparison."""

from soar_lab.application.use_cases.experiment_compare import ExperimentCompareUseCase

ALERTS = [
    {"alert_id": "A1", "timestamp": "2025-01-01T00:00:00", "experiment_tag": "v1"},
    {"alert_id": "A2", "timestamp": "2025-01-01T00:00:00", "experiment_tag": "v1"},
    {"alert_id": "B1", "timestamp": "2025-01-01T00:00:00", "data": {"experiment_tag": "v2"}},
    {"alert_id": "B2", "timestamp": "2025-01-01T00:00:00", "experiment_tag": "v2"},
    {"alert_id": "U1", "timestamp": "2025-01-01T00:00:00"},  # untagged
]
CASES = [
    {"case_id": "C1", "alert_id": "A1", "timestamp": "2025-01-01T00:00:10"},
    {"case_id": "C2", "alert_id": "A2", "timestamp": "2025-01-01T00:00:20"},
    {"case_id": "C3", "alert_id": "B1", "timestamp": "2025-01-01T00:00:30"},
    {"case_id": "C4", "alert_id": "B2", "timestamp": "2025-01-01T00:01:00"},
    {"case_id": "C5", "alert_id": "U1", "timestamp": "2025-01-01T00:00:05"},
]


def _uc(alerts=ALERTS, cases=CASES):
    return ExperimentCompareUseCase(alerts_provider=lambda: alerts, cases_provider=lambda: cases)


class TestLatencies:
    def test_grouped_by_tag(self):
        groups = _uc().latencies_by_variant()
        assert groups["v1"] == [10.0, 20.0]
        assert groups["v2"] == [30.0, 60.0]
        assert "U1" not in groups  # untagged alerts excluded

    def test_unmatched_alerts_skipped(self):
        alerts = [{"alert_id": "X", "timestamp": "2025-01-01T00:00:00", "experiment_tag": "v"}]
        assert _uc(alerts=alerts, cases=[]).latencies_by_variant() == {}


class TestCompare:
    def test_delta_and_variants(self):
        out = _uc().compare("v1", "v2")
        assert out["variant_a"]["n"] == 2
        assert out["variant_b"]["stats"]["mean"] == 45.0
        assert out["delta_mean_seconds"] == -30.0
        assert out["delta_ci95"] is not None
        assert out["known_variants"] == ["v1", "v2"]

    def test_missing_variant(self):
        out = _uc().compare("v1", "ghost")
        assert out["variant_b"]["n"] == 0
        assert out["delta_ci95"] is None

    def test_requires_providers(self):
        import pytest

        with pytest.raises(ValueError):
            ExperimentCompareUseCase(None, None)
