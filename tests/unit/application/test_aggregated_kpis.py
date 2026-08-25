#!/usr/bin/env python3
"""Unit tests for AggregatedKpisUseCase.

Verifies the use case logic with lightweight in-memory fakes instead of
patching every collaborator. The ES client, KPI analyzer and statistical
calculator are replaced by simple stubs that record calls and return
deterministic data.
"""

from __future__ import annotations

from soar_lab.application.use_cases.aggregated_kpis import (
    DEFAULT_KPI_SEARCH_SIZE,
    METRICS_INDEX,
    AggregatedKpisUseCase,
)


class FakeESClient:
    """Minimal ES client stub that returns canned documents."""

    def __init__(self, documents: list[dict] | None = None) -> None:
        self._documents = documents or []
        self.calls: list[dict] = []

    def get_latest_documents(self, *, size: int, index: str) -> list[dict]:
        self.calls.append({"size": size, "index": index})
        return self._documents


class FakeKPIAnalyzer:
    """Stub KPI analyzer returning deterministic aggregations."""

    def __init__(
        self,
        by_alert_type: dict | None = None,
        services: dict | None = None,
    ) -> None:
        self._by_alert_type = by_alert_type or {"by_alert_type": {"malicious": 5}}
        self._services = services or {"services": {"shuffle": 3}}
        self.calls: list[str] = []

    def calculate_kpis_by_alert_type(self, data: list[dict], hours: int) -> dict:
        self.calls.append(f"by_alert_type:{hours}")
        return self._by_alert_type

    def calculate_service_integration_kpis(self, data: list[dict], hours: int) -> dict:
        self.calls.append(f"services:{hours}")
        return self._services


class FakeStatisticalCalculator:
    """Stub statistical calculator returning fixed MTTR stats."""

    def __init__(self, stats: dict | None = None) -> None:
        self._stats = stats or {"mean": 120.0, "median": 100.0}
        self.calls: list[list[float]] = []

    def calculate_statistical_metrics(self, values: list[float]) -> dict:
        self.calls.append(values)
        return self._stats


class TestAggregatedKpisExecute:
    """Tests for AggregatedKpisUseCase.execute."""

    def test_empty_metrics_returns_defaults(self):
        es = FakeESClient(documents=[])
        uc = AggregatedKpisUseCase(
            es_client=es,
            kpi_analyzer=FakeKPIAnalyzer(),
            statistical_calculator=FakeStatisticalCalculator(),
        )

        result = uc.execute(hours=24)

        assert result["period_hours"] == 24
        assert result["total_alerts"] == 0
        assert result["by_alert_type"] == {}
        assert result["services"] == {}
        assert "mttr_statistics" not in result or result["mttr_statistics"] == {}
        assert "timestamp" in result

    def test_uses_default_search_size_and_index(self):
        es = FakeESClient(documents=[])
        uc = AggregatedKpisUseCase(
            es_client=es,
            kpi_analyzer=FakeKPIAnalyzer(),
            statistical_calculator=FakeStatisticalCalculator(),
        )

        uc.execute()

        assert len(es.calls) == 1
        assert es.calls[0]["size"] == DEFAULT_KPI_SEARCH_SIZE
        assert es.calls[0]["index"] == METRICS_INDEX

    def test_with_metrics_invokes_analyzers(self):
        documents = [
            {"mttr_seconds": 60, "alert_type": "malicious"},
            {"mttr_seconds": 180, "alert_type": "benign"},
        ]
        es = FakeESClient(documents=documents)
        analyzer = FakeKPIAnalyzer(
            by_alert_type={"by_alert_type": {"malicious": 1, "benign": 1}},
            services={"services": {"shuffle": 2}},
        )
        stat_calc = FakeStatisticalCalculator(stats={"mean": 120.0})
        uc = AggregatedKpisUseCase(
            es_client=es,
            kpi_analyzer=analyzer,
            statistical_calculator=stat_calc,
        )

        result = uc.execute(hours=12)

        assert result["total_alerts"] == 2
        assert result["by_alert_type"] == {"malicious": 1, "benign": 1}
        assert result["services"] == {"shuffle": 2}
        assert result["mttr_statistics"] == {"mean": 120.0}
        assert result["period_hours"] == 12
        assert "by_alert_type:12" in analyzer.calls
        assert "services:12" in analyzer.calls

    def test_no_mttr_values_returns_empty_stats(self):
        documents = [{"alert_type": "malicious"}]  # no mttr_seconds field
        es = FakeESClient(documents=documents)
        stat_calc = FakeStatisticalCalculator()
        uc = AggregatedKpisUseCase(
            es_client=es,
            kpi_analyzer=FakeKPIAnalyzer(),
            statistical_calculator=stat_calc,
        )

        result = uc.execute()

        assert result["mttr_statistics"] == {}
        assert stat_calc.calls == []  # not invoked when no MTTR values

    def test_hours_parameter_propagated_to_analyzers(self):
        es = FakeESClient(documents=[{"mttr_seconds": 60}])
        analyzer = FakeKPIAnalyzer()
        uc = AggregatedKpisUseCase(
            es_client=es,
            kpi_analyzer=analyzer,
            statistical_calculator=FakeStatisticalCalculator(),
        )

        uc.execute(hours=48)

        assert "by_alert_type:48" in analyzer.calls
        assert "services:48" in analyzer.calls


class TestExtractMttrValues:
    """Tests for the static _extract_mttr_values helper."""

    def test_numeric_mttr(self):
        data = [{"mttr_seconds": 60}, {"mttr_seconds": 120.5}]
        result = AggregatedKpisUseCase._extract_mttr_values(data)
        assert result == [60, 120.5]

    def test_dict_mttr_with_message(self):
        data = [
            {"mttr_seconds": {"message": "MTTR: 90s"}},
            {"mttr_seconds": {"message": "MTTR: 45s"}},
        ]
        result = AggregatedKpisUseCase._extract_mttr_values(data)
        assert result == [90.0, 45.0]

    def test_dict_mttr_without_mttr_keyword(self):
        data = [{"mttr_seconds": {"message": "some other text"}}]
        result = AggregatedKpisUseCase._extract_mttr_values(data)
        assert result == []

    def test_mixed_numeric_and_dict(self):
        data = [
            {"mttr_seconds": 30},
            {"mttr_seconds": {"message": "MTTR: 60s"}},
            {"mttr_seconds": "invalid"},
        ]
        result = AggregatedKpisUseCase._extract_mttr_values(data)
        assert result == [30, 60.0]

    def test_missing_mttr_field(self):
        data = [{"other": "value"}]
        result = AggregatedKpisUseCase._extract_mttr_values(data)
        assert result == []

    def test_empty_list(self):
        result = AggregatedKpisUseCase._extract_mttr_values([])
        assert result == []

    def test_malformed_dict_mttr_ignored(self):
        data = [{"mttr_seconds": {"message": "MTTR: abc s"}}]  # non-numeric
        result = AggregatedKpisUseCase._extract_mttr_values(data)
        assert result == []
