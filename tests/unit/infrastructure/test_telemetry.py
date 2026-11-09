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
