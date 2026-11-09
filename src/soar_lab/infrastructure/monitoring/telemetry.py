"""OpenTelemetry wiring for the SOAR API (O1).

When ``OTEL_ENABLED=1`` the app boots a TracerProvider exporting spans
over OTLP/HTTP to ``OTEL_EXPORTER_OTLP_ENDPOINT`` (any OTLP receiver —
Tempo, Jaeger, Grafana Alloy, otel-collector). FastAPI and the
``requests`` stack are auto-instrumented, which yields a real
distributed trace: ingest request → outbound calls to Shuffle, TheHive,
Cortex, MISP and Elasticsearch all appear as child spans, so MTTR can
be attributed per stage instead of only end-to-end.

Disabled by default — a lab run without an OTLP receiver must not pay
exporter overhead or emit connection errors.
"""

from typing import Any

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_AVAILABLE = True
except ImportError:
    # Stale images / minimal installs without the otel extras: the API
    # must still boot — init_telemetry() reports disabled instead of
    # crashing the whole service over an observability add-on.
    trace = OTLPSpanExporter = FastAPIInstrumentor = RequestsInstrumentor = None
    Resource = TracerProvider = BatchSpanProcessor = None
    OTEL_AVAILABLE = False


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def init_telemetry(app: Any, config_provider: Any) -> bool:
    """Enable OTel tracing on the FastAPI app when configured.

    Args:
        app: FastAPI application instance.
        config_provider: Resolves ``OTEL_ENABLED``,
            ``OTEL_EXPORTER_OTLP_ENDPOINT`` (default
            ``http://localhost:4318``) and ``OTEL_SERVICE_NAME``
            (default ``soar-api``).

    Returns:
        bool: ``True`` when instrumentation was installed.
    """
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry packages not installed — tracing unavailable")
        return False
    if not _truthy(config_provider.get("OTEL_ENABLED", "0")):
        logger.info("OpenTelemetry disabled (OTEL_ENABLED != 1)")
        return False

    endpoint = str(config_provider.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"))
    service_name = str(config_provider.get("OTEL_SERVICE_NAME", "soar-api"))

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces"))
    )
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    RequestsInstrumentor().instrument()
    app.state.otel_tracer_provider = provider
    logger.info("OpenTelemetry enabled service=%s exporter=%s", service_name, endpoint)
    return True


def shutdown_telemetry(app: Any) -> None:
    """Flush pending spans on app shutdown."""
    provider = getattr(app.state, "otel_tracer_provider", None)
    if provider is not None:
        provider.shutdown()
