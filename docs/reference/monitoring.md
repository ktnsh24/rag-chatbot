# Monitoring & Observability

> **Stories:** I30 (Query Logging), I31 (OpenTelemetry & Metrics)
>
> **Related docs:**
> - [API Reference — Queries](api-reference.md#query-debugging-i30) — endpoint specs
> - [API Reference — Metrics](api-reference.md#prometheus-metrics-i31) — Prometheus format
> - [Hands-On Labs Phase 5](../hands-on-labs/hands-on-labs-phase-5.md) — Labs 14–16

---

## The Three Pillars

The RAG Chatbot implements all three pillars of observability:

| Pillar | Implementation | Story | Endpoint | 🚚 Courier |
|---|---|---|---| --- |
| **Logs** | JSONL per-query structured logs with failure categories | I30 | `GET /api/queries/failures`, `GET /api/queries/stats` | Door the customer knocks on — Logs: JSONL per-query structured logs with failure categories · I30 · GET /api/queries/failures, GET /api/queries/stats |
| **Metrics** | Prometheus text format (counters, gauges) | I31 | `GET /api/metrics` | The tachograph strapped to every courier — counters and gauges, scraped by Prometheus at /api/metrics. |
| **Traces** | OpenTelemetry TracerProvider + FastAPIInstrumentor | I31 | OTLP exporter (configurable) | Entry gate to the depot — Traces: OpenTelemetry TracerProvider + FastAPIInstrumentor · I31 · OTLP exporter (configurable) |

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Pillar 1: Structured Query Logging (I30)

Every `/api/chat` request is logged as a structured JSONL record in `logs/queries/YYYY-MM-DD.jsonl`.

**What's captured per query:**

| Field | Description | 🚚 Courier |
|---|---| --- |
| `request_id` | Unique request identifier | Tracking number stamped on the parcel so the courier can find it again |
| `question` | What the user asked | Courier-side view of question — affects how the courier loads, reads, or delivers the parcels |
| `chunks` | Retrieved documents with relevance scores | The parcel pockets the courier pulled for this query, each tagged with a similarity score. |
| `answer` | LLM response | What the courier wrote on the shipping manifest after reading the parcel |
| `retrieval_score` | How relevant the chunks were (0–1) | Score from 0 to 1 grading how on-target the parcel pockets were for the user's question. |
| `faithfulness_score` | Did the answer stick to the chunks? (0–1) | Did the courier stick to what was inside the parcel pockets, or invent extra fuel? Scored 0–1. |
| `answer_relevance_score` | Did the answer address the question? (0–1) | Right address on the parcel — answer_relevance_score: Did the answer address the question? (0–1) |
| `failure_category` | Triage: `none`, `bad_retrieval`, `hallucination`, `both_bad`, `off_topic`, `marginal` | Triage tag explaining why the courier wandered off — bad retrieval, hallucination, off-topic, or marginal delivery. |
| `latency_ms` | Total response time | Cost of keeping the courier fed — latency_ms: Total response time |

**Failure triage table:**

| Category | Root Cause | Fix | 🚚 Courier |
|---|---|---| --- |
| `bad_retrieval` | Wrong chunks returned | Better chunking, more documents, tune top_k | The courier grabbed the wrong parcel pockets — fix chunking, add documents, or tune top_k. |
| `hallucination` | Good chunks, LLM fabricated | Better system prompt, lower temperature | Parcel was fine, but the courier embellished — tighten the shipping manifest and lower temperature so it sticks to the parcels |
| `both_bad` | Wrong chunks AND fabrication | Both fixes above | Wrong parcel pockets AND the courier hallucinated on top — apply both retrieval and faithfulness fixes. |
| `off_topic` | Question outside document scope | Add documents or refuse gracefully | Courier-side view of off_topic — affects how the courier loads, reads, or delivers the parcels |
| `marginal` | Borderline scores | Monitor, may need prompt tuning | Instructions tucked in the pannier — marginal: Borderline scores · Monitor, may need prompt tuning |

**Config:**

| Env Var | Default | Description | 🚚 Courier |
|---|---|---| --- |
| `QUERY_LOG_ENABLED` | `true` | Enable/disable query logging | Bouncer at the depot door — QUERY_LOG_ENABLED: true · Enable/disable query logging |
| `QUERY_LOG_DIR` | `logs/queries` | Directory for JSONL files | Courier's trip log — every delivery's details written to disk for later review |

**Files:** `src/monitoring/query_logger.py`, `src/api/routes/queries.py`

- 🚚 **Courier:** The warehouse robot dispatched to find the right parcel shelf — it uses GPS coordinates (embeddings) to locate the nearest relevant chunks in ~9 hops.

---

## Pillar 2: Prometheus Metrics (I31)

`GET /api/metrics` returns all metrics in Prometheus text format.

**Chat metrics (from MetricsCollector):**

| Metric | Type | Description | 🚚 Courier |
|---|---|---| --- |
| `rag_chat_requests_total` | counter | Total chat requests | Tachograph counter — how many deliveries the courier completed |
| `rag_chat_errors_total` | counter | Total errors | Tachograph reading — recorded on every courier trip and shown on the dashboard |
| `rag_chat_error_rate_percent` | gauge | Current error rate | Tachograph reading — recorded on every courier trip and shown on the dashboard |
| `rag_chat_latency_p50/p95/p99_ms` | gauge | Latency percentiles | Tachograph reading — how long the courier took on the round trip |
| `rag_tokens_input_total` | counter | Input tokens consumed | Tachograph counter tallying every fuel bale fed into the courier across all queries. |
| `rag_tokens_output_total` | counter | Output tokens generated | Counter for every fuel bale the courier brayed back out as answer tokens. |
| `rag_tokens_cost_usd_total` | counter | Estimated cost | Running dollar total for fuel consumed — the trip's accumulated delivery bill. |
| `rag_documents_ingested_total` | counter | Documents ingested | Post office sorting raw mail into GPS-labelled boxes before the courier's first trip |
| `rag_chunks_created_total` | counter | Chunks created | Counter of parcel pockets the post office has stitched during all document ingestions. |
| `rag_uptime_seconds` | gauge | Application uptime | Tachograph reading — recorded on every courier trip and shown on the dashboard |

**Query quality metrics (from QueryLogger):**

| Metric | Type | Description | 🚚 Courier |
|---|---|---| --- |
| `rag_queries_total` | gauge | Queries logged today | Tachograph reading — recorded on every courier trip and shown on the dashboard |
| `rag_queries_pass_rate_percent` | gauge | Evaluation pass rate | Tachograph reading — recorded on every courier trip and shown on the dashboard |
| `rag_queries_avg_retrieval` | gauge | Avg retrieval score | Average score grading how well the courier is fetching the right parcel pockets lately. |
| `rag_queries_avg_faithfulness` | gauge | Avg faithfulness score | How confidently the warehouse says 'this parcel matches' — higher = closer GPS hit |
| `rag_queries_failure_{category}` | gauge | Failures by category | Tachograph reading — recorded on every courier trip and shown on the dashboard |

**Prometheus scrape config:**

```yaml
scrape_configs:
  - job_name: 'rag-chatbot'
    metrics_path: '/api/metrics'
    static_configs:
      - targets: ['localhost:8000']
```

**File:** `src/api/routes/metrics.py`

- 🚚 **Courier:** The tachograph reading — every delivery time, token cost, and quality score recorded for review.

---

## Pillar 3: Distributed Tracing (I31)

OpenTelemetry is wired up in `src/monitoring/tracing.py`. When enabled, every HTTP request gets a trace with spans for each processing step.

**Config:**

| Env Var | Default | Description | 🚚 Courier |
|---|---|---| --- |
| `OTEL_ENABLED` | `false` | Enable OpenTelemetry tracing | Tachograph reading — recorded on every courier trip and shown on the dashboard |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP collector endpoint | Depot's front door — OTEL_EXPORTER_OTLP_ENDPOINT: — · OTLP collector endpoint |
| `OTEL_SERVICE_NAME` | `rag-chatbot` | Service name in traces | Courier-side view of OTEL_SERVICE_NAME — affects how the courier loads, reads, or delivers the parcels |

**What's traced:**
- FastAPI request/response (via FastAPIInstrumentor)
- Embedding calls
- Vector store searches
- LLM generation calls

**File:** `src/monitoring/tracing.py`

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Recommended Alert Thresholds

| Scenario | Metric | Threshold | 🚚 Courier |
|---|---|---| --- |
| System errors | `rag_chat_error_rate_percent` | > 50% for 5 min | Courier-side view of System errors — affects how the courier loads, reads, or delivers the parcels |
| Slow responses | `rag_chat_latency_p95_ms` | > 10,000ms for 5 min | Tachograph reading — how long the courier took on the round trip |
| Quality drop | `rag_queries_pass_rate_percent` | < 60% for 1 hour | Courier's report card — share of test deliveries that scored above the bar |
| Hallucination spike | `rag_queries_failure_hallucination` | > 10 in 1 hour | Courier's report card — share of test deliveries that scored above the bar |
| Cost runaway | `rag_tokens_cost_usd_total` | > daily budget | Watch the fuel bill climb past the daily budget — courier is eating through parcels too fast. |

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Cloud-Specific Setup

### AWS (CloudWatch)

| Feature | Setup | 🚚 Courier |
|---|---| --- |
| **Logs** | ECS tasks → CloudWatch Logs (stdout) | Stopwatch on the courier's harness — Logs: ECS tasks → CloudWatch Logs (stdout) |
| **Metrics** | Prometheus → CloudWatch via `aws-otel-collector` sidecar | Tally board on the dispatch board — Metrics: Prometheus → CloudWatch via aws-otel-collector sidecar |
| **Dashboard** | CloudWatch → Dashboards → import metrics | Tachograph reading — Dashboard: CloudWatch → Dashboards → import metrics |
| **Alarms** | CloudWatch → Alarms → select metric → set threshold | Stopwatch on the courier's harness — Alarms: CloudWatch → Alarms → select metric → set threshold |

### Azure (App Insights)

| Feature | Setup | 🚚 Courier |
|---|---| --- |
| **Logs** | Container Apps → Log Analytics | Stall that houses the worker — Logs: Container Apps → Log Analytics |
| **Metrics** | OpenTelemetry → Azure Monitor via OTLP exporter | Courier's odometer dial — Metrics: OpenTelemetry → Azure Monitor via OTLP exporter |
| **Dashboard** | Azure Portal → Monitor → Workbooks | Workbook on the Azure hub where depot-hands view all the courier's tachograph charts. |
| **Alerts** | Azure Monitor → Alerts → create rule | Azure hub paging system that wakes depot-hands when courier metrics breach thresholds. |

- 🚚 **Courier:** Loading up the courier for the first time — installing the bag, attaching the parcels, and confirming the GPS coordinates before the first run.
