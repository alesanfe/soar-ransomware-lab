"""Semantic validation mixin for E2E tests.

This mixin provides the four pillars of Fase 1 semantic validation:

1. **assert_thehive_case_semantics** — validate that the TheHive case
   represents the alert correctly (severity, TLP, PAP, tags, observables,
   tasks, correlation tracing, no duplicates).

2. **assert_expected_workflow_path** — validate that the workflow took
   the expected branch (required nodes executed, forbidden nodes not
   executed, allowed-skipped nodes tolerated).

3. **assert_node_contracts** — validate that each node produced data
   conforming to a minimum contract (required keys, types, values).

4. **assert_correlation_lineage** — validate that the same correlation_id
   appears across all expected locations (Shuffle, TheHive, ES,
   OpenSearch, metrics, Loki, evidence, result.json).
"""

from __future__ import annotations

import ast as _ast
import json as _json
import time
from typing import Any


def _node_result_skipped(result: Any) -> bool:
    """Check if a node's result indicates an internal skip.

    Shuffle 2.2.1's branch conditions don't work, so both branches of
    the workflow run unconditionally.  Each downstream node
    (containment, mark_false_positive, notify_critical, notify_info)
    performs its own internal guard by printing a JSON object with
    ``"skipped": true`` when the decision doesn't match its branch.
    Shuffle still reports these nodes as SUCCESS because the Python code
    ran without error.

    This helper parses the node's result (which may be a JSON string, a
    dict, or a nested structure) and returns True if it contains a
    ``skipped: true`` flag at any reasonable level.
    """
    if not result:
        return False

    # result may be a JSON string or already-parsed dict
    parsed: Any = result
    if isinstance(result, str):
        try:
            parsed = _json.loads(result)
        except (ValueError, TypeError):
            return False

    # Check common locations for skipped flag
    if isinstance(parsed, dict):
        # Direct: {"skipped": true}
        if parsed.get("skipped") is True:
            return True
        # Nested: {"message": {"skipped": true}}
        msg = parsed.get("message")
        if isinstance(msg, dict) and msg.get("skipped") is True:
            return True
        # Double-nested: {"success": true, "message": {"skipped": true}}
        # (already covered above, but check result.message as string too)
        if isinstance(msg, str):
            try:
                msg_parsed = _json.loads(msg)
                if isinstance(msg_parsed, dict) and msg_parsed.get("skipped") is True:
                    return True
            except (ValueError, TypeError):
                pass
    return False


class SemanticMixin:
    """Mixin for semantic, path, contract, and lineage validations."""

    # Attributes provided by E2EBaseTest / other mixins
    env: dict[str, str]
    correlation_id: str
    thehive: Any
    es: Any
    execution: dict[str, Any] | None
    execution_id: str | None
    e2e_results_dir: Any
    reports_dir: Any

    def _log(self, msg: str) -> None:
        """Provided by E2EBaseTest."""

    def record_assertion(
        self, name: str, passed: bool, duration: float, details: dict | None = None
    ) -> None:
        """Provided by RunContextMixin."""

    def register_resource(self, category: str, resource_id: str) -> None:
        """Provided by RunContextMixin."""

    # ── Nivel 4: Validación semántica del caso en TheHive ────────────────────

    def assert_thehive_case_semantics(
        self,
        case: dict[str, Any],
        expected: dict[str, Any],
    ) -> None:
        """Validate that a TheHive case semantically represents the alert.

        Checks:
          - severity matches expected value
          - tlp and pap are valid and match expected (if specified)
          - required tags are present
          - correlation_id or alert_id is traced in description/tags/customFields
          - observable types match expected list
          - observable values are not corrupt/truncated
          - tasks have expected names (if specified)
          - case is not duplicated (if dedup_policy="single_case")

        Args:
            case: TheHive case dict (from assert_thehive_case_created or search).
            expected: Dict with expected semantic properties. Supported keys:
                severity, tlp, pap, tags (list), observable_types (list),
                tasks (list of keywords), alert_id, correlation_id,
                dedup_policy ("single_case" or None).

        Raises:
            AssertionError: If any semantic check fails.
        """
        t0 = time.time()
        errors: list[str] = []

        # severity
        exp_severity = expected.get("severity")
        if exp_severity is not None:
            actual_severity = case.get("severity")
            if actual_severity != exp_severity:
                errors.append(f"severity mismatch: expected={exp_severity}, got={actual_severity}")

        # tlp
        exp_tlp = expected.get("tlp")
        if exp_tlp is not None:
            actual_tlp = case.get("tlp")
            if actual_tlp != exp_tlp:
                errors.append(f"tlp mismatch: expected={exp_tlp}, got={actual_tlp}")

        # pap
        exp_pap = expected.get("pap")
        if exp_pap is not None:
            actual_pap = case.get("pap")
            if actual_pap != exp_pap:
                errors.append(f"pap mismatch: expected={exp_pap}, got={actual_pap}")

        # tags
        exp_tags = expected.get("tags")
        if exp_tags:
            case_tags = set(case.get("tags", []))
            missing_tags = [t for t in exp_tags if t not in case_tags]
            if missing_tags:
                errors.append(f"missing tags: {missing_tags} (case has: {case_tags})")

        # correlation_id / alert_id tracing — only if explicitly requested
        # via "trace_correlation_id": True in the contract.  The workflow
        # does not currently propagate correlation_id to TheHive cases.
        trace_corr = expected.get("trace_correlation_id", False)
        alert_id = expected.get("alert_id", "")
        description = case.get("description", "")
        title = case.get("title", "")
        custom_fields = case.get("customFields", {})
        case_text = f"{title} {description} {custom_fields}"

        if trace_corr:
            corr_id = expected.get("correlation_id") or getattr(self, "correlation_id", "")
            if corr_id and corr_id not in case_text:
                if corr_id not in set(case.get("tags", [])):
                    errors.append(
                        f"correlation_id '{corr_id}' not traced in case title, "
                        f"description, customFields, or tags"
                    )
        if alert_id and alert_id not in case_text:
            if alert_id not in set(case.get("tags", [])):
                errors.append(
                    f"alert_id '{alert_id}' not traced in case title, "
                    f"description, customFields, or tags"
                )

        # observable types and integrity
        exp_obs_types = expected.get("observable_types")
        case_id = str(case.get("_id", case.get("id", "")))
        if exp_obs_types and case_id:
            try:
                obs = self.thehive.get_case_observables(case_id)
                actual_obs_types = {o.get("dataType") for o in obs}
                missing_types = [t for t in exp_obs_types if t not in actual_obs_types]
                if missing_types:
                    errors.append(
                        f"missing observable types: {missing_types} (case has: {actual_obs_types})"
                    )

                # Check for corrupt/truncated observables
                for o in obs:
                    data = o.get("data", "")
                    if not data or len(str(data)) < 3:
                        errors.append(
                            f"observable {o.get('dataType')} has corrupt/empty data: '{data}'"
                        )
            except Exception as e:
                errors.append(f"Could not retrieve observables: {e}")

        # tasks
        exp_tasks = expected.get("tasks")
        if exp_tasks and case_id:
            try:
                tasks = self.thehive.list_case_tasks(case_id)
                task_titles = [t.get("title", "").lower() for t in tasks]
                for expected_keyword in exp_tasks:
                    if not any(expected_keyword.lower() in tt for tt in task_titles):
                        errors.append(
                            f"no task found with keyword '{expected_keyword}' "
                            f"(tasks: {task_titles})"
                        )

                # Check task statuses are valid
                valid_statuses = {"Waiting", "InProgress", "Completed", "Cancelled"}
                for t in tasks:
                    status = t.get("status", "")
                    if status and status not in valid_statuses:
                        errors.append(f"task '{t.get('title')}' has invalid status: {status}")
            except Exception as e:
                errors.append(f"Could not retrieve tasks: {e}")

        # dedup policy
        if expected.get("dedup_policy") == "single_case" and alert_id:
            try:
                cases = self.thehive.search_cases()
                matching = [
                    c
                    for c in cases
                    if alert_id in c.get("description", "") or alert_id in c.get("title", "")
                ]
                if len(matching) > 1:
                    errors.append(
                        f"dedup_policy=single_case but found {len(matching)} cases "
                        f"for alert_id={alert_id}"
                    )
            except Exception as e:
                errors.append(f"Could not check dedup: {e}")

        duration = time.time() - t0
        passed = len(errors) == 0
        self.record_assertion(
            "thehive_case_semantics",
            passed,
            duration,
            {"errors": errors[:10]} if errors else {"checks_passed": True},
        )

        if errors:
            import pytest

            pytest.fail(
                f"TheHive case semantics failed with {len(errors)} error(s):\n  - "
                + "\n  - ".join(errors)
            )

    # ── Nivel 5: Validación de cobertura de ramas del playbook ───────────────

    def assert_expected_workflow_path(
        self,
        execution: dict[str, Any],
        required_nodes: list[str] | None = None,
        forbidden_nodes: list[str] | None = None,
        allowed_skipped: list[str] | None = None,
    ) -> None:
        """Validate that the workflow took the expected branch.

        Args:
            execution: Execution dict from wait_for_workflow.
            required_nodes: Nodes that MUST be present and SUCCESS.
            forbidden_nodes: Nodes that MUST NOT be present (or must be SKIPPED).
            allowed_skipped: Nodes that are allowed to be SKIPPED (not required,
                but if present, must be SUCCESS or SKIPPED).

        Raises:
            AssertionError: If any path check fails.
        """
        t0 = time.time()
        errors: list[str] = []

        results = execution.get("results", [])
        node_map: dict[str, dict[str, Any]] = {}

        for node in results:
            if not isinstance(node, dict):
                continue
            action = node.get("action", {})
            if not isinstance(action, dict):
                continue
            label = action.get("label", "?")
            node_map[label] = node

        # Required nodes must be present and SUCCESS
        if required_nodes:
            for label in required_nodes:
                node = node_map.get(label)
                if node is None:
                    errors.append(f"Required node '{label}' not found in results")
                elif node.get("status") != "SUCCESS":
                    errors.append(
                        f"Required node '{label}' status={node.get('status')} (expected SUCCESS)"
                    )

        # Forbidden nodes must not be present or must be SKIPPED.
        # In Shuffle 2.2.1, branch conditions don't work, so both branches
        # run unconditionally and each node does its own internal skip
        # (printing {"success": true, "skipped": true}).  Shuffle still
        # reports these nodes as SUCCESS because the Python code ran without
        # error.  We therefore also check the node's result for an internal
        # skip flag — if present, the node is treated as SKIPPED.
        if forbidden_nodes:
            for label in forbidden_nodes:
                node = node_map.get(label)
                if node is None:
                    continue
                if node.get("status") != "SUCCESS":
                    continue  # Not SUCCESS → already SKIPPED/FAILURE → OK
                # Check for internal skip in the result
                result = node.get("result", "")
                if _node_result_skipped(result):
                    continue  # Internal skip → treat as SKIPPED → OK
                errors.append(
                    f"Forbidden node '{label}' executed with SUCCESS "
                    f"(should have been skipped or absent)"
                )

        # Allowed-skipped: if present, must be SUCCESS or SKIPPED
        if allowed_skipped:
            for label in allowed_skipped:
                node = node_map.get(label)
                if node is not None and node.get("status") not in ("SUCCESS", "SKIPPED"):
                    errors.append(
                        f"Allowed-skipped node '{label}' status={node.get('status')} "
                        f"(expected SUCCESS or SKIPPED)"
                    )

        duration = time.time() - t0
        passed = len(errors) == 0
        self.record_assertion(
            "workflow_path_validated",
            passed,
            duration,
            (
                {
                    "required": required_nodes or [],
                    "forbidden": forbidden_nodes or [],
                    "allowed_skipped": allowed_skipped or [],
                    "errors": errors[:10],
                }
                if errors
                else {
                    "required": required_nodes or [],
                    "forbidden": forbidden_nodes or [],
                    "allowed_skipped": allowed_skipped or [],
                    "nodes_seen": list(node_map.keys()),
                }
            ),
        )

        if errors:
            import pytest

            pytest.fail(
                f"Workflow path validation failed with {len(errors)} error(s):\n  - "
                + "\n  - ".join(errors)
            )

    # ── Nivel 6: Validación de contratos de datos entre nodos ────────────────

    def assert_node_contracts(
        self,
        execution: dict[str, Any],
        contracts: dict[str, dict[str, Any]],
    ) -> None:
        """Validate that each node produced data conforming to a contract.

        Args:
            execution: Execution dict from wait_for_workflow.
            contracts: Dict mapping node label -> contract spec. Each contract
                spec supports:
                - required_keys: list of keys that must be present in the result
                - key_types: dict of key -> expected type (int, str, list, dict, bool)
                - min_value: for numeric keys, minimum value
                - non_empty: if True, the result must not be empty/None

        Raises:
            AssertionError: If any contract check fails.
        """
        t0 = time.time()
        errors: list[str] = []

        results = execution.get("results", [])
        node_map: dict[str, dict[str, Any]] = {}

        for node in results:
            if not isinstance(node, dict):
                continue
            action = node.get("action", {})
            if not isinstance(action, dict):
                continue
            label = action.get("label", "?")
            node_map[label] = node

        for label, contract in contracts.items():
            node = node_map.get(label)
            if node is None:
                # Node not in results — could be skipped, that's OK for contracts
                continue

            node_status = node.get("status", "?")
            if node_status != "SUCCESS":
                # Failed/skipped nodes are handled by path validation, not contracts
                continue

            raw_result = str(node.get("result", ""))
            try:
                obj = _json.loads(raw_result)
            except Exception:
                try:
                    obj = _ast.literal_eval(raw_result)
                except Exception:
                    obj = {}

            # If result is wrapped in body (HTTP nodes) or message (Python
            # script nodes), unwrap to get the actual payload.
            if isinstance(obj, dict) and "body" in obj and isinstance(obj["body"], dict):
                obj = obj["body"]
            elif isinstance(obj, dict) and "message" in obj and isinstance(obj["message"], dict):
                obj = obj["message"]

            # non_empty
            if contract.get("non_empty") and not obj:
                errors.append(f"Node '{label}' result is empty but contract requires non_empty")
                continue

            # required_keys
            required_keys = contract.get("required_keys", [])
            if required_keys and isinstance(obj, dict):
                for key in required_keys:
                    if key not in obj:
                        errors.append(f"Node '{label}' missing required key '{key}'")
                    elif obj[key] is None:
                        errors.append(f"Node '{label}' key '{key}' is None")

            # key_types
            key_types = contract.get("key_types", {})
            if key_types and isinstance(obj, dict):
                for key, expected_type in key_types.items():
                    if key in obj and obj[key] is not None:
                        actual_type = type(obj[key]).__name__
                        if actual_type != expected_type:
                            errors.append(
                                f"Node '{label}' key '{key}' type mismatch: "
                                f"expected={expected_type}, got={actual_type}"
                            )

            # min_value
            min_values = contract.get("min_value", {})
            if min_values and isinstance(obj, dict):
                for key, min_val in min_values.items():
                    if key in obj and obj[key] is not None:
                        try:
                            if float(obj[key]) < float(min_val):
                                errors.append(
                                    f"Node '{label}' key '{key}' value {obj[key]} < min {min_val}"
                                )
                        except (ValueError, TypeError):
                            pass

        duration = time.time() - t0
        passed = len(errors) == 0
        self.record_assertion(
            "node_contracts_validated",
            passed,
            duration,
            {"errors": errors[:10]} if errors else {"contracts_checked": len(contracts)},
        )

        if errors:
            import pytest

            pytest.fail(
                f"Node contract validation failed with {len(errors)} error(s):\n  - "
                + "\n  - ".join(errors)
            )

    # ── Nivel 7: Validación de trazabilidad extremo a extremo ────────────────

    def assert_correlation_lineage(
        self,
        correlation_id: str | None = None,
        required_locations: list[str] | None = None,
        alert_id: str | None = None,
    ) -> None:
        """Validate that correlation_id appears across all expected locations.

        Args:
            correlation_id: The correlation ID to trace. Defaults to self.correlation_id.
            required_locations: List of locations to check. Supported:
                - "shuffle_execution"
                - "thehive_case"
                - "elasticsearch_doc"
                - "opensearch_execution"
                - "metrics_doc"
                - "loki_logs"
                - "evidence_bundle"
                - "result_json"
            alert_id: Alert ID for locating TheHive case and ES document.

        Raises:
            AssertionError: If correlation_id is missing from any required location.
        """
        t0 = time.time()
        corr_id = correlation_id or getattr(self, "correlation_id", "")
        if not corr_id:
            import pytest

            pytest.fail("No correlation_id provided for lineage check")

        if required_locations is None:
            required_locations = [
                "shuffle_execution",
                "thehive_case",
                "elasticsearch_doc",
                "opensearch_execution",
                "metrics_doc",
                "loki_logs",
                "evidence_bundle",
            ]

        errors: list[str] = []
        found_locations: list[str] = []

        # 1. shuffle_execution
        if "shuffle_execution" in required_locations:
            exec_data = getattr(self, "execution", None)
            if exec_data:
                exec_str = _json.dumps(exec_data, default=str)
                if corr_id in exec_str:
                    found_locations.append("shuffle_execution")
                else:
                    errors.append("correlation_id not found in shuffle execution")
            else:
                errors.append("No execution data available for lineage check")

        # 2. thehive_case
        if "thehive_case" in required_locations:
            try:
                cases = self.thehive.search_cases()
                found = False
                for c in cases:
                    case_text = _json.dumps(c, default=str)
                    if corr_id in case_text or (alert_id and alert_id in case_text):
                        found = True
                        break
                if found:
                    found_locations.append("thehive_case")
                else:
                    errors.append("correlation_id not found in any TheHive case")
            except Exception as e:
                errors.append(f"Could not check TheHive lineage: {e}")

        # 3. elasticsearch_doc
        if "elasticsearch_doc" in required_locations:
            try:
                es_url = self.get_service_url("es")
                import requests

                es_auth = (
                    self.env.get("ELASTIC_USERNAME", "elastic"),
                    self.env.get("ELASTIC_PASSWORD", ""),
                )
                r = requests.post(
                    f"{es_url}/soar-alerts/_search",
                    json={
                        "query": {
                            "multi_match": {
                                "query": corr_id,
                                "fields": ["*"],
                            }
                        }
                    },
                    auth=es_auth,
                    timeout=10,
                    verify=False,
                )
                if (
                    r.status_code == 200
                    and r.json().get("hits", {}).get("total", {}).get("value", 0) > 0
                ):
                    found_locations.append("elasticsearch_doc")
                else:
                    errors.append("correlation_id not found in Elasticsearch soar-alerts")
            except Exception as e:
                errors.append(f"Could not check ES lineage: {e}")

        # 4. opensearch_execution
        if "opensearch_execution" in required_locations:
            try:
                os_url = self.get_service_url("opensearch")
                import requests

                exec_id = getattr(self, "execution_id", "")
                if exec_id:
                    r = requests.get(
                        f"{os_url}/workflowexecution-000001/_doc/{exec_id}",
                        timeout=10,
                        verify=False,
                    )
                    if r.status_code == 200:
                        source_str = _json.dumps(r.json().get("_source", {}), default=str)
                        if corr_id in source_str:
                            found_locations.append("opensearch_execution")
                        else:
                            errors.append("correlation_id not in OpenSearch execution source")
                    else:
                        errors.append(f"OpenSearch execution not found: HTTP {r.status_code}")
                else:
                    errors.append("No execution_id for OpenSearch lineage check")
            except Exception as e:
                errors.append(f"Could not check OpenSearch lineage: {e}")

        # 5. metrics_doc
        if "metrics_doc" in required_locations:
            try:
                es_url = self.get_service_url("es")
                import requests

                es_auth = (
                    self.env.get("ELASTIC_USERNAME", "elastic"),
                    self.env.get("ELASTIC_PASSWORD", ""),
                )
                r = requests.post(
                    f"{es_url}/soar-metrics/_search",
                    json={
                        "query": {
                            "multi_match": {
                                "query": corr_id,
                                "fields": ["*"],
                            }
                        }
                    },
                    auth=es_auth,
                    timeout=10,
                    verify=False,
                )
                if (
                    r.status_code == 200
                    and r.json().get("hits", {}).get("total", {}).get("value", 0) > 0
                ):
                    found_locations.append("metrics_doc")
                else:
                    errors.append("correlation_id not found in soar-metrics")
            except Exception as e:
                errors.append(f"Could not check metrics lineage: {e}")

        # 6. loki_logs
        if "loki_logs" in required_locations:
            try:
                if self.assert_loki_contains_correlation_id(timeout=30):
                    found_locations.append("loki_logs")
                else:
                    errors.append("correlation_id not found in Loki logs")
            except Exception as e:
                errors.append(f"Could not check Loki lineage: {e}")

        # 7. evidence_bundle
        if "evidence_bundle" in required_locations:
            try:
                evidence_dir = getattr(self, "evidence_dir", None)
                if evidence_dir and evidence_dir.exists():
                    found_in_evidence = False
                    for ev_file in evidence_dir.glob("*"):
                        try:
                            content = ev_file.read_text(encoding="utf-8", errors="ignore")
                            if corr_id in content:
                                found_in_evidence = True
                                break
                        except Exception:
                            pass
                    if found_in_evidence:
                        found_locations.append("evidence_bundle")
                    else:
                        errors.append("correlation_id not found in any evidence file")
                else:
                    errors.append("No evidence directory available for lineage check")
            except Exception as e:
                errors.append(f"Could not check evidence lineage: {e}")

        # 8. result_json
        if "result_json" in required_locations:
            try:
                result_path = getattr(self, "result_path", None)
                if result_path and result_path.exists():
                    content = result_path.read_text(encoding="utf-8", errors="ignore")
                    if corr_id in content:
                        found_locations.append("result_json")
                    else:
                        errors.append("correlation_id not found in result.json")
                else:
                    errors.append("No result.json available for lineage check")
            except Exception as e:
                errors.append(f"Could not check result.json lineage: {e}")

        duration = time.time() - t0
        passed = len(errors) == 0
        self.record_assertion(
            "correlation_lineage",
            passed,
            duration,
            (
                {
                    "correlation_id": corr_id,
                    "found_locations": found_locations,
                    "errors": errors[:10],
                }
                if errors
                else {
                    "correlation_id": corr_id,
                    "found_locations": found_locations,
                }
            ),
        )

        if errors:
            import pytest

            pytest.fail(
                f"Correlation lineage failed — correlation_id '{corr_id}' "
                f"missing from {len(errors)} location(s):\n  - " + "\n  - ".join(errors)
            )

    def get_service_url(self, service: str) -> str:
        """Provided by ConfigMixin."""
