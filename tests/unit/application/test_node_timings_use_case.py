#!/usr/bin/env python3
"""Unit tests for NodeTimingsUseCase.

Verifies the use case logic with lightweight in-memory fakes instead of
patching every collaborator. The ES client and node timing extractor are
replaced by simple stubs that record calls and return deterministic
data.
"""

from __future__ import annotations

from soar_lab.application.use_cases.node_timings import (
    DEFAULT_ANALYTICS_SEARCH_SIZE,
    METRICS_INDEX,
    NodeTimingsUseCase,
)


class FakeESClient:
    """Minimal ES client stub that returns canned search results."""

    def __init__(self, search_result: dict | None = None) -> None:
        self._search_result = search_result or {"hits": {"hits": []}}
        self.calls: list[dict] = []

    def search(self, *, query: dict, index: str, size: int) -> dict:
        self.calls.append({"query": query, "index": index, "size": size})
        return self._search_result


_MISSING = object()


class FakeExtractor:
    """Stub node timing extractor returning deterministic per-execution
    data."""

    def __init__(self, result: dict | None = _MISSING) -> None:
        self._result: dict | None = (
            {"execution_id": "exec-1", "nodes": {}} if result is _MISSING else result
        )
        self.calls: list[tuple[str, str]] = []

    def process_execution(self, execution_id: str, alert_id: str = "") -> dict | None:
        self.calls.append((execution_id, alert_id))
        return self._result


class TestGetExecution:
    """Tests for NodeTimingsUseCase.get_execution."""

    def test_returns_extractor_result(self):
        extractor = FakeExtractor(result={"execution_id": "exec-1", "nodes": {"n1": {}}})
        uc = NodeTimingsUseCase(es_client=FakeESClient(), node_timing_extractor=extractor)

        result = uc.get_execution("exec-1")

        assert result == {"execution_id": "exec-1", "nodes": {"n1": {}}}
        assert extractor.calls == [("exec-1", "")]

    def test_alert_id_propagated(self):
        extractor = FakeExtractor()
        uc = NodeTimingsUseCase(es_client=FakeESClient(), node_timing_extractor=extractor)

        uc.get_execution("exec-2", alert_id="alert-99")

        assert extractor.calls == [("exec-2", "alert-99")]

    def test_returns_none_when_extractor_returns_none(self):
        extractor = FakeExtractor(result=None)  # type: ignore[arg-type]
        uc = NodeTimingsUseCase(es_client=FakeESClient(), node_timing_extractor=extractor)

        result = uc.get_execution("missing")

        assert result is None


class TestGetAggregated:
    """Tests for NodeTimingsUseCase.get_aggregated."""

    def test_empty_results(self):
        es = FakeESClient(search_result={"hits": {"hits": []}})
        uc = NodeTimingsUseCase(es_client=es, node_timing_extractor=FakeExtractor())

        result = uc.get_aggregated(hours=1)

        assert result["period_hours"] == 1
        assert result["total_executions"] == 0
        assert result["executions"] == []
        assert "timestamp" in result

    def test_with_hits_extracts_fields(self):
        es = FakeESClient(
            search_result={
                "hits": {
                    "hits": [
                        {
                            "_source": {
                                "alert_id": "alert-1",
                                "execution_id": "exec-1",
                                "workflow_duration_s": 45.0,
                                "total_nodes": 5,
                                "slowest_nodes": [{"name": "enrich", "duration_s": 10}],
                                "nodes": {"enrich": {"duration_s": 10}},
                            }
                        },
                        {
                            "_source": {
                                "alert_id": "alert-2",
                                "execution_id": "exec-2",
                                "workflow_duration_s": 90.0,
                                "total_nodes": 3,
                                "slowest_nodes": [],
                                "nodes": {},
                            }
                        },
                    ]
                }
            }
        )
        uc = NodeTimingsUseCase(es_client=es, node_timing_extractor=FakeExtractor())

        result = uc.get_aggregated(hours=2)

        assert result["period_hours"] == 2
        assert result["total_executions"] == 2
        assert len(result["executions"]) == 2
        assert result["executions"][0]["alert_id"] == "alert-1"
        assert result["executions"][0]["execution_id"] == "exec-1"
        assert result["executions"][0]["workflow_duration_s"] == 45.0
        assert result["executions"][0]["total_nodes"] == 5
        assert result["executions"][1]["alert_id"] == "alert-2"

    def test_missing_source_fields_use_defaults(self):
        es = FakeESClient(search_result={"hits": {"hits": [{"_source": {}}]}})
        uc = NodeTimingsUseCase(es_client=es, node_timing_extractor=FakeExtractor())

        result = uc.get_aggregated()

        assert result["total_executions"] == 1
        assert result["executions"][0]["alert_id"] == ""
        assert result["executions"][0]["execution_id"] == ""
        assert result["executions"][0]["workflow_duration_s"] == 0
        assert result["executions"][0]["total_nodes"] == 0
        assert result["executions"][0]["slowest_nodes"] == []
        assert result["executions"][0]["nodes"] == {}

    def test_hit_without_source(self):
        es = FakeESClient(search_result={"hits": {"hits": [{"_id": "doc1"}]}})
        uc = NodeTimingsUseCase(es_client=es, node_timing_extractor=FakeExtractor())

        result = uc.get_aggregated()

        assert result["total_executions"] == 1
        assert result["executions"][0]["alert_id"] == ""

    def test_uses_correct_index_and_size(self):
        es = FakeESClient()
        uc = NodeTimingsUseCase(es_client=es, node_timing_extractor=FakeExtractor())

        uc.get_aggregated()

        assert len(es.calls) == 1
        assert es.calls[0]["index"] == METRICS_INDEX
        assert es.calls[0]["size"] == DEFAULT_ANALYTICS_SEARCH_SIZE

    def test_query_filters_by_metric_type_and_time_range(self):
        es = FakeESClient()
        uc = NodeTimingsUseCase(es_client=es, node_timing_extractor=FakeExtractor())

        uc.get_aggregated(hours=3)

        query = es.calls[0]["query"]
        assert query["bool"]["must"][0]["term"]["metric_type"] == "node_timings"
        time_filter = query["bool"]["filter"][0]["range"]["@timestamp"]
        assert "gte" in time_filter

    def test_empty_hits_key_handled(self):
        es = FakeESClient(search_result={})
        uc = NodeTimingsUseCase(es_client=es, node_timing_extractor=FakeExtractor())

        result = uc.get_aggregated()

        assert result["total_executions"] == 0
        assert result["executions"] == []
