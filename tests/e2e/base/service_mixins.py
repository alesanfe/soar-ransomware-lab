"""Service-specific mixins for E2E tests.

This module provides mixins for interacting with TheHive, Cortex, MISP,
Shuffle, and search backends (Elasticsearch, OpenSearch, Redis).
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import requests


class ShuffleMixin:
    """Mixin for Shuffle workflow operations."""

    env: dict[str, str]
    webhook_url: str
    workflow_id: str
    correlation_id: str
    trace_id: str

    def create_shuffle_client(self) -> None:
        """Create the Shuffle client."""
        from soar_lab.infrastructure.integrations.shuffle.client import ShuffleClient

        shuffle_url = self.get_service_url("shuffle")
        shuffle_api_key = self.env.get("SHUFFLE_DEFAULT_APIKEY") or self.env.get(
            "SHUFFLE_API_KEY", "placeholder"
        )
        self.shuffle = ShuffleClient(
            base_url=shuffle_url, api_key=shuffle_api_key, verify_ssl=False
        )

    def build_alert_payload(
        self,
        alert_id: str | None = None,
        alert_type: str = "ransomware",
        hostname: str = "WORKSTATION-001",
        src_ip: str = "172.31.54.117",
        hash_val: str = "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
        severity: int = 3,
        domain: str = "google.com",
        **extra: Any,
    ) -> dict[str, Any]:
        """Build a standard alert payload for the Shuffle webhook.

        The correlation_id and trace_id are automatically included in the
        payload.  If ``trace_id`` is supplied via ``**extra`` it is reused;
        otherwise a new UUID4-hex trace ID is generated and stored in
        ``self.trace_id``.
        """
        aid = alert_id or f"TC01-{self.correlation_id}-{int(time.time())}"
        # Generate or reuse trace_id for end-to-end correlation
        tid = extra.get("trace_id") or getattr(self, "trace_id", "") or uuid.uuid4().hex
        self.trace_id = tid
        payload: dict[str, Any] = {
            "alert_id": aid,
            "alert_type": alert_type,
            "hostname": hostname,
            "src_ip": src_ip,
            "hash": hash_val,
            "severity": severity,
            "domain": domain,
            "correlation_id": self.correlation_id,
            "trace_id": tid,
        }
        payload.update(extra)
        return payload

    def submit_alert(self, payload: dict[str, Any]) -> str | None:
        """Submit an alert to the Shuffle webhook and return the execution ID.

        Retries up to 5 times on failure (connection error or non-200
        response) with a 10-second backoff between attempts, matching
        the behaviour of the original TC-01 test.

        The ``X-Request-ID`` header is set from ``payload["trace_id"]`` (or
        ``self.trace_id``) so that the TraceIdMiddleware can propagate it
        end-to-end through the SOAR pipeline.
        """
        if not self.webhook_url:
            import pytest

            pytest.fail("No webhook URL configured — run make init-webhook first")

        # Record payload in evidence (only once, even if we retry)
        self.write_evidence("payload.json", payload)

        # Propagate trace_id via X-Request-ID header for end-to-end correlation
        tid = payload.get("trace_id") or getattr(self, "trace_id", "")
        headers = {"X-Request-ID": tid} if tid else {}

        # Use the Shuffle client's webhook session if available (it has the
        # correct SSL/timeout configuration), otherwise fall back to requests.
        session = getattr(self.shuffle, "_webhook_session", None) or requests

        for attempt in range(5):
            try:
                r = session.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=20,
                    verify=False,
                )
                if r.status_code == 200:
                    body = r.json() if r.content else {}
                    exec_id = body.get("execution_id") or body.get("id") or body.get("executionId")
                    self._log(f"Alert submitted: {payload.get('alert_id')} -> exec={exec_id}")
                    self.execution_id = exec_id
                    return exec_id
                self._log(f"  Attempt {attempt + 1}/5: HTTP {r.status_code}, retrying in 10s...")
            except Exception as e:
                self._log(f"  Attempt {attempt + 1}/5: {e}, retrying in 10s...")
            time.sleep(10)

        self._log(f"Webhook POST failed after 5 attempts: {payload.get('alert_id')}")
        return None

    def wait_for_workflow(
        self,
        execution_id: str | None = None,
        timeout: int = 600,
        poll_interval: int = 5,
    ) -> dict[str, Any]:
        """Wait for a Shuffle workflow execution to complete.

        Returns the execution dict. Raises TimeoutError or
        AssertionError.
        """
        exec_id = execution_id or getattr(self, "execution_id", None)
        if not exec_id:
            import pytest

            pytest.fail("No execution ID provided — alert submission failed")

        self._log(f"Waiting for workflow execution {exec_id} (timeout={timeout}s)")
        deadline = time.time() + timeout
        last_status = "UNKNOWN"

        while time.time() < deadline:
            try:
                execution = self._get_execution(exec_id)
                if execution:
                    last_status = execution.get("status", "UNKNOWN")
                    if last_status in ("FINISHED", "ABORTED", "FAILED"):
                        self._log(f"Workflow completed: status={last_status}")
                        self.execution = execution
                        return execution
            except Exception as e:
                self._log(f"  Poll error: {e}")
            time.sleep(poll_interval)

        raise TimeoutError(
            f"Workflow {exec_id} did not complete within {timeout}s (last status: {last_status})"
        )

    def _get_execution(self, execution_id: str) -> dict[str, Any] | None:
        """Get execution status from Shuffle client (preferred) or OpenSearch
        fallback."""
        # Try Shuffle client first (uses the same auth/session as the workflow)
        try:
            ex = self.shuffle.get_execution(self.workflow_id, execution_id, include_results=True)
            if ex and isinstance(ex, dict):
                return ex
        except Exception:
            pass

        # Fallback: direct Shuffle API call
        try:
            r = requests.get(
                f"{self.shuffle.base_url}/api/v1/executions/{execution_id}",
                timeout=30,
                verify=False,
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass

        # Fallback: query OpenSearch directly
        try:
            os_url = self.get_service_url("opensearch")
            r = requests.get(
                f"{os_url}/workflowexecution-000001/_doc/{execution_id}",
                timeout=30,
                verify=False,
            )
            if r.status_code == 200:
                return r.json().get("_source", {})
        except Exception:
            pass

        return None


class TheHiveMixin:
    """Mixin for TheHive operations."""

    env: dict[str, str]

    def create_thehive_client(self) -> None:
        """Create the TheHive client."""
        from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient

        thehive_url = self.get_service_url("thehive")
        self.thehive = TheHiveClient(
            base_url=thehive_url,
            api_key=self.env.get("THEHIVE_API_KEY", ""),
            verify_ssl=False,
        )

    def assert_thehive_case_created(
        self, alert_id: str, timeout: int = 120
    ) -> dict[str, Any] | None:
        """Assert that a TheHive case was created for the given alert_id.

        Records the assertion and returns the case if found.
        """
        t0 = time.time()
        deadline = time.time() + timeout
        case = None

        while time.time() < deadline:
            try:
                cases = self.thehive.search_cases()
                for c in cases:
                    title = c.get("title", "")
                    description = c.get("description", "")
                    if alert_id in title or alert_id in description:
                        case = c
                        break
                if case:
                    break
            except Exception as e:
                self._log(f"  + TheHive search error: {e}")
            time.sleep(5)

        duration = time.time() - t0
        if case:
            case_id = case.get("_id", case.get("id", "N/A"))
            self._log(f"  + TheHive case found: {case_id}")
            self.register_resource("thehive_cases", case_id)
            self.record_assertion(
                "thehive_case_created",
                True,
                duration,
                {"case_id": case_id},
            )
            return case
        else:
            self._log(f"  + TheHive case NOT found for alert_id={alert_id}")
            self.record_assertion(
                "thehive_case_created",
                False,
                duration,
                {"alert_id": alert_id},
            )
            return None


class CortexMixin:
    """Mixin for Cortex operations."""

    env: dict[str, str]

    def create_cortex_client(self) -> None:
        """Create the Cortex client with the cookie-jar fix applied."""
        from soar_lab.infrastructure.integrations.cortex.client import CortexClient

        cortex_url = self.get_service_url("cortex")
        self.cortex = CortexClient(
            base_url=cortex_url,
            api_key=self.env.get("CORTEX_API_KEY", ""),
            verify_ssl=False,
            admin_user=self.env.get("CORTEX_ADMIN_USER", "admin"),
            admin_password=self.env.get("CORTEX_ADMIN_PASSWORD", ""),
            timeout=60,
        )

    def assert_cortex_jobs_created(
        self, data_type: str, data: str, timeout: int = 60
    ) -> dict[str, Any] | None:
        """Assert that a Cortex analyzer job can be created for the given data.

        Records the assertion and returns the job if successful.
        """
        t0 = time.time()
        try:
            analyzers = self.cortex.list_analyzers_by_type(data_type)
            if not analyzers:
                self.record_assertion(
                    "cortex_jobs_created",
                    False,
                    time.time() - t0,
                    {"error": f"No analyzers for type={data_type}"},
                )
                return None

            analyzer_id = analyzers[0]["_id"]
            job = self.cortex.run_analyzer(analyzer_id, data_type, data)
            job_id = job.get("id", "N/A")
            self._log(f"  + Cortex job created: {job_id}")
            self.register_resource("cortex_jobs", job_id)
            self.record_assertion(
                "cortex_jobs_created",
                True,
                time.time() - t0,
                {"job_id": job_id, "analyzer": analyzer_id},
            )
            return job
        except Exception as e:
            self._log(f"  + Cortex analyzer failed: {e}")
            self.record_assertion(
                "cortex_jobs_created",
                False,
                time.time() - t0,
                {"error": str(e)},
            )
            return None


class MispMixin:
    """Mixin for MISP operations."""

    env: dict[str, str]

    def create_misp_client(self) -> None:
        """Create the MISP client."""
        from soar_lab.infrastructure.integrations.misp.client import MISPClient

        misp_url = self.get_service_url("misp")
        self.misp = MISPClient(
            base_url=misp_url,
            api_key=self.env.get("MISP_API_KEY", ""),
            verify_ssl=False,
        )

    def assert_misp_lookup_done(
        self, ioc_value: str, expected_hit: bool | None = None
    ) -> list[dict[str, Any]]:
        """Assert that MISP lookup was performed and optionally check hit/no-
        hit.

        Records the assertion and returns matching events.
        """
        t0 = time.time()
        try:
            events = self.misp.search_events(ioc_value)
            self._log(f"  + MISP search for {ioc_value}: {len(events)} event(s)")

            if expected_hit is not None:
                passed = (len(events) > 0) == expected_hit
                self.record_assertion(
                    "misp_lookup_done",
                    passed,
                    time.time() - t0,
                    {
                        "ioc_value": ioc_value,
                        "events_found": len(events),
                        "expected_hit": expected_hit,
                    },
                )
            else:
                self.record_assertion(
                    "misp_lookup_done",
                    True,
                    time.time() - t0,
                    {"ioc_value": ioc_value, "events_found": len(events)},
                )

            return events
        except Exception as e:
            self._log(f"  + MISP search failed: {e}")
            self.record_assertion(
                "misp_lookup_done",
                False,
                time.time() - t0,
                {"error": str(e)},
            )
            return []

    def seed_misp_indicator(
        self,
        value: str,
        type_: str = "ip-src",
        category: str = "Network activity",
    ) -> dict[str, Any] | None:
        """Seed a MISP event with an indicator for positive-hit scenarios.

        Registers the event for cleanup tracking.
        """
        try:
            event = self.misp.create_event(
                info=f"E2E fixture {self.correlation_id}",
                tags=["e2e", self.correlation_id],
                attributes=[
                    {
                        "type": type_,
                        "category": category,
                        "value": value,
                        "comment": f"E2E fixture {self.correlation_id}",
                    }
                ],
            )
            event_id = event.get("Event", {}).get("id", "")
            if event_id:
                self.register_resource("misp_events", event_id)
            self._log(f"  + MISP event seeded: {event_id}")
            return event
        except Exception as e:
            self._log(f"  + MISP seed failed: {e}")
            return None


class SearchMixin:
    """Mixin for Elasticsearch, OpenSearch, and Redis operations."""

    env: dict[str, str]

    def create_search_clients(self) -> None:
        """Create Elasticsearch and Redis clients."""
        from soar_lab.infrastructure.integrations.elasticsearch.client import (
            ElasticsearchClient,
        )

        es_url = self.get_service_url("es")
        self.es = ElasticsearchClient(
            base_url=es_url,
            username=self.env.get("ELASTIC_USERNAME", "elastic"),
            password=self.env.get("ELASTIC_PASSWORD", ""),
        )

    def assert_elasticsearch_document_indexed(
        self, alert_id: str, index: str = "soar-alerts", timeout: int = 60
    ) -> dict[str, Any] | None:
        """Assert that an alert was indexed in Elasticsearch.

        Forces refresh and polls until found or timeout.
        """
        t0 = time.time()
        es_url = self.get_service_url("es")
        es_auth = (
            self.env.get("ELASTIC_USERNAME", "elastic"),
            self.env.get("ELASTIC_PASSWORD", ""),
        )

        # Force refresh
        try:
            requests.post(f"{es_url}/{index}/_refresh", auth=es_auth, timeout=10, verify=False)
        except Exception:
            pass

        deadline = time.time() + timeout
        doc = None
        while time.time() < deadline:
            try:
                doc = self.es.search_by_alert_id(alert_id, index=index)
                if doc:
                    break
            except Exception as e:
                self._log(f"  + ES search error: {e}")
            time.sleep(5)
            try:
                requests.post(f"{es_url}/{index}/_refresh", auth=es_auth, timeout=10, verify=False)
            except Exception:
                pass

        duration = time.time() - t0
        if doc:
            doc_id = doc.get("_id", "N/A")
            self._log(f"  + ES document found: id={doc_id}")
            self.register_resource("elasticsearch_documents", f"{index}/_doc/{doc_id}")
            self.record_assertion(
                "elasticsearch_document_indexed",
                True,
                duration,
                {"document_id": doc_id, "index": index},
            )
            return doc
        else:
            self._log(f"  + ES document NOT found for alert_id={alert_id}")
            self.record_assertion(
                "elasticsearch_document_indexed",
                False,
                duration,
                {"alert_id": alert_id, "index": index},
            )
            return None

    def assert_opensearch_execution_registered(
        self, execution_id: str, timeout: int = 30
    ) -> dict[str, Any] | None:
        """Assert that a workflow execution was registered in OpenSearch."""
        t0 = time.time()
        os_url = self.get_service_url("opensearch")

        try:
            r = requests.get(
                f"{os_url}/workflowexecution-000001/_doc/{execution_id}",
                timeout=timeout,
                verify=False,
            )
            duration = time.time() - t0
            if r.status_code == 200:
                source = r.json().get("_source", {})
                self._log(f"  + OpenSearch execution found: {execution_id}")
                self.register_resource(
                    "opensearch_documents",
                    f"workflowexecution-000001/_doc/{execution_id}",
                )
                self.record_assertion(
                    "opensearch_execution_registered",
                    True,
                    duration,
                    {"execution_id": execution_id},
                )
                return source
            else:
                self._log(f"  + OpenSearch execution NOT found: HTTP {r.status_code}")
                self.record_assertion(
                    "opensearch_execution_registered",
                    False,
                    duration,
                    {"execution_id": execution_id, "http_status": r.status_code},
                )
                return None
        except Exception as e:
            self._log(f"  + OpenSearch check failed: {e}")
            self.record_assertion(
                "opensearch_execution_registered",
                False,
                time.time() - t0,
                {"error": str(e)},
            )
            return None

    def assert_metrics_created(
        self, alert_id: str, index: str = "soar-metrics", timeout: int = 30
    ) -> dict[str, Any] | None:
        """Assert that metrics were created in the soar-metrics index."""
        t0 = time.time()
        es_url = self.get_service_url("es")
        es_auth = (
            self.env.get("ELASTIC_USERNAME", "elastic"),
            self.env.get("ELASTIC_PASSWORD", ""),
        )

        # Force refresh
        try:
            requests.post(f"{es_url}/{index}/_refresh", auth=es_auth, timeout=10, verify=False)
        except Exception:
            pass

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                r = requests.post(
                    f"{es_url}/{index}/_search",
                    json={"query": {"match": {"alert_id": alert_id}}},
                    auth=es_auth,
                    timeout=10,
                    verify=False,
                )
                if r.status_code == 200:
                    hits = r.json().get("hits", {}).get("hits", [])
                    if hits:
                        doc_id = hits[0].get("_id", "N/A")
                        self._log(f"  + Metrics found: id={doc_id}")
                        self.register_resource("elasticsearch_documents", f"{index}/_doc/{doc_id}")
                        self.record_assertion(
                            "metrics_created",
                            True,
                            time.time() - t0,
                            {"document_id": doc_id, "index": index},
                        )
                        return hits[0]
            except Exception as e:
                self._log(f"  + Metrics search error: {e}")
            time.sleep(5)

        self._log(f"  + Metrics NOT found for alert_id={alert_id}")
        self.record_assertion(
            "metrics_created",
            False,
            time.time() - t0,
            {"alert_id": alert_id, "index": index},
        )
        return None

    def verify_redis_cache(self, key_fragment: str) -> bool:
        """Check if a key exists in Redis cache."""
        import redis as _redis

        try:
            r = _redis.Redis(
                host=self.get_redis_host(),
                port=self.get_redis_port(),
                password=self.get_redis_password(),
                decode_responses=True,
            )
            for key in r.scan_iter(f"*{key_fragment}*"):
                self._log(f"  + Redis key found: {key}")
                self.register_resource("redis_keys", key)
                return True
            self._log(f"  + Redis key NOT found for fragment={key_fragment}")
            return False
        except Exception as e:
            self._log(f"  + Redis check failed: {e}")
            return False
