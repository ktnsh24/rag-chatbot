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
| **Logs** | JSONL per-query structured logs with failure categories | I30 | `GET /api/queries/failures`, `GET /api/queries/stats` | Door the customer knocks on — Logs: JSONL per-query structured logs with failure categories · I30 · GET /api/queries/failures, GET /api/queries/stats |
| **Metrics** | Prometheus text format (counters, gauges) | I31 | `GET /api/metrics` | The tachograph strapped to every donkey — counters and gauges, scraped by Prometheus at /api/metrics. |
| **Traces** | OpenTelemetry TracerProvider + FastAPIInstrumentor | I31 | OTLP exporter (configurable) | Entry gate to the stable — Traces: OpenTelemetry TracerProvider + FastAPIInstrumentor · I31 · OTLP exporter (configurable) |

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Pillar 1: Structured Query Logging (I30)

Every `/api/chat` request is logged as a structured JSONL record in `logs/queries/YYYY-MM-DD.jsonl`.

**What's captured per query:**

| Field | Description | 🫏 Donkey |
|---|---| --- |
| `request_id` | Unique request identifier | Tracking number stamped on the parcel so the donkey can find it again |
| `question` | What the user asked | Donkey-side view of question — affects how the donkey loads, reads, or delivers the cargo |
| `chunks` | Retrieved documents with relevance scores | The backpack pockets the donkey pulled for this query, each tagged with a similarity score. |
| `answer` | LLM response | What the donkey wrote on the delivery note after reading the backpack |
| `retrieval_score` | How relevant the chunks were (0–1) | Score from 0 to 1 grading how on-target the backpack pockets were for the user's question. |
| `faithfulness_score` | Did the answer stick to the chunks? (0–1) | Did the donkey stick to what was inside the backpack pockets, or invent extra hay? Scored 0–1. |
| `answer_relevance_score` | Did the answer address the question? (0–1) | Right address on the parcel — answer_relevance_score: Did the answer address the question? (0–1) |
| `failure_category` | Triage: `none`, `bad_retrieval`, `hallucination`, `both_bad`, `off_topic`, `marginal` | Triage tag explaining why the donkey wandered off — bad retrieval, hallucination, off-topic, or marginal delivery. |
| `latency_ms` | Total response time | Cost of keeping the donkey fed — latency_ms: Total response time |

**Failure triage table:**

| Category | Root Cause | Fix | 🫏 Donkey |
|---|---|---| --- |
| `bad_retrieval` | Wrong chunks returned | Better chunking, more documents, tune top_k | The donkey grabbed the wrong backpack pockets — fix chunking, add documents, or tune top_k. |
| `hallucination` | Good chunks, LLM fabricated | Better system prompt, lower temperature | Backpack was fine, but the donkey embellished — tighten the standing orders and lower temperature so it sticks to the cargo |
| `both_bad` | Wrong chunks AND fabrication | Both fixes above | Wrong backpack pockets AND the donkey hallucinated on top — apply both retrieval and faithfulness fixes. |
| `off_topic` | Question outside document scope | Add documents or refuse gracefully | Donkey-side view of off_topic — affects how the donkey loads, reads, or delivers the cargo |
| `marginal` | Borderline scores | Monitor, may need prompt tuning | Instructions tucked in the pannier — marginal: Borderline scores · Monitor, may need prompt tuning |

**Config:**

| Env Var | Default | Description | 🫏 Donkey |
|---|---|---| --- |
| `QUERY_LOG_ENABLED` | `true` | Enable/disable query logging | Bouncer at the stable door — QUERY_LOG_ENABLED: true · Enable/disable query logging |
| `QUERY_LOG_DIR` | `logs/queries` | Directory for JSONL files | Donkey's trip log — every delivery's details written to disk for later review |

**Files:** `src/monitoring/query_logger.py`, `src/api/routes/queries.py`

- 🫏 **Donkey:** The warehouse robot dispatched to find the right backpack shelf — it uses GPS coordinates (embeddings) to locate the nearest relevant chunks in ~9 hops.

---

## Pillar 2: Prometheus Metrics (I31)

`GET /api/metrics` returns all metrics in Prometheus text format.

**Chat metrics (from MetricsCollector):**

| Metric | Type | Description | 🫏 Donkey |
|---|---|---| --- |
| `rag_chat_requests_total` | counter | Total chat requests | Tachograph counter — how many deliveries the donkey completed |
| `rag_chat_errors_total` | counter | Total errors | Tachograph reading — recorded on every donkey trip and shown on the dashboard |
| `rag_chat_error_rate_percent` | gauge | Current error rate | Tachograph reading — recorded on every donkey trip and shown on the dashboard |
| `rag_chat_latency_p50/p95/p99_ms` | gauge | Latency percentiles | Tachograph reading — how long the donkey took on the round trip |
| `rag_tokens_input_total` | counter | Input tokens consumed | Tachograph counter tallying every hay bale fed into the donkey across all queries. |
| `rag_tokens_output_total` | counter | Output tokens generated | Counter for every hay bale the donkey brayed back out as answer tokens. |
| `rag_tokens_cost_usd_total` | counter | Estimated cost | Running dollar total for hay consumed — the trip's accumulated delivery bill. |
| `rag_documents_ingested_total` | counter | Documents ingested | Post office sorting raw mail into GPS-labelled boxes before the donkey's first trip |
| `rag_chunks_created_total` | counter | Chunks created | Counter of backpack pockets the post office has stitched during all document ingestions. |
| `rag_uptime_seconds` | gauge | Application uptime | Tachograph reading — recorded on every donkey trip and shown on the dashboard |

**Query quality metrics (from QueryLogger):**

| Metric | Type | Description | 🫏 Donkey |
|---|---|---| --- |
| `rag_queries_total` | gauge | Queries logged today | Tachograph reading — recorded on every donkey trip and shown on the dashboard |
| `rag_queries_pass_rate_percent` | gauge | Evaluation pass rate | Tachograph reading — recorded on every donkey trip and shown on the dashboard |
| `rag_queries_avg_retrieval` | gauge | Avg retrieval score | Average score grading how well the donkey is fetching the right backpack pockets lately. |
| `rag_queries_avg_faithfulness` | gauge | Avg faithfulness score | How confidently the warehouse says 'this backpack matches' — higher = closer GPS hit |
| `rag_queries_failure_{category}` | gauge | Failures by category | Tachograph reading — recorded on every donkey trip and shown on the dashboard |

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
| `OTEL_ENABLED` | `false` | Enable OpenTelemetry tracing | Tachograph reading — recorded on every donkey trip and shown on the dashboard |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP collector endpoint | Stable's front door — OTEL_EXPORTER_OTLP_ENDPOINT: — · OTLP collector endpoint |
| `OTEL_SERVICE_NAME` | `rag-chatbot` | Service name in traces | Donkey-side view of OTEL_SERVICE_NAME — affects how the donkey loads, reads, or delivers the cargo |

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
| System errors | `rag_chat_error_rate_percent` | > 50% for 5 min | Donkey-side view of System errors — affects how the donkey loads, reads, or delivers the cargo |
| Slow responses | `rag_chat_latency_p95_ms` | > 10,000ms for 5 min | Tachograph reading — how long the donkey took on the round trip |
| Quality drop | `rag_queries_pass_rate_percent` | < 60% for 1 hour | Donkey's report card — share of test deliveries that scored above the bar |
| Hallucination spike | `rag_queries_failure_hallucination` | > 10 in 1 hour | Donkey's report card — share of test deliveries that scored above the bar |
| Cost runaway | `rag_tokens_cost_usd_total` | > daily budget | Watch the hay bill climb past the daily budget — donkey is eating through cargo too fast. |

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Cloud-Specific Setup

### AWS (CloudWatch)

| Feature | Setup | 🫏 Donkey |
|---|---| --- |
| **Logs** | ECS tasks → CloudWatch Logs (stdout) | Stopwatch on the donkey's harness — Logs: ECS tasks → CloudWatch Logs (stdout) |
| **Metrics** | Prometheus → CloudWatch via `aws-otel-collector` sidecar | Tally board on the stable wall — Metrics: Prometheus → CloudWatch via aws-otel-collector sidecar |
| **Dashboard** | CloudWatch → Dashboards → import metrics | Tachograph reading — Dashboard: CloudWatch → Dashboards → import metrics |
| **Alarms** | CloudWatch → Alarms → select metric → set threshold | Stopwatch on the donkey's harness — Alarms: CloudWatch → Alarms → select metric → set threshold |

### Azure (App Insights)

| Feature | Setup | 🫏 Donkey |
|---|---| --- |
| **Logs** | Container Apps → Log Analytics | Stall that houses the worker — Logs: Container Apps → Log Analytics |
| **Metrics** | OpenTelemetry → Azure Monitor via OTLP exporter | Donkey's odometer dial — Metrics: OpenTelemetry → Azure Monitor via OTLP exporter |
| **Dashboard** | Azure Portal → Monitor → Workbooks | Workbook on the Azure hub where stable-hands view all the donkey's tachograph charts. |
| **Alerts** | Azure Monitor → Alerts → create rule | Azure hub paging system that wakes stable-hands when donkey metrics breach thresholds. |

- 🫏 **Donkey:** Loading up the donkey for the first time — installing the bag, attaching the backpacks, and confirming the GPS coordinates before the first run.
