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

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

---

## DE Parallel

| Concept | Data Engineering | RAG Chatbot | 🫏 Donkey |
| --- | --- | --- | --- |
| **What you expose** | DAG run count, task duration, queue depth | Chat requests, LLM latency, token usage | Tachograph entries — every chat trip's count, latency, and token usage published for scrapers |
| **Format** | Prometheus text exposition | Prometheus text exposition | Tachograph 📊 |
| **Scraper** | Prometheus → Grafana | Prometheus → Grafana | Tachograph 📊 |
| **Alert on** | DAG failure rate > 5%, task duration > SLA | Pass rate < 80%, latency p95 > 2s | Hoof check 🔧 |
| **Pattern** | `GET /metrics` on Airflow webserver | `GET /api/metrics` on FastAPI | Tachograph 📊 |

**Bottom line:** Same infrastructure pattern, different business metrics.

- 🫏 **Donkey:** Running multiple donkeys on the same route to confirm that AI engineering and data engineering practices mirror each other.

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

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

---

## Metrics Exposed

### Counters (monotonically increasing)

| Metric | Type | What it measures | 🫏 Donkey |
| --- | --- | --- | --- |
| `rag_chat_requests_total` | counter | Total chat requests processed | Tachograph counter — how many deliveries the donkey completed |
| `rag_chat_errors_total` | counter | Total chat request errors | Tachograph reading — recorded on every donkey trip and shown on the dashboard |
| `rag_tokens_input_total` | counter | Total input tokens consumed | Cargo unit ⚖️ |
| `rag_tokens_output_total` | counter | Total output tokens generated | Cargo unit ⚖️ |
| `rag_documents_uploaded_total` | counter | Total documents ingested | Post office sorting raw mail into GPS-labelled boxes before the donkey's first trip |
| `rag_queries_total` | counter | Total evaluated queries (from query logs) | Tachograph reading — recorded on every donkey trip and shown on the dashboard |
| `rag_queries_passed_total` | counter | Queries that passed evaluation | Tachograph reading — recorded on every donkey trip and shown on the dashboard |
| `rag_queries_failed_total` | counter | Queries that failed evaluation | Tachograph reading — recorded on every donkey trip and shown on the dashboard |

### Gauges (point-in-time values)

| Metric | Type | What it measures | 🫏 Donkey |
| --- | --- | --- | --- |
| `rag_chat_latency_p50_ms` | gauge | Median chat response time | Tachograph reading — how long the donkey took on the round trip |
| `rag_chat_latency_p95_ms` | gauge | 95th percentile chat response time | Tachograph reading — how long the donkey took on the round trip |
| `rag_chat_latency_p99_ms` | gauge | 99th percentile chat response time | Tachograph reading — how long the donkey took on the round trip |
| `rag_query_pass_rate` | gauge | Current pass rate (0.0–1.0) | Tachograph reading — recorded on every donkey trip and shown on the dashboard |
| `rag_query_avg_retrieval` | gauge | Average retrieval score | backpack fetch 🎒 |
| `rag_query_avg_faithfulness` | gauge | Average faithfulness score | How confidently the warehouse says 'this backpack matches' — higher = closer GPS hit |
| `rag_failures_bad_retrieval` | gauge | Count of bad_retrieval failures (last 24h) | Donkey grabs the nearest backpacks from the GPS warehouse before writing the answer |
| `rag_failures_hallucination` | gauge | Count of hallucination failures (last 24h) | Tachograph reading — recorded on every donkey trip and shown on the dashboard |

### Why counters vs gauges?

- **Counters** only go up — Prometheus calculates rates from them (e.g., `rate(rag_chat_requests_total[5m])` = requests per second)
- **Gauges** can go up or down — they represent current state (e.g., current latency, current pass rate)

- 🫏 **Donkey:** The tachograph reading — every delivery time, token cost, and quality score recorded for review.

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

- 🫏 **Donkey:** Adjusting the bag fit and route preferences so the donkey delivers to the right address every time.

---

## Building a Grafana Dashboard

With the metrics above, you can build panels for:

| Panel | PromQL query | What it shows | 🫏 Donkey |
| --- | --- | --- | --- |
| Request rate | `rate(rag_chat_requests_total[5m])` | Requests per second | Tachograph counter — how many deliveries the donkey completed |
| Error rate | `rate(rag_chat_errors_total[5m]) / rate(rag_chat_requests_total[5m])` | Percentage of errors | Tachograph counter — how many deliveries the donkey completed |
| Latency (p95) | `rag_chat_latency_p95_ms` | Response time for slow requests | Tachograph reading — how long the donkey took on the round trip |
| Pass rate | `rag_query_pass_rate` | AI quality over time | Donkey's report card — share of test deliveries that scored above the bar |
| Token burn | `rate(rag_tokens_output_total[1h])` | Output tokens per hour (cost proxy) | Cargo unit ⚖️ |
| Failure breakdown | `rag_failures_bad_retrieval` / `rag_failures_hallucination` | Which failure types dominate | Donkey grabs the nearest backpacks from the GPS warehouse before writing the answer |

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

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

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

- 🫏 **Donkey:** A quick quiz for the trainee stable hand — answer these to confirm the key donkey delivery concepts have landed.

---

## What to Study Next

- **Previous:** [Queries Endpoint](queries-endpoint-explained.md) — the failure data this builds on
- **Reference:** [API Routes Overview](../api-routes-explained.md) — how all routes fit together
- **Hands-on:** [Phase 5 Labs](../../hands-on-labs/hands-on-labs-phase-5.md) — Lab 15 exercises this endpoint

- 🫏 **Donkey:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
