"""Calculate global quality score (0-100) from all metrics."""

from typing import Any


def calculate(metrics: dict[str, Any]) -> dict[str, Any]:
    """Calculate weighted quality score.

    Weights:
        20% maintainability
        20% coverage
        15% complexity
        15% linting
        10% typing
        10% security
         5% documentation
         5% architecture
    """
    scores: dict[str, float] = {}

    mi = metrics.get("maintainability", {})
    avg_mi = mi.get("average_mi", 0)
    scores["maintainability"] = min(avg_mi, 100)

    cov = metrics.get("coverage", {})
    line_cov = cov.get("global_line_coverage", 0)
    scores["coverage"] = line_cov

    cx = metrics.get("complexity", {})
    avg_cx = cx.get("average_complexity", 0)
    if avg_cx <= 5:
        scores["complexity"] = 100
    elif avg_cx <= 10:
        scores["complexity"] = 80
    elif avg_cx <= 15:
        scores["complexity"] = 60
    elif avg_cx <= 20:
        scores["complexity"] = 40
    else:
        scores["complexity"] = 20

    ruff = metrics.get("linting", {})
    errors = ruff.get("total_errors", 0)
    scores["linting"] = max(0, 100 - errors * 2)

    mypy = metrics.get("typing", {})
    mypy_errors = mypy.get("error_count", 0)
    scores["typing"] = max(0, 100 - mypy_errors * 10)

    sec = metrics.get("security", {})
    by_sev = sec.get("by_severity", {})
    high = by_sev.get("HIGH", 0)
    medium = by_sev.get("MEDIUM", 0)
    if high > 0:
        scores["security"] = 0
    elif medium > 0:
        scores["security"] = max(0, 100 - medium * 10)
    else:
        scores["security"] = 100

    doc = metrics.get("documentation", {})
    doc_cov = doc.get("coverage_percent", 0)
    scores["documentation"] = doc_cov

    arch = metrics.get("architecture", {})
    violations = arch.get("violation_count", 0)
    scores["architecture"] = max(0, 100 - violations * 10)

    weights = {
        "maintainability": 0.20,
        "coverage": 0.20,
        "complexity": 0.15,
        "linting": 0.15,
        "typing": 0.10,
        "security": 0.10,
        "documentation": 0.05,
        "architecture": 0.05,
    }
    total = sum(scores.get(k, 0) * w for k, w in weights.items())

    if total >= 90:
        classification = "Excellent"
    elif total >= 80:
        classification = "Good"
    elif total >= 70:
        classification = "Acceptable"
    elif total >= 60:
        classification = "Medium risk"
    elif total >= 50:
        classification = "High risk"
    else:
        classification = "Critical"

    return {
        "score": round(total, 1),
        "classification": classification,
        "category_scores": {k: round(v, 1) for k, v in scores.items()},
        "weights": weights,
    }
