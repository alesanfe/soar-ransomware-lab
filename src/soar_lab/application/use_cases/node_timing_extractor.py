#!/usr/bin/env python3
"""Extract per-node timing metrics from Shuffle workflow executions.

This module queries OpenSearch (where Shuffle stores workflow execution
results with per-node started_at/completed_at timestamps) and produces
a structured timing breakdown for each execution.

The resulting data is used to:
  1. Index per-node durations into soar-metrics for dashboards.
  2. Identify bottlenecks for workflow optimization.
  3. Provide data for the TFM's performance analysis tables.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import requests

from soar_lab.common.constants import (
    AUTH_BASIC_PREFIX,
    CONTENT_TYPE_JSON,
    DEFAULT_ELASTICSEARCH_URL,
    DEFAULT_NODE_TIMING_TIMEOUT,
    DEFAULT_OPENSEARCH_URL,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
    METRICS_INDEX,
    SHUFFLE_EXECUTION_INDEX,
)
from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class NodeTimingExtractor:
    """Extract per-node timing data from Shuffle/OpenSearch executions."""

    def __init__(
        self,
        opensearch_url: str = DEFAULT_OPENSEARCH_URL,
        opensearch_user: str = "admin",
        opensearch_pass: str | None = None,
        elasticsearch_url: str = DEFAULT_ELASTICSEARCH_URL,
        elasticsearch_user: str = "elastic",
        elasticsearch_pass: str | None = None,
        metrics_index: str = METRICS_INDEX,
    ) -> None:
        """Initialize the extractor with OpenSearch and Elasticsearch.

        credentials.

        Args:
            opensearch_url: OpenSearch base URL (e.g. ``http://opensearch:9200``).
            opensearch_user: OpenSearch username (default ``admin``).
            opensearch_pass: OpenSearch password (None to skip auth).
            elasticsearch_url: Elasticsearch base URL for indexing metrics.
            elasticsearch_user: Elasticsearch username (default ``elastic``).
            elasticsearch_pass: Elasticsearch password (None to skip auth).
            metrics_index: Target ES index for node-timing documents.
        """
        self.os_url = opensearch_url.rstrip("/")
        self.os_auth = (
            base64_b64encode(f"{opensearch_user}:{opensearch_pass}".encode())
            if opensearch_pass
            else ""
        )
        self.es_url = elasticsearch_url.rstrip("/")
        self.es_auth = (
            base64_b64encode(f"{elasticsearch_user}:{elasticsearch_pass}".encode())
            if elasticsearch_pass
            else ""
        )
        self.metrics_index = metrics_index

    def _os_headers(self) -> dict[str, str]:
        """Build HTTP headers for OpenSearch requests with optional auth."""
        h = {HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON}
        if self.os_auth:
            h[HEADER_AUTHORIZATION] = f"{AUTH_BASIC_PREFIX} {self.os_auth}"
        return h

    def _es_headers(self) -> dict[str, str]:
        """Build HTTP headers for Elasticsearch requests with optional auth."""
        h = {HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON}
        if self.es_auth:
            h[HEADER_AUTHORIZATION] = f"{AUTH_BASIC_PREFIX} {self.es_auth}"
        return h

    def fetch_execution(self, execution_id: str) -> dict[str, Any] | None:
        """Fetch a single workflow execution from OpenSearch by execution_id.

        Args:
            execution_id: Shuffle execution identifier to query.

        Returns:
            dict: Execution document from OpenSearch, or None if not found.
        """
        body = json.dumps(
            {
                "size": 1,
                "query": {"term": {"execution_id": execution_id}},
                "_source": True,
            }
        ).encode()
        try:
            r = requests.post(
                f"{self.os_url}/{SHUFFLE_EXECUTION_INDEX}/_search",
                data=body,
                headers=self._os_headers(),
                timeout=DEFAULT_NODE_TIMING_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            hits = data.get("hits", {}).get("hits", [])
            if hits:
                return dict(hits[0]["_source"])
        except Exception as e:
            logger.warning("Failed to fetch execution %s: %s", execution_id, e)
        return None

    def extract_timings(self, execution: dict[str, Any]) -> dict[str, Any]:
        """Extract per-node timings from a workflow execution document.

        Args:
            execution: Execution document from OpenSearch with ``results`` list.

        Returns:
            dict: Timings with ``execution_id``, ``workflow_start/end/duration``,
            ``nodes`` (label -> timing), ``slowest_nodes`` (top 5), and
            ``parallel_groups``.
        """
        exec_id = execution.get("execution_id", "")
        wf_start = execution.get("started_at", 0)
        wf_end = execution.get("completed_at", 0)
        # OpenSearch/Shuffle stores workflow started_at/completed_at as epoch
        # seconds (e.g. 1723848000). Node-level started_at/completed_at inside
        # results[] are stored as epoch milliseconds.
        wf_start_s = float(wf_start)
        wf_end_s = float(wf_end)
        wf_duration = round(wf_end_s - wf_start_s, 3) if wf_end_s and wf_start_s else 0

        results = execution.get("results", [])
        nodes: dict[str, dict[str, Any]] = {}
        for r in results:
            if not isinstance(r, dict):
                continue
            action = r.get("action", {})
            label = action.get("label", "?") if isinstance(action, dict) else "?"
            start_ms = r.get("started_at", 0)
            end_ms = r.get("completed_at", 0)
            status = r.get("status", "")
            if start_ms and end_ms:
                # Node timestamps are in milliseconds
                start_s = start_ms / 1000.0
                end_s = end_ms / 1000.0
                duration_s = round(end_s - start_s, 3)
                start_offset = round(start_s - wf_start_s, 3)
                nodes[label] = {
                    "start_offset_s": start_offset,
                    "duration_s": duration_s,
                    "status": status,
                }

        # Identify slowest nodes
        sorted_nodes = sorted(nodes.items(), key=lambda x: x[1].get("duration_s", 0), reverse=True)
        slowest = [{"label": lbl} | info for lbl, info in sorted_nodes[:10]]

        # Identify parallel groups (nodes that start within 2s of each other)
        parallel_groups: list[dict[str, Any]] = []
        sorted_by_start = sorted(nodes.items(), key=lambda x: x[1].get("start_offset_s", 0))
        current_group: list[str] = []
        current_group_start = -1
        for lbl, info in sorted_by_start:
            offset = info.get("start_offset_s", 0)
            if current_group_start < 0 or abs(offset - current_group_start) <= 2:
                current_group.append(lbl)
                if current_group_start < 0:
                    current_group_start = offset
            else:
                if len(current_group) > 1:
                    parallel_groups.append(
                        {"nodes": current_group.copy(), "start_offset_s": current_group_start}
                    )
                current_group = [lbl]
                current_group_start = offset
        if len(current_group) > 1:
            parallel_groups.append(
                {"nodes": current_group.copy(), "start_offset_s": current_group_start}
            )

        return {
            "execution_id": exec_id,
            "workflow_start": wf_start,
            "workflow_end": wf_end,
            "workflow_duration_s": round(wf_duration, 3),
            "total_nodes": len(nodes),
            "nodes": nodes,
            "slowest_nodes": slowest,
            "parallel_groups": parallel_groups,
            "extracted_at": datetime.now(UTC).isoformat(),
        }

    def index_timings(self, timings: dict[str, Any], alert_id: str = "") -> bool:
        """Index per-node timing data into soar-metrics index.

        Args:
            timings: Timings dict from ``extract_timings``.
            alert_id: Optional alert ID to associate with the document.

        Returns:
            bool: True if the document was indexed successfully.
        """
        doc = {
            "alert_id": alert_id or timings.get("execution_id", ""),
            "metric_type": "node_timings",
            "@timestamp": datetime.now(UTC).isoformat(),
            "timestamp": datetime.now(UTC).isoformat(),
            "source": "node-timing-extractor",
        } | timings
        body = json.dumps(doc).encode()
        try:
            r = requests.post(
                f"{self.es_url}/{self.metrics_index}/_doc",
                data=body,
                headers=self._es_headers(),
                timeout=DEFAULT_NODE_TIMING_TIMEOUT,
            )
            r.raise_for_status()
            logger.info("Indexed node timings for %s", alert_id)
            return True
        except Exception as e:
            logger.warning("Failed to index node timings: %s", e)
            return False

    def process_execution(self, execution_id: str, alert_id: str = "") -> dict[str, Any] | None:
        """Fetch an execution, extract timings, and index them.

        Args:
            execution_id: Shuffle execution identifier to process.
            alert_id: Optional alert ID to associate with the timings.

        Returns:
            dict: Extracted timings if the execution was found, None otherwise.
        """
        execution = self.fetch_execution(execution_id)
        if not execution:
            return None
        timings = self.extract_timings(execution)
        self.index_timings(timings, alert_id)
        return timings


def base64_b64encode(s: bytes) -> str:
    """Base64-encode bytes and return a UTF-8 string (helper for HTTP Basic.

    auth).

    Args:
        s: Bytes to encode (e.g. ``b"user:pass"``).

    Returns:
        str: Base64-encoded UTF-8 string suitable for ``Authorization`` headers.
    """
    import base64

    return base64.b64encode(s).decode()
