"""Cleanup mixin for E2E tests.

Handles controlled cleanup of test data, with conservative policies that
preserve data needed for reporting.
"""

from __future__ import annotations

from typing import Any


class CleanupMixin:
    """Mixin for controlled cleanup of test-generated data."""

    env: dict[str, str]
    manifest: dict[str, Any]
    correlation_id: str

    def should_cleanup(self) -> bool:
        """Determine if cleanup should run based on test result and config."""
        # Check if test passed or failed
        failed = sum(1 for a in self._assertions if not a["passed"])

        if failed > 0:
            # Don't cleanup on failure unless explicitly configured
            return self.env.get("E2E_CLEANUP_ON_FAILURE", "false").lower() == "true"

        # Cleanup on success if enabled
        return self.env.get("E2E_CLEANUP_ON_SUCCESS", "true").lower() == "true"

    def preserve_report_data(self) -> bool:
        """Check if report data should be preserved."""
        return self.env.get("E2E_PRESERVE_REPORT_DATA", "true").lower() == "true"

    def cleanup_test_data(self) -> None:
        """Execute cleanup steps for test-generated data.

        Conservative policy:
        - Always preserve evidence files (manifest, result, assertions, evidence/*)
        - Always preserve Loki logs (historical evidence)
        - Preserve ES/OpenSearch data if needed for reporting
        - Only clean Redis keys with e2e: prefix
        - Clean MISP fixtures if not needed for reporting
        """
        errors: list[dict[str, str]] = []

        cleanup_steps = [
            self.cleanup_redis,
        ]

        if not self.preserve_report_data():
            cleanup_steps.extend(
                [
                    self.cleanup_misp,
                    self.cleanup_thehive,
                    self.cleanup_elasticsearch,
                    self.cleanup_opensearch,
                ]
            )

        for step in cleanup_steps:
            try:
                step()
            except Exception as exc:
                errors.append({"step": step.__name__, "error": str(exc)})

        cleanup_result = {
            "correlation_id": self.correlation_id,
            "preserve_report_data": self.preserve_report_data(),
            "errors": errors,
            "status": "success" if not errors else "partial_failure",
        }

        self.write_cleanup_result(cleanup_result)

        fail_on_error = self.env.get("E2E_FAIL_ON_CLEANUP_ERROR", "false").lower() == "true"
        if errors and fail_on_error:
            import pytest

            pytest.fail(f"Cleanup errors: {errors}")

    def cleanup_redis(self) -> None:
        """Clean Redis keys with e2e: prefix only.

        Never FLUSHALL.
        """
        import redis as _redis

        try:
            r = _redis.Redis(
                host=self.get_redis_host(),
                port=self.get_redis_port(),
                password=self.get_redis_password(),
                decode_responses=True,
            )
            pattern = f"e2e:{self.correlation_id}:*"
            deleted = 0
            for key in r.scan_iter(pattern):
                r.delete(key)
                deleted += 1
            self._log(f"  + Redis cleanup: deleted {deleted} key(s)")
        except Exception as e:
            self._log(f"  + Redis cleanup failed: {e}")
            raise

    def cleanup_misp(self) -> None:
        """Clean MISP events created as fixtures by this test."""
        mode = self.env.get("E2E_MISP_CLEANUP_MODE", "delete_after_report")
        if mode == "keep":
            self._log("  + MISP cleanup: skipped (mode=keep)")
            return

        misp_events = self.manifest.get("resources", {}).get("misp_events", [])
        if not misp_events:
            self._log("  + MISP cleanup: no events to clean")
            return

        deleted = 0
        for event_id in misp_events:
            try:
                # MISP delete event
                self.misp.delete_event(event_id)
                deleted += 1
            except Exception as e:
                self._log(f"  + MISP cleanup: failed to delete event {event_id}: {e}")

        self._log(f"  + MISP cleanup: deleted {deleted}/{len(misp_events)} event(s)")

    def cleanup_thehive(self) -> None:
        """Clean or close TheHive cases created by this test."""
        mode = self.env.get("E2E_THEHIVE_CLEANUP_MODE", "close")
        if mode == "keep":
            self._log("  + TheHive cleanup: skipped (mode=keep)")
            return

        thehive_cases = self.manifest.get("resources", {}).get("thehive_cases", [])
        if not thehive_cases:
            self._log("  + TheHive cleanup: no cases to clean")
            return

        cleaned = 0
        for case_id in thehive_cases:
            try:
                if mode == "delete":
                    self.thehive.delete_case(case_id)
                else:  # close
                    self.thehive.update_case(case_id, {"status": "Closed"})
                cleaned += 1
            except Exception as e:
                self._log(f"  + TheHive cleanup: failed for case {case_id}: {e}")

        self._log(f"  + TheHive cleanup: {cleaned}/{len(thehive_cases)} case(s) ({mode})")

    def cleanup_elasticsearch(self) -> None:
        """Clean Elasticsearch documents created by this test."""
        import requests as _req

        es_url = self.get_service_url("es")
        es_auth = (
            self.env.get("ELASTIC_USERNAME", "elastic"),
            self.env.get("ELASTIC_PASSWORD", ""),
        )

        es_docs = self.manifest.get("resources", {}).get("elasticsearch_documents", [])
        if not es_docs:
            self._log("  + ES cleanup: no documents to clean")
            return

        deleted = 0
        for doc_ref in es_docs:
            # doc_ref format: "index/_doc/id"
            try:
                parts = doc_ref.split("/")
                if len(parts) >= 3:
                    index = parts[0]
                    doc_id = parts[2]
                    r = _req.delete(
                        f"{es_url}/{index}/_doc/{doc_id}",
                        auth=es_auth,
                        timeout=10,
                        verify=False,
                    )
                    if r.status_code in (200, 204):
                        deleted += 1
            except Exception as e:
                self._log(f"  + ES cleanup: failed for {doc_ref}: {e}")

        self._log(f"  + ES cleanup: deleted {deleted}/{len(es_docs)} document(s)")

    def cleanup_opensearch(self) -> None:
        """Clean OpenSearch documents created by this test.

        Conservative: does not delete workflow executions by default
        as they may be needed for reporting statistics.
        """
        self._log("  + OpenSearch cleanup: skipped (preserve workflow executions)")
