"""F5: SigmaEvalUseCase — sigma-lite detection over stored alerts."""

import pytest

from soar_lab.application.use_cases.sigma_eval import (
    SigmaEvalUseCase,
    SigmaRule,
    SigmaUnsupportedError,
)

RULE = SigmaRule(
    {
        "title": "impact technique",
        "level": "high",
        "detection": {
            "selection": {"data.mitre_techniques|contains": ["T1486", "T1490"]},
            "condition": "selection",
        },
    }
)

RULE_AND = SigmaRule(
    {
        "title": "c2 and ransomware",
        "detection": {
            "sel_ip": {"data.source_ip|contains": "185.220"},
            "sel_sev": {"severity": "high"},
            "condition": "sel_ip and sel_sev",
        },
    }
)

RULE_OR = SigmaRule(
    {
        "title": "either",
        "detection": {
            "a": {"severity": "critical"},
            "b": {"severity": "high"},
            "condition": "a or b",
        },
    }
)

RULE_1OF = SigmaRule(
    {
        "title": "one of infra",
        "detection": {
            "infra_ip": {"data.source_ip|contains": "185.220"},
            "infra_dom": {"data.domain|endswith": ".bit"},
            "condition": "1 of infra_*",
        },
    }
)

ALERT = {
    "severity": "high",
    "data": {"mitre_techniques": ["T1486"], "source_ip": "185.220.101.4"},
}
ALERT_LOW = {"severity": "low", "data": {"mitre_techniques": ["T1059"]}}


class TestEval:
    def test_contains_list_or(self):
        uc = SigmaEvalUseCase([RULE])
        assert uc.evaluate(RULE, ALERT) is True
        assert uc.evaluate(RULE, ALERT_LOW) is False

    def test_and_condition(self):
        uc = SigmaEvalUseCase()
        assert uc.evaluate(RULE_AND, ALERT) is True
        assert uc.evaluate(RULE_AND, ALERT_LOW) is False

    def test_or_condition(self):
        uc = SigmaEvalUseCase()
        assert uc.evaluate(RULE_OR, ALERT_LOW) is False
        assert uc.evaluate(RULE_OR, ALERT) is True

    def test_one_of_prefix(self):
        uc = SigmaEvalUseCase()
        assert uc.evaluate(RULE_1OF, ALERT) is True
        assert uc.evaluate(RULE_1OF, ALERT_LOW) is False

    def test_missing_field_is_no_match(self):
        uc = SigmaEvalUseCase()
        assert uc.evaluate(RULE_AND, {"data": {}}) is False

    def test_unsupported_condition_loud(self):
        bad = SigmaRule({"title": "x", "detection": {"sel": {"a": 1}, "condition": "all of them"}})
        with pytest.raises(SigmaUnsupportedError):
            SigmaEvalUseCase().evaluate(bad, {})


class TestLoadAndScan:
    def test_loads_repo_rules(self):
        rules = SigmaEvalUseCase.load_rules("detections/sigma")
        assert len(rules) >= 2
        assert all("detection" in r for r in rules)

    def test_scan_reports_matches(self):
        rules = SigmaEvalUseCase.load_rules("detections/sigma")
        uc = SigmaEvalUseCase(rules)
        out = uc.scan([ALERT, ALERT_LOW])
        assert out["rules_loaded"] >= 2
        assert out["alerts_scanned"] == 2
        by_title = {r["rule"]: r for r in out["results"]}
        assert by_title["Ransomware impact techniques observed"]["matches"] == 1

    def test_empty_dir(self):
        assert SigmaEvalUseCase.load_rules("/nonexistent") == []
