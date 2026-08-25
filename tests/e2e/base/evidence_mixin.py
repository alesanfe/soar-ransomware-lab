"""Evidence mixin for E2E tests.

Handles export of evidence files to reports/validation/results/e2e/<correlation_id>/evidence/.
"""

from __future__ import annotations

from typing import Any

import requests


class EvidenceMixin:
    """Mixin for exporting evidence artifacts."""

    env: dict[str, str]
    correlation_id: str
    execution: dict[str, Any] | None
    execution_id: str | None

    def collect_evidence(self) -> None:
        """Collect all evidence artifacts after test execution.

        Exports:
        - service_health.json
        - docker_state.json
        - payload.json (if not already written)
        - workflow_execution.json
        - thehive_case.json
        - cortex_jobs.json
        - misp_data.json
        - elasticsearch_docs.json
        - opensearch_docs.json
        - loki_logs.json
        """
        self.export_service_health()
        self.export_docker_state()
        self.export_shuffle_execution()
        self.export_thehive_case()
        self.export_cortex_jobs()
        self.export_misp_data()
        self.export_search_documents()
        self.export_loki_logs()

    def export_service_health(self) -> None:
        """Export service health status as evidence."""
        health: dict[str, Any] = {}
        services = [
            ("elasticsearch", self.verify_elasticsearch),
            ("opensearch", self.verify_opensearch),
            ("redis", self.verify_redis),
            ("thehive", self.verify_thehive),
            ("cortex", self.verify_cortex),
            ("misp", self.verify_misp),
            ("shuffle", self.verify_shuffle_backend),
            ("network_watcher", self.verify_network_watcher),
            ("tenzir", self.verify_tenzir),
            ("api", self.verify_soar_api),
            ("loki", self.verify_loki),
            ("promtail", self.verify_promtail),
            ("grafana", self.verify_grafana),
        ]
        for name, check_fn in services:
            try:
                ok, msg = check_fn()
                health[name] = {"healthy": ok, "message": msg}
            except Exception as e:
                health[name] = {"healthy": False, "message": str(e)[:100]}

        self.write_evidence("service_health.json", health)

    def export_docker_state(self) -> None:
        """Export Docker container state as evidence."""
        state = self.get_docker_state()
        self.write_evidence("docker_state.json", state)

    def export_shuffle_execution(self) -> None:
        """Export Shuffle workflow execution details as evidence."""
        exec_id = getattr(self, "execution_id", None)
        if not exec_id:
            self.write_evidence("workflow_execution.json", {"error": "No execution_id"})
            return
        execution = self._get_execution(exec_id)
        self.write_evidence("workflow_execution.json", execution or {})

    def export_thehive_case(self) -> None:
        """Export TheHive case data as evidence."""
        try:
            cases = self.thehive.search_cases()
            # Filter to cases related to this correlation_id
            relevant = [
                c
                for c in cases
                if self.correlation_id in c.get("title", "")
                or self.correlation_id in c.get("description", "")
            ]
            # If no correlation_id match, export all recent cases
            if not relevant:
                relevant = cases[:10]  # Last 10 cases
            self.write_evidence("thehive_case.json", {"cases": relevant, "total": len(cases)})
        except Exception as e:
            self.write_evidence("thehive_case.json", {"error": str(e)})

    def export_cortex_jobs(self) -> None:
        """Export Cortex job data as evidence."""
        try:
            jobs = self.cortex.list_jobs(start=0, count=20)
            self.write_evidence("cortex_jobs.json", {"jobs": jobs, "count": len(jobs)})
        except Exception as e:
            self.write_evidence("cortex_jobs.json", {"error": str(e)})

    def export_misp_data(self) -> None:
        """Export MISP data as evidence."""
        try:
            # Get recent events
            events = self.misp.search_events(self.correlation_id)
            self.write_evidence("misp_data.json", {"events": events, "count": len(events)})
        except Exception as e:
            self.write_evidence("misp_data.json", {"error": str(e)})

    def export_search_documents(self) -> None:
        """Export Elasticsearch and OpenSearch documents as evidence."""
        es_url = self.get_service_url("es")
        es_auth = (
            self.env.get("ELASTIC_USERNAME", "elastic"),
            self.env.get("ELASTIC_PASSWORD", ""),
        )

        # Elasticsearch documents — search by correlation_id (the field that
        # build_alert_payload injects into every payload) rather than alert_id,
        # since alert_id is derived from correlation_id + timestamp and won't
        # match a plain correlation_id query.
        es_docs: dict[str, Any] = {}
        for index in ["soar-alerts", "soar-metrics"]:
            try:
                r = requests.post(
                    f"{es_url}/{index}/_search",
                    json={
                        "query": {
                            "multi_match": {
                                "query": self.correlation_id,
                                "fields": ["correlation_id", "alert_id"],
                            }
                        },
                        "size": 10,
                    },
                    auth=es_auth,
                    timeout=10,
                    verify=False,
                )
                if r.status_code == 200:
                    es_docs[index] = r.json().get("hits", {}).get("hits", [])
                else:
                    es_docs[index] = {"error": f"HTTP {r.status_code}"}
            except Exception as e:
                es_docs[index] = {"error": str(e)}
        self.write_evidence("elasticsearch_docs.json", es_docs)

        # OpenSearch documents
        os_url = self.get_service_url("opensearch")
        os_docs: dict[str, Any] = {}
        exec_id = getattr(self, "execution_id", None)
        if exec_id:
            try:
                r = requests.get(
                    f"{os_url}/workflowexecution-000001/_doc/{exec_id}",
                    timeout=10,
                    verify=False,
                )
                if r.status_code == 200:
                    os_docs["execution"] = r.json().get("_source", {})
                else:
                    os_docs["execution"] = {"error": f"HTTP {r.status_code}"}
            except Exception as e:
                os_docs["execution"] = {"error": str(e)}
        self.write_evidence("opensearch_docs.json", os_docs)

    def export_loki_logs(self) -> None:
        """Export Loki logs as evidence.

        Delegates to ObservabilityMixin.export_loki_logs (which has MRO
        precedence) to avoid duplicating the Loki query logic.
        """
        # ObservabilityMixin.export_loki_logs writes evidence directly.
        # If observability is disabled, write an empty placeholder.
        if not getattr(self, "_loki_exported", False):
            try:
                data = self.export_loki_logs_raw()  # type: ignore[attr-defined]
                self.write_evidence("loki_logs.json", data)
            except AttributeError:
                self.write_evidence("loki_logs.json", {"error": "Loki export unavailable"})
