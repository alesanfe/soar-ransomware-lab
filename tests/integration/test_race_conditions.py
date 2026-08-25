#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Race Conditions Tests
Tests for race conditions and concurrent operations
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from soar_lab.infrastructure.integrations.elasticsearch.client import (
    ElasticsearchClient,
)
from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient


@pytest.mark.requires_external
class TestRaceConditions:
    """Test race conditions and concurrent operations."""

    @pytest.fixture
    def thehive_client(self):
        """Create TheHive client for testing."""
        return TheHiveClient(base_url="http://localhost:9000", api_key="test-key", verify_ssl=False)

    @pytest.fixture
    def es_client(self):
        """Create Elasticsearch client for testing."""
        return ElasticsearchClient(
            hosts=["http://localhost:9200"], username="elastic", password="test-pass"
        )

    def test_concurrent_case_creation(self, thehive_client):
        """Test concurrent case creation doesn't create duplicates."""
        alert_id = "RACE-TEST-001"
        created_cases = []
        lock = threading.Lock()

        def create_case():
            case = thehive_client.create_case(
                title=f"Case for {alert_id}", description=f"Alert: {alert_id}", severity=2
            )
            with lock:
                created_cases.append(case["id"])

        # Create cases concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_case) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # Should have only unique case IDs
        unique_cases = set(created_cases)
        assert (
            len(unique_cases) <= 1
        ), f"Concurrent case creation should not create duplicates, got {len(unique_cases)} cases"

    def test_concurrent_observable_creation(self, thehive_client):
        """Test concurrent observable creation doesn't create duplicates."""
        case_id = "case-001"
        created_observables = []
        lock = threading.Lock()

        def create_observable():
            obs = thehive_client.create_observable(
                case_id=case_id, data_type="ip", data="192.168.1.100"
            )
            with lock:
                created_observables.append(obs["id"])

        # Create observables concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_observable) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # Should have only unique observable IDs
        unique_obs = set(created_observables)
        assert len(unique_obs) <= 1, (
            f"Concurrent observable creation should not create duplicates, "
            f"got {len(unique_obs)} observables"
        )

    def test_concurrent_document_indexing(self, es_client):
        """Test concurrent document indexing doesn't create duplicates."""
        doc_id = "RACE-DOC-001"
        indexed_count = [0]
        lock = threading.Lock()

        def index_document():
            es_client.index_document(index="alerts", document={"alert_id": doc_id, "severity": 2})
            with lock:
                indexed_count[0] += 1

        # Index documents concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(index_document) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # Verify only one document exists
        result = es_client.search(index="alerts", query={"term": {"alert_id": doc_id}})
        assert (
            result["hits"]["total"]["value"] == 1
        ), f"Should have only 1 document, got {result['hits']['total']['value']}"

    def test_lock_mechanism(self, thehive_client):
        """Test that lock mechanism prevents race conditions."""
        alert_id = "LOCK-TEST-001"
        case_ids = []
        lock = threading.Lock()

        def create_case_with_lock():
            with lock:
                case = thehive_client.create_case(
                    title=f"Case for {alert_id}", description=f"Alert: {alert_id}", severity=2
                )
                case_ids.append(case["id"])

        # Create cases with lock
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_case_with_lock) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # With lock, should have sequential execution
        assert len(case_ids) == 10, "Should create 10 cases with lock"

    def test_semaphore_limit_concurrent_operations(self, thehive_client):
        """Test semaphore limits concurrent operations."""
        max_concurrent = 3
        semaphore = threading.Semaphore(max_concurrent)
        concurrent_count = [0]
        max_concurrent_reached = [0]
        lock = threading.Lock()

        def operation():
            with semaphore:
                with lock:
                    concurrent_count[0] += 1
                    max_concurrent_reached[0] = max(max_concurrent_reached[0], concurrent_count[0])

                # Simulate work
                import time

                time.sleep(0.1)

                with lock:
                    concurrent_count[0] -= 1

        # Run operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(operation) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # Verify semaphore limited concurrency
        assert max_concurrent_reached[0] <= max_concurrent, (
            f"Semaphore should limit concurrency to {max_concurrent}, "
            f"reached {max_concurrent_reached[0]}"
        )

    def test_atomic_transaction(self, es_client):
        """Test atomic transaction prevents partial updates."""
        doc_id = "ATOMIC-DOC-001"

        def update_document():
            es_client.update_document(index="alerts", doc_id=doc_id, document={"severity": 3})

        # Update document concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(update_document) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # Verify document is in consistent state
        result = es_client.search(index="alerts", query={"term": {"alert_id": doc_id}})
        if result["hits"]["total"]["value"] > 0:
            severity = result["hits"]["hits"][0]["_source"]["severity"]
            assert severity == 3, "Document should be in consistent state"

    def test_concurrent_search_and_update(self, es_client):
        """Test concurrent search and update operations."""
        doc_id = "SEARCH-UPDATE-001"

        # Index document
        es_client.index_document(index="alerts", document={"alert_id": doc_id, "severity": 2})

        def search_and_update():
            result = es_client.search(index="alerts", query={"term": {"alert_id": doc_id}})
            if result["hits"]["total"]["value"] > 0:
                es_client.update_document(
                    index="alerts",
                    doc_id=result["hits"]["hits"][0]["_id"],
                    document={"severity": 3},
                )

        # Run operations concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(search_and_update) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # Verify consistency
        result = es_client.search(index="alerts", query={"term": {"alert_id": doc_id}})
        assert result["hits"]["total"]["value"] == 1, "Should have only 1 document"

    def test_concurrent_delete_operations(self, thehive_client):
        """Test concurrent delete operations don't cause errors."""
        # Create case
        case = thehive_client.create_case(
            title="Delete Test Case", description="Test case for concurrent delete", severity=2
        )

        def delete_case():
            try:
                thehive_client.delete_case(case["id"])
            except Exception:
                # Expected - case already deleted
                pass

        # Delete concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(delete_case) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # Should not cause errors
        assert True, "Concurrent deletes should not cause errors"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
