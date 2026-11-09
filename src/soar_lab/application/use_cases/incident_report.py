"""Post-incident report use case (IR4).

Packages a single incident — the ingested alert, its downstream case,
execution KPIs and timeline — into a reproducible markdown/JSON report
so every experiment run leaves a post-incident artifact without manual
report assembly.
"""

from datetime import UTC, datetime
from typing import Any

__all__ = ["IncidentReportUseCase"]

RESPONDED_STATUSES = {"forwarded", "responded", "contained", "resolved", "closed"}


class IncidentReportUseCase:
    """Build a post-incident report from repository data."""

    def __init__(
        self,
        alert_provider: Any,
        cases_provider: Any | None = None,
        test_results_provider: Any | None = None,
    ) -> None:
        """Create the use case.

        Args:
            alert_provider: Callable ``(alert_id) -> dict | None``.
            cases_provider: Optional callable returning case dicts; the
                report links cases whose ``alert_id`` matches.
            test_results_provider: Optional callable ``(hours) -> list``
                returning KPI rows to attach the latest execution metrics.
        """
        if alert_provider is None:
            raise ValueError("alert_provider is required for IncidentReportUseCase")
        self._alert_provider = alert_provider
        self._cases_provider = cases_provider
        self._tests_provider = test_results_provider

    def build(self, alert_id: str) -> dict[str, Any] | None:
        """Assemble the structured report; ``None`` if the alert is unknown."""
        alert = self._alert_provider(alert_id)
        if alert is None:
            return None

        related_cases = self._related_cases(alert_id)
        status = str(alert.get("status") or "new").lower()
        data = alert.get("data") if isinstance(alert.get("data"), dict) else {}

        return {
            "report_type": "post_incident",
            "generated_at": datetime.now(UTC).isoformat(),
            "incident": {
                "alert_id": alert.get("alert_id", alert_id),
                "alert_type": alert.get("alert_type"),
                "severity": alert.get("severity"),
                "hostname": alert.get("hostname"),
                "timestamp": alert.get("timestamp"),
                "status": status,
                "responded": status in RESPONDED_STATUSES,
            },
            "mitre": {
                "techniques": data.get("mitre_techniques") or data.get("techniques") or [],
                "tactics": data.get("mitre_tactics") or data.get("tactics") or [],
            },
            "response": {
                "cases": [
                    {
                        "case_id": c.get("case_id"),
                        "title": c.get("title"),
                        "severity": c.get("severity"),
                        "status": c.get("status"),
                    }
                    for c in related_cases
                ],
                "case_count": len(related_cases),
            },
            "kpis": self._latest_kpis(),
        }

    def build_markdown(self, alert_id: str) -> str | None:
        """Render the report as markdown; ``None`` if the alert is unknown."""
        report = self.build(alert_id)
        if report is None:
            return None
        inc = report["incident"]
        mitre = report["mitre"]
        resp = report["response"]
        lines = [
            f"# Post-Incident Report — {inc['alert_id']}",
            "",
            f"- Generated: {report['generated_at']}",
            f"- Type: {inc['alert_type']}  ·  Severity: {inc['severity']}",
            f"- Host: {inc['hostname'] or 'n/a'}",
            f"- Alerted at: {inc['timestamp']}",
            f"- Status: {inc['status']}"
            + (" (responded)" if inc["responded"] else " (not responded)"),
            "",
            "## MITRE ATT&CK",
            f"- Techniques: {', '.join(mitre['techniques']) or 'none tagged'}",
            f"- Tactics: {', '.join(mitre['tactics']) or 'none tagged'}",
            "",
            f"## Response ({resp['case_count']} case(s))",
        ]
        for case in resp["cases"]:
            lines.append(f"- `{case['case_id']}` {case['title']} — {case['status'] or 'open'}")
        if resp["case_count"] == 0:
            lines.append("- No downstream cases recorded.")
        kpis = report.get("kpis")
        if kpis:
            lines += ["", "## Latest execution KPIs"]
            for key, value in kpis.items():
                lines.append(f"- {key}: {value}")
        return "\n".join(lines) + "\n"

    def _related_cases(self, alert_id: str) -> list[dict[str, Any]]:
        if self._cases_provider is None:
            return []
        try:
            return [
                c
                for c in (self._cases_provider() or [])
                if isinstance(c, dict) and c.get("alert_id") == alert_id
            ]
        except Exception:
            return []

    def _latest_kpis(self) -> dict[str, Any] | None:
        if self._tests_provider is None:
            return None
        try:
            rows = self._tests_provider(24) or []
        except Exception:
            return None
        return rows[0] if rows else None
