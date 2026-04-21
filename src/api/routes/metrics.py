"""
Metrics Route — Prometheus-compatible metrics endpoint.

Story I31: Exposes application metrics in Prometheus text format at /api/metrics.
This allows Prometheus/Grafana to scrape and visualize:

    - Chat request count, latency percentiles, error rate
    - Token usage (input, output, cost)
    - Document ingestion count
    - Query evaluation pass rate

Prometheus scrape config:
    - job_name: 'rag-chatbot'
      metrics_path: '/api/metrics'
      static_configs:
        - targets: ['localhost:8000']

DE parallel: This is like exposing Airflow metrics for Prometheus — same
pattern, same scraping, same Grafana dashboards.
"""

from fastapi import APIRouter, Request, Response
from loguru import logger

router = APIRouter()


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description=(
        "Returns application metrics in Prometheus text exposition format. "
        "Configure your Prometheus scraper to hit this endpoint."
    ),
    response_class=Response,
)
async def prometheus_metrics(request: Request) -> Response:
    """
    Export metrics in Prometheus text format.

    Reads from the in-memory MetricsCollector and formats as Prometheus gauges/counters.
    Also includes query log stats if available.
    """
    metrics = getattr(request.app.state, "metrics", None)
    query_logger = getattr(request.app.state, "query_logger", None)

    lines: list[str] = []

    # --- Chat metrics ---
    if metrics:
        summary = metrics.get_summary()
        chat = summary.get("chat", {})
        tokens = summary.get("tokens", {})
        docs = summary.get("documents", {})

        lines.extend([
            "# HELP rag_chat_requests_total Total chat requests processed.",
            "# TYPE rag_chat_requests_total counter",
            f'rag_chat_requests_total {chat.get("total_requests", 0)}',
            "",
            "# HELP rag_chat_errors_total Total chat request errors.",
            "# TYPE rag_chat_errors_total counter",
            f'rag_chat_errors_total {chat.get("total_errors", 0)}',
            "",
            "# HELP rag_chat_error_rate_percent Current error rate percentage.",
            "# TYPE rag_chat_error_rate_percent gauge",
            f'rag_chat_error_rate_percent {chat.get("error_rate", 0)}',
            "",
            "# HELP rag_chat_latency_p50_ms Chat latency 50th percentile in ms.",
            "# TYPE rag_chat_latency_p50_ms gauge",
            f'rag_chat_latency_p50_ms {chat.get("latency_p50_ms", 0)}',
            "",
            "# HELP rag_chat_latency_p95_ms Chat latency 95th percentile in ms.",
            "# TYPE rag_chat_latency_p95_ms gauge",
            f'rag_chat_latency_p95_ms {chat.get("latency_p95_ms", 0)}',
            "",
            "# HELP rag_chat_latency_p99_ms Chat latency 99th percentile in ms.",
            "# TYPE rag_chat_latency_p99_ms gauge",
            f'rag_chat_latency_p99_ms {chat.get("latency_p99_ms", 0)}',
            "",
            "# HELP rag_tokens_input_total Total input tokens consumed.",
            "# TYPE rag_tokens_input_total counter",
            f'rag_tokens_input_total {tokens.get("total_input", 0)}',
            "",
            "# HELP rag_tokens_output_total Total output tokens generated.",
            "# TYPE rag_tokens_output_total counter",
            f'rag_tokens_output_total {tokens.get("total_output", 0)}',
            "",
            "# HELP rag_tokens_cost_usd_total Estimated total cost in USD.",
            "# TYPE rag_tokens_cost_usd_total counter",
            f'rag_tokens_cost_usd_total {tokens.get("estimated_cost_usd", 0)}',
            "",
            "# HELP rag_documents_ingested_total Total documents ingested.",
            "# TYPE rag_documents_ingested_total counter",
            f'rag_documents_ingested_total {docs.get("total_ingested", 0)}',
            "",
            "# HELP rag_chunks_created_total Total chunks created.",
            "# TYPE rag_chunks_created_total counter",
            f'rag_chunks_created_total {docs.get("total_chunks", 0)}',
            "",
            "# HELP rag_uptime_seconds Application uptime in seconds.",
            "# TYPE rag_uptime_seconds gauge",
            f'rag_uptime_seconds {summary.get("uptime_seconds", 0)}',
        ])

    # --- Query evaluation metrics (from query logger) ---
    if query_logger:
        try:
            stats = await query_logger.get_stats(days=1)
            lines.extend([
                "",
                "# HELP rag_queries_total Total queries logged today.",
                "# TYPE rag_queries_total gauge",
                f'rag_queries_total {stats.get("total_queries", 0)}',
                "",
                "# HELP rag_queries_passed Queries that passed evaluation today.",
                "# TYPE rag_queries_passed gauge",
                f'rag_queries_passed {stats.get("passed", 0)}',
                "",
                "# HELP rag_queries_failed Queries that failed evaluation today.",
                "# TYPE rag_queries_failed gauge",
                f'rag_queries_failed {stats.get("failed", 0)}',
                "",
                "# HELP rag_queries_pass_rate_percent Evaluation pass rate today.",
                "# TYPE rag_queries_pass_rate_percent gauge",
                f'rag_queries_pass_rate_percent {stats.get("pass_rate", 0)}',
                "",
                "# HELP rag_queries_avg_retrieval Average retrieval score today.",
                "# TYPE rag_queries_avg_retrieval gauge",
                f'rag_queries_avg_retrieval {stats.get("avg_retrieval", 0)}',
                "",
                "# HELP rag_queries_avg_faithfulness Average faithfulness score today.",
                "# TYPE rag_queries_avg_faithfulness gauge",
                f'rag_queries_avg_faithfulness {stats.get("avg_faithfulness", 0)}',
                "",
                "# HELP rag_queries_avg_relevance Average answer relevance score today.",
                "# TYPE rag_queries_avg_relevance gauge",
                f'rag_queries_avg_relevance {stats.get("avg_relevance", 0)}',
            ])

            # Failure breakdown by category
            breakdown = stats.get("failure_breakdown", {})
            for category, count in breakdown.items():
                if category != "none":
                    lines.extend([
                        "",
                        f'# HELP rag_queries_failure_{category} Queries failing with {category} today.',
                        f'# TYPE rag_queries_failure_{category} gauge',
                        f'rag_queries_failure_{category} {count}',
                    ])
        except Exception as e:
            logger.warning(f"Failed to get query stats for metrics: {e}")

    lines.append("")  # trailing newline
    body = "\n".join(lines)

    return Response(
        content=body,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
