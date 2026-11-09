"""Run context mixin for E2E tests.

Manages the correlation_id, test results directory, manifest.json,
result.json, and assertions.json for each test execution.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from soar_lab.common.ids import uuid7_hex


def _now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    """SHA-256 hex digest of a file's bytes (EVID-001 integrity)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Env keys whose VALUES must never appear verbatim in exported evidence.
_SECRET_ENV_PATTERN = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASS|CREDENTIAL)", re.IGNORECASE)

# EVID-002: session-level pytest facts (randomly seed, xdist workers)
# recorded once by conftest.pytest_configure so every environment.json
# carries the reproduction parameters of its session.
_SESSION_INFO: dict[str, Any] = {}


def record_session_info(config: Any) -> None:
    """Capture pytest session parameters for environment.json (EVID-002).

    Called once from ``pytest_configure``; the mixin reads ``_SESSION_INFO``
    when writing each test's environment record.
    """
    opt = getattr(config, "option", None)
    if opt is None:
        return
    seed = getattr(opt, "randomly_seed", None)
    workers = getattr(opt, "numprocesses", None)
    if seed is not None:
        _SESSION_INFO["randomly_seed"] = seed
    if workers:
        _SESSION_INFO["xdist_workers"] = workers


def _collect_secret_values(env: dict[str, str]) -> list[str]:
    """Collect env values that look like credentials (for redaction)."""
    secrets = []
    for key, value in env.items():
        if _SECRET_ENV_PATTERN.search(key) and isinstance(value, str) and len(value) >= 6:
            secrets.append(value)
    return secrets


def _redact_obj(obj: Any, secrets: list[str]) -> Any:
    """Recursively replace secret values with ``[REDACTED]``."""
    if isinstance(obj, str):
        for s in secrets:
            obj = obj.replace(s, "[REDACTED]")
        return obj
    if isinstance(obj, dict):
        return {k: _redact_obj(v, secrets) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_redact_obj(v, secrets) for v in obj]
    return obj


class RunContextMixin:
    """Mixin for managing test run context, correlation IDs, and result files."""

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
        self.correlation_id = f"e2e-{self.test_name}-{uuid7_hex()[:12]}"
        self.trace_id = uuid7_hex()
        self.started_at = _now_iso()
        self.start_time = time.time()
        # Per-run namespace (E2E-ISO-001): short uuid so two parallel runs
        # of the same test cannot collide on timestamped alert_ids.
        # init_run_namespace lives in IsolationMixin; fall back to a local
        # namespace when this mixin is used standalone (unit tests).
        if hasattr(self, "init_run_namespace"):
            self.init_run_namespace()
        else:
            self.run_id = getattr(self, "run_id", None) or uuid.uuid4().hex[:8]
            self._uid_counter = getattr(self, "_uid_counter", 0)

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
        # Secret values captured once per run — evidence redaction (EVID-001)
        self._secret_values = _collect_secret_values(getattr(self, "env", {}) or {})

        # EVID-002: environment capture — reproducibility needs commit,
        # runtime and plugin versions recorded before the test runs.
        self._write_environment()

    def now_iso(self) -> str:
        """Return current UTC time in ISO format."""
        return _now_iso()

    def _git_probe(self) -> dict[str, Any]:
        """Best-effort git metadata for environment.json (EVID-002).

        The test container runs from /app where .git is not mounted, so
        all fields degrade gracefully to None rather than failing setup.
        """

        def _git(*args: str) -> str | None:
            try:
                r = subprocess.run(
                    ["git", *args],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return r.stdout.strip() if r.returncode == 0 else None
            except Exception:
                return None

        return {
            "commit": _git("rev-parse", "HEAD"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": _git("status", "--porcelain") is not None
            and bool(_git("status", "--porcelain")),
        }

    def _write_environment(self) -> None:
        """Write environment.json — the reproducibility context (EVID-002).

        Records runtime, plugins, host, git state and the effective
        (non-secret) environment so a run can be reproduced or audited.
        """
        import sys

        import pytest

        env_public = {
            k: v
            for k, v in (getattr(self, "env", {}) or {}).items()
            if not _SECRET_ENV_PATTERN.search(k)
        }
        plugins = sorted(
            {
                name.split(".")[0]
                for name in sys.modules
                if name.startswith(("pytest_", "xdist", "pluggy"))
            }
        )
        environment = {
            "captured_at": _now_iso(),
            "correlation_id": self.correlation_id,
            "run_id": getattr(self, "run_id", None),
            "python": platform.python_version(),
            "pytest": pytest.__version__,
            "plugins": plugins,
            "platform": platform.platform(),
            "host": platform.node(),
            "cpu_count": os.cpu_count(),
            "ram_mb": self._ram_mb(),
            "timezone": "UTC",
            "git": self._git_probe(),
            "docker_server": self._docker_server_version(),
            "docker_images": self._docker_image_probe(),
            "session": dict(_SESSION_INFO),
            "env_public": env_public,
        }
        self.write_json("environment.json", environment)

    @staticmethod
    def _ram_mb() -> int | None:
        """Total RAM in MiB, or None when psutil is unavailable (EVID-002)."""
        try:
            import psutil

            return int(psutil.virtual_memory().total // (1024 * 1024))
        except Exception:
            return None

    @staticmethod
    def _docker_server_version() -> str | None:
        """Docker daemon version (not the client) — pins the runtime (EVID-002)."""
        try:
            import docker

            return docker.from_env().version().get("Version")
        except Exception:
            return None

    def _docker_image_probe(self) -> dict[str, str]:
        """Best-effort image tags/digests of running lab containers.

        Queries the Docker socket when mounted; returns service->image
        mapping including RepoDigests so results are pinned to exact
        image builds (EVID-003).
        """
        try:
            import docker

            client = docker.from_env()
            out: dict[str, str] = {}
            for c in client.containers.list(all=False):
                try:
                    # Read image refs from the container record itself: the
                    # docker-socket-proxy allows /containers/json but 403s
                    # /images/{id}/json (c.image triggers that call).
                    attrs = getattr(c, "attrs", {}) or {}
                    cfg = attrs.get("Config") or {}
                    tag = cfg.get("Image") or ""
                    image_id = attrs.get("Image", "")
                    if tag and image_id:
                        out[c.name] = f"{tag}@{image_id[:19]}"
                    elif tag or image_id:
                        out[c.name] = tag or image_id[:19]
                except Exception:
                    continue
            return out
        except Exception:
            return {}

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

        Secrets present in the run environment are redacted before
        serialization (EVID-001: "los secretos están redactados"), and the
        file's SHA-256 is recorded in the manifest for integrity.
        """
        secrets = getattr(self, "_secret_values", None)
        if secrets is None:
            secrets = _collect_secret_values(getattr(self, "env", {}) or {})
        redacted = _redact_obj(data, secrets)
        path = self.evidence_dir / filename
        path.write_text(json.dumps(redacted, indent=2, default=str), encoding="utf-8")
        rel = f"evidence/{filename}"
        if rel not in self._evidence_files:
            self._evidence_files.append(rel)
        # Update manifest artifacts with integrity digest
        self.manifest["artifacts"][filename] = {
            "path": str(path),
            "sha256": _sha256_file(path),
        }
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

    # EVID-001: formal outcome discriminator for artifacts. Every recorded
    # assertion and the run as a whole carries one of these values so
    # report consumers can distinguish "not run / does not apply" from a
    # real pass — a check that never ran must never count as passed.
    OUTCOMES = ("passed", "failed", "warning", "skipped", "not_applicable")

    def record_assertion(
        self,
        name: str,
        passed: bool,
        duration_s: float = 0.0,
        details: dict[str, Any] | None = None,
        outcome: str | None = None,
    ) -> None:
        """Record an assertion result for assertions.json.

        Args:
            name: Assertion name (e.g. "thehive_case_created").
            passed: Whether the assertion passed.
            duration_s: Duration in seconds.
            details: Optional details dict.
            outcome: Formal discriminator — one of ``self.OUTCOMES``.
                Defaults to ``"passed"``/``"failed"`` from *passed*. Use
                ``"warning"`` for advisory checks that found anomalies but
                do not fail the test, ``"skipped"`` when the check did not
                run, and ``"not_applicable"`` when it does not apply to
                this environment. Non-pass/fail outcomes keep
                ``passed=True`` semantics for counting (they are not
                failures) but remain visible to report consumers.
        """
        if outcome is None:
            outcome = "passed" if passed else "failed"
        if outcome not in self.OUTCOMES:
            raise ValueError(f"Invalid assertion outcome {outcome!r}; expected {self.OUTCOMES}")
        entry: dict[str, Any] = {
            "name": name,
            "passed": passed,
            "outcome": outcome,
            "duration_s": round(duration_s, 3),
        }
        if details:
            entry["details"] = details
        self._assertions.append(entry)

    def record_check(
        self,
        name: str,
        outcome: str,
        duration_s: float = 0.0,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record a non-binary check (warning/skipped/not_applicable).

        Convenience wrapper over ``record_assertion`` for checks whose
        result is not a pass/fail verdict.
        """
        if outcome in ("passed", "failed"):
            raise ValueError("Use record_assertion for binary pass/fail checks")
        self.record_assertion(
            name, passed=True, duration_s=duration_s, details=details, outcome=outcome
        )

    def mark_not_applicable(self, reason: str) -> None:
        """Mark the whole test as not applicable to this environment (EVID-001)."""
        self._not_applicable = reason

    def _overall_outcome(self, failed: int) -> str:
        """Formal run outcome — precedence: skipped > failed > n/a > warning > passed."""
        if getattr(self, "_pytest_outcome", None) == "skipped":
            return "skipped"
        if getattr(self, "_pytest_failed", False) or failed:
            return "failed"
        outcomes = [a.get("outcome") for a in self._assertions]
        if getattr(self, "_not_applicable", False) or (
            outcomes and all(o == "not_applicable" for o in outcomes)
        ):
            return "not_applicable"
        if "warning" in outcomes:
            return "warning"
        return "passed"

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
            # _pytest_failed is set by the e2e conftest makereport hook when
            # pytest reports a failure the recorded-assertion count cannot
            # see (bare assert, exception).  Never claim PASSED in that case
            # (BUG-065).
            "pytest_failed": getattr(self, "_pytest_failed", False),
            "all_passed": failed == 0 and not getattr(self, "_pytest_failed", False),
            # EVID-001: formal outcome discriminator (OUTCOMES).
            "outcome": self._overall_outcome(failed),
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
                        "status": (
                            "PASSED"
                            if failed == 0 and not getattr(self, "_pytest_failed", False)
                            else "FAILED"
                        ),
                        # EVID-001: full discriminator alongside the
                        # PASSED/FAILED status the report consumes.
                        "outcome": self._overall_outcome(failed),
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
