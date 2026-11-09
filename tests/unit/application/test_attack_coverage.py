"""Unit tests for AttackCoverageUseCase (ATT&CK coverage / Navigator export)."""

import pytest

from soar_lab.application.use_cases.attack_coverage import AttackCoverageUseCase


def _uc(alerts):
    return AttackCoverageUseCase(alerts_provider=lambda: alerts)


class TestCoverage:
    def test_empty_repository(self):
        result = _uc([]).coverage()
        assert result["total_alerts"] == 0
        assert result["coverage_percent"] == 0.0
        assert result["techniques"] == {}

    def test_root_level_techniques_aggregated(self):
        alerts = [
            {"alert_id": "a1", "mitre_techniques": ["T1486", "T1059"]},
            {"alert_id": "a2", "mitre_techniques": ["T1486"]},
            {"alert_id": "a3"},
        ]
        result = _uc(alerts).coverage()
        assert result["total_alerts"] == 3
        assert result["alerts_with_techniques"] == 2
        assert result["techniques"] == {"T1486": 2, "T1059": 1}
        assert result["unique_techniques"] == 2
        assert result["coverage_percent"] == pytest.approx(66.67)

    def test_nested_data_techniques_aggregated(self):
        alerts = [{"alert_id": "a1", "data": {"mitre_techniques": ["T1567"]}}]
        result = _uc(alerts).coverage()
        assert result["techniques"] == {"T1567": 1}
        assert result["alerts_with_techniques"] == 1

    def test_tactics_aggregated(self):
        alerts = [{"mitre_tactics": ["impact", "impact", "exfiltration"]}]
        # tactics list inside one alert counts occurrences
        result = _uc(alerts).coverage()
        assert result["tactics"]["impact"] == 2
        assert result["tactics"]["exfiltration"] == 1

    def test_string_and_legacy_keys_supported(self):
        alerts = [{"techniques": "T1486"}]
        result = _uc(alerts).coverage()
        assert result["techniques"] == {"T1486": 1}

    def test_limit_bounds_analysis(self):
        alerts = [{"mitre_techniques": ["T1"]}, {"mitre_techniques": ["T2"]}]
        result = _uc(alerts).coverage(limit=1)
        assert result["total_alerts"] == 1

    def test_non_dict_alerts_skipped(self):
        result = _uc([None, "junk", {"mitre_techniques": ["T1486"]}]).coverage()
        assert result["alerts_with_techniques"] == 1

    def test_requires_provider(self):
        with pytest.raises(ValueError):
            AttackCoverageUseCase(alerts_provider=None)


class TestNavigatorLayer:
    def test_layer_structure(self):
        alerts = [{"mitre_techniques": ["T1486", "T1486", "T1059"]}]
        layer = _uc(alerts).navigator_layer(name="test layer")
        assert layer["name"] == "test layer"
        assert layer["domain"] == "enterprise-attack"
        assert layer["versions"]["layer"] == "4.5"
        scores = {t["techniqueID"]: t["score"] for t in layer["techniques"]}
        assert scores == {"T1486": 2, "T1059": 1}
        assert layer["gradient"]["maxValue"] == 2

    def test_empty_layer_valid(self):
        layer = _uc([]).navigator_layer()
        assert layer["techniques"] == []
        assert layer["gradient"]["maxValue"] == 1


class TestHeatmap:
    """IR1: coverage×response matrix — responded vs uncovered techniques."""

    def test_response_rate_per_technique(self):
        alerts = [
            {"mitre_techniques": ["T1486"], "status": "forwarded"},
            {"mitre_techniques": ["T1486"], "status": "new"},
            {"mitre_techniques": ["T1490"], "status": "contained"},
        ]
        out = _uc(alerts).heatmap()
        t1486 = out["techniques"]["T1486"]
        assert t1486["alerts"] == 2
        assert t1486["responded"] == 1
        assert t1486["response_rate"] == 50.0
        assert out["techniques"]["T1490"]["response_rate"] == 100.0

    def test_aggregate_rate(self):
        alerts = [
            {"mitre_techniques": ["T1486"], "status": "forwarded"},
            {"mitre_techniques": ["T1486"], "status": "new"},
        ]
        out = _uc(alerts).heatmap()
        assert out["response_rate_percent"] == 50.0
        assert out["tagged_alerts"] == 2
        assert out["responded_alerts"] == 1

    def test_empty_corpus(self):
        out = _uc([]).heatmap()
        assert out["techniques"] == {}
        assert out["response_rate_percent"] == 0.0
