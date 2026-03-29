# Monitoring & Observability

## What we monitor

| Metric | What it tells you | Alert threshold |
| --- | --- | --- |
| **Request latency (p95)** | How fast the API responds | > 5 seconds |
| **Error rate** | Percentage of failed requests | > 5% |
| **Token usage** | Cost tracking | > 10K tokens/day |
| **Retrieval quality** | Are the right chunks being found? | Average score < 0.5 |
| **Document count** | How many documents are indexed | N/A (informational) |
| **Uptime** | Is the app running? | < 99% |

## How metrics are collected

The `MetricsCollector` class (`src/monitoring/metrics.py`) tracks:

- Every chat request: latency, tokens, success/failure
- Every document ingestion: chunk count
- Running totals and percentiles

Access metrics via: `GET /api/health` (includes basic metrics).

## AWS Monitoring (CloudWatch)

| Feature | How to set up |
| --- | --- |
| **Logs** | ECS tasks automatically send stdout to CloudWatch Logs |
| **Metrics** | Use `boto3` to publish custom metrics |
| **Dashboard** | AWS Console → CloudWatch → Dashboards → Create |
| **Alarms** | CloudWatch → Alarms → Create alarm → Select metric → Set threshold |

## Azure Monitoring (App Insights)

| Feature | How to set up |
| --- | --- |
| **Logs** | Container Apps automatically send to Log Analytics |
| **Metrics** | Use OpenTelemetry SDK to export custom metrics |
| **Dashboard** | Azure Portal → Monitor → Workbooks → Create |
| **Alerts** | Azure Monitor → Alerts → Create alert rule |

## OpenTelemetry Integration

The project uses OpenTelemetry for distributed tracing. Enable with `ENABLE_TRACING=true` in `.env`.

This adds trace IDs to every request, letting you follow a request through all services (API → RAG chain → LLM → vector store).
