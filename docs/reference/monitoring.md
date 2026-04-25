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

| Pillar | Implementation | Story | Endpoint | 🫏 Donkey |
|---|---|---|---| --- |
| **Logs** | JSONL per-query structured logs with failure categories | I30 | `GET /api/queries/failures`, `GET /api/queries/stats` | Stable door 🚪 |
| **Metrics** | Prometheus text format (counters, gauges) | I31 | `GET /api/metrics` | Tachograph 📊 |
| **Traces** | OpenTelemetry TracerProvider + FastAPIInstrumentor | I31 | OTLP exporter (configurable) | Stable door 🚪 |

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Pillar 1: Structured Query Logging (I30)

Every `/api/chat` request is logged as a structured JSONL record in `logs/queries/YYYY-MM-DD.jsonl`.

**What's captured per query:**

| Field | Description | 🫏 Donkey |
|---|---| --- |
| `request_id` | Unique request identifier | 🫏 On the route |
| `question` | What the user asked | 🫏 On the route |
| `chunks` | Retrieved documents with relevance scores | Saddlebag piece 📦 |
| `answer` | LLM response | The donkey 🐴 |
| `retrieval_score` | How relevant the chunks were (0–1) | Saddlebag piece 📦 |
| `faithfulness_score` | Did the answer stick to the chunks? (0–1) | Saddlebag piece 📦 |
| `answer_relevance_score` | Did the answer address the question? (0–1) | Right address 🎯 |
| `failure_category` | Triage: `none`, `bad_retrieval`, `hallucination`, `both_bad`, `off_topic`, `marginal` | Memory drift ⚠️ |
| `latency_ms` | Total response time | Feed bill 🌾 |

**Failure triage table:**

| Category | Root Cause | Fix | 🫏 Donkey |
|---|---|---| --- |
| `bad_retrieval` | Wrong chunks returned | Better chunking, more documents, tune top_k | Saddlebag piece 📦 |
| `hallucination` | Good chunks, LLM fabricated | Better system prompt, lower temperature | The donkey 🐴 |
| `both_bad` | Wrong chunks AND fabrication | Both fixes above | Saddlebag piece 📦 |
| `off_topic` | Question outside document scope | Add documents or refuse gracefully | 🫏 On the route |
| `marginal` | Borderline scores | Monitor, may need prompt tuning | Delivery note 📋 |

**Config:**

| Env Var | Default | Description | 🫏 Donkey |
|---|---|---| --- |
| `QUERY_LOG_ENABLED` | `true` | Enable/disable query logging | Gate guard 🔐 |
| `QUERY_LOG_DIR` | `logs/queries` | Directory for JSONL files | 🫏 On the route |

**Files:** `src/monitoring/query_logger.py`, `src/api/routes/queries.py`

- 🫏 **Donkey:** The warehouse robot dispatched to find the right saddlebag shelf — it uses GPS coordinates (embeddings) to locate the nearest relevant chunks in ~9 hops.

---

## Pillar 2: Prometheus Metrics (I31)

`GET /api/metrics` returns all metrics in Prometheus text format.

**Chat metrics (from MetricsCollector):**

| Metric | Type | Description | 🫏 Donkey |
|---|---|---| --- |
| `rag_chat_requests_total` | counter | Total chat requests | Saddlebag check 🫏 |
| `rag_chat_errors_total` | counter | Total errors | Saddlebag check 🫏 |
| `rag_chat_error_rate_percent` | gauge | Current error rate | Saddlebag check 🫏 |
| `rag_chat_latency_p50/p95/p99_ms` | gauge | Latency percentiles | Saddlebag check 🫏 |
| `rag_tokens_input_total` | counter | Input tokens consumed | Cargo unit ⚖️ |
| `rag_tokens_output_total` | counter | Output tokens generated | Cargo unit ⚖️ |
| `rag_tokens_cost_usd_total` | counter | Estimated cost | Cargo unit ⚖️ |
| `rag_documents_ingested_total` | counter | Documents ingested | Saddlebag check 🫏 |
| `rag_chunks_created_total` | counter | Chunks created | Saddlebag piece 📦 |
| `rag_uptime_seconds` | gauge | Application uptime | Saddlebag check 🫏 |

**Query quality metrics (from QueryLogger):**

| Metric | Type | Description | 🫏 Donkey |
|---|---|---| --- |
| `rag_queries_total` | gauge | Queries logged today | Saddlebag check 🫏 |
| `rag_queries_pass_rate_percent` | gauge | Evaluation pass rate | Saddlebag check 🫏 |
| `rag_queries_avg_retrieval` | gauge | Avg retrieval score | Saddlebag fetch 🎒 |
| `rag_queries_avg_faithfulness` | gauge | Avg faithfulness score | Saddlebag check 🫏 |
| `rag_queries_failure_{category}` | gauge | Failures by category | Saddlebag check 🫏 |

**Prometheus scrape config:**

```yaml
scrape_configs:
  - job_name: 'rag-chatbot'
    metrics_path: '/api/metrics'
    static_configs:
      - targets: ['localhost:8000']
```

**File:** `src/api/routes/metrics.py`

- 🫏 **Donkey:** The tachograph reading — every delivery time, token cost, and quality score recorded for review.

---

## Pillar 3: Distributed Tracing (I31)

OpenTelemetry is wired up in `src/monitoring/tracing.py`. When enabled, every HTTP request gets a trace with spans for each processing step.

**Config:**

| Env Var | Default | Description | 🫏 Donkey |
|---|---|---| --- |
| `OTEL_ENABLED` | `false` | Enable OpenTelemetry tracing | 🫏 On the route |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP collector endpoint | Stable door 🚪 |
| `OTEL_SERVICE_NAME` | `rag-chatbot` | Service name in traces | Saddlebag check 🫏 |

**What's traced:**
- FastAPI request/response (via FastAPIInstrumentor)
- Embedding calls
- Vector store searches
- LLM generation calls

**File:** `src/monitoring/tracing.py`

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Recommended Alert Thresholds

| Scenario | Metric | Threshold | 🫏 Donkey |
|---|---|---| --- |
| System errors | `rag_chat_error_rate_percent` | > 50% for 5 min | Saddlebag check 🫏 |
| Slow responses | `rag_chat_latency_p95_ms` | > 10,000ms for 5 min | Saddlebag check 🫏 |
| Quality drop | `rag_queries_pass_rate_percent` | < 60% for 1 hour | Saddlebag check 🫏 |
| Hallucination spike | `rag_queries_failure_hallucination` | > 10 in 1 hour | Saddlebag check 🫏 |
| Cost runaway | `rag_tokens_cost_usd_total` | > daily budget | Cargo unit ⚖️ |

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Cloud-Specific Setup

### AWS (CloudWatch)

| Feature | Setup | 🫏 Donkey |
|---|---| --- |
| **Logs** | ECS tasks → CloudWatch Logs (stdout) | Tachograph 📊 |
| **Metrics** | Prometheus → CloudWatch via `aws-otel-collector` sidecar | Tachograph 📊 |
| **Dashboard** | CloudWatch → Dashboards → import metrics | Tachograph 📊 |
| **Alarms** | CloudWatch → Alarms → select metric → set threshold | Tachograph 📊 |

### Azure (App Insights)

| Feature | Setup | 🫏 Donkey |
|---|---| --- |
| **Logs** | Container Apps → Log Analytics | Stable stall 🐎 |
| **Metrics** | OpenTelemetry → Azure Monitor via OTLP exporter | Tachograph 📊 |
| **Dashboard** | Azure Portal → Monitor → Workbooks | Azure hub ☁️ |
| **Alerts** | Azure Monitor → Alerts → create rule | Azure hub ☁️ |

- 🫏 **Donkey:** Loading up the donkey for the first time — installing the saddle, attaching the saddlebags, and confirming the GPS coordinates before the first run.
