"""ATT&CK coverage use case — aggregates technique coverage across alerts.

Produces two views from the stored alert corpus:

- ``coverage()``: per-technique and per-tactic hit counts plus totals,
  suitable for dashboards and coverage KPIs.
- ``navigator_layer()``: a MITRE ATT&CK Navigator layer document (layer
  spec v4.5) that can be imported directly into
  https://mitre-attack.github.io/attack-navigator/ to visualise which
  techniques the lab exercises and how often.
"""

from collections import Counter
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any

__all__ = ["AttackCoverageUseCase"]

TECHNIQUE_KEYS = ("mitre_techniques", "techniques")
TACTIC_KEYS = ("mitre_tactics", "tactics")

NAVIGATOR_LAYER_VERSION = "4.5"
NAVIGATOR_ATTACK_VERSION = "17"
NAVIGATOR_VERSION = "5.1.0"


def _flatten(values: Any) -> list[str]:
    """Normalise a technique/tactic field to a flat list of strings."""
    if not values:
        return []
    if isinstance(values, str):
        return [values]
    if isinstance(values, Iterable):
        return [v for v in values if isinstance(v, str)]
    return []


def _extract_tags(alert: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    """Pull a tag list from the alert root or its nested ``data`` payload."""
    for key in keys:
        found = _flatten(alert.get(key))
        if found:
            return found
    data = alert.get("data")
    if isinstance(data, dict):
        for key in keys:
            found = _flatten(data.get(key))
            if found:
                return found
    return []


class AttackCoverageUseCase:
    """Aggregate ATT&CK technique/tactic coverage over stored alerts."""

    def __init__(self, alerts_provider: Callable[[], Iterable[dict[str, Any]]]) -> None:
        """Create the use case.

        Args:
            alerts_provider: Zero-arg callable returning the alerts to
                analyse (e.g. ``repo.get_alerts``). Kept as a callable so
                the use case does not depend on a concrete repository
                signature — SQLite and in-memory repos expose different
                ``get_alerts`` keyword arguments.
        """
        if alerts_provider is None:
            raise ValueError("alerts_provider is required for AttackCoverageUseCase")
        self._alerts_provider = alerts_provider

    def coverage(self, limit: int | None = None) -> dict[str, Any]:
        """Compute technique and tactic coverage over the stored alerts.

        Args:
            limit: Optional cap on the number of alerts analysed (most
                recent first, whatever ordering the provider uses).

        Returns:
            dict: ``total_alerts``, ``alerts_with_techniques``,
            ``coverage_percent`` (share of alerts carrying technique tags),
            ``techniques`` (``{technique_id: count}``), ``tactics``
            (``{tactic: count}``) and ``unique_techniques``.
        """
        alerts = list(self._alerts_provider() or [])
        if limit is not None:
            alerts = alerts[: max(0, limit)]

        techniques: Counter[str] = Counter()
        tactics: Counter[str] = Counter()
        with_techniques = 0

        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            alert_techniques = _extract_tags(alert, TECHNIQUE_KEYS)
            if alert_techniques:
                with_techniques += 1
            techniques.update(alert_techniques)
            tactics.update(_extract_tags(alert, TACTIC_KEYS))

        total = len(alerts)
        return {
            "total_alerts": total,
            "alerts_with_techniques": with_techniques,
            "coverage_percent": round(100.0 * with_techniques / total, 2) if total else 0.0,
            "unique_techniques": len(techniques),
            "techniques": dict(techniques.most_common()),
            "tactics": dict(tactics.most_common()),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def heatmap(
        self,
        limit: int | None = None,
        responded_statuses: Iterable[str] = (
            "forwarded",
            "responded",
            "contained",
            "resolved",
            "closed",
        ),
    ) -> dict[str, Any]:
        """IR1: coverage × response matrix per technique.

        ``coverage()`` counts which techniques the corpus exercises;
        ``heatmap()`` adds the response dimension — for each technique,
        how many tagged alerts also reached a responded state
        (``alert.status`` in ``responded_statuses``). A technique with
        high coverage and zero response is a playbook gap.

        Returns per-technique ``{alerts, responded, response_rate}``
        plus aggregate ``response_rate_percent``.
        """
        alerts = list(self._alerts_provider() or [])
        if limit is not None:
            alerts = alerts[: max(0, limit)]

        per_technique, tagged_alerts, responded_alerts = self._accumulate(
            alerts, {s.lower() for s in responded_statuses}
        )

        matrix = {
            tid: stats | {"response_rate": round(100.0 * stats["responded"] / stats["alerts"], 2)}
            for tid, stats in sorted(
                per_technique.items(), key=lambda kv: kv[1]["alerts"], reverse=True
            )
        }
        return {
            "techniques": matrix,
            "unique_techniques": len(matrix),
            "tagged_alerts": tagged_alerts,
            "responded_alerts": responded_alerts,
            "response_rate_percent": (
                round(100.0 * responded_alerts / tagged_alerts, 2) if tagged_alerts else 0.0
            ),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @staticmethod
    def _accumulate(
        alerts: list[dict[str, Any]], responded_set: set[str]
    ) -> tuple[dict[str, dict[str, int]], int, int]:
        """Count alerts/responded per technique over the corpus."""
        per_technique: dict[str, dict[str, int]] = {}
        responded_alerts = 0
        tagged_alerts = 0
        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            techniques = _extract_tags(alert, TECHNIQUE_KEYS)
            if not techniques:
                continue
            tagged_alerts += 1
            is_responded = str(alert.get("status") or "").lower() in responded_set
            if is_responded:
                responded_alerts += 1
            for tid in techniques:
                stats = per_technique.setdefault(tid, {"alerts": 0, "responded": 0})
                stats["alerts"] += 1
                if is_responded:
                    stats["responded"] += 1
        return per_technique, tagged_alerts, responded_alerts

    def navigator_layer(self, name: str = "SOAR Lab ATT&CK coverage") -> dict[str, Any]:
        """Export coverage as a MITRE ATT&CK Navigator layer document.

        Args:
            name: Display name for the layer inside Navigator.

        Returns:
            dict: Navigator layer JSON (spec v4.5); import it via
            "Open Existing Layer" in the ATT&CK Navigator.
        """
        summary = self.coverage()
        techniques: dict[str, int] = summary["techniques"]
        max_count = max(techniques.values(), default=1)

        return {
            "name": name,
            "versions": {
                "attack": NAVIGATOR_ATTACK_VERSION,
                "navigator": NAVIGATOR_VERSION,
                "layer": NAVIGATOR_LAYER_VERSION,
            },
            "domain": "enterprise-attack",
            "description": (
                "Techniques exercised by the SOAR Ransomware Lab alert "
                "corpus; score = number of alerts tagged with the technique."
            ),
            "techniques": [
                {
                    "techniqueID": tid,
                    "score": count,
                    "comment": f"{count} alert(s)",
                }
                for tid, count in techniques.items()
            ],
            "gradient": {
                "colors": ["#e8f4ff", "#ff6666"],
                "minValue": 0,
                "maxValue": max_count,
            },
            "legendItems": [
                {
                    "label": "alerts tagged with technique",
                    "color": "#ff6666",
                }
            ],
            "metadata": [
                {"name": "generated_at", "value": summary["timestamp"]},
                {"name": "total_alerts", "value": str(summary["total_alerts"])},
                {
                    "name": "coverage_percent",
                    "value": str(summary["coverage_percent"]),
                },
            ],
        }
