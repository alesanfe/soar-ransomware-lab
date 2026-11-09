"""O2: SLO evaluation against aggregated KPIs."""

from soar_lab.application.use_cases.slo import evaluate_slos, load_slo_definitions

PAYLOAD = {
    "total_alerts": 12,
    "mttr_statistics": {"p50": 60.0, "p95": 250.0, "mean": 80.0},
}


class TestLoadDefinitions:
    def test_loads_repo_slo_yaml(self):
        defs = load_slo_definitions()
        assert len(defs) >= 3
        names = {d["name"] for d in defs}
        assert "mttr_p50_seconds" in names


class TestEvaluate:
    def test_all_met(self):
        out = evaluate_slos(PAYLOAD)
        assert out["all_met"] is True
        assert out["met_count"] == out["total"]

    def test_breach_reported(self):
        payload = {**PAYLOAD, "mttr_statistics": {"p50": 999.0, "p95": 250.0}}
        out = evaluate_slos(payload)
        by_name = {s["name"]: s for s in out["slos"]}
        assert by_name["mttr_p50_seconds"]["met"] is False
        assert out["all_met"] is False

    def test_missing_metric_is_none_not_pass(self):
        out = evaluate_slos({"total_alerts": 5})
        by_name = {s["name"]: s for s in out["slos"]}
        assert by_name["mttr_p50_seconds"]["met"] is None
        assert out["all_met"] is False

    def test_custom_definitions(self):
        defs = [{"name": "x", "metric": "total_alerts", "comparator": "gte", "target": 10}]
        out = evaluate_slos(PAYLOAD, defs)
        assert out["slos"][0]["met"] is True
        assert out["total"] == 1
