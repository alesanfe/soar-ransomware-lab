#!/usr/bin/env python3
"""Unit tests for NodeTimingExtractor."""

from unittest.mock import MagicMock

import pytest

from soar_lab.application.use_cases.node_timing_extractor import NodeTimingExtractor


@pytest.fixture
def mock_post():
    return MagicMock()


@pytest.fixture
def extractor(mock_post):
    return NodeTimingExtractor(
        opensearch_url="https://opensearch:9200",
        opensearch_user="admin",
        opensearch_pass="test",
        elasticsearch_url="https://elasticsearch:9200",
        elasticsearch_user="elastic",
        elasticsearch_pass="test",
        metrics_index="soar-metrics",
        http_post=mock_post,
    )


@pytest.fixture
def sample_execution():
    """Sample workflow execution document from OpenSearch.

    Workflow started_at/completed_at are epoch seconds. Node-level
    started_at/completed_at are epoch milliseconds.
    """
    base = 1723848000  # epoch seconds
    return {
        "execution_id": "test-exec-123",
        "started_at": base,  # seconds
        "completed_at": base + 100,  # seconds (100s later)
        "status": "FINISHED",
        "results": [
            {
                "action": {"label": "normalize_inputs"},
                "started_at": (base + 0) * 1000,  # ms
                "completed_at": (base + 1) * 1000,  # ms (1s)
                "status": "SUCCESS",
            },
            {
                "action": {"label": "thehive_create_case"},
                "started_at": (base + 1) * 1000,  # ms
                "completed_at": (base + 50) * 1000,  # ms (49s)
                "status": "SUCCESS",
            },
            {
                "action": {"label": "cortex_hash"},
                "started_at": (base + 2) * 1000,  # ms
                "completed_at": (base + 17) * 1000,  # ms (15s)
                "status": "SUCCESS",
            },
            {
                "action": {"label": "cortex_ip"},
                "started_at": (base + 2) * 1000,  # ms
                "completed_at": (base + 17) * 1000,  # ms (15s)
                "status": "SUCCESS",
            },
            {
                "action": {"label": "calc_mttr"},
                "started_at": (base + 90) * 1000,  # ms
                "completed_at": (base + 91) * 1000,  # ms (1s)
                "status": "SUCCESS",
            },
        ],
    }


class TestNodeTimingExtractor:
    def test_extract_timings_basic(self, extractor, sample_execution):
        """Test that timings are extracted correctly from execution."""
        timings = extractor.extract_timings(sample_execution)

        assert timings["execution_id"] == "test-exec-123"
        assert timings["workflow_duration_s"] == 100.0
        assert timings["total_nodes"] == 5

    def test_extract_timings_node_durations(self, extractor, sample_execution):
        """Test that individual node durations are correct."""
        timings = extractor.extract_timings(sample_execution)
        nodes = timings["nodes"]

        assert "normalize_inputs" in nodes
        assert nodes["normalize_inputs"]["duration_s"] == 1.0
        assert nodes["thehive_create_case"]["duration_s"] == 49.0
        assert nodes["cortex_hash"]["duration_s"] == 15.0

    def test_extract_timings_slowest_nodes(self, extractor, sample_execution):
        """Test that slowest nodes are identified and sorted."""
        timings = extractor.extract_timings(sample_execution)
        slowest = timings["slowest_nodes"]

        assert len(slowest) <= 10
        # TheHive create case is the slowest (49s)
        assert slowest[0]["label"] == "thehive_create_case"
        assert slowest[0]["duration_s"] == 49.0
        # Sorted descending
        durations = [n["duration_s"] for n in slowest]
        assert durations == sorted(durations, reverse=True)

    def test_extract_timings_parallel_groups(self, extractor, sample_execution):
        """Test that parallel groups are detected."""
        timings = extractor.extract_timings(sample_execution)
        parallel_groups = timings["parallel_groups"]

        # cortex_hash and cortex_ip start within 2s of each other (1002)
        assert len(parallel_groups) >= 1
        # At least one group should contain both cortex nodes
        all_group_nodes = [n for pg in parallel_groups for n in pg["nodes"]]
        assert "cortex_hash" in all_group_nodes
        assert "cortex_ip" in all_group_nodes

    def test_extract_timings_empty_results(self, extractor):
        """Test extraction with empty results."""
        execution = {
            "execution_id": "empty",
            "started_at": 1723848000,
            "completed_at": 1723848001,
            "results": [],
        }
        timings = extractor.extract_timings(execution)
        assert timings["total_nodes"] == 0
        assert timings["nodes"] == {}
        assert timings["slowest_nodes"] == []
        assert timings["parallel_groups"] == []

    def test_extract_timings_missing_timestamps(self, extractor):
        """Test extraction with nodes missing timestamps."""
        base = 1723848000
        execution = {
            "execution_id": "partial",
            "started_at": base,
            "completed_at": base + 100,
            "results": [
                {
                    "action": {"label": "node_with_timestamps"},
                    "started_at": (base + 0) * 1000,
                    "completed_at": (base + 10) * 1000,
                    "status": "SUCCESS",
                },
                {
                    "action": {"label": "node_without_timestamps"},
                    "status": "SKIPPED",
                },
            ],
        }
        timings = extractor.extract_timings(execution)
        assert "node_with_timestamps" in timings["nodes"]
        assert "node_without_timestamps" not in timings["nodes"]

    def test_fetch_execution_success(self, extractor, mock_post):
        """Test fetching execution from OpenSearch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "hits": {"hits": [{"_source": {"execution_id": "test-123"}}]}
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = extractor.fetch_execution("test-123")
        assert result is not None
        assert result["execution_id"] == "test-123"

    def test_fetch_execution_not_found(self, extractor, mock_post):
        """Test fetching non-existent execution."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"hits": {"hits": []}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = extractor.fetch_execution("nonexistent")
        assert result is None

    def test_index_timings_success(self, extractor, mock_post):
        """Test indexing timings to Elasticsearch."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        timings = {"execution_id": "test", "workflow_duration_s": 100.0}
        result = extractor.index_timings(timings, alert_id="alert-1")
        assert result is True

    def test_index_timings_failure(self, extractor, mock_post):
        """Test indexing timings failure."""
        mock_post.side_effect = Exception("Connection error")

        timings = {"execution_id": "test", "workflow_duration_s": 100.0}
        result = extractor.index_timings(timings, alert_id="alert-1")
        assert result is False

    def test_extract_timings_start_offset(self, extractor, sample_execution):
        """Test that start_offset_s is calculated correctly."""
        timings = extractor.extract_timings(sample_execution)
        nodes = timings["nodes"]

        # normalize_inputs starts at 1000, workflow starts at 1000
        assert nodes["normalize_inputs"]["start_offset_s"] == 0.0
        # thehive_create_case starts at 1001, workflow starts at 1000
        assert nodes["thehive_create_case"]["start_offset_s"] == 1.0


class TestMalformedTimestamps:
    """Bug: float('garbage') on malformed workflow/node timestamps crashes
    extract_timings instead of degrading gracefully (ES -> 500)."""

    def test_malformed_workflow_timestamp_no_crash(self, extractor):
        result = extractor.extract_timings(
            {"execution_id": "x", "started_at": "garbage", "completed_at": 0, "results": []}
        )
        assert result["workflow_duration_s"] == 0
        assert result["nodes"] == {}

    def test_malformed_node_timestamp_skipped(self, extractor):
        result = extractor.extract_timings(
            {
                "execution_id": "x",
                "started_at": 1000,
                "completed_at": 1010,
                "results": [
                    {
                        "action": {"label": "bad"},
                        "started_at": "garbage",
                        "completed_at": 2000,
                        "status": "SUCCESS",
                    },
                    {
                        "action": {"label": "good"},
                        "started_at": 1000000,
                        "completed_at": 1002000,
                        "status": "SUCCESS",
                    },
                ],
            }
        )
        assert "bad" not in result["nodes"]
        assert "good" in result["nodes"]
