"""
Metrics Collector — Custom application metrics.

Tracks:
    - Chat request count, latency, errors
    - Token usage (input, output, cost)
    - Document ingestion count
    - Vector store query latency

These metrics can be exported to:
    - CloudWatch (AWS)
    - App Insights (Azure)
    - Prometheus (self-hosted)
    - Console logs (development)

See docs/monitoring.md for dashboards and alerting setup.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from loguru import logger


@dataclass
class MetricPoint:
    """A single metric measurement."""

    name: str
    value: float
    timestamp: datetime
    tags: dict = field(default_factory=dict)


class MetricsCollector:
    """
    In-memory metrics collector.

    In production, this would push to CloudWatch/App Insights.
    For local development, metrics are available via the /api/metrics endpoint.

    Usage:
        metrics = MetricsCollector()
        metrics.record_chat_request(latency_ms=150, token_usage=usage)
        summary = metrics.get_summary()
    """

    def __init__(self):
        self._chat_requests: int = 0
        self._chat_errors: int = 0
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0
        self._total_estimated_cost: float = 0.0
        self._latencies: list[int] = []
        self._documents_ingested: int = 0
        self._chunks_created: int = 0
        self._start_time = datetime.now(timezone.utc)

    def record_chat_request(self, latency_ms: int, token_usage=None):
        """Record a successful chat request."""
        self._chat_requests += 1
        self._latencies.append(latency_ms)

        if token_usage:
            self._total_input_tokens += token_usage.input_tokens
            self._total_output_tokens += token_usage.output_tokens
            self._total_estimated_cost += token_usage.estimated_cost_usd

    def record_chat_error(self):
        """Record a failed chat request."""
        self._chat_errors += 1

    def record_document_ingestion(self, chunk_count: int):
        """Record a document ingestion."""
        self._documents_ingested += 1
        self._chunks_created += chunk_count

    def get_summary(self) -> dict:
        """
        Get a summary of all metrics.

        Returns a dict suitable for JSON serialization.
        """
        sorted_latencies = sorted(self._latencies) if self._latencies else [0]

        return {
            "uptime_seconds": int((datetime.now(timezone.utc) - self._start_time).total_seconds()),
            "chat": {
                "total_requests": self._chat_requests,
                "total_errors": self._chat_errors,
                "error_rate": (
                    round(self._chat_errors / max(self._chat_requests, 1) * 100, 2)
                ),
                "latency_p50_ms": sorted_latencies[len(sorted_latencies) // 2],
                "latency_p95_ms": sorted_latencies[int(len(sorted_latencies) * 0.95)],
                "latency_p99_ms": sorted_latencies[int(len(sorted_latencies) * 0.99)],
            },
            "tokens": {
                "total_input": self._total_input_tokens,
                "total_output": self._total_output_tokens,
                "total": self._total_input_tokens + self._total_output_tokens,
                "estimated_cost_usd": round(self._total_estimated_cost, 4),
            },
            "documents": {
                "total_ingested": self._documents_ingested,
                "total_chunks": self._chunks_created,
            },
        }
