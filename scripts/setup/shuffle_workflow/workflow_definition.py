"""Workflow Builder — assemble the complete Shuffle workflow payload.

This module is declarative: it receives a :class:`WorkflowContext`
(already-resolved keys, IDs, analyzer info) and produces the final
workflow definition dict that Shuffle's API expects.
"""

from __future__ import annotations

from typing import Any

from . import config
from .utils import param, pos
from .workflow_actions import (
    ACT_NORMALIZE,
    TRIGGER_NODE,
    WorkflowContext,
    build_actions,
    build_branches,
)


def build_workflow_definition(ctx: WorkflowContext) -> dict[str, Any]:
    """Assemble the complete workflow payload for Shuffle's API."""
    actions = build_actions(ctx)
    branches = build_branches(ctx)

    return {
        "name": config.WF_NAME,
        "description": (
            "Complete SOAR workflow: receives ransomware alert via webhook, "
            "creates case in TheHive, analyzes IOCs in Cortex, searches MISP, "
            "analyzes traffic with Tenzir, monitors network with Network Watcher, "
            "caches IoCs in Redis, searches logs in Loki, "
            "calculates risk score and verdict from Cortex results, "
            "branches into containment (malicious) or FalsePositive (benign), "
            "updates case status, sends notification, "
            "enriches case with results, calculates MTTR and indexes metrics in Elasticsearch."
        ),
        "start": ACT_NORMALIZE,
        "triggers": [
            {
                "app_name": "Shuffle Triggers",
                "name": "Webhook",
                "id": TRIGGER_NODE,
                "trigger_type": "webhook",
                "status": "running",
                "environment": "Shuffle",
                "position": pos(0, 0),
                "parameters": [param("info", "SIEM ransomware alert intake")],
                "is_valid": True,
                "isStartNode": True,
            }
        ],
        "actions": actions,
        "branches": branches,
    }
