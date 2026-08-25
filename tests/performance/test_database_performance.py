#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Database Performance Tests
Performance tests for database operations
"""

import time

import pytest

from soar_lab.infrastructure.integrations.elasticsearch.client import (
    ElasticsearchClient,
)


@pytest.mark.requires_external
class TestDatabasePerformance:
    """Test database performance."""

    @pytest.fixture
    def es_client(self):
        """Create Elasticsearch client for testing."""
        return ElasticsearchClient(
            hosts=["http://elasticsearch:9200"], username="elastic", password="test-pass"
        )

    def test_query_latency(self, es_client):
        """Test query latency benchmarks."""
        # Index test data
        for i in range(100):
            es_client.index_document(
                index="alerts", document={"alert_id": f"PERF-{i}", "severity": i % 4}
            )

        es_client.indices.refresh(index="alerts")

        # Benchmark query latency
        start_time = time.time()
        es_client.search(index="alerts", query={"match_all": {}})
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000
        assert latency_ms < 100, f"Query latency should be < 100ms, got {latency_ms}ms"

    def test_write_latency(self, es_client):
        """Test write latency benchmarks."""
        document = {"alert_id": "WRITE-PERF-001", "severity": 2}

        # Benchmark write latency
        start_time = time.time()
        es_client.index_document(index="alerts", document=document)
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000
        assert latency_ms < 50, f"Write latency should be < 50ms, got {latency_ms}ms"

    def test_throughput_under_load(self, es_client):
        """Test throughput under load."""
        num_documents = 1000
        documents = [{"alert_id": f"LOAD-{i}", "severity": i % 4} for i in range(num_documents)]

        # Benchmark throughput
        start_time = time.time()
        es_client.bulk_index(index="alerts", documents=documents)
        end_time = time.time()

        duration = end_time - start_time
        throughput = num_documents / duration

        assert throughput > 100, f"Throughput should be > 100 docs/sec, got {throughput} docs/sec"

    def test_bulk_indexing_performance(self, es_client):
        """Test bulk indexing performance."""
        batch_sizes = [100, 500, 1000, 5000]

        for batch_size in batch_sizes:
            documents = [{"alert_id": f"BULK-{i}", "severity": i % 4} for i in range(batch_size)]

            start_time = time.time()
            es_client.bulk_index(index="alerts", documents=documents)
            end_time = time.time()

            duration = end_time - start_time
            throughput = batch_size / duration

            print(f"Batch size {batch_size}: {throughput:.2f} docs/sec")
            assert throughput > 50, f"Throughput should be > 50 docs/sec for batch {batch_size}"

    def test_aggregation_performance(self, es_client):
        """Test aggregation query performance."""
        # Index test data
        for i in range(1000):
            es_client.index_document(
                index="alerts",
                document={
                    "alert_id": f"AGG-{i}",
                    "severity": i % 4,
                    "type": "ransomware" if i % 2 == 0 else "malware",
                },
            )

        es_client.indices.refresh(index="alerts")

        # Benchmark aggregation
        start_time = time.time()
        es_client.search(
            index="alerts",
            query={"match_all": {}},
            aggs={
                "severity_distribution": {"terms": {"field": "severity"}},
                "type_distribution": {"terms": {"field": "type"}},
            },
        )
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000
        assert latency_ms < 200, f"Aggregation latency should be < 200ms, got {latency_ms}ms"

    def test_concurrent_read_performance(self, es_client):
        """Test concurrent read performance."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Index test data
        for i in range(100):
            es_client.index_document(
                index="alerts", document={"alert_id": f"CONCURRENT-{i}", "severity": i % 4}
            )

        es_client.indices.refresh(index="alerts")

        def query():
            return es_client.search(index="alerts", query={"match_all": {}})

        # Benchmark concurrent reads
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(query) for _ in range(50)]
            for future in as_completed(futures):
                future.result()
        end_time = time.time()

        duration = end_time - start_time
        throughput = 50 / duration

        assert (
            throughput > 10
        ), f"Concurrent read throughput should be > 10 queries/sec, got {throughput} queries/sec"

    def test_concurrent_write_performance(self, es_client):
        """Test concurrent write performance."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def index_doc(i):
            es_client.index_document(
                index="alerts", document={"alert_id": f"CONCURRENT-WRITE-{i}", "severity": i % 4}
            )

        # Benchmark concurrent writes
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(index_doc, i) for i in range(100)]
            for future in as_completed(futures):
                future.result()
        end_time = time.time()

        duration = end_time - start_time
        throughput = 100 / duration

        assert (
            throughput > 20
        ), f"Concurrent write throughput should be > 20 docs/sec, got {throughput} docs/sec"

    def test_index_size_impact(self, es_client):
        """Test performance impact of index size."""
        sizes = [100, 1000, 10000]
        latencies = []

        for size in sizes:
            # Index documents
            documents = [{"alert_id": f"SIZE-{i}", "severity": i % 4} for i in range(size)]
            es_client.bulk_index(index="alerts", documents=documents)
            es_client.indices.refresh(index="alerts")

            # Benchmark query
            start_time = time.time()
            es_client.search(index="alerts", query={"match_all": {}})
            end_time = time.time()

            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

            print(f"Index size {size}: {latency_ms:.2f}ms")

        # Latency should not increase linearly with size
        assert (
            latencies[2] < latencies[0] * 50
        ), "Query latency should not increase linearly with index size"

    def test_complex_query_performance(self, es_client):
        """Test complex query performance."""
        # Index test data
        for i in range(1000):
            es_client.index_document(
                index="alerts",
                document={
                    "alert_id": f"COMPLEX-{i}",
                    "severity": i % 4,
                    "hostname": f"host-{i % 10}",
                    "src_ip": f"192.168.1.{i % 255}",
                },
            )

        es_client.indices.refresh(index="alerts")

        # Benchmark complex query
        start_time = time.time()
        es_client.search(
            index="alerts",
            query={
                "bool": {
                    "must": [{"range": {"severity": {"gte": 2}}}, {"term": {"hostname": "host-5"}}],
                    "filter": [{"range": {"src_ip": {"lte": "192.168.1.100"}}}],
                }
            },
        )
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000
        assert latency_ms < 150, f"Complex query latency should be < 150ms, got {latency_ms}ms"

    def test_update_performance(self, es_client):
        """Test update operation performance."""
        # Index document
        es_client.index_document(
            index="alerts", document={"alert_id": "UPDATE-PERF-001", "severity": 2}
        )
        es_client.indices.refresh(index="alerts")

        # Get document ID
        result = es_client.search(index="alerts", query={"term": {"alert_id": "UPDATE-PERF-001"}})
        doc_id = result["hits"]["hits"][0]["_id"]

        # Benchmark update
        start_time = time.time()
        es_client.update_document(index="alerts", doc_id=doc_id, document={"severity": 3})
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000
        assert latency_ms < 50, f"Update latency should be < 50ms, got {latency_ms}ms"

    def test_delete_performance(self, es_client):
        """Test delete operation performance."""
        # Index document
        es_client.index_document(
            index="alerts", document={"alert_id": "DELETE-PERF-001", "severity": 2}
        )
        es_client.indices.refresh(index="alerts")

        # Get document ID
        result = es_client.search(index="alerts", query={"term": {"alert_id": "DELETE-PERF-001"}})
        doc_id = result["hits"]["hits"][0]["_id"]

        # Benchmark delete
        start_time = time.time()
        es_client.delete_document(index="alerts", doc_id=doc_id)
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000
        assert latency_ms < 50, f"Delete latency should be < 50ms, got {latency_ms}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
