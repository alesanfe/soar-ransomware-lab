"""IR4: IncidentReportUseCase — post-incident report packaging."""

from soar_lab.application.use_cases.incident_report import IncidentReportUseCase

ALERT = {
    "alert_id": "AL-001",
    "alert_type": "ransomware",
    "severity": "high",
    "hostname": "ws-01",
    "timestamp": "2025-01-01T00:00:00",
    "status": "forwarded",
    "data": {"mitre_techniques": ["T1486"], "mitre_tactics": ["impact"]},
}
CASES = [
    {
        "case_id": "C-1",
        "title": "Ransomware ws-01",
        "severity": "high",
        "status": "TruePositive",
        "alert_id": "AL-001",
    },
    {"case_id": "C-2", "title": "Other", "severity": "low", "status": "New", "alert_id": "AL-999"},
]


def _uc(alert=ALERT, cases=CASES, tests=None):
    return IncidentReportUseCase(
        alert_provider=lambda aid: alert if aid == alert["alert_id"] else None,
        cases_provider=(lambda: cases) if cases is not None else None,
        test_results_provider=(lambda h: tests) if tests is not None else None,
    )


class TestBuild:
    def test_report_structure(self):
        r = _uc().build("AL-001")
        assert r["report_type"] == "post_incident"
        assert r["incident"]["responded"] is True
        assert r["mitre"]["techniques"] == ["T1486"]
        assert r["response"]["case_count"] == 1
        assert r["response"]["cases"][0]["case_id"] == "C-1"

    def test_unknown_alert_returns_none(self):
        assert _uc().build("nope") is None

    def test_unresponded_status(self):
        a = {**ALERT, "status": "new"}
        assert _uc(alert=a).build("AL-001")["incident"]["responded"] is False

    def test_no_providers_still_builds(self):
        uc = IncidentReportUseCase(alert_provider=lambda aid: ALERT)
        r = uc.build("AL-001")
        assert r["response"]["cases"] == []
        assert r["kpis"] is None

    def test_kpis_attached(self):
        r = _uc(tests=[{"mttr": 42}]).build("AL-001")
        assert r["kpis"] == {"mttr": 42}

    def test_requires_provider(self):
        import pytest

        with pytest.raises(ValueError):
            IncidentReportUseCase(alert_provider=None)


class TestMarkdown:
    def test_markdown_render(self):
        md = _uc(tests=[{"mttr": 42}]).build_markdown("AL-001")
        assert md.startswith("# Post-Incident Report — AL-001")
        assert "T1486" in md and "C-1" in md and "mttr: 42" in md

    def test_markdown_unknown_alert(self):
        assert _uc().build_markdown("nope") is None
