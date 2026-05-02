# Module 2: Observability Fundamentals

**Question this module answers:** "What is the system doing right now in production?"

**Labs in this module:** 3 hands-on experiments
- Lab 4: Metric Types (Counter vs Gauge)
- Lab 5: Quality and Reliability Metrics  
- Lab 6: Failure Category Triage

**Time:** 90 minutes total

**Prerequisite:** Run Module 1 labs first (so you have evaluation data).

---

## Lab 4: Counter vs Gauge — Understanding Metric Types

### Goal

Learn the difference between counters (cumulative totals) and gauges (point-in-time values).

### Run in Swagger UI

`GET /api/metrics` → opens Prometheus text format.

Copy the URL `http://localhost:8000/api/metrics` into your browser or use curl:

```bash
curl http://localhost:8000/api/metrics
```

### Sample output with numbers

```text
# TYPE rag_chat_requests_total counter
rag_chat_requests_total 120

# TYPE rag_chat_errors_total counter
rag_chat_errors_total 9

# TYPE rag_chat_error_rate_percent gauge
rag_chat_error_rate_percent 7.5

# TYPE rag_chat_latency_p50_ms gauge
rag_chat_latency_p50_ms 1800

# TYPE rag_chat_latency_p95_ms gauge
rag_chat_latency_p95_ms 6200

# TYPE rag_chat_latency_p99_ms gauge
rag_chat_latency_p99_ms 12100

# TYPE rag_queries_pass_rate_percent gauge
rag_queries_pass_rate_percent 68

# TYPE rag_queries_failure_bad_retrieval counter
rag_queries_failure_bad_retrieval 14

# TYPE rag_queries_failure_hallucination counter
rag_queries_failure_hallucination 6

# TYPE rag_queries_failure_off_topic counter
rag_queries_failure_off_topic 11
```

### Interpret each metric type

| Metric | Type | What the number means | How to read it | How to use it |
| --- | --- | --- | --- | --- |
| `rag_chat_requests_total` | Counter | Total chat requests since process start. Only goes UP. | `120` = 120 total requests ever. If it was 100 before, that's 20 new requests. | Use **rate** not raw value: "We got 20 requests in the last 5 minutes" = `(120-100)/5min = 4 req/min`. |
| `rag_chat_errors_total` | Counter | Total errors since process start. Only goes UP. | `9` = 9 requests failed total. | Calculate error rate: `9/120 = 7.5%`. Alert if rate rises unexpectedly. |
| `rag_chat_error_rate_percent` | Gauge | Current error percentage computed from counters. Can go UP or DOWN. | `7.5` = Right now, 7.5% of requests fail. | Alert if `> 10%` for 5 minutes = reliability issue. |
| `rag_chat_latency_p50_ms` | Gauge | Median response time in milliseconds. Can vary per sample. | `1800` = Half of recent requests are faster than 1.8 seconds. | Typical baseline. Compare p50 vs p95 to spot tail latency issues. |
| `rag_chat_latency_p95_ms` | Gauge | 95th percentile latency. Can vary per sample. | `6200` = 95 out of 100 requests are faster than 6.2 seconds. | Alert if `> 8000ms` = UX degradation. This is usually more important than average. |
| `rag_chat_latency_p99_ms` | Gauge | 99th percentile latency (worst "normal" requests). Can vary. | `12100` = Worst 1% of requests are around 12.1 seconds. | Watch for spikes. If p99 jumps 5x = tail instability or timeouts. |
| `rag_queries_pass_rate_percent` | Gauge | Percent of evaluated queries passing quality checks. Can go UP or DOWN. | `68` = 68% pass today. 32% fail (need triage). | Alert if `< 70%` for 1 hour = quality regression. Check failure categories. |
| `rag_queries_failure_bad_retrieval` | Counter | Total queries that failed due to poor chunk relevance. Only goes UP. | `14` = 14 queries failed because retrieval was weak. | Highest failure reason here → tune `top_k`, reranker, chunking first. |
| `rag_queries_failure_hallucination` | Counter | Total queries that failed due to unsupported claims. Only goes UP. | `6` = 6 queries made up facts. | Tighten system prompt and grounding rules. Lower than bad_retrieval here = good sign. |
| `rag_queries_failure_off_topic` | Counter | Total queries that failed due to intent mismatch. Only goes UP. | `11` = 11 queries answered the wrong question. | Improve query routing and prompt intent framing. |

### Key insight: Counter vs Gauge

| Type | Behavior | Example | Alert strategy |
| --- | --- | --- | --- |
| **Counter** | Only increases or resets on app restart. | `requests_total: 100 → 105 → 110` = 3 requests happened. | Alert on RATE, not raw value: "rate > 10 req/sec for 5 min". |
| **Gauge** | Goes up and down, represents NOW. | `latency_p95: 4200 → 6800 → 5100` = latency varies. | Alert on THRESHOLD: "if > 8000 for 5 min". |

**Common mistake:** Setting alert on counter raw value. ❌ Don't do: "if `requests_total > 500` alert". ✅ Do: "if `rate(requests_total) > 50 per minute` alert".

### Action table

| If you see this | First action |
| --- | --- |
| `error_rate_percent > 10` | Check app logs for exception types. Is it a known issue or a regression? |
| `latency_p95 > 8000` and `latency_p50 < 3000` | Tail latency issue (slow 5%). Check retrieval and LLM generation times. |
| `latency_p95` jumping 3x in 5 minutes | Likely cascade failure or provider latency. Check dependencies. |
| `pass_rate_percent < 70` | Drop to Module 3 lab to see which failure category spiked. |

---

## Lab 5: Quality and Reliability Metrics

### Goal

Understand which metrics matter for quality and cost, and how to set alert thresholds.

### Run in Swagger UI

Send 10-20 test queries via `POST /api/chat` to generate metric data, then check `/api/metrics`.

### Sample scenario

After running 120 requests:

```text
rag_chat_requests_total 120
rag_chat_errors_total 9
rag_chat_error_rate_percent 7.5

rag_chat_latency_p50_ms 1800
rag_chat_latency_p95_ms 6200

rag_queries_pass_rate_percent 68
rag_queries_failure_bad_retrieval 14
rag_queries_failure_hallucination 6
rag_queries_failure_off_topic 11

rag_tokens_input_total 45000
rag_tokens_output_total 12000
```

### Interpret the health picture

| Area | Metric | Value | Health status | Action |
| --- | --- | --- | --- | --- |
| **Reliability** | error_rate_percent | 7.5 | ⚠️ Borderline (< 10% = OK, > 10% = warning) | Monitor error logs. |
| **UX Speed** | latency_p95_ms | 6200 | ✅ Good (< 8000 typical SLO) | Acceptable. |
| **Quality** | pass_rate_percent | 68 | ⚠️ Weak (< 70% = fail, ≥ 70% = pass) | Drop to Module 3 to triage failures. |
| **Cost** | input_tokens / request | 45000/120 = 375 | ✅ Reasonable | Expected for 5-chunk retrieval. |
| **Cost** | output_tokens / request | 12000/120 = 100 | ✅ Reasonable | Answers are concise. |

### Action table

| Symptom | Root cause check | Fix |
| --- | --- | --- |
| error_rate 7.5% staying stable for 1 hour | Is it network, model provider, or app bug? | Read logs in `/logs/` or check provider status. |
| pass_rate 68% and error_rate 7.5% both rising | System overloaded or model degradation? | Reduce `top_k`, check model provider uptime. |
| latency_p95 6200 after code deploy | Did code change add expensive stage? | Revert and profile. Likely retrieval or LLM generation. |
| input tokens 375/req but nothing changed | More complex queries or looser retrieval? | Check query logs in `/api/queries/stats` for trend. |

---

## Lab 6: Failure Category Triage

### Goal

When quality drops, quickly identify which component failed.

### Run in Swagger UI

`GET /api/queries/stats` → "Try it out" → "Execute"

### Sample output with numbers

```json
{
  "total_queries_evaluated": 120,
  "passed_queries": 82,
  "failed_queries": 38,
  "pass_rate_percent": 68,
  "failure_breakdown": {
    "bad_retrieval": 14,
    "hallucination": 6,
    "off_topic": 11,
    "marginal": 7
  },
  "average_scores": {
    "retrieval": 0.71,
    "faithfulness": 0.78,
    "answer_relevance": 0.81
  }
}
```

### Interpret failure categories

| Category | Count | What it means | First fix to try |
| --- | --- | --- | --- |
| `bad_retrieval` | 14 (37% of failures) | Vector store returned irrelevant chunks. | Increase `top_k`, enable reranker, or add missing documents. |
| `hallucination` | 6 (16% of failures) | Answer added unsupported facts. | Tighten system prompt and answer constraints. |
| `off_topic` | 11 (29% of failures) | Answer answered wrong question. | Improve query intent detection or routing. |
| `marginal` | 7 (18% of failures) | One or more scores just under threshold (not critical). | Borderline cases; improve retrieval or grounding slightly. |

### Prioritize fixes

Bad retrieval is 37% of failures → **Fix retrieval first** (biggest impact).

If bad_retrieval < 20% but hallucination > 20% → **Fix prompt grounding next**.

### Action table

| If you see this | First action |
| --- | --- |
| bad_retrieval > 30% of failures | Module 4 Lab: increase `top_k` from 5 to 10, test again. |
| hallucination > 20% of failures | Tighten system prompt: "Only use facts from retrieved context." |
| off_topic > 25% of failures | Check if questions are ambiguous. Add intent examples to system prompt. |
| marginal > 20% of failures | Marginal means scores are close to threshold. Small tuning might move many to pass. |

---

## What You've Learned

- **Counters = totals** (use `rate()` in alerts, not raw value)
- **Gauges = now** (use thresholds in alerts)
- **p95 latency** > p50 by 3-4x is normal; spikes are bad
- **Pass rate < 70%** = quality issue; always check failure breakdown
- **Failure categories tell you where to fix:** bad_retrieval → tuning, hallucination → prompt, off_topic → routing
- **Alert set (minimum):** error_rate > 10%, latency_p95 > 8s, pass_rate < 70%

---

## Next Steps

- Move to [Module 3: Failure Diagnosis](module-3-diagnosis.md) to learn how to read query logs
- Or jump to [Module 4: Tuning](module-4-tuning.md) to fix bad_retrieval issues
