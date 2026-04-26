# Metrics Endpoint — Deep Dive

> `GET /api/metrics` — Prometheus-compatible application metrics.

> **DE verdict: ★★☆☆☆ — Standard Prometheus exposition, nothing AI-specific in the route.**
> If you've exposed Airflow or ECS metrics for Prometheus scraping, this is
> identical. The only difference is *what* is being measured (LLM latency, token
> usage, retrieval scores) instead of (DAG duration, task retries, queue depth).

> **Related docs:**
> - [API Routes Overview](../api-routes-explained.md) — how all routes fit together
> - [Queries Endpoint Deep Dive](queries-endpoint-explained.md) — the failure data this endpoint includes
> - [API Reference → Metrics](../../reference/api-reference.md) — request/response examples

---

## Table of Contents

1. [What This Endpoint Does — The 30-Second Version](#what-this-endpoint-does)
2. [DE Parallel — Prometheus Metrics for Pipelines](#de-parallel)
3. [The Route Code](#the-route-code)
4. [Metrics Exposed](#metrics-exposed)
5. [Prometheus Scrape Configuration](#prometheus-scrape-configuration)
6. [Building a Grafana Dashboard](#building-a-grafana-dashboard)
7. [Self-Check Questions](#self-check-questions)

---

## Plain-English Walkthrough (Start Here)

> **Read this first if you're new to the chatbot.** Same courier analogy as the [Chat Walkthrough](./chat-endpoint-explained.md#plain-english-walkthrough-start-here). This explains what's specific about the metrics endpoint.

### What this endpoint is for

`GET /api/metrics` returns a **plain-text** dump of internal counters and gauges in the format that Prometheus scrapers understand. Prometheus periodically polls this URL, parses the lines, stores them in its time-series database, and Grafana then graphs them.

> **Courier version.** It's the courier's logbook hanging by the door. Every few seconds an inspector (Prometheus) walks past, copies down the latest tally — how many parcels delivered, average delivery time, total fuel spent — and adds it to a wall chart so the depot manager can see trends.

### What really happens

This endpoint does **no expensive work**. It reads two in-memory objects — the `MetricsCollector` and the `QueryLogger` — and formats their current values as Prometheus exposition text. The only "computation" is summarising query stats over the last 24 hours via the query logger's stats method.

```
1. Read MetricsCollector summary  (in-memory; instant)
2. Read QueryLogger stats(days=1) (database query — slower)
3. Format as Prometheus text lines
4. Return as text/plain
```

### What metrics are exposed

Two families:

| Family | Counters/Gauges | Source |
| --- | --- | --- |
| **Chat** | request count, error count, error rate, latency p50/p95/p99, input/output/cost tokens, document count, chunk count, uptime | `MetricsCollector` (in-memory) |
| **Quality** | total queries today, passed, failed, pass rate, avg retrieval/faithfulness/relevance, failure breakdown per category | `QueryLogger.get_stats(days=1)` (database) |

A truncated example response:

```
# HELP rag_chat_requests_total Total chat requests processed.
# TYPE rag_chat_requests_total counter
rag_chat_requests_total 1428

# HELP rag_chat_latency_p95_ms Chat latency 95th percentile in ms.
# TYPE rag_chat_latency_p95_ms gauge
rag_chat_latency_p95_ms 2341

# HELP rag_queries_pass_rate_percent Evaluation pass rate today.
# TYPE rag_queries_pass_rate_percent gauge
rag_queries_pass_rate_percent 87.4
```

### The two storage models

Notice the family-1 (chat) metrics are **in-memory only** — they reset every time the process restarts. So a restart at 09:00 wipes the request count, even though Prometheus stores its own history elsewhere. This is fine if you only ever look at the values *after* Prometheus has scraped them — Prometheus itself preserves the historical view.

The family-2 (quality) metrics come from the query log database, so they survive restarts. But they're computed **every time `/api/metrics` is hit** by re-running the query log's `get_stats` query. If your scraper hits this endpoint every 15 seconds, you're running that database query every 15 seconds. Cheap on a small log table; not free at scale.

### Quirks worth knowing

1. **Per-process counters reset on restart.** Multi-pod deployments will have different counts per pod; Prometheus will see them as separate time series unless you aggregate by `job` and not `instance`.
2. **No auth.** Anyone hitting the URL can read your operational metrics including total cost. Standard for Prometheus, but think twice about exposing publicly.
3. **Quality metrics run a database query on every scrape.** Index `query_logs(created_at)` if your log table grows large.
4. **No histograms** — only pre-computed percentiles. So you can't re-bucket latencies in Grafana; you're stuck with whatever percentiles the collector pre-computes (p50/p95/p99).
5. **Cost tracker is a counter** — there's no per-provider breakdown in the metrics, only total dollars across all providers.
6. **Failure-category gauges are dynamic** — only categories with non-zero counts in the last 24h appear. Your Grafana dashboard needs `or vector(0)` clauses to handle the missing-series case.

### TL;DR

- Plain-text endpoint, designed for Prometheus scraping.
- Two metric families: chat counters (in-memory, per-process) and quality stats (from query log, recomputed each scrape).
- No auth; no histograms; counters reset per process restart.
- Total cost is a single counter — no per-provider breakdown today.

---

## What This Endpoint Does

Returns application metrics in **Prometheus text exposition format** — the standard
that Prometheus, Grafana, Datadog, and CloudWatch can all scrape.

```text
GET /api/metrics
→ Returns plain text:

# HELP rag_chat_requests_total Total chat requests processed.
# TYPE rag_chat_requests_total counter
rag_chat_requests_total 142

# HELP rag_chat_latency_p95_ms 95th percentile chat latency.
# TYPE rag_chat_latency_p95_ms gauge
rag_chat_latency_p95_ms 1250.0
```

No JSON. No HTML. Just the Prometheus text format that monitoring tools expect.

- 🚚 **Courier:** The specific delivery address the courier is dispatched to — each route handles a different type of parcels drop-off.

---

## DE Parallel

| Concept | Data Engineering | RAG Chatbot | 🚚 Courier |
| --- | --- | --- | --- |
| **What you expose** | DAG run count, task duration, queue depth | Chat requests, LLM latency, token usage | Tachograph entries — every chat trip's count, latency, and token usage published for scrapers |
| **Format** | Prometheus text exposition | Prometheus text exposition | Tally board on the dispatch board — Format: Prometheus text exposition · Prometheus text exposition |
| **Scraper** | Prometheus → Grafana | Prometheus → Grafana | Stopwatch on the courier's harness — Scraper: Prometheus → Grafana · Prometheus → Grafana |
| **Alert on** | DAG failure rate > 5%, task duration > SLA | Pass rate < 80%, latency p95 > 2s | Depot-owner alarms — wake someone if too few courier trips pass or the round trips get too slow |
| **Pattern** | `GET /metrics` on Airflow webserver | `GET /api/metrics` on FastAPI | Tally board on the dispatch board — Pattern: GET /metrics on Airflow webserver · GET /api/metrics on FastAPI |

**Bottom line:** Same infrastructure pattern, different business metrics.

- 🚚 **Courier:** Running multiple couriers on the same route to confirm that AI engineering and data engineering practices mirror each other.

---

## The Route Code

```python
@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    response_class=Response,
)
async def prometheus_metrics(request: Request) -> Response:
    metrics = getattr(request.app.state, "metrics", None)
    query_logger = getattr(request.app.state, "query_logger", None)

    lines: list[str] = []

    # Collect from MetricsCollector (chat, tokens, documents)
    if metrics:
        summary = metrics.get_summary()
        # Format as Prometheus text lines...

    # Collect from QueryLogger (pass rate, failure breakdown)
    if query_logger:
        stats = await query_logger.get_stats(days=1)
        # Format as Prometheus text lines...

    return Response(
        content="\n".join(lines),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
```

### What to notice

1. **Two data sources** — `MetricsCollector` (in-memory counters for chat/tokens) and `QueryLogger` (JSONL-based evaluation stats)
2. **Response class** — `Response` not a Pydantic model, because Prometheus expects plain text
3. **Media type** — `text/plain; version=0.0.4` is the Prometheus exposition format MIME type
4. **No auth** — metrics endpoints are typically unprotected (Prometheus needs to scrape without tokens)

- 🚚 **Courier:** The specific delivery address the courier is dispatched to — each route handles a different type of parcels drop-off.

---

## Metrics Exposed

### Counters (monotonically increasing)

| Metric | Type | What it measures | 🚚 Courier |
| --- | --- | --- | --- |
| `rag_chat_requests_total` | counter | Total chat requests processed | Tachograph counter — how many deliveries the courier completed |
| `rag_chat_errors_total` | counter | Total chat request errors | Tachograph reading — recorded on every courier trip and shown on the dashboard |
| `rag_tokens_input_total` | counter | Total input tokens consumed | Tally of all fuel loads the courier consumed reading shipping manifests — counts input tokens across all chat trips. |
| `rag_tokens_output_total` | counter | Total output tokens generated | Tally of fuel loads burned writing answers — counts output tokens the courier produced; acts as a generation-cost proxy. |
| `rag_documents_uploaded_total` | counter | Total documents ingested | Post office sorting raw mail into GPS-labelled boxes before the courier's first trip |
| `rag_queries_total` | counter | Total evaluated queries (from query logs) | Tachograph reading — recorded on every courier trip and shown on the dashboard |
| `rag_queries_passed_total` | counter | Queries that passed evaluation | Tachograph reading — recorded on every courier trip and shown on the dashboard |
| `rag_queries_failed_total` | counter | Queries that failed evaluation | Tachograph reading — recorded on every courier trip and shown on the dashboard |

### Gauges (point-in-time values)

| Metric | Type | What it measures | 🚚 Courier |
| --- | --- | --- | --- |
| `rag_chat_latency_p50_ms` | gauge | Median chat response time | Tachograph reading — how long the courier took on the round trip |
| `rag_chat_latency_p95_ms` | gauge | 95th percentile chat response time | Tachograph reading — how long the courier took on the round trip |
| `rag_chat_latency_p99_ms` | gauge | 99th percentile chat response time | Tachograph reading — how long the courier took on the round trip |
| `rag_query_pass_rate` | gauge | Current pass rate (0.0–1.0) | Tachograph reading — recorded on every courier trip and shown on the dashboard |
| `rag_query_avg_retrieval` | gauge | Average retrieval score | Live average of how cleanly the GPS warehouse handed the courier the right parcels across recent evaluated trips. |
| `rag_query_avg_faithfulness` | gauge | Average faithfulness score | How confidently the warehouse says 'this parcel matches' — higher = closer GPS hit |
| `rag_failures_bad_retrieval` | gauge | Count of bad_retrieval failures (last 24h) | Courier grabs the nearest parcels from the GPS warehouse before writing the answer |
| `rag_failures_hallucination` | gauge | Count of hallucination failures (last 24h) | Tachograph reading — recorded on every courier trip and shown on the dashboard |

### Why counters vs gauges?

- **Counters** only go up — Prometheus calculates rates from them (e.g., `rate(rag_chat_requests_total[5m])` = requests per second)
- **Gauges** can go up or down — they represent current state (e.g., current latency, current pass rate)

- 🚚 **Courier:** The tachograph reading — every delivery time, token cost, and quality score recorded for review.

---

## Prometheus Scrape Configuration

Add this to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'rag-chatbot'
    metrics_path: '/api/metrics'
    scrape_interval: 30s
    static_configs:
      - targets: ['localhost:8000']
```

For AWS ECS or Azure Container Apps, replace `localhost:8000` with the service
discovery target.

- 🚚 **Courier:** Adjusting the bag fit and route preferences so the courier delivers to the right address every time.

---

## Building a Grafana Dashboard

With the metrics above, you can build panels for:

| Panel | PromQL query | What it shows | 🚚 Courier |
| --- | --- | --- | --- |
| Request rate | `rate(rag_chat_requests_total[5m])` | Requests per second | Tachograph counter — how many deliveries the courier completed |
| Error rate | `rate(rag_chat_errors_total[5m]) / rate(rag_chat_requests_total[5m])` | Percentage of errors | Tachograph counter — how many deliveries the courier completed |
| Latency (p95) | `rag_chat_latency_p95_ms` | Response time for slow requests | Tachograph reading — how long the courier took on the round trip |
| Pass rate | `rag_query_pass_rate` | AI quality over time | Courier's report card — share of test deliveries that scored above the bar |
| Token burn | `rate(rag_tokens_output_total[1h])` | Output tokens per hour (cost proxy) | fuel-burn rate per hour — output tokens the courier is consuming, a live cost-per-trip proxy on the dashboard. |
| Failure breakdown | `rag_failures_bad_retrieval` / `rag_failures_hallucination` | Which failure types dominate | Courier grabs the nearest parcels from the GPS warehouse before writing the answer |

### Alert rules

```yaml
groups:
  - name: rag-chatbot
    rules:
      - alert: LowPassRate
        expr: rag_query_pass_rate < 0.80
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "RAG pass rate below 80% for 10 minutes"

      - alert: HighLatency
        expr: rag_chat_latency_p95_ms > 5000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Chat p95 latency exceeds 5 seconds"
```

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Self-Check Questions

### Tier 1 — Must understand

- [ ] What format does `/api/metrics` return? (not JSON!)
- [ ] What's the difference between a counter and a gauge?
- [ ] Where does this endpoint get its data from? (two sources)

### Tier 2 — Should understand

- [ ] Why is `text/plain; version=0.0.4` used as the media type?
- [ ] How would Prometheus calculate "requests per second" from a counter?
- [ ] Why include query evaluation metrics alongside chat metrics?

### Tier 3 — Go deeper

- [ ] How would you add a histogram for latency distribution?
- [ ] How would you add custom labels (e.g., per-document-type metrics)?

- 🚚 **Courier:** A quick quiz for the trainee dispatch clerk — answer these to confirm the key courier delivery concepts have landed.

---

## What to Study Next

- **Previous:** [Queries Endpoint](queries-endpoint-explained.md) — the failure data this builds on
- **Reference:** [API Routes Overview](../api-routes-explained.md) — how all routes fit together
- **Hands-on:** [Phase 5 Labs](../../hands-on-labs/hands-on-labs-phase-5.md) — Lab 15 exercises this endpoint

- 🚚 **Courier:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
