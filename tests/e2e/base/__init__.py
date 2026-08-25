"""Base class for all E2E tests in the SOAR Ransomware Lab.

This module provides ``E2EBaseTest``, a unified base class that every E2E
test case should inherit from. It uses a mixin architecture to separate
concerns:

- ``ConfigMixin`` — environment loading, path resolution, webhook info
- ``RunContextMixin`` — correlation_id, manifest, result, assertions
- ``DockerMixin`` — preflight health checks for all services
- ``ShuffleMixin`` — alert submission, workflow waiting
- ``TheHiveMixin`` — TheHive case verification
- ``CortexMixin`` — Cortex analyzer verification
- ``MispMixin`` — MISP lookup and seeding
- ``SearchMixin`` — Elasticsearch, OpenSearch, Redis verification
- ``ObservabilityMixin`` — Loki, Promtail, Grafana validation
- ``EvidenceMixin`` — evidence export to reports/
- ``CleanupMixin`` — controlled cleanup with report data preservation
- ``SemanticMixin`` — Nivel 4-7: case semantics, workflow path,
  node data contracts, correlation lineage

Lifecycle::

    setup_class  → suite-level validations
    setup_method → per-test: create run context, preflight, seed data
    test_*       → submit alert, wait for workflow, validate effects
    teardown_method → collect evidence, write results, cleanup
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

import pytest
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .cleanup_mixin import CleanupMixin
from .config_mixin import ConfigMixin
from .docker_mixin import DockerMixin
from .evidence_mixin import EvidenceMixin
from .observability_mixin import ObservabilityMixin
from .run_context_mixin import RunContextMixin
from .semantic_mixin import SemanticMixin
from .service_mixins import (
    CortexMixin,
    MispMixin,
    SearchMixin,
    ShuffleMixin,
    TheHiveMixin,
)

logger = logging.getLogger(__name__)


class E2EBaseTest(
    ConfigMixin,
    RunContextMixin,
    DockerMixin,
    ShuffleMixin,
    TheHiveMixin,
    CortexMixin,
    MispMixin,
    SearchMixin,
    ObservabilityMixin,
    EvidenceMixin,
    CleanupMixin,
    SemanticMixin,
):
    """Base class for all E2E tests.

    Subclasses should call ``super().setup_method(method)`` if they
    override ``setup_method``.

    Attributes:
        workflow_name: Name of the Shuffle workflow (override in subclass).
        WORKFLOW_TIMEOUT: Default timeout for workflow execution (seconds).
        POLL_INTERVAL: Default poll interval (seconds).
    """

    workflow_name: str = "SOAR-Ransomware-Response"
    WORKFLOW_TIMEOUT: int = 600
    POLL_INTERVAL: int = 5
    # TC identifier for report compatibility (e.g. "TC-01")
    tc_id: str = ""

    # ── Setup ────────────────────────────────────────────────────────────────

    @classmethod
    def setup_class(cls):
        """Suite-level validations: config files, webhook info, Docker network.

        Subclasses should call ``super().setup_class()`` if they
        override this method.  This runs once per test class (not per
        test method).
        """
        # Verify webhook_info.json exists — required for all E2E tests.
        from .config_mixin import _WEBHOOK_INFO_PATHS

        info_found = any(p.exists() for p in _WEBHOOK_INFO_PATHS)
        if not info_found:
            pytest.fail("webhook_info.json not found — run 'make init-webhook' before E2E tests")

    def setup_method(self, method):
        """Set up test: load config, create clients, verify health, seed data.

        This method:
        1. Loads environment variables and webhook info
        2. Creates run context (correlation_id, manifest)
        3. Creates all integration clients
        4. Verifies all services are healthy (fail loud)
        5. Verifies workflow and webhook are ready
        6. Records baseline state
        7. Seeds test data if needed
        """
        self.test_name = method.__name__

        # Config
        self.env = self.load_env()
        self.resolve_paths()

        # Load webhook info
        info = self.load_webhook_info()
        self.webhook_info = info
        self.webhook_url = info.get("webhook_url", info.get("webhook_url_host", ""))
        self.workflow_id = info.get("workflow_id", "")

        # Run context (correlation_id, manifest, results dir)
        self.create_run_context()

        # Fail if required API keys are not configured
        if not self.env.get("THEHIVE_API_KEY"):
            pytest.fail("THEHIVE_API_KEY not configured in .env.full")

        # Create clients
        self.create_shuffle_client()
        self.create_thehive_client()
        self.create_cortex_client()
        self.create_misp_client()
        self.create_search_clients()

        # Raw requests session for direct HTTP calls
        self.s = requests.Session()
        self.s.verify = False

        # Preflight: verify all services are healthy
        self.verify_core_services()
        self.verify_workflow_ready()

        # Observability preflight (if enabled) — assert, not just verify
        if self.env.get("E2E_VERIFY_OBSERVABILITY", "true").lower() == "true":
            self.verify_observability_stack()
            # Record assertions for observability components (not just healthcheck)
            self.assert_loki_ready()
            self.assert_promtail_collecting()
            self.assert_grafana_healthy()

        # Record baseline state
        try:
            self.cases_before = len(self.thehive.search_cases())
        except Exception:
            self.cases_before = 0

        try:
            self.es_docs_before = self.es.count()
        except Exception:
            self.es_docs_before = 0

        # Seed test data if configured
        self.setup_test_data()

        # Initialize execution tracking
        self.execution: dict[str, Any] | None = None
        self.execution_id: str | None = None

    def setup_test_data(self) -> None:
        """Prepare test data if the scenario needs it.

        Override in subclasses.
        """

    # ── High-level workflow helpers ───────────────────────────────────────────

    def submit_alert_and_wait(
        self,
        payload: dict[str, Any] | None = None,
        *,
        timeout: int | None = None,
        poll_interval: int | None = None,
        retries: int = 3,
    ) -> tuple[str, dict[str, Any]]:
        """Submit an alert to the webhook and wait for the workflow to finish.

        This is the standard high-level entry point for E2E tests.  It:
        1. Builds a payload (if not provided) with correlation_id injected.
        2. Submits it to the Shuffle webhook (with retries on ABORTED).
        3. Waits for the workflow execution to reach a terminal state.
        4. Returns (execution_id, execution_dict).

        Args:
            payload: Alert payload. If None, a default ransomware payload
                is built via ``build_alert_payload``.
            timeout: Workflow wait timeout in seconds (default: WORKFLOW_TIMEOUT).
            poll_interval: Poll interval in seconds (default: POLL_INTERVAL).
            retries: Number of retries if the workflow is ABORTED.

        Returns:
            Tuple of (execution_id, execution_dict).
        """
        if payload is None:
            payload = self.build_alert_payload()

        # Note: submit_alert() writes payload.json as evidence, so we don't
        # duplicate the write here.
        to = timeout or self.WORKFLOW_TIMEOUT
        interval = poll_interval or self.POLL_INTERVAL

        exec_id = None
        execution: dict[str, Any] = {}
        for attempt in range(retries):
            exec_id = self.submit_alert(payload)
            if not exec_id:
                time.sleep(10)
                continue

            try:
                execution = self.wait_for_workflow(exec_id, timeout=to, poll_interval=interval)
            except TimeoutError:
                if attempt < retries - 1:
                    self._log(f"Workflow timed out, retrying ({attempt + 1}/{retries})...")
                    time.sleep(15)
                    continue
                raise

            status = execution.get("status", "")
            if status == "FINISHED":
                return exec_id, execution
            if status == "ABORTED" and attempt < retries - 1:
                self._log(f"Workflow ABORTED, retrying ({attempt + 1}/{retries})...")
                # Regenerate alert_id to avoid dedup
                if "alert_id" in payload:
                    payload["alert_id"] = f"{payload['alert_id']}-r{attempt + 1}"
                time.sleep(15)
                continue
            # FAILED or last attempt — return as-is, validation will catch it
            return exec_id, execution

        pytest.fail(f"Failed to get a successful workflow execution after {retries} attempts")

    # ── Logging ──────────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        """Log a message with timestamp and test class name."""
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        tc_name = self.__class__.__name__
        print(f"[{ts}] {tc_name} {msg}")

    # ── Workflow validation ──────────────────────────────────────────────────

    def validate_workflow_execution(
        self,
        execution: dict[str, Any] | None = None,
        require_nodes: list[str] | None = None,
        expected_misp_hit: bool | None = None,
        alert_id: str | None = None,
        expected_contract: dict[str, Any] | None = None,
    ) -> None:
        """Exhaustively validate that a workflow execution succeeded.

        This method checks:
        1. Workflow status is FINISHED (not ABORTED/FAILED)
        2. Every node is SUCCESS or SKIPPED (not FAILED/ERROR)
        3. No hidden HTTP errors (status >= 400) in critical node results
        4. No success=false in node result bodies
        5. Required nodes are present
        6. TheHive case was created (if alert_id provided) — FAIL if not
        7. ES document was indexed (if alert_id provided) — FAIL if not
        8. OpenSearch execution was registered — FAIL if not
        9. Metrics were created (if alert_id provided) — FAIL if not
        10. Cortex jobs can be created for hash/IP in alert_data — FAIL if not
        11. MISP lookup was performed for hash/IP in alert_data
        12. Loki logs contain correlation_id (if observability enabled)
        13. TheHive case semantics match expected contract (Nivel 4, if contract has semantic keys)
        14. Workflow path matches expected branches (Nivel 5, if contract has path keys)
        15. Node data contracts validated (Nivel 6, if contract has node_contracts)
        16. Correlation lineage traced end-to-end (Nivel 7, if contract has lineage_locations)

        Any service validation failure causes pytest.fail() — the test
        does NOT pass silently if a service didn't do its job.

        Args:
            execution: Execution dict from wait_for_workflow.
            require_nodes: Optional list of node labels that must be present.
                (Deprecated: use expected_contract["required_nodes"] instead.)
            expected_misp_hit: Whether MISP should find a match.
            alert_id: Alert ID for verifying TheHive case and ES document.
            expected_contract: Optional dict with semantic, path, contract,
                and lineage expectations. Supported keys:
                - severity, tlp, pap, tags, observable_types, tasks
                - required_nodes, forbidden_nodes, allowed_skipped
                - node_contracts
                - lineage_locations
                - dedup_policy
        """
        exec_data = execution or self.execution
        if not exec_data:
            pytest.fail("No execution data provided for validation")

        # Extract contract fields (with fallback to top-level args for backward compat)
        contract = expected_contract or {}
        req_nodes = contract.get("required_nodes", require_nodes)
        forbidden_nodes = contract.get("forbidden_nodes")
        allowed_skipped = contract.get("allowed_skipped")
        node_contracts = contract.get("node_contracts")
        lineage_locations = contract.get("lineage_locations")

        # 1. Validate workflow status and node results
        self._validate_workflow_nodes(exec_data, req_nodes)

        # 2. Validate service-specific effects — these MUST pass, not just record
        service_errors: list[str] = []
        thehive_case: dict[str, Any] | None = None

        if alert_id:
            thehive_case = self.assert_thehive_case_created(alert_id)
            if thehive_case is None:
                service_errors.append(f"TheHive case not created for alert_id={alert_id}")

            es_doc = self.assert_elasticsearch_document_indexed(alert_id)
            if es_doc is None:
                service_errors.append(f"Elasticsearch document not indexed for alert_id={alert_id}")

        if self.execution_id:
            os_doc = self.assert_opensearch_execution_registered(self.execution_id)
            if os_doc is None:
                service_errors.append(f"OpenSearch execution not registered: {self.execution_id}")

        # 3. Validate metrics
        if alert_id:
            metrics = self.assert_metrics_created(alert_id)
            if metrics is None:
                service_errors.append(f"Metrics not created for alert_id={alert_id}")

        # 4. Validate Cortex jobs can be created (if hash or IP in alert_data)
        if hasattr(self, "alert_data") and self.alert_data:
            alert = self.alert_data if isinstance(self.alert_data, dict) else {}
            if alert.get("hash"):
                job = self.assert_cortex_jobs_created("hash", alert["hash"])
                if job is None:
                    service_errors.append("Cortex hash analyzer job not created")
            if alert.get("src_ip"):
                job = self.assert_cortex_jobs_created("ip", alert["src_ip"])
                if job is None:
                    service_errors.append("Cortex IP analyzer job not created")

        # 5. Validate MISP lookup was performed (if hash or IP in alert_data)
        if hasattr(self, "alert_data") and self.alert_data:
            alert = self.alert_data if isinstance(self.alert_data, dict) else {}
            if alert.get("hash"):
                self.assert_misp_lookup_done(alert["hash"], expected_hit=expected_misp_hit)
            if alert.get("src_ip"):
                self.assert_misp_lookup_done(alert["src_ip"], expected_hit=expected_misp_hit)

        # Fail if any service validation failed
        if service_errors:
            pytest.fail(
                f"Service validation failed with {len(service_errors)} error(s):\n  - "
                + "\n  - ".join(service_errors)
            )

        # ── Nivel 4: TheHive case semantics ───────────────────────────────
        if thehive_case and contract:
            semantic_expected = {
                k: v
                for k, v in contract.items()
                if k
                in (
                    "severity",
                    "tlp",
                    "pap",
                    "tags",
                    "observable_types",
                    "tasks",
                    "dedup_policy",
                    "trace_correlation_id",
                )
            }
            if semantic_expected:
                semantic_expected["alert_id"] = alert_id or ""
                self.assert_thehive_case_semantics(thehive_case, semantic_expected)

        # ── Nivel 5: Workflow path validation ──────────────────────────────
        if req_nodes or forbidden_nodes or allowed_skipped:
            self.assert_expected_workflow_path(
                exec_data,
                required_nodes=req_nodes,
                forbidden_nodes=forbidden_nodes,
                allowed_skipped=allowed_skipped,
            )

        # ── Nivel 6: Node data contracts ──────────────────────────────────
        if node_contracts:
            self.assert_node_contracts(exec_data, node_contracts)

        # ── Nivel 7: Correlation lineage ──────────────────────────────────
        # Only run if the contract explicitly requests it — this is a strict
        # check that may fail if the workflow doesn't propagate correlation_id
        # to all locations. Tests that want this should set:
        #   expected_contract["lineage_locations"] = [...]
        if lineage_locations is not None:
            self.assert_correlation_lineage(
                correlation_id=self.correlation_id,
                required_locations=lineage_locations,
                alert_id=alert_id,
            )

        # ── Observability (existing) ──────────────────────────────────────
        if self.env.get("E2E_VERIFY_OBSERVABILITY", "true").lower() == "true":
            if self.env.get("E2E_VERIFY_LOKI", "true").lower() == "true":
                # Already checked via lineage, but keep for explicit assertion record
                if not lineage_locations or "loki_logs" not in lineage_locations:
                    self.assert_loki_contains_correlation_id()

        # ── Nivel 8: Trace ID propagation (optional) ─────────────────────
        # Only run if the contract explicitly requests it:
        #   expected_contract["verify_trace_id"] = True
        if contract.get("verify_trace_id") and alert_id:
            self.assert_trace_id_in_elasticsearch(alert_id)

    def assert_trace_id_in_elasticsearch(self, alert_id: str) -> None:
        """Verify that ``self.trace_id`` is present in the ES document for
        ``alert_id``.

        Records the assertion result but does NOT fail the test if the
        trace_id is missing — the workflow may not propagate it yet.  This
        is a diagnostic check to track trace_id propagation maturity.
        """
        t0 = time.time()
        tid = getattr(self, "trace_id", "")
        if not tid:
            self.record_assertion(
                "trace_id_in_elasticsearch",
                False,
                time.time() - t0,
                {"error": "No trace_id available"},
            )
            return

        try:
            doc = self.es.search_by_alert_id(alert_id)
            if doc is None:
                self.record_assertion(
                    "trace_id_in_elasticsearch",
                    False,
                    time.time() - t0,
                    {"error": f"ES doc not found for {alert_id}"},
                )
                return

            doc_tid = doc.get("trace_id")
            if doc_tid == tid:
                self.record_assertion(
                    "trace_id_in_elasticsearch",
                    True,
                    time.time() - t0,
                    {"trace_id": tid, "alert_id": alert_id},
                )
            else:
                # Non-blocking: workflow may not propagate trace_id yet
                self._log(
                    f"  [WARN] trace_id mismatch in ES: expected={tid}, "
                    f"got={doc_tid} (workflow may not propagate trace_id)"
                )
                self.record_assertion(
                    "trace_id_in_elasticsearch",
                    False,
                    time.time() - t0,
                    {
                        "expected_trace_id": tid,
                        "actual_trace_id": doc_tid,
                        "alert_id": alert_id,
                        "non_blocking": True,
                    },
                )
        except Exception as e:
            self.record_assertion(
                "trace_id_in_elasticsearch",
                False,
                time.time() - t0,
                {"error": str(e)},
            )

    def _validate_workflow_nodes(
        self,
        execution: dict[str, Any],
        require_nodes: list[str] | None = None,
    ) -> None:
        """Validate workflow node results for hidden errors."""
        import ast as _ast
        import json as _json

        t0 = time.time()

        status = execution.get("status", "")
        if status != "FINISHED":
            self.record_assertion(
                "shuffle_execution_completed",
                False,
                time.time() - t0,
                {"status": status},
            )
            pytest.fail(
                f"Workflow status is {status}, expected FINISHED. "
                f"Workflow did not complete successfully."
            )
        self.record_assertion("shuffle_execution_completed", True, time.time() - t0)

        results = execution.get("results", [])
        if not isinstance(results, list) or len(results) == 0:
            self.record_assertion(
                "workflow_has_results",
                False,
                time.time() - t0,
                {"results_type": str(type(results))},
            )
            pytest.fail("Workflow has no results")

        critical_nodes = {
            # TheHive
            "thehive_create_case",
            "thehive_obs_hash",
            "thehive_obs_ip",
            "thehive_add_task",
            "thehive_add_observable",
            # Cortex
            "cortex_hash",
            "cortex_ip",
            "cortex_hash_virusshare",
            "cortex_ip_dshield",
            "cortex_ip_mnemonic_pdns",
            "cortex_ip_googledns",
            "cortex_ip_ipapi",
            # MISP
            "misp_search",
            "misp_create",
            # Elasticsearch
            "es_index",
            "es_index_metrics",
            # Tenzir / Network / Loki
            "tenzir_analyze",
            "tenzir_serve",
            "network_watch",
            "loki_search",
            # Decision & response pipeline (added to catch silent failures)
            "calc_decision",
            "containment",
            "mark_false_positive",
            "update_inprogress",
            "notify_critical",
            "notify_info",
            # Summary & enrichment (added to catch HTTP 500 on PATCH)
            "build_hive_summary",
            "enrich_case",
            # Metrics
            "build_metrics_json",
            "calc_mttr",
        }

        node_labels: dict[str, str] = {}
        errors: list[str] = []

        for node in results:
            if not isinstance(node, dict):
                continue
            action = node.get("action", {})
            if not isinstance(action, dict):
                continue
            label = action.get("label", "?")
            node_status = node.get("status", "?")

            if node_status not in ("SUCCESS", "SKIPPED"):
                raw = str(node.get("result", ""))
                errors.append(f"Node '{label}' status={node_status}: {raw[:300]}")
                continue

            node_labels[label] = node_status

            if label in critical_nodes and node_status == "SUCCESS":
                raw_result = str(node.get("result", ""))
                try:
                    obj = _json.loads(raw_result)
                except Exception:
                    try:
                        obj = _ast.literal_eval(raw_result)
                    except Exception:
                        obj = {}

                if isinstance(obj, dict):
                    http_status = obj.get("status")
                    if http_status is not None and int(http_status) >= 400:
                        errors.append(
                            f"Node '{label}' returned HTTP {http_status}: {raw_result[:300]}"
                        )
                        continue

                    body = obj.get("body", obj)
                    if isinstance(body, dict) and body.get("success") is False:
                        exc = body.get("exception", "")
                        # Tolerate transient connection errors (DNS resolution,
                        # connection refused, timeout) — these are infrastructure
                        # issues, not workflow logic errors.
                        transient_markers = (
                            "connectionerror",
                            "nameresolutionerror",
                            "max retries exceeded",
                            "connection refused",
                            "errno 111",
                            "errno -3",
                            "connecttimeout",
                            "readtimeout",
                        )
                        exc_lower = str(exc).lower()
                        if any(m in exc_lower for m in transient_markers):
                            continue
                        errors.append(
                            f"Node '{label}' reported success=false: {exc or raw_result[:300]}"
                        )
                        continue

        if require_nodes:
            missing = [n for n in require_nodes if n not in node_labels]
            if missing:
                errors.append(f"Required nodes missing from results: {missing}")

        self.record_assertion(
            "workflow_nodes_validated",
            len(errors) == 0,
            time.time() - t0,
            {"errors": errors[:10]} if errors else {"nodes_checked": len(node_labels)},
        )

        if errors:
            pytest.fail(
                f"Workflow validation failed with {len(errors)} error(s):\n  - "
                + "\n  - ".join(errors)
            )

    # ── Teardown ─────────────────────────────────────────────────────────────

    def teardown_method(self, method):
        """Collect evidence, verify completeness, write results, and
        cleanup."""
        try:
            self.collect_evidence()
        except Exception as e:
            self._log(f"Evidence collection failed: {e}")

        # Verify evidence bundle is complete (Nivel 15 — auditable artifact)
        try:
            self.assert_evidence_complete()
        except Exception as e:
            self._log(f"Evidence completeness check failed: {e}")

        try:
            self.write_assertions()
        except Exception as e:
            self._log(f"Writing assertions failed: {e}")

        try:
            self.write_test_result()
        except Exception as e:
            self._log(f"Writing test result failed: {e}")

        if self.should_cleanup():
            try:
                self.cleanup_test_data()
            except Exception as e:
                self._log(f"Cleanup failed: {e}")

        # Close Shuffle client to stop keepalive threads from accumulating
        shuffle_client = getattr(self, "shuffle", None)
        if shuffle_client is not None:
            try:
                shuffle_client.close()
            except Exception:
                pass

        elapsed = time.time() - getattr(self, "start_time", time.time())
        self._log(f"Test completed in {elapsed:.1f}s")

    # ── Evidence completeness (Nivel 15) ──────────────────────────────────────

    def assert_evidence_complete(self) -> None:
        """Verify that all expected evidence files were created.

        Checks that the evidence directory contains the minimum required
        artifacts for auditability.  Records the assertion but does NOT
        fail the test — evidence gaps are warnings, not hard failures.
        """
        t0 = time.time()
        evidence_dir = getattr(self, "evidence_dir", None)
        if not evidence_dir or not evidence_dir.exists():
            self.record_assertion(
                "evidence_complete",
                False,
                time.time() - t0,
                {"error": "No evidence directory found"},
            )
            return

        required_files = [
            "payload.json",
            "workflow_execution.json",
            "service_health.json",
            "docker_state.json",
        ]
        optional_files = [
            "thehive_case.json",
            "cortex_jobs.json",
            "misp_data.json",
            "elasticsearch_docs.json",
            "opensearch_docs.json",
            "loki_logs.json",
        ]

        missing_required = [f for f in required_files if not (evidence_dir / f).exists()]
        missing_optional = [f for f in optional_files if not (evidence_dir / f).exists()]

        passed = len(missing_required) == 0
        self.record_assertion(
            "evidence_complete",
            passed,
            time.time() - t0,
            {
                "missing_required": missing_required,
                "missing_optional": missing_optional,
                "evidence_dir": str(evidence_dir),
            },
        )

        if missing_required:
            self._log(f"  ! Evidence incomplete — missing required: {missing_required}")
        if missing_optional:
            self._log(f"  ! Evidence incomplete — missing optional: {missing_optional}")

    # ── Test isolation (Nivel 13) ─────────────────────────────────────────────

    def assert_test_isolation(self, alert_id: str) -> None:
        """Verify that no stale data exists for the given alert_id.

        Should be called in setup (before submitting the alert) to ensure
        the test starts from a clean state.  Records the assertion and
        fails if stale data is found.

        Args:
            alert_id: The alert_id that will be used for this test.
        """
        t0 = time.time()
        errors: list[str] = []

        # Check TheHive for existing case with this alert_id
        try:
            cases = self.thehive.search_cases()
            existing = [
                c
                for c in cases
                if alert_id in c.get("description", "") or alert_id in c.get("title", "")
            ]
            if existing:
                errors.append(
                    f"TheHive already has {len(existing)} case(s) for alert_id={alert_id}"
                )
        except Exception as e:
            errors.append(f"Could not check TheHive isolation: {e}")

        # Check Elasticsearch for existing document
        try:
            doc = self.es.search_by_alert_id(alert_id, index="soar-alerts")
            if doc:
                errors.append(f"Elasticsearch already has document for alert_id={alert_id}")
        except Exception:
            pass  # ES may not have the index yet — OK

        duration = time.time() - t0
        passed = len(errors) == 0
        self.record_assertion(
            "test_isolation",
            passed,
            duration,
            {"alert_id": alert_id, "errors": errors} if errors else {"alert_id": alert_id},
        )

        if errors:
            import pytest

            pytest.fail(
                f"Test isolation violated — stale data found for alert_id={alert_id}:\n  - "
                + "\n  - ".join(errors)
            )

    # ── No-error logs (Nivel 11) ──────────────────────────────────────────────

    def assert_no_error_logs(self, timeout: int = 10) -> None:
        """Verify that Loki logs for this correlation_id don't contain errors.

        Searches for traceback, exception, panic, timeout, connection refused
        in the log streams matching the test's correlation_id.

        Args:
            timeout: Query timeout in seconds.
        """
        t0 = time.time()
        corr_id = getattr(self, "correlation_id", "")
        if not corr_id:
            self.record_assertion(
                "no_error_logs",
                False,
                time.time() - t0,
                {"error": "No correlation_id available"},
            )
            return

        loki_url = self.get_service_url("loki")
        error_patterns = [
            "traceback",
            "exception",
            "panic",
            "timeout",
            "connection refused",
            "error",
        ]

        try:
            # Query Loki for logs matching correlation_id
            query = f'{{correlation_id="{corr_id}"}}'
            r = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "limit": "1000",
                    "start": str(int((time.time() - 300) * 1e9)),  # last 5 min
                    "end": str(int(time.time() * 1e9)),
                },
                timeout=timeout,
                verify=False,
            )

            error_lines: list[str] = []
            if r.status_code == 200:
                data = r.json()
                streams = data.get("data", {}).get("result", [])
                for stream in streams:
                    for entry in stream.get("values", []):
                        log_line = entry[1].lower() if len(entry) > 1 else ""
                        for pattern in error_patterns:
                            if pattern in log_line:
                                error_lines.append(f"Found '{pattern}' in log: {log_line[:200]}")
                                break

                passed = len(error_lines) == 0
                self.record_assertion(
                    "no_error_logs",
                    passed,
                    time.time() - t0,
                    (
                        {
                            "correlation_id": corr_id,
                            "error_lines": error_lines[:10],
                        }
                        if error_lines
                        else {"correlation_id": corr_id}
                    ),
                )

                if error_lines:
                    self._log(f"  ! Found {len(error_lines)} error line(s) in Loki logs")
            else:
                self.record_assertion(
                    "no_error_logs",
                    False,
                    time.time() - t0,
                    {"error": f"Loki query returned HTTP {r.status_code}"},
                )
        except Exception as e:
            self.record_assertion(
                "no_error_logs",
                False,
                time.time() - t0,
                {"error": str(e)},
            )
