"""Run context mixin for E2E tests.

Manages the correlation_id, test results directory, manifest.json,
result.json, and assertions.json for each test execution.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class RunContextMixin:
    """Mixin for managing test run context, correlation IDs, and result
    files."""

    # These attributes are expected to be set by other mixins
    e2e_results_dir: Path
    test_name: str
    workflow_name: str
    correlation_id: str
    trace_id: str

    def create_run_context(self) -> None:
        """Create a unique correlation_id and trace_id for this test run.

        Generates:
        - self.correlation_id: Unique ID for this test run (domain-level)
        - self.trace_id: UUID4-hex trace ID for HTTP/log correlation
        - self.test_results_dir: Directory for this test's artifacts
        - self.evidence_dir: Directory for evidence files
        - self.manifest: Manifest dict (written to manifest.json)
        """
        self.correlation_id = f"e2e-{self.test_name}-{uuid.uuid4().hex[:12]}"
        self.trace_id = uuid.uuid4().hex
        self.started_at = _now_iso()
        self.start_time = time.time()

        self.test_results_dir = self.e2e_results_dir / self.correlation_id
        self.evidence_dir = self.test_results_dir / "evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

        self.manifest: dict[str, Any] = {
            "schema_version": "1.0",
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "test_name": self.test_name,
            "started_at": self.started_at,
            "workflow_name": self.workflow_name,
            "resources": {
                "misp_events": [],
                "thehive_cases": [],
                "cortex_jobs": [],
                "elasticsearch_documents": [],
                "opensearch_documents": [],
                "redis_keys": [],
                "files": [],
            },
            "artifacts": {},
        }

        self.write_json("manifest.json", self.manifest)

        # Track assertions for assertions.json
        self._assertions: list[dict[str, Any]] = []
        # Track evidence files
        self._evidence_files: list[str] = []

    def now_iso(self) -> str:
        """Return current UTC time in ISO format."""
        return _now_iso()

    def write_json(self, filename: str, data: Any) -> Path:
        """Write JSON data to a file in the test results directory.

        Args:
            filename: Filename (relative to test_results_dir).
            data: Data to serialize as JSON.

        Returns:
            Path to the written file.
        """
        path = self.test_results_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return path

    def write_evidence(self, filename: str, data: Any) -> Path:
        """Write evidence JSON to the evidence directory.

        Args:
            filename: Evidence filename (e.g. "loki_logs.json").
            data: Data to serialize as JSON.

        Returns:
            Path to the written file.
        """
        path = self.evidence_dir / filename
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        rel = f"evidence/{filename}"
        if rel not in self._evidence_files:
            self._evidence_files.append(rel)
        # Update manifest artifacts
        self.manifest["artifacts"][filename] = str(path)
        self.write_json("manifest.json", self.manifest)
        return path

    def register_resource(self, category: str, resource_id: str) -> None:
        """Register a resource created by this test for tracking/cleanup.

        Args:
            category: Resource category (e.g. "misp_events", "thehive_cases").
            resource_id: Resource identifier (e.g. event ID, case ID).
        """
        if category in self.manifest["resources"]:
            if resource_id not in self.manifest["resources"][category]:
                self.manifest["resources"][category].append(resource_id)
                self.write_json("manifest.json", self.manifest)

    def record_assertion(
        self,
        name: str,
        passed: bool,
        duration_s: float = 0.0,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record an assertion result for assertions.json.

        Args:
            name: Assertion name (e.g. "thehive_case_created").
            passed: Whether the assertion passed.
            duration_s: Duration in seconds.
            details: Optional details dict.
        """
        entry: dict[str, Any] = {
            "name": name,
            "passed": passed,
            "duration_s": round(duration_s, 3),
        }
        if details:
            entry["details"] = details
        self._assertions.append(entry)

    def write_test_result(self) -> None:
        """Write result.json with test outcome summary."""
        finished_at = _now_iso()
        duration_s = time.time() - self.start_time

        passed = sum(1 for a in self._assertions if a["passed"])
        failed = sum(1 for a in self._assertions if not a["passed"])
        total = len(self._assertions)

        # Get workflow info if available
        workflow_info: dict[str, Any] = {}
        if hasattr(self, "execution") and self.execution:
            workflow_info = {
                "name": self.workflow_name,
                "workflow_id": getattr(self, "workflow_id", ""),
                "execution_id": getattr(self, "execution_id", ""),
                "status": self.execution.get("status", ""),
            }
            if self.start_time:
                workflow_info["duration_s"] = round(duration_s, 1)

        result = {
            "schema_version": "1.0",
            "name": self.test_name,
            "correlation_id": self.correlation_id,
            "started_at": self.started_at,
            "finished_at": finished_at,
            "duration_s": round(duration_s, 1),
            "all_passed": failed == 0,
            "passed": passed,
            "failed": failed,
            "total": total,
            "workflow": workflow_info,
            "evidence_files": self._evidence_files,
            "cleanup": getattr(self, "_cleanup_result", None),
        }

        self.write_json("result.json", result)

        # Also write a TC-compatible summary file for generate_e2e_report.py
        # The report script looks for TC-*_*.json files in reports/validation/results/
        # (the parent of e2e/), so we write there for backward compatibility.
        tc_id = getattr(self, "tc_id", "")
        if tc_id:
            # Write in the parent results dir so generate_e2e_report.py finds it
            tc_file = self.validation_results_dir / f"{tc_id}_{self.correlation_id}.json"
            tc_file.write_text(
                json.dumps(
                    {
                        "tc_id": tc_id,
                        "test_name": self.test_name,
                        "correlation_id": self.correlation_id,
                        "status": "PASSED" if failed == 0 else "FAILED",
                        "elapsed_s": round(duration_s, 1),
                        "passed": passed,
                        "failed": failed,
                        "total": total,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

    def write_assertions(self) -> None:
        """Write assertions.json with all recorded assertions."""
        self.write_json("assertions.json", self._assertions)

    def write_cleanup_result(self, cleanup_result: dict[str, Any]) -> None:
        """Write cleanup.json with cleanup execution results.

        Args:
            cleanup_result: Cleanup result dict.
        """
        self._cleanup_result = cleanup_result
        self.write_json("cleanup.json", cleanup_result)
