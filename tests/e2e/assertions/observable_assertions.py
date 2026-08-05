"""
Shared assertions for observable validation in E2E tests.
"""

from typing import Dict, List, Any


# TheHive 3.x stores TLP/PAP as integers (0=white, 1=green, 2=amber, 3=red).
_TLP_MAP = {
    0: 0, "0": 0, "white": 0,
    1: 1, "1": 1, "green": 1,
    2: 2, "2": 2, "amber": 2,
    3: 3, "3": 3, "red": 3,
}


def _normalize_tlp(value: Any) -> Any:
    """Return canonical numeric TLP/PAP level for comparison."""
    if value is None:
        return None
    mapped = _TLP_MAP.get(value)
    if mapped is not None:
        return mapped
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def assert_observable_type(observable: Dict[str, Any], expected_type: str):
    """Assert that an observable has the expected type."""
    assert observable.get(
        "dataType") == expected_type, f"Expected type {expected_type}, got {observable.get('dataType')}"


def assert_observable_value(observable: Dict[str, Any], expected_value: str):
    """Assert that an observable has the expected value."""
    assert observable.get("data") == expected_value, f"Expected value {expected_value}, got {observable.get('data')}"


def assert_observable_tlp(observable: Dict[str, Any], expected_tlp: Any):
    """Assert that an observable has the expected TLP level."""
    actual = observable.get("tlp")
    assert _normalize_tlp(actual) == _normalize_tlp(expected_tlp), f"Expected TLP {expected_tlp}, got {actual}"


def assert_observable_pap(observable: Dict[str, Any], expected_pap: Any):
    """Assert that an observable has the expected PAP level."""
    actual = observable.get("pap")
    assert _normalize_tlp(actual) == _normalize_tlp(expected_pap), f"Expected PAP {expected_pap}, got {actual}"


def assert_observable_has_tags(observable: Dict[str, Any], min_tags: int = 1):
    """Assert that an observable has at least the minimum number of tags."""
    tags = observable.get("tags", [])
    assert len(tags) >= min_tags, f"Expected at least {min_tags} tags, got {len(tags)}"


def assert_observable_has_tag(observable: Dict[str, Any], tag: str):
    """Assert that an observable has a specific tag."""
    tags = observable.get("tags", [])
    assert tag in tags, f"Expected tag {tag}, not found in {tags}"


def assert_observables_match_payload(observables: List[Dict[str, Any]], payload_iocs: List[Dict[str, Any]]):
    """Assert that observables match the IoCs from the payload."""
    obs_values = {obs.get("value") for obs in observables}
    payload_values = {ioc.get("value") for ioc in payload_iocs}

    missing = payload_values - obs_values
    extra = obs_values - payload_values

    assert not missing, f"Missing observables for IoCs: {missing}"
    assert not extra, f"Extra observables not in payload: {extra}"
