#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Metrics Export Tests
Tests for metrics export to Elasticsearch
"""

import pytest
from datetime import datetime, timezone
from soar_lab.analytics.metrics import MetricsExporter
from soar_lab.infrastructure.external.integrations.elasticsearch_client import ElasticsearchClient
from unittest.mock import Mock, patch


class TestMetricsExport:
    """Test metrics export functionality"""

    @pytest.fixture
    def es_client(self):
        """Create Elasticsearch client for testing"""
        return ElasticsearchClient(
            hosts=["http://localhost:9200"],
            username="elastic",
            password="test-pass"
        )

    @pytest.fixture
    def metrics_exporter(self, es_client):
        """Create metrics exporter for testing"""
        return MetricsExporter(es_client)

    def test_metrics_exported_to_es(self, metrics_exporter, es_client):
        """Test that metrics are exported to Elasticsearch"""
        metrics = {
            "mttr_seconds": 3600,
            "total_cases": 100,
            "resolved_cases": 80,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Export metrics
        metrics_exporter.export_metrics(metrics)

        # Verify metrics are indexed
        result = es_client.search(
            index="soar-metrics",
            query={"match_all": {}}
        )

        assert result['hits']['total']['value'] > 0, "Metrics should be exported to ES"

    def test_metrics_format_validation(self, metrics_exporter):
        """Test that metrics have correct format"""
        metrics = {
            "mttr_seconds": 3600.5,
            "total_cases": 100,
            "resolved_cases": 80,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Validate format
        is_valid = metrics_exporter.validate_metrics_format(metrics)
        assert is_valid, "Metrics should have correct format"

    def test_kpi_aggregation(self, metrics_exporter, es_client):
        """Test KPI aggregation"""
        # Index multiple metric documents
        for i in range(10):
            metrics = {
                "mttr_seconds": 3000 + (i * 100),
                "total_cases": 100 + i,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            metrics_exporter.export_metrics(metrics)

        # Aggregate KPIs
        aggregated = metrics_exporter.aggregate_kpis("soar-metrics")

        assert "avg_mttr" in aggregated, "Should calculate average MTTR"
        assert "total_cases" in aggregated, "Should calculate total cases"

    def test_metrics_timestamp_validation(self, metrics_exporter):
        """Test that metrics have valid timestamps"""
        metrics = {
            "mttr_seconds": 3600,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Validate timestamp
        timestamp = metrics_exporter.parse_timestamp(metrics["timestamp"])
        assert timestamp is not None, "Timestamp should be valid"
        assert timestamp.tzinfo is not None, "Timestamp should have timezone"

    def test_metrics_index_creation(self, metrics_exporter, es_client):
        """Test that metrics index is created with correct mapping"""
        # Export metrics (should create index if not exists)
        metrics = {
            "mttr_seconds": 3600,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        metrics_exporter.export_metrics(metrics)

        # Verify index exists
        assert es_client.index_exists("soar-metrics"), "Metrics index should be created"

        # Verify mapping
        mapping = es_client.client.indices.get_mapping(index="soar-metrics")
        assert "soar-metrics" in mapping, "Should retrieve mapping"

    def test_metrics_retention_policy(self, metrics_exporter, es_client):
        """Test metrics retention policy"""
        # Index old metrics
        old_metrics = {
            "mttr_seconds": 3600,
            "timestamp": "2020-01-01T00:00:00Z"
        }
        metrics_exporter.export_metrics(old_metrics)

        # Apply retention policy (e.g., keep only last 30 days)
        metrics_exporter.apply_retention_policy(days=30)

        # Verify old metrics are deleted
        result = es_client.search(
            index="soar-metrics",
            query={"range": {"timestamp": {"lte": "2020-02-01T00:00:00Z"}}}
        )
        assert result['hits']['total']['value'] == 0, "Old metrics should be deleted"

    def test_metrics_real_time_export(self, metrics_exporter):
        """Test real-time metrics export"""
        metrics = {
            "mttr_seconds": 3600,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Export in real-time
        start_time = datetime.now(timezone.utc)
        metrics_exporter.export_metrics(metrics, real_time=True)
        end_time = datetime.now(timezone.utc)

        # Should be fast (< 1 second)
        duration = (end_time - start_time).total_seconds()
        assert duration < 1.0, f"Real-time export should be fast, took {duration}s"

    def test_metrics_batch_export(self, metrics_exporter, es_client):
        """Test batch metrics export"""
        metrics_batch = [
            {
                "mttr_seconds": 3000 + (i * 100),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            for i in range(100)
        ]

        # Export batch
        metrics_exporter.export_metrics_batch(metrics_batch)

        # Verify all metrics are indexed
        result = es_client.search(index="soar-metrics", query={"match_all": {}})
        assert result['hits']['total']['value'] >= 100, "All batch metrics should be exported"

    def test_metrics_error_handling(self, metrics_exporter):
        """Test error handling in metrics export"""
        invalid_metrics = {
            "mttr_seconds": "invalid",  # Should be number
            "timestamp": "invalid-timestamp"
        }

        # Should handle error gracefully
        with pytest.raises(ValueError):
            metrics_exporter.export_metrics(invalid_metrics)

    def test_metrics_aggregation_by_time_range(self, metrics_exporter, es_client):
        """Test metrics aggregation by time range"""
        # Index metrics with different timestamps
        for i in range(10):
            metrics = {
                "mttr_seconds": 3000 + (i * 100),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            metrics_exporter.export_metrics(metrics)

        # Aggregate by time range
        start_date = "2024-01-01T00:00:00Z"
        end_date = "2099-12-31T23:59:59Z"
        aggregated = metrics_exporter.aggregate_by_time_range(
            "soar-metrics",
            start_date,
            end_date
        )

        assert "count" in aggregated, "Should return count"
        assert "avg_mttr" in aggregated, "Should return average MTTR"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
