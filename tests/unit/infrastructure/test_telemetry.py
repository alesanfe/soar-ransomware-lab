"""O1: telemetry init — disabled by default, instruments when enabled."""

from unittest.mock import Mock, patch

from soar_lab.infrastructure.monitoring.telemetry import init_telemetry


class CP:
    def __init__(self, values):
        self._v = values

    def get(self, k, d=None):
        return self._v.get(k, d)


class TestInitTelemetry:
    def test_disabled_by_default(self):
        assert init_telemetry(Mock(), CP({})) is False

    def test_enabled_instruments_app(self):
        app = Mock()
        app.state = Mock()
        with (
            patch("soar_lab.infrastructure.monitoring.telemetry.FastAPIInstrumentor") as fi,
            patch("soar_lab.infrastructure.monitoring.telemetry.RequestsInstrumentor") as ri,
        ):
            ok = init_telemetry(app, CP({"OTEL_ENABLED": "1"}))
        assert ok is True
        fi.instrument_app.assert_called_once_with(app)
        ri.return_value.instrument.assert_called_once()

    def test_exporter_endpoint_from_config(self):
        app = Mock()
        app.state = Mock()
        with (
            patch("soar_lab.infrastructure.monitoring.telemetry.OTLPSpanExporter") as exp,
            patch("soar_lab.infrastructure.monitoring.telemetry.FastAPIInstrumentor"),
            patch("soar_lab.infrastructure.monitoring.telemetry.RequestsInstrumentor"),
        ):
            init_telemetry(
                app,
                CP({"OTEL_ENABLED": "1", "OTEL_EXPORTER_OTLP_ENDPOINT": "http://tempo:4318/"}),
            )
        exp.assert_called_once_with(endpoint="http://tempo:4318/v1/traces")


class TestTelemetryEdges:
    """OTEL_AVAILABLE=False fallback + shutdown flush (lines 57-59, 80-84)."""

    def test_unavailable_packages_warns_and_disables(self, caplog):
        import logging

        import soar_lab.infrastructure.monitoring.telemetry as tel

        with patch.object(tel, "OTEL_AVAILABLE", False):
            with caplog.at_level(logging.WARNING):
                assert init_telemetry(Mock(), CP({"OTEL_ENABLED": "1"})) is False
        assert "not installed" in caplog.text

    def test_shutdown_without_provider_noop(self):
        from soar_lab.infrastructure.monitoring.telemetry import shutdown_telemetry

        app = Mock()
        app.state = Mock(spec=[])  # no otel_tracer_provider attr
        shutdown_telemetry(app)  # must not raise

    def test_shutdown_flushes_provider(self):
        from soar_lab.infrastructure.monitoring.telemetry import shutdown_telemetry

        provider = Mock()
        app = Mock()
        app.state = Mock()
        app.state.otel_tracer_provider = provider
        shutdown_telemetry(app)
        provider.shutdown.assert_called_once()
