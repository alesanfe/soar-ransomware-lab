"""Shared workflow validation helpers for E2E tests.

This module provides `validate_workflow_results` which checks that a
workflow execution completed successfully with no hidden service
failures.

All E2E tests that verify workflow execution results should use this
helper to ensure that HTTP errors, silently failed nodes, and service
failures are detected. Without this, a workflow can finish as "FINISHED"
while every service call (Cortex, MISP, TheHive) fails silently.
"""

import ast
import json


def validate_workflow_results(
    execution: dict,
    require_nodes: list[str] | None = None,
):
    """Validate that a workflow execution completed successfully with no hidden
    errors.

    Args:
        execution: Workflow execution dict from Shuffle API or OpenSearch.
        require_nodes: Optional list of node labels that must be present.

    Raises:
        AssertionError: If the workflow status is not FINISHED, if any node
            has a non-SUCCESS/SKIPPED status, or if any critical node has a
            hidden HTTP error (status >= 400 or success=false in body).
    """
    status = execution.get("status", "")
    assert (
        status == "FINISHED"
    ), f"Workflow status is {status}, expected FINISHED. Workflow did not complete successfully."

    results = execution.get("results", [])
    assert isinstance(results, list), "Workflow results must be a list"
    # results may be empty if the execution was fetched with include_results=False
    # In that case, skip node-level validation (the caller should fetch with
    # include_results=True if they need node validation)
    if not results:
        return

    # Nodes that make HTTP calls to external services - their results must
    # be checked for hidden HTTP errors even when status is SUCCESS.
    critical_nodes = {
        "thehive_create_case",
        "thehive_obs_hash",
        "thehive_obs_ip",
        "thehive_add_task",
        "thehive_add_observable",
        "cortex_hash",
        "cortex_ip",
        "cortex_hash_virusshare",
        "cortex_ip_dshield",
        "cortex_ip_mnemonic_pdns",
        "cortex_ip_googledns",
        "cortex_ip_ipapi",
        "misp_search",
        "misp_create",
        "es_index",
        "es_index_metrics",
        "tenzir_analyze",
        "tenzir_serve",
        "network_watch",
        "redis_cache",
        "loki_search",
    }

    node_labels = {}
    errors = []

    for node in results:
        if not isinstance(node, dict):
            continue
        action = node.get("action", {})
        if not isinstance(action, dict):
            continue
        label = action.get("label", "?")
        node_status = node.get("status", "?")

        # Every node must be SUCCESS or SKIPPED
        if node_status not in ("SUCCESS", "SKIPPED"):
            raw = str(node.get("result", ""))
            errors.append(
                f"Node '{label}' status={node_status}: {raw[:300]}"
            )
            continue

        node_labels[label] = node_status

        # For critical nodes with SUCCESS status, check for hidden HTTP errors
        if label in critical_nodes and node_status == "SUCCESS":
            raw_result = str(node.get("result", ""))
            try:
                obj = json.loads(raw_result)
            except Exception:
                try:
                    obj = ast.literal_eval(raw_result)
                except Exception:
                    obj = {}

            if isinstance(obj, dict):
                http_status = obj.get("status")
                if http_status is not None and int(http_status) >= 400:
                    errors.append(f"Node '{label}' returned HTTP {http_status}: {raw_result[:300]}")
                    continue

                body = obj.get("body", obj)
                if isinstance(body, dict) and body.get("success") is False:
                    exc = body.get("exception", "")
                    errors.append(
                        f"Node '{label}' reported success=false: {exc or raw_result[:300]}"
                    )
                    continue

    # Check required nodes are present
    if require_nodes:
        missing = [n for n in require_nodes if n not in node_labels]
        if missing:
            errors.append(f"Required nodes missing from results: {missing}")

    if errors:
        raise AssertionError(
            f"Workflow validation failed with {len(errors)} error(s):\n  - " + "\n  - ".join(errors)
        )
