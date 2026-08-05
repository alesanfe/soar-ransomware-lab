"""
Shared assertions for trace validation in E2E tests.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Union


def _parse_timestamp(ts: Union[str, int, float]) -> datetime:
    """Parse an ISO string or Unix timestamp (seconds or milliseconds) into an aware datetime."""
    if isinstance(ts, (int, float)):
        value = float(ts)
        if value > 1e12:
            value = value / 1000.0
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(ts, str):
        s = ts.strip()
        try:
            value = float(s)
            if value > 1e12:
                value = value / 1000.0
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except ValueError:
            pass
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    raise ValueError(f"Unsupported timestamp type: {type(ts)}")


def assert_trace_id_present(data: Dict[str, Any], trace_id: str):
    """Assert that a trace_id is present in the data."""
    assert data.get("trace_id") == trace_id, f"Expected trace_id {trace_id}, got {data.get('trace_id')}"


def assert_trace_id_consistent(systems: List[Dict[str, Any]], trace_id: str):
    """Assert that all systems have the same trace_id."""
    for system in systems:
        system_name = system.get("name", "unknown")
        assert system.get(
            "trace_id") == trace_id, f"System {system_name} has trace_id {system.get('trace_id')}, expected {trace_id}"


def assert_trace_id_in_logs(logs: List[str], trace_id: str):
    """Assert that trace_id appears in logs."""
    trace_logs = [log for log in logs if trace_id in log]
    assert len(trace_logs) > 0, f"Trace ID {trace_id} not found in logs"


def assert_trace_timestamps_sequential(systems: List[Dict[str, Any]]):
    """Assert that trace timestamps are sequential across systems."""
    timestamps = []
    for system in systems:
        ts = system.get("timestamp")
        if ts:
            timestamps.append((system.get("name"), _parse_timestamp(ts)))

    timestamps.sort(key=lambda x: x[1])

    for i in range(1, len(timestamps)):
        prev_name, prev_ts = timestamps[i - 1]
        curr_name, curr_ts = timestamps[i]
        assert curr_ts >= prev_ts, f"Timestamp out of order: {prev_name} ({prev_ts}) -> {curr_name} ({curr_ts})"
