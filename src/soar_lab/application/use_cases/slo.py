"""SLO evaluation use case (O2).

SLOs are declared in ``config/slo.yaml`` — a metric path inside the
aggregated-KPI payload, a comparator and a target. ``evaluate`` walks
each definition against the computed KPI dict and reports compliance,
turning "we track MTTR" into "MTTR p50 meets its bound".
"""

from pathlib import Path
from typing import Any

import yaml

__all__ = ["SLODefinition", "evaluate_slos", "load_slo_definitions"]

_DEFAULT_SLO_PATH = Path(__file__).resolve().parents[2] / "config" / "slo.yaml"


class SLODefinition(dict):
    """Mapping subclass for one SLO row (name/metric/comparator/target)."""


def load_slo_definitions(path: Path | None = None) -> list[SLODefinition]:
    """Load SLO rows from ``slo.yaml``; missing/empty file → no SLOs."""
    slo_path = path or _DEFAULT_SLO_PATH
    if not slo_path.exists():
        return []
    data = yaml.safe_load(slo_path.read_text(encoding="utf-8")) or {}
    rows = data.get("slos") or []
    return [SLODefinition(r) for r in rows if isinstance(r, dict)]


def _metric_value(payload: dict[str, Any], dotted: str) -> Any:
    node: Any = payload
    for part in dotted.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def evaluate_slos(
    kpi_payload: dict[str, Any],
    definitions: list[SLODefinition] | None = None,
    *,
    slo_path: Path | None = None,
) -> dict[str, Any]:
    """Evaluate declared SLOs against an aggregated-KPI payload.

    Returns ``{slos: [{name, metric, comparator, target, actual, met}],
    met_count, total, all_met}``. A missing metric reports ``met=None``
    (no data) rather than silently passing or failing.
    """
    defs = definitions if definitions is not None else load_slo_definitions(slo_path)
    results: list[dict[str, Any]] = []
    met_count = 0
    for row in defs:
        actual = _metric_value(kpi_payload, str(row.get("metric", "")))
        target = row.get("target")
        comparator = str(row.get("comparator", "lte"))
        met: bool | None
        if actual is None or target is None:
            met = None
        elif comparator == "lte":
            met = actual <= target
        elif comparator == "gte":
            met = actual >= target
        else:
            met = None
        if met:
            met_count += 1
        results.append(
            {
                "name": row.get("name"),
                "description": row.get("description", ""),
                "metric": row.get("metric"),
                "comparator": comparator,
                "target": target,
                "actual": actual,
                "met": met,
            }
        )
    return {
        "slos": results,
        "met_count": met_count,
        "total": len(results),
        "all_met": bool(results) and met_count == len(results),
    }
