"""Generic helpers for building Shuffle workflow payloads.

These functions are pure (no I/O, no env access) and can be unit-tested
in isolation.
"""

from __future__ import annotations

from typing import Any


def pos(x: float, y: float) -> dict[str, float]:
    """Build a Shuffle canvas position."""
    return {"x": float(x), "y": float(y)}


def action(
    aid: str,
    name: str,
    app_name: str,
    app_version: str,
    action_name: str,
    params: list[dict[str, Any]],
    position: dict[str, float],
    environment: str = "Shuffle",
    app_id: str = "",
) -> dict[str, Any]:
    """Build a Shuffle action node."""
    return {
        "id": aid,
        "name": action_name,  # must match the app function name (POST, GET, etc.)
        "label": name,  # human-readable label shown in the UI
        "app_name": app_name,
        "app_version": app_version,
        "app_id": app_id,
        "action_name": action_name,
        "parameters": params,
        "position": position,
        "environment": environment,
        "is_valid": True,
        "errors": [],
        "authentication": [],
    }


def execute_python_action(
    aid: str,
    label: str,
    code: str,
    position: dict[str, float],
    app_id: str,
    app_version: str = "1.2.0",
) -> dict[str, Any]:
    """Build a Shuffle Tools ``execute_python`` action node.

    This is a convenience wrapper around :func:`action` for the very
    common case of an embedded Python script node.
    """
    return {
        "id": aid,
        "name": "execute_python",
        "label": label,
        "app_name": "Shuffle Tools",
        "app_version": app_version,
        "app_id": app_id,
        "action_name": "execute_python",
        "parameters": [{"name": "code", "value": code, "variant": "STATIC_VALUE"}],
        "position": position,
        "environment": "Shuffle",
        "is_valid": True,
        "errors": [],
        "authentication": [],
    }


def branch(bid: str, src: str, dst: str, conditions: list | None = None) -> dict[str, Any]:
    """Build a Shuffle branch."""
    return {
        "id": bid,
        "source_id": src,
        "destination_id": dst,
        "conditions": conditions or [],
    }


def cond(source_value: str, check: str, dest_value: str) -> dict[str, Any]:
    """Build a Shuffle branch condition.

    Format matches Shuffle's Condition struct:
    - source: WorkflowAppActionParameter with the left-side value
    - condition: WorkflowAppActionParameter with the operator (EQUALS, CONTAINS, etc.)
    - destination: WorkflowAppActionParameter with the right-side value
    """
    return {
        "source": {"name": "value", "value": source_value, "variant": "STATIC_VALUE"},
        "condition": {"name": "value", "value": check, "variant": "STATIC_VALUE"},
        "destination": {"name": "value", "value": dest_value, "variant": "STATIC_VALUE"},
    }


def param(name: str, value: Any, variant: str = "STATIC_VALUE") -> dict[str, Any]:
    """Build a Shuffle action parameter."""
    return {"name": name, "value": value, "variant": variant}
