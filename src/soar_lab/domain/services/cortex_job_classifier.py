"""Classify Cortex analyzer job outcomes (CTX-001).

Distinguishes *expected* analyzer outcomes (a verdict/report, or a
legitimate "no data" answer) from *infrastructure* failures (Docker,
network, timeouts, OOM — i.e. things the SOC should fix) so dashboards
don't flag empty-lookup jobs as platform incidents.
"""

from __future__ import annotations

from typing import Any

# Categories returned by classify_job()
CATEGORY_SUCCESS = "success"
CATEGORY_EXPECTED_EMPTY = "expected_no_data"
CATEGORY_VERDICT_ERROR = "analyzer_error"
CATEGORY_INFRA_FAILURE = "infrastructure_failure"
CATEGORY_UNKNOWN = "unknown"

# Message fingerprints — checked case-insensitively against the job's
# error/statusMessage fields.
_INFRA_HINTS = (
    "connection refused",
    "connection error",
    "timeout",
    "timed out",
    "no such host",
    "name or service not known",
    "cannot connect",
    "docker",
    "container",
    "image",
    "pull access denied",
    "oom",
    "out of memory",
    "killed",
    "internal server error",
    "502",
    "503",
    "504",
    "econnrefused",
    "socket",
    "certificate",
)

_EMPTY_HINTS = (
    "no data",
    "not found",
    "no results",
    "no result",
    "empty",
    "nxdomain",
    "no records",
    "does not exist",
    "unavailable data",
    "no information",
    "nothing to report",
    "null response",
)


def _messages(job: dict[str, Any]) -> str:
    """Collect searchable text from a job document."""
    parts: list[str] = []
    for key in ("statusMessage", "message", "error", "errorMessage"):
        v = job.get(key)
        if v:
            parts.append(str(v))
    report = job.get("report") or {}
    if isinstance(report, dict):
        for key in ("errorMessage", "message", "summary"):
            v = report.get(key)
            if v:
                parts.append(str(v))
    return " ".join(parts).lower()


def classify_job(job: dict[str, Any]) -> str:
    """Return the outcome category for one Cortex job document."""
    status = str(job.get("status", "")).upper()
    if status in ("SUCCESS", "FINISHED", "DONE"):
        return CATEGORY_SUCCESS
    if status in ("WAITING", "INPROGRESS", "RUNNING", "STARTED"):
        return CATEGORY_UNKNOWN

    text = _messages(job)
    if any(h in text for h in _INFRA_HINTS):
        return CATEGORY_INFRA_FAILURE
    if any(h in text for h in _EMPTY_HINTS):
        return CATEGORY_EXPECTED_EMPTY
    if status in ("FAILURE", "FAILED", "ERROR"):
        return CATEGORY_VERDICT_ERROR
    return CATEGORY_UNKNOWN


def summarize_jobs(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate jobs into counts + a drill-down of non-benign failures."""
    by_category: dict[str, int] = {}
    by_analyzer: dict[str, dict[str, int]] = {}
    flagged: list[dict[str, Any]] = []

    for job in jobs:
        cat = classify_job(job)
        by_category[cat] = by_category.get(cat, 0) + 1

        analyzer = (
            job.get("analyzerDefinitionId")
            or job.get("workerName")
            or job.get("analyzerName")
            or "unknown"
        )
        slot = by_analyzer.setdefault(analyzer, {})
        slot[cat] = slot.get(cat, 0) + 1

        if cat in (CATEGORY_INFRA_FAILURE, CATEGORY_VERDICT_ERROR):
            flagged.append(
                {
                    "job_id": job.get("id") or job.get("_id"),
                    "analyzer": analyzer,
                    "category": cat,
                    "status": job.get("status"),
                    "message": (job.get("statusMessage") or job.get("message") or "")[:300],
                }
            )

    return {
        "total": len(jobs),
        "by_category": by_category,
        "by_analyzer": by_analyzer,
        "flagged": flagged,
    }
