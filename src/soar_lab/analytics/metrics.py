from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


class MetricsExporter:
    """Export and aggregate SOAR metrics in Elasticsearch."""

    DEFAULT_INDEX = "soar-metrics"

    def __init__(self, client=None) -> None:
        self.client = client

    # Legacy stubs kept for compatibility
    def export(self, metrics: Dict[str, Any]) -> bool:
        try:
            self.export_metrics(metrics)
            return True
        except Exception:
            return False

    def get_metrics(self) -> List[Dict[str, Any]]:
        try:
            result = self.client.search(index=self.DEFAULT_INDEX, query={"match_all": {}}, size=1000)
            return [hit.get("_source", hit) for hit in result.get("hits", {}).get("hits", [])]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def parse_timestamp(self, timestamp: str) -> Optional[datetime]:
        """Parse an ISO 8601 timestamp into a timezone-aware datetime."""
        if not timestamp or not isinstance(timestamp, str):
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                dt = datetime.strptime(timestamp, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        # Fallback to fromisoformat (handles 'Z')
        try:
            ts = timestamp.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    def validate_metrics_format(self, metrics: Dict[str, Any]) -> bool:
        """Validate that metrics have the expected shape and types."""
        if not isinstance(metrics, dict):
            return False
        if "mttr_seconds" in metrics and not isinstance(metrics["mttr_seconds"], (int, float)):
            return False
        if "timestamp" in metrics and self.parse_timestamp(metrics["timestamp"]) is None:
            return False
        return True

    # ------------------------------------------------------------------
    # Export methods
    # ------------------------------------------------------------------
    def export_metrics(
        self,
        metrics: Dict[str, Any],
        index: Optional[str] = None,
        real_time: bool = False,
    ) -> Dict[str, Any]:
        """Export a single metrics document to Elasticsearch."""
        if not self.validate_metrics_format(metrics):
            raise ValueError(f"Invalid metrics format: {metrics}")

        idx = index or self.DEFAULT_INDEX
        doc = dict(metrics)
        if "timestamp" not in doc:
            doc["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Ensure @timestamp is present for Grafana
        if "@timestamp" not in doc:
            doc["@timestamp"] = doc["timestamp"]

        if not self.client:
            return {"result": "no_client", "_index": idx}

        if real_time:
            doc["real_time"] = True

        return self.client.index_document(index=idx, document=doc)

    def export_metrics_batch(
        self,
        metrics_batch: List[Dict[str, Any]],
        index: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export a batch of metrics documents using the bulk API."""
        idx = index or self.DEFAULT_INDEX
        for metrics in metrics_batch:
            if not self.validate_metrics_format(metrics):
                raise ValueError(f"Invalid metrics format in batch: {metrics}")

        if not self.client:
            return {"result": "no_client", "count": len(metrics_batch)}

        return self.client.bulk_index(index=idx, documents=metrics_batch)

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------
    def aggregate_kpis(self, index: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate KPIs from the metrics index."""
        idx = index or self.DEFAULT_INDEX
        if not self.client:
            return {"avg_mttr": 0.0, "total_cases": 0, "count": 0}

        result = self.client.search(
            index=idx,
            query={"match_all": {}},
            size=1000,
        )
        hits = result.get("hits", {}).get("hits", [])
        docs = [hit.get("_source", hit) for hit in hits]

        mttr_values = [d.get("mttr_seconds") for d in docs if isinstance(d.get("mttr_seconds"), (int, float))]
        total_cases = sum(
            d.get("total_cases", 0) for d in docs if isinstance(d.get("total_cases"), (int, float))
        )

        avg_mttr = sum(mttr_values) / len(mttr_values) if mttr_values else 0.0
        return {
            "avg_mttr": round(avg_mttr, 2),
            "total_cases": total_cases,
            "count": len(docs),
        }

    def aggregate_by_time_range(
        self,
        index: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Aggregate metrics within a timestamp range."""
        if not self.client:
            return {"count": 0, "avg_mttr": 0.0}

        query = {
            "range": {
                "timestamp": {
                    "gte": start_date,
                    "lte": end_date,
                }
            }
        }
        result = self.client.search(index=index, query=query, size=1000)
        hits = result.get("hits", {}).get("hits", [])
        docs = [hit.get("_source", hit) for hit in hits]
        mttr_values = [d.get("mttr_seconds") for d in docs if isinstance(d.get("mttr_seconds"), (int, float))]
        avg_mttr = sum(mttr_values) / len(mttr_values) if mttr_values else 0.0
        return {
            "count": len(docs),
            "avg_mttr": round(avg_mttr, 2),
        }

    # ------------------------------------------------------------------
    # Retention
    # ------------------------------------------------------------------
    def apply_retention_policy(self, days: int = 30, index: Optional[str] = None) -> Dict[str, Any]:
        """Delete metrics documents older than the specified number of days."""
        idx = index or self.DEFAULT_INDEX
        if not self.client:
            return {"deleted": 0}

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        query = {
            "range": {
                "timestamp": {
                    "lte": cutoff,
                }
            }
        }
        # Use delete_by_query if available
        try:
            result = self.client.post(f"/{idx}/_delete_by_query", data={"query": query})
            return {"deleted": result.get("deleted", 0)}
        except Exception:
            # Fallback: search and delete individually
            result = self.client.search(index=idx, query=query, size=1000)
            hits = result.get("hits", {}).get("hits", [])
            deleted = 0
            for hit in hits:
                try:
                    self.client.delete_document(doc_id=hit["_id"], index=idx)
                    deleted += 1
                except Exception:
                    pass
            return {"deleted": deleted}
