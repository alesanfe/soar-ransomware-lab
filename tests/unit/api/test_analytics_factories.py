#!/usr/bin/env python3
"""Tests for the analytics route factories.

``create_aggregated_kpis_use_case`` / ``create_node_timings_use_case``
build real adapters (settings → config provider → ES client /
NodeTimingExtractor). Constructors must be side-effect-free (no network)
so the factory is callable in unit tests — that property is part of the
composition contract (ARC-001).
"""

from unittest.mock import Mock, patch

import soar_lab.interfaces.api.routes_analytics as ra
from soar_lab.application.use_cases.aggregated_kpis import AggregatedKpisUseCase
from soar_lab.application.use_cases.node_timings import NodeTimingsUseCase


class TestAggregatedKpisFactory:
    def test_factory_builds_use_case_with_wired_deps(self):
        with patch.object(ra, "ElasticsearchClient", Mock()):
            use_case = ra.create_aggregated_kpis_use_case()
        assert isinstance(use_case, AggregatedKpisUseCase)


class TestNodeTimingsFactory:
    def test_factory_injects_http_post_adapter(self):
        extractor_holder = {}

        class SpyExtractor(ra.NodeTimingExtractor):
            def __init__(self, **kw):
                extractor_holder.update(kw)
                super().__init__(**kw)

        with (
            patch.object(ra, "ElasticsearchClient", Mock()),
            patch.object(ra, "NodeTimingExtractor", SpyExtractor),
        ):
            use_case = ra.create_node_timings_use_case()

        assert isinstance(use_case, NodeTimingsUseCase)
        # ARC-001: the composition root wires a callable for HTTP POST —
        # the application layer never imports requests itself.
        assert callable(extractor_holder.get("http_post"))
