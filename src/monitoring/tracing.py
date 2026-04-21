"""
OpenTelemetry Setup — Distributed tracing and instrumentation.

Story I31: Wires up the OTel packages that were already in pyproject.toml
but never initialized. Provides:

    1. TracerProvider with OTLP exporter (sends traces to Jaeger/Tempo/etc.)
    2. FastAPI auto-instrumentation (every request becomes a span)
    3. Custom span helpers for RAG-specific operations

When ENABLE_TRACING=false (default), this module is a no-op.
When ENABLE_TRACING=true + OTEL_EXPORTER_OTLP_ENDPOINT is set, full tracing activates.

DE parallel: This is like enabling Airflow's OpenLineage integration —
every task/step becomes a span in a trace, so you can see the full DAG
execution in Jaeger the same way you'd see it in the Airflow UI.
"""

from __future__ import annotations

from fastapi import FastAPI
from loguru import logger

from src.config import Settings


def setup_tracing(app: FastAPI, settings: Settings) -> None:
    """
    Initialize OpenTelemetry tracing if enabled.

    This is called once at app startup from main.py lifespan.
    If tracing is disabled, this function does nothing.

    Args:
        app: The FastAPI application to instrument.
        settings: Application settings with OTel config.
    """
    if not settings.enable_tracing:
        logger.info("OpenTelemetry tracing disabled (ENABLE_TRACING=false)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Create a resource that identifies this service in traces
        resource = Resource.create(
            {
                "service.name": settings.otel_service_name,
                "service.version": "0.1.0",
                "deployment.environment": settings.app_env.value,
                "cloud.provider": settings.cloud_provider.value,
            }
        )

        # Create the tracer provider
        provider = TracerProvider(resource=resource)

        # Add OTLP exporter if endpoint is configured
        if settings.otel_exporter_otlp_endpoint:
            exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info(f"OTLP exporter configured → {settings.otel_exporter_otlp_endpoint}")
        else:
            logger.warning("Tracing enabled but OTEL_EXPORTER_OTLP_ENDPOINT not set — traces won't be exported")

        # Set as global tracer provider
        trace.set_tracer_provider(provider)

        # Auto-instrument FastAPI — every request becomes a span
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=provider,
            excluded_urls="health,docs,redoc,openapi.json,metrics",
        )

        logger.info(
            f"OpenTelemetry tracing initialized — service={settings.otel_service_name}, "
            f"env={settings.app_env.value}"
        )

    except ImportError as e:
        logger.warning(f"OpenTelemetry packages not installed — tracing disabled: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
