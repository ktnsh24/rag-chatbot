# Monitoring & Observability

> **Stories:** I30 (Query Logging), I31 (OpenTelemetry & Metrics)
>
> **Related docs:**
> - [API Reference — Queries](api-reference.md#query-debugging-i30) — endpoint specs
> - [API Reference — Metrics](api-reference.md#prometheus-metrics-i31) — Prometheus format
> - [Hands-On Labs Phase 5](../docs/hands-on-labs/hands-on-labs-phase-5.md) — Labs 14–16

---

## The Three Pillars

The RAG Chatbot implements all three pillars of observability:

| Pillar | Implementation | Story | Endpoint |
|---|---|---|---|
| **Logs** | JSONL per-query structured logs with failure categories | I30 | `GET /api/queries/failures`, `GET /api/queries/stats` |
| **Metrics** | Prometheus text format (counters, gauges) | I31 | `GET /api/metrics` |
| **Traces** | OpenTelemetry TracerProvider + FastAPIInstrumentor | I31 | OTLP exporter (configurable) |

---

## Pillar 1: Structured Query Logging (I30)

Every `/api/chat` request is logged as a structured JSONL record in `logs/queries/YYYY-MM-DD.jsonl`.

**What's captured per query:**

| Field | Description |
|---|---|
| `request_id` | Unique request identifier |
| `question` | What the user asked |
| `chunks` | Retrieved documents with relevance scores |
| `answer` | LLM response |
| `retrieval_score` | How relevant the chunks were (0–1) |
| `faithfulness_score` | Did the answer stick to the chunks? (0–1) |
| `answer_relevance_score` | Did the answer address the question? (0–1) |
| `failure_category` | Triage: `none`, `bad_retrieval`, `hallucination`, `both_bad`, `off_topic`, `marginal` |
| `latency_ms` | Total response time |

**Failure triage table:**

| Category | Root Cause | Fix |
|---|---|---|
| `bad_retrieval` | Wrong chunks returned | Better chunking, more documents, tune top_k |
| `hallucination` | Good chunks, LLM fabricated | Better system prompt, lower temperature |
| `both_bad` | Wrong chunks AND fabrication | Both fixes above |
| `off_topic` | Question outside document scope | Add documents or refuse gracefully |
| `marginal` | Borderline scores | Monitor, may need prompt tuning |

**Config:**

| Env Var | Default | Description |
|---|---|---|
| `QUERY_LOG_ENABLED` | `true` | Enable/disable query logging |
| `QUERY_LOG_DIR` | `logs/queries` | Directory for JSONL files |

**Files:** `src/monitoring/query_logger.py`, `src/api/routes/queries.py`

---

## Pillar 2: Prometheus Metrics (I31)

`GET /api/metrics` returns all metrics in Prometheus text format.

**Chat metrics (from MetricsCollector):**

| Metric | Type | Description |
|---|---|---|
| `rag_chat_requests_total` | counter | Total chat requests |
| `rag_chat_errors_total` | counter | Total errors |
| `rag_chat_error_rate_percent` | gauge | Current error rate |
| `rag_chat_latency_p50/p95/p99_ms` | gauge | Latency percentiles |
| `rag_tokens_input_total` | counter | Input tokens consumed |
| `rag_tokens_output_total` | counter | Output tokens generated |
| `rag_tokens_cost_usd_total` | counter | Estimated cost |
| `rag_documents_ingested_total` | counter | Documents ingested |
| `rag_chunks_created_total` | counter | Chunks created |
| `rag_uptime_seconds` | gauge | Application uptime |

**Query quality metrics (from QueryLogger):**

| Metric | Type | Description |
|---|---|---|
| `rag_queries_total` | gauge | Queries logged today |
| `rag_queries_pass_rate_percent` | gauge | Evaluation pass rate |
| `rag_queries_avg_retrieval` | gauge | Avg retrieval score |
| `rag_queries_avg_faithfulness` | gauge | Avg faithfulness score |
| `rag_queries_failure_{category}` | gauge | Failures by category |

**Prometheus scrape config:**

```yaml
scrape_configs:
  - job_name: 'rag-chatbot'
    metrics_path: '/api/metrics'
    static_configs:
      - targets: ['localhost:8000']
```

**File:** `src/api/routes/metrics.py`

---

## Pillar 3: Distributed Tracing (I31)

OpenTelemetry is wired up in `src/monitoring/tracing.py`. When enabled, every HTTP request gets a trace with spans for each processing step.

**Config:**

| Env Var | Default | Description |
|---|---|---|
| `OTEL_ENABLED` | `false` | Enable OpenTelemetry tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP collector endpoint |
| `OTEL_SERVICE_NAME` | `rag-chatbot` | Service name in traces |

**What's traced:**
- FastAPI request/response (via FastAPIInstrumentor)
- Embedding calls
- Vector store searches
- LLM generation calls

**File:** `src/monitoring/tracing.py`

---

## Recommended Alert Thresholds

| Scenario | Metric | Threshold |
|---|---|---|
| System errors | `rag_chat_error_rate_percent` | > 50% for 5 min |
| Slow responses | `rag_chat_latency_p95_ms` | > 10,000ms for 5 min |
| Quality drop | `rag_queries_pass_rate_percent` | < 60% for 1 hour |
| Hallucination spike | `rag_queries_failure_hallucination` | > 10 in 1 hour |
| Cost runaway | `rag_tokens_cost_usd_total` | > daily budget |

---

## Cloud-Specific Setup

### AWS (CloudWatch)

| Feature | Setup |
|---|---|
| **Logs** | ECS tasks → CloudWatch Logs (stdout) |
| **Metrics** | Prometheus → CloudWatch via `aws-otel-collector` sidecar |
| **Dashboard** | CloudWatch → Dashboards → import metrics |
| **Alarms** | CloudWatch → Alarms → select metric → set threshold |

### Azure (App Insights)

| Feature | Setup |
|---|---|
| **Logs** | Container Apps → Log Analytics |
| **Metrics** | OpenTelemetry → Azure Monitor via OTLP exporter |
| **Dashboard** | Azure Portal → Monitor → Workbooks |
| **Alerts** | Azure Monitor → Alerts → create rule |
