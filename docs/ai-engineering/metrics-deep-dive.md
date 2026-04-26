# Deep Dive: Metrics & Monitoring — `src/monitoring/metrics.py`

> **Study order:** #16 · **Difficulty:** ★★★☆☆ (familiar patterns — the new concept is what AI-specific metrics to track)  
>
> **File:** [`src/monitoring/metrics.py`](../../src/monitoring/metrics.py)  
>
> **Prerequisite:** [#14 — Evaluation Framework](evaluation-framework-deep-dive.md) · [#13 — RAG Chain](rag-chain-deep-dive.md)  
>
> **Part of:** [Architecture Overview](../architecture-and-design/architecture.md)

---

## Table of Contents

1. [Why This File Matters](#why-this-file-matters)
2. [DE Parallel — Metrics Are Pipeline Observability](#de-parallel--metrics-are-pipeline-observability)
3. [Architecture Overview](#architecture-overview)
4. [The `MetricPoint` Dataclass](#the-metricpoint-dataclass)
5. [The `MetricsCollector` Class](#the-metricscollector-class)
6. [Recording Chat Requests](#recording-chat-requests)
7. [Recording Errors](#recording-errors)
8. [Recording Document Ingestion](#recording-document-ingestion)
9. [The Summary Endpoint — `get_summary()`](#the-summary-endpoint--get_summary)
10. [Percentile Calculations — P50, P95, P99](#percentile-calculations)
11. [How Metrics Flow Through the Application](#how-metrics-flow-through-the-application)
12. [Cloud vs Local — Export Targets](#cloud-vs-local--export-targets)
13. [AI-Specific Metrics — What to Watch](#ai-specific-metrics--what-to-watch)
14. [Self-Test Questions](#self-test-questions)
15. [What to Study Next](#what-to-study-next)

---

## Why This File Matters

In data engineering, you monitor pipeline runs, row counts, and job durations. In AI engineering, you monitor **the same things** plus AI-specific metrics: token usage, response latency, estimated cost, and quality scores. This file is the central metrics collector — every route records metrics through it.

| What you'll learn | DE parallel | 🚚 Courier |
|---|---| --- |
| Request counting and error rates | Pipeline run counts and failure rates | Mechanical groom — Request counting and error rates: Pipeline run counts and failure rates |
| Latency tracking (P50/P95/P99) | Job duration monitoring | Stopwatch on the courier's harness — Latency tracking (P50/P95/P99): Job duration monitoring |
| Token usage tracking | Row count / byte count tracking | Tracks how many fuel loads (tokens) the courier consumed per trip — key for cost monitoring |
| Cost estimation per request | Cloud cost per pipeline run | What the depot charges this month — Cost estimation per request: Cloud cost per pipeline run |
| In-memory metrics collection | StatsD / Prometheus client | Courier's odometer dial — In-memory metrics collection: StatsD / Prometheus client |

- 🚚 **Courier:** Think of this as the orientation briefing given to a new courier before its first delivery run — it sets the context for everything that follows.

---

## DE Parallel — Metrics Are Pipeline Observability

```
DATA ENGINEER                              AI ENGINEER
────────────────                           ──────────────
Pipeline monitoring:                       RAG monitoring:
  runs_total: 1523                           chat_requests_total: 1523
  runs_failed: 12                            chat_errors_total: 12
  avg_duration: 45s                          p50_latency: 1200ms
  p99_duration: 180s                         p99_latency: 4500ms
  rows_processed: 2.1M                       tokens_used: 1.2M
  data_freshness: 5min                       documents_ingested: 847
  ──────                                     estimated_cost: $9.87
  cost_per_run: $0.02                        cost_per_query: $0.0065

Monitored via:                             Monitored via:
  CloudWatch / Datadog / Grafana             GET /health (this file's output)
```

- 🚚 **Courier:** The tachograph reading — every delivery time, token cost, and quality score recorded for review.

---

## Architecture Overview

```
src/monitoring/metrics.py
│
├── MetricPoint (dataclass)        ← Single measurement
│     name: str
│     value: float
│     timestamp: datetime
│     tags: dict[str, str]
│
└── MetricsCollector (class)       ← Aggregates all measurements
      _start_time: datetime        ← When app started
      _chat_requests: int          ← Total chat queries
      _chat_errors: int            ← Total errors
      _total_input_tokens: int     ← Cumulative input tokens
      _total_output_tokens: int    ← Cumulative output tokens
      _total_estimated_cost: float ← Cumulative cost ($)
      _latencies: list[float]      ← All request latencies (for percentiles)
      _documents_ingested: int     ← Total docs uploaded
      _chunks_created: int         ← Total chunks stored
      │
      ├── record_chat_request()    ← Called after every successful chat
      ├── record_chat_error()      ← Called after every failed chat
      ├── record_document_ingestion() ← Called after every document upload
      └── get_summary()            ← Called by GET /health
```

- 🚚 **Courier:** Like a depot floor plan showing where the courier enters, where the parcels are loaded, and which route it takes to the customer.

---

## The `MetricPoint` Dataclass

```python
@dataclass
class MetricPoint:
    """A single metric measurement."""
    name: str                          # e.g., "chat_latency_ms"
    value: float                       # e.g., 1234.5
    timestamp: datetime = field(       # When it was recorded
        default_factory=datetime.utcnow
    )
    tags: dict[str, str] = field(      # Optional metadata
        default_factory=dict
    )
```

**DE parallel:** This is a single row in a metrics table:

```sql
CREATE TABLE metrics (
    name VARCHAR(100),       -- metric name
    value FLOAT,             -- measurement
    timestamp TIMESTAMP,     -- when
    tags JSONB               -- dimensions
);
```

**In practice,** `MetricPoint` isn't heavily used in this codebase — the `MetricsCollector` aggregates directly. But the dataclass exists for future export to external systems (CloudWatch, Application Insights, Prometheus).

- 🚚 **Courier:** The tachograph reading — every delivery time, token cost, and quality score recorded for review.

---

## The `MetricsCollector` Class

```python
class MetricsCollector:
    """Collects and aggregates application metrics in-memory."""

    def __init__(self):
        self._start_time = datetime.utcnow()
        self._chat_requests: int = 0
        self._chat_errors: int = 0
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0
        self._total_estimated_cost: float = 0.0
        self._latencies: list[float] = []
        self._documents_ingested: int = 0
        self._chunks_created: int = 0
```

**Key design decision: in-memory.** All metrics are stored in Python variables. If the app restarts, metrics reset to zero. This is acceptable for a single-instance app but would need Redis/DynamoDB for multi-instance deployments.

**DE parallel:** This is like keeping counters in a Python script vs writing to a database:

```python
# In-memory (this file)          # Persistent (production)
rows_processed += 1              cursor.execute("UPDATE metrics SET count = count + 1")
```

- 🚚 **Courier:** The tachograph reading — every delivery time, token cost, and quality score recorded for review.

---

## Recording Chat Requests

```python
def record_chat_request(
    self, latency_ms: float, token_usage: dict
) -> None:
    """Record a successful chat request."""
    self._chat_requests += 1
    self._latencies.append(latency_ms)
    self._total_input_tokens += token_usage.get("input_tokens", 0)
    self._total_output_tokens += token_usage.get("output_tokens", 0)
    self._total_estimated_cost += token_usage.get("estimated_cost", 0.0)
```

**Called from the chat route after every successful response:**

```python
# In routes/chat.py (simplified)
start = time.time()
result = await chain.query(question)
latency = (time.time() - start) * 1000  # Convert to ms

metrics.record_chat_request(
    latency_ms=latency,
    token_usage=result["token_usage"],  # {input_tokens, output_tokens, estimated_cost}
)
```

**What gets tracked:**

| Counter | What it measures | Why it matters | 🚚 Courier |
|---|---|---| --- |
| `_chat_requests` | Total queries served | Throughput — are people using the system? | Courier-hire fee — _chat_requests: Total queries served · Throughput — are people using the system? |
| `_latencies` | Response time in ms | UX — are responses fast enough? | Tachograph reading — how long the courier took on the round trip |
| `_total_input_tokens` | Cumulative tokens sent to LLM | Cost driver — input tokens are cheaper | fuel loaded onto the courier on the way out — cheaper per bale, but it adds up across every trip |
| `_total_output_tokens` | Cumulative tokens received from LLM | Cost driver — output tokens are 3-5x more expensive | fuel the courier burns writing the reply — 3–5x pricier than input fuel, so verbose answers hurt the budget |
| `_total_estimated_cost` | Running cost total | Budget tracking — are we within SLA? | Depot's monthly feed bill — _total_estimated_cost: Running cost total · Budget tracking — are we within SLA? |

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Recording Errors

```python
def record_chat_error(self) -> None:
    """Record a failed chat request."""
    self._chat_errors += 1
```

**Simple but critical.** The error rate is:

```
error_rate = _chat_errors / _chat_requests
```

| Error rate | Status | Action | 🚚 Courier |
|---|---|---| --- |
| < 1% | ✅ Healthy | Normal operation | Under 1% failed deliveries means the courier is healthy and completing almost every trip |
| 1-5% | ⚠️ Warning | Investigate — LLM timeouts? | Courier is stumbling on a few trips — check whether the LLM is timing out or the parcel is arriving empty |
| > 5% | 🔴 Critical | Page on-call — system is degraded | Courier-side view of > 5% — affects how the courier loads, reads, or delivers the parcels |

**DE parallel:** Same as pipeline failure rate. If more than 5% of Airflow DAG runs fail, something is wrong.

- 🚚 **Courier:** When the courier returns empty-hooved — use the trip log and bag inspection checklist to find what went wrong.

---

## Recording Document Ingestion

```python
def record_document_ingestion(self, chunk_count: int) -> None:
    """Record a document ingestion."""
    self._documents_ingested += 1
    self._chunks_created += chunk_count
```

**Tracks the write path.** If a user uploads a 50-page PDF that produces 200 chunks:

```python
metrics.record_document_ingestion(chunk_count=200)
# _documents_ingested: 1 → 2
# _chunks_created: 500 → 700
```

**Why track chunk count?** Because it directly correlates to vector store size and search performance. 10,000 chunks search faster than 1,000,000 chunks.

- 🚚 **Courier:** Post office pre-sorting: mail is split into parcel-sized chunks, stamped with GPS coordinates (embeddings), and shelved in the warehouse before the courier ever arrives.

---

## The Summary Endpoint — `get_summary()`

This is the method called by `GET /health` to return the full metrics snapshot:

```python
def get_summary(self) -> dict:
    """Return a summary of all collected metrics."""
    uptime = (datetime.utcnow() - self._start_time).total_seconds()

    return {
        "uptime_seconds": round(uptime, 1),
        "chat": {
            "total_requests": self._chat_requests,
            "total_errors": self._chat_errors,
            "error_rate": round(
                self._chat_errors / max(self._chat_requests, 1), 4
            ),
            "latency_p50_ms": self._percentile(50),
            "latency_p95_ms": self._percentile(95),
            "latency_p99_ms": self._percentile(99),
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
```

**Example output (after 100 queries, 5 documents):**

```json
{
    "uptime_seconds": 3600.0,
    "chat": {
        "total_requests": 100,
        "total_errors": 2,
        "error_rate": 0.02,
        "latency_p50_ms": 1200.0,
        "latency_p95_ms": 3500.0,
        "latency_p99_ms": 5200.0
    },
    "tokens": {
        "total_input": 84500,
        "total_output": 20000,
        "total": 104500,
        "estimated_cost_usd": 0.5535
    },
    "documents": {
        "total_ingested": 5,
        "total_chunks": 847
    }
}
```

- 🚚 **Courier:** The specific delivery address the courier is dispatched to — each route handles a different type of parcels drop-off.

---

## Percentile Calculations

```python
def _percentile(self, p: int) -> float:
    """Calculate the p-th percentile of latencies."""
    if not self._latencies:
        return 0.0

    sorted_latencies = sorted(self._latencies)
    index = int(len(sorted_latencies) * p / 100)
    index = min(index, len(sorted_latencies) - 1)

    return round(sorted_latencies[index], 1)
```

**Why P50/P95/P99?**

```
P50 (median):  What most users experience        → 1200ms
P95:           What 1 in 20 users experience      → 3500ms
P99:           What 1 in 100 users experience     → 5200ms

If P50 is good but P99 is terrible:
  → Most users are happy, but some have a bad experience
  → Common cause: cold starts, large documents, complex questions
```

**DE parallel:**

```sql
-- You've written this exact pattern before
SELECT
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration) AS p50,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration) AS p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration) AS p99
FROM pipeline_runs;
```

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## How Metrics Flow Through the Application

```
User request
     │
     ▼
 POST /chat ──────────────────────────── POST /documents
     │                                        │
     ▼                                        ▼
 chain.query()                           chain.ingest_document()
     │                                        │
     ▼                                        ▼
 result = {answer, sources, token_usage} chunk_count = 200
     │                                        │
     ▼                                        ▼
 metrics.record_chat_request(            metrics.record_document_ingestion(
   latency_ms=1200,                        chunk_count=200
   token_usage={                          )
     input_tokens: 845,
     output_tokens: 200,
     estimated_cost: 0.0055
   }
 )
     │                                        │
     ▼────────────────┬───────────────────────┘
                      │
                 GET /health
                      │
                      ▼
              metrics.get_summary()
                      │
                      ▼
              JSON response to monitoring dashboard
```

**The metrics collector is a singleton** stored in `app.state.metrics` — all routes share the same instance. This is the dependency injection pattern used throughout the app:

```python
# In main.py
app.state.metrics = MetricsCollector()

# In any route
metrics = request.app.state.metrics
metrics.record_chat_request(...)
```

- 🚚 **Courier:** The tachograph reading — every delivery time, token cost, and quality score recorded for review.

---

## Cloud vs Local — Export Targets

The `MetricsCollector` stores metrics in-memory. To make them persistent, you'd export to an external system:

| Provider | Export target | How | Cost | 🚚 Courier |
|---|---|---|---| --- |
| **AWS** | CloudWatch Metrics | `boto3.client('cloudwatch').put_metric_data()` | ~$0.30/metric/month | Ship the tachograph readings to CloudWatch via boto3 — roughly 30¢ per metric per month. |
| **Azure** | Application Insights | `opencensus` or `azure-monitor-opentelemetry` | ~$2.30/GB ingested | Ship tachograph readings to Application Insights via OpenTelemetry — billed by the gigabyte of trip logs ingested. |
| **Local** | Console / Prometheus | `print()` or Prometheus client library | **$0** | Courier's odometer dial — Local: Console / Prometheus · print() or Prometheus client library · $0 |

### 🏠 Local development — console export

```python
# Simple: check GET /health via Swagger UI or browser
# Open http://localhost:8000/health in your browser
```

### AWS — CloudWatch export (future)

```python
import boto3

cloudwatch = boto3.client('cloudwatch', region_name='eu-west-1')

def export_to_cloudwatch(summary: dict):
    cloudwatch.put_metric_data(
        Namespace='RAGChatbot',
        MetricData=[
            {'MetricName': 'ChatRequests', 'Value': summary['chat']['total_requests']},
            {'MetricName': 'ChatErrors', 'Value': summary['chat']['total_errors']},
            {'MetricName': 'LatencyP99', 'Value': summary['chat']['latency_p99_ms']},
            {'MetricName': 'EstimatedCostUSD', 'Value': summary['tokens']['estimated_cost_usd']},
        ]
    )
```

### Azure — Application Insights export (future)

```python
from opencensus.ext.azure import metrics_exporter

exporter = metrics_exporter.new_metrics_exporter(
    connection_string="InstrumentationKey=xxx"
)
# Automatically exports metrics every 60s
```

**The in-memory approach works for development and single-instance deployments.** For production with multiple ECS tasks or Azure Container Instances, you'd need external storage.

- 🚚 **Courier:** Running the courier on rented pasture — AWS or Azure provides the depot so you only pay for the fuel consumed.

---

## AI-Specific Metrics — What to Watch

These are metrics that **don't exist in traditional software** but are critical for AI applications:

| Metric | What it measures | Alert threshold | Why | 🚚 Courier |
|---|---|---|---| --- |
| **Token usage / request** | How much context + answer per query | > 2000 tokens/request | Cost growth | Over 2000 fuel loads per trip means the courier is eating too much — review parcel sizes |
| **Cost per query** | $ per chat interaction | > $0.02/query | Budget overrun | Cost of keeping the courier fed — Cost per query: $ per chat interaction · > $0.02/query · Budget overrun |
| **Input/output ratio** | Input tokens ÷ output tokens | > 10:1 means verbose context | Over-retrieval | Input-to-output ratio over 10:1 means parcels are huge relative to the answer the courier wrote |
| **Latency P99** | Worst-case response time | > 10s | UX degradation | Tachograph reading — how long the courier took on the round trip |
| **Error rate** | Failures / total requests | > 5% | System reliability | Depot's monthly feed bill — Error rate: Failures / total requests · > 5% · System reliability |
| **Chunks per document** | Average chunk count | > 500/doc | Storage bloat | Over 500 parcel chunks per document means the post office is slicing parcels too finely |

### Cost monitoring formula

```
daily_cost = avg_cost_per_query × queries_per_day
monthly_cost = daily_cost × 30

# AWS example:
#   avg_cost = $0.0055
#   queries/day = 1000
#   daily = $5.50
#   monthly = $165

# Local example:
#   avg_cost = $0.00
#   monthly = $0 (but hardware costs ~$50-200/month)
```

### Latency breakdown (typical query)

```
Step                        AWS        Azure      Local
────────────────────        ───        ─────      ─────
Embed question              50ms       60ms       100ms
Vector search              100ms      120ms        20ms  ← ChromaDB is local = fast
LLM generation             800ms      700ms      2000ms  ← Local model is slowest
Build response              10ms       10ms        10ms
────────────────────        ───        ─────      ─────
Total                      960ms      890ms      2130ms
```

**Key insight:** Local is free but 2x slower. For development this doesn't matter. For production, cloud models are faster.

- 🚚 **Courier:** The tachograph reading — every delivery time, token cost, and quality score recorded for review.

---

## Self-Test Questions

### Tier 1 — Must understand

- [ ] What are the three `record_*` methods and when is each called?
- [ ] What does `get_summary()` return and which endpoint calls it?
- [ ] Why are metrics stored in-memory and what's the limitation?
- [ ] What do P50, P95, P99 latency values tell you?

### Tier 2 — Should understand

- [ ] Why track input and output tokens separately?
- [ ] What error rate threshold should trigger an alert?
- [ ] How does cost tracking work with `CLOUD_PROVIDER=local`?
- [ ] Why is the `MetricsCollector` stored as a singleton in `app.state`?

### Tier 3 — AI engineering territory

- [ ] How would you make metrics persistent across app restarts?
- [ ] How would you add evaluation scores (faithfulness, relevance) to the metrics? → **Done in I31:** `GET /api/metrics` now includes `rag_queries_pass_rate_percent`, `rag_queries_avg_faithfulness`, and failure category breakdowns.
- [ ] Design a CloudWatch dashboard for this application — what widgets would you add?
- [ ] At what point do you need Prometheus + Grafana instead of in-memory metrics? → **Done in I31:** `GET /api/metrics` returns Prometheus text format, ready for scraping.

- 🚚 **Courier:** Sending the courier on 25 standard test deliveries (golden dataset) to verify it returns the right packages every time.

---

## What to Study Next

🎉 **You've completed the original deep-dive documentation!**

The following files were added in **Phase 9 (Production Observability)** and extend the monitoring story:

- **File #17:** [`src/monitoring/query_logger.py`](../../src/monitoring/query_logger.py) — Structured per-query JSONL logging with failure classification (I30)
- **File #18:** [`src/monitoring/tracing.py`](../../src/monitoring/tracing.py) — OpenTelemetry TracerProvider + Prometheus /metrics endpoint (I31)
- **File #19:** [`src/api/routes/queries.py`](../../src/api/routes/queries.py) — Production debugging endpoints: `GET /queries/failures` + `GET /queries/stats` (I30)
- **File #20:** [`src/api/routes/metrics.py`](../../src/api/routes/metrics.py) — Prometheus-compatible `GET /metrics` endpoint (I31)

📖 **Related docs:**
- [Monitoring Reference](../reference/monitoring.md) — full operational guide with all three pillars
- [API Reference → Queries](../reference/api-reference.md#query-debugging-i30) — endpoint specs
- [API Reference → Metrics](../reference/api-reference.md#prometheus-metrics-i31) — Prometheus format
- [Hands-On Labs Phase 5](../hands-on-labs/hands-on-labs-phase-5.md) — Labs 14–16

Here's a summary of every component covered across the docs:

### Phase 1 — DE-familiar files ✅
- [x] #1: `pyproject.toml` — dependencies
- [x] #2: `src/config/settings.py` — configuration
- [x] #3: `src/api/main.py` — FastAPI app
- [x] #4: `src/api/routes/health.py` — health endpoint
- [x] #5: `src/api/routes/chat.py` — chat endpoint
- [x] #6: `src/api/routes/documents.py` — documents endpoint

### Phase 2 — Bridge files ✅
- [x] #7: [`src/llm/base.py`](llm-interface-deep-dive.md) — LLM interface
- [x] #8: [`src/vectorstore/base.py`](vectorstore-interface-deep-dive.md) — Vector store interface
- [x] #9: [`src/embeddings/base.py`](embedding-interface-deep-dive.md) — Embedding interface
- [x] #10: [`src/models/`](pydantic-models.md) — Pydantic models
- [x] #11: [`src/rag/ingestion.py`](ingestion-pipeline-deep-dive.md) — Ingestion pipeline

### Phase 3 — Pure AI engineering ✅
- [x] #12: [`src/rag/prompts.py`](prompts-deep-dive.md) — Prompt engineering
- [x] #13: [`src/rag/chain.py`](rag-chain-deep-dive.md) — RAG chain orchestrator
- [x] #14: [`src/evaluation/evaluator.py`](evaluation-framework-deep-dive.md) — Evaluation framework
- [x] #15: [`src/evaluation/golden_dataset.py`](golden-dataset-deep-dive.md) — Golden dataset
- [x] #16: [`src/monitoring/metrics.py`](metrics-deep-dive.md) — Metrics & monitoring

📖 **Related docs:**
- [Health Endpoint Deep Dive](../architecture-and-design/api-routes/health-endpoint-explained.md) — where metrics are exposed
- [Monitoring Reference](../reference/monitoring.md) — operational monitoring guide
- [Cost Analysis](cost-analysis.md) — detailed cost breakdown
- [Architecture Overview](../architecture-and-design/architecture.md)

- 🚚 **Courier:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
