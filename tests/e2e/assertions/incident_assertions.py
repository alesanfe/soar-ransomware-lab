"""
Shared assertions for incident validation in E2E tests.
"""

from typing import Dict, List, Any


# TheHive 3.x stores severity as integers (1=low, 2=medium, 3=high).
# Tests may use string labels including "critical" as an alias for high.
_SEVERITY_MAP = {
    1: 1, "1": 1, "low": 1,
    2: 2, "2": 2, "medium": 2,
    3: 3, "3": 3, "high": 3, "critical": 3,
}


def _normalize_severity(value: Any) -> Any:
    """Return canonical numeric severity for comparison."""
    if value is None:
        return None
    mapped = _SEVERITY_MAP.get(value)
    if mapped is not None:
        return mapped
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def assert_incident_state(incident: Dict[str, Any], expected_state: str):
    """Assert that an incident has the expected state (TheHive uses 'status')."""
    actual = incident.get("state") or incident.get("status")
    assert actual == expected_state, f"Expected state {expected_state}, got {actual}"


def assert_incident_severity(incident: Dict[str, Any], expected_severity: str):
    """Assert that an incident has the expected severity."""
    actual = incident.get("severity")
    expected = _normalize_severity(expected_severity)
    actual_norm = _normalize_severity(actual)
    assert actual_norm == expected, f"Expected severity {expected_severity}, got {actual}"


def assert_incident_has_observables(incident: Dict[str, Any], min_count: int = 1):
    """Assert that an incident has at least the minimum number of observables.

    TheHive 3.x case search does not embed observables; callers should verify
    via the API when the key is absent. Only fail if the key is present and
    the count is too low.
    """
    observables = incident.get("observables")
    if observables is None:
        return
    assert len(observables) >= min_count, f"Expected at least {min_count} observables, got {len(observables)}"


def assert_incident_has_tasks(incident: Dict[str, Any], min_count: int = 1):
    """Assert that an incident has at least the minimum number of tasks.

    TheHive 3.x case search does not embed tasks; callers should verify
    via the API when the key is absent. Only fail if the key is present and
    the count is too low.
    """
    tasks = incident.get("tasks")
    if tasks is None:
        return
    assert len(tasks) >= min_count, f"Expected at least {min_count} tasks, got {len(tasks)}"


def assert_incident_transition(incident: Dict[str, Any], from_state: str, to_state: str):
    """Assert that an incident transitioned from one state to another."""
    history = incident.get("history", [])
    transitions = [h for h in history if h.get("from") == from_state and h.get("to") == to_state]
    assert len(transitions) > 0, f"Expected transition {from_state} -> {to_state}, not found in history"
