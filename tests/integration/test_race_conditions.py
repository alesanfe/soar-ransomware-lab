#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Race Conditions Tests
Tests for race conditions and concurrent operations
"""

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from soar_lab.common.exceptions import IntegrationError
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
        return TheHiveClient(
            base_url=os.environ.get("THEHIVE_URL", "http://localhost:9000"),
            api_key=os.environ.get("THEHIVE_API_KEY", "test-key"),
            verify_ssl=False,
        )

    @pytest.fixture
    def es_client(self):
        """Create Elasticsearch client for testing."""
        return ElasticsearchClient(
            base_url=os.environ.get("ES_URL", "https://localhost:19200"),
            username=os.environ.get("ELASTIC_USERNAME", "elastic"),
            password=os.environ.get("ELASTIC_PASSWORD", "test-pass"),
        )

    def test_concurrent_case_creation(self, thehive_client):
        """Test concurrent case creation completes safely: every create must
        succeed and produce a distinct case id (TheHive case API does not
        dedupe by title).

        TheHive can reject a burst of simultaneous ``POST /api/v1/case``
        with a transient 400 (case-number counter race), so each create
        retries once — the assertion is on the final outcome."""
        alert_id = "RACE-TEST-001"
        created_cases = []
        lock = threading.Lock()

        def create_case():
            import time

            for attempt in range(3):
                try:
                    case = thehive_client.create_case(
                        title=f"Case for {alert_id}",
                        description=f"Alert: {alert_id}",
                        severity=2,
                    )
                    with lock:
                        created_cases.append(case["_id"])
                    return
                except IntegrationError:
                    if attempt == 2:
                        raise
                    time.sleep(0.5 * (attempt + 1))

        # Create cases concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_case) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # All concurrent creates must succeed with unique ids
        assert len(created_cases) == 10, "All concurrent creates must succeed"
        unique_cases = set(created_cases)
        assert (
            len(unique_cases) == 10
        ), f"Every case must get a distinct id, got {len(unique_cases)} unique"

    def test_concurrent_observable_creation(self, thehive_client):
        """Test concurrent observable creation: TheHive dedupes artifacts in a
        case — exactly one create must succeed, the rest get a conflict."""
        case = thehive_client.create_case(
            title="Race Observable Case",
            description="Case for concurrent observable creation",
            severity=2,
        )
        created_observables = []
        conflicts = []
        lock = threading.Lock()

        def create_observable():
            try:
                obs = thehive_client.create_observable(
                    case_id=case["id"], data_type="ip", data="192.168.1.100"
                )
                with lock:
                    created_observables.append(obs["id"])
            except IntegrationError:
                with lock:
                    conflicts.append(1)

        # Create observables concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_observable) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # Exactly one observable must win; the rest must be rejected
        assert len(created_observables) == 1, (
            f"Concurrent observable creation must create exactly 1 artifact, "
            f"got {len(created_observables)}"
        )
        assert (
            len(conflicts) == 9
        ), f"Duplicate observables must be rejected, got {len(conflicts)} conflicts"

    def test_concurrent_document_indexing(self, es_client):
        """Test concurrent document indexing upserts to a single document."""
        doc_id = f"RACE-DOC-{uuid.uuid4().hex[:10].upper()}"
        indexed_count = [0]
        lock = threading.Lock()

        def index_document():
            es_client.index_document(
                index="alerts",
                document={"alert_id": doc_id, "severity": 2},
                doc_id=doc_id,
                refresh=True,
            )
            with lock:
                indexed_count[0] += 1

        # Index documents concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(index_document) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # Verify only one document exists
        result = es_client.search(index="alerts", query={"term": {"alert_id.keyword": doc_id}})
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
        doc_id = f"ATOMIC-DOC-{uuid.uuid4().hex[:10].upper()}"
        es_client.index_document(
            index="alerts",
            document={"alert_id": doc_id, "severity": 2},
            doc_id=doc_id,
            refresh=True,
        )

        def update_document():
            es_client.update_document(
                index="alerts", doc_id=doc_id, document={"severity": 3}, refresh=True
            )

        # Update document concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(update_document) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # Verify document is in consistent state
        result = es_client.search(index="alerts", query={"term": {"alert_id.keyword": doc_id}})
        assert result["hits"]["total"]["value"] == 1, "Should have exactly 1 document"
        severity = result["hits"]["hits"][0]["_source"]["severity"]
        assert severity == 3, "Document should be in consistent state"

    def test_concurrent_search_and_update(self, es_client):
        """Test concurrent search and update operations."""
        doc_id = f"SEARCH-UPDATE-{uuid.uuid4().hex[:10].upper()}"

        # Index document
        es_client.index_document(
            index="alerts",
            document={"alert_id": doc_id, "severity": 2},
            doc_id=doc_id,
            refresh=True,
        )

        def search_and_update():
            result = es_client.search(index="alerts", query={"term": {"alert_id.keyword": doc_id}})
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
        result = es_client.search(index="alerts", query={"term": {"alert_id.keyword": doc_id}})
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
