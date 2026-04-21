# Hands-On Labs — Phase 5: Production Observability

---

## Table of Contents

- [🫏 The Donkey Analogy — Understanding Phase 5 Metrics](#-the-donkey-analogy--understanding-phase-5-metrics)
- [Lab 14: Query Logging & Failure Triage — "What went wrong and why?"](#lab-14-query-logging--failure-triage--what-went-wrong-and-why)
  - [The concept](#the-concept)
  - [Experiment 14a — Generate and inspect query logs](#experiment-14a--generate-and-inspect-query-logs)
  - [Experiment 14b — Query the failure API](#experiment-14b--query-the-failure-api)
- [Lab 15: OpenTelemetry & Prometheus Metrics — "What's happening right now?"](#lab-15-opentelemetry--prometheus-metrics--whats-happening-right-now)
  - [The concept](#the-concept-1)
  - [Experiment 15a — Read the /metrics endpoint](#experiment-15a--read-the-metrics-endpoint)
  - [Experiment 15b — Understand metric types](#experiment-15b--understand-metric-types)
  - [Experiment 15c — Design an alert](#experiment-15c--design-an-alert)
- [Lab 16: Golden Dataset Regression Testing — "Did my change break anything?"](#lab-16-golden-dataset-regression-testing--did-my-change-break-anything)
  - [The concept](#the-concept-2)
  - [Experiment 16a — Run the golden dataset](#experiment-16a--run-the-golden-dataset)
  - [Experiment 16b — Analyse edge cases](#experiment-16b--analyse-edge-cases)
  - [Experiment 16c — Add a new case (the flywheel in action)](#experiment-16c--add-a-new-case-the-flywheel-in-action)
- [Summary — What You Learned in Phase 5](#summary--what-you-learned-in-phase-5)
  - [The Three Pillars of AI Observability](#the-three-pillars-of-ai-observability)
- [Phase 5 Labs — Skills Checklist](#phase-5-labs--skills-checklist)

---

## 🫏 The Donkey Analogy — Understanding Phase 5 Metrics

Phase 1–4 built and hardened the donkey. Phase 5 is about **watching it work in
production** — because you can't fix what you can't see.

| Metric / Concept | Donkey version | What it really measures |
| --- | --- | --- |
| **query log** | A **delivery diary** that records every trip: what the customer asked, which shelf the donkey visited, which packages it picked, what it delivered, and whether the customer was happy. One line per delivery. You read the diary to find patterns. | JSONL file where each line is a structured record: question, retrieved chunks, answer, scores, failure category, timestamp. |
| **failure triage** | The diary flags bad deliveries with a **reason code**: `bad_retrieval` = donkey went to the wrong shelf. `hallucination` = donkey added things from its pocket. `both_bad` = wrong shelf AND added extras. `off_topic` = right shelf, honest delivery, but not what the customer wanted. `marginal` = borderline — no single thing was terrible. | Automatic categorisation of failed queries based on which score dimensions fell below threshold. |
| **pass rate** | Out of 100 deliveries today, how many were **satisfactory** (overall >= 0.70)? If 87 passed — 87% pass rate. If it was 92% yesterday and 75% today — something broke. | Percentage of evaluated queries that meet the quality threshold. The single most important production health metric. |
| **Prometheus counter** | A tally board on the warehouse wall: "Total deliveries: 142. Total errors: 3. Total hay consumed: 4,500 bales." Counters only go UP — you never un-deliver a package. Prometheus calculates the *rate* for you. | Monotonically increasing metrics: total requests, total errors, total tokens. Prometheus computes `rate()` from the delta. |
| **Prometheus gauge** | A thermometer on the warehouse wall: "Current delivery time (p95): 12 minutes. Current pass rate: 87%." Gauges go UP and DOWN — they show the current state, not cumulative history. | Point-in-time metrics: latency percentiles, current pass rate, current failure counts. Can increase or decrease. |
| **golden dataset regression** | Your morning checklist of test deliveries. Yesterday all 5 passed. Today #3 failed. **Something changed overnight** — maybe a document was deleted, maybe the donkey's route changed. The checklist caught it before real customers noticed. | Running the curated evaluation suite after every change. If a previously-passing case now fails, you have a regression. |

**The Phase 5 insight:** The three pillars of AI observability map perfectly:

```text
🫏 Delivery diary     = Query logs    (Lab 14) — what happened per request
🫏 Warehouse dashboard = Metrics       (Lab 15) — what's happening right now
🫏 Morning checklist   = Golden dataset (Lab 16) — did anything break since yesterday
```

Without all three, you're running a delivery service blindfolded.

---

## Lab 14: Query Logging & Failure Triage — "What went wrong and why?"

**Skill:** Structured logging, failure classification, debugging from logs

**Time:** 20 minutes

**Prerequisite story:** I30 (Query-Level Structured Logging)

**What you'll understand after:** How every RAG query is logged as a structured record with evaluation scores and failure categories — the AI equivalent of Airflow task logs.

### The concept

```
Without structured query logging:
  User reports: "The chatbot gave me a wrong answer."
  You: grep stdout | find nothing useful | ¯\_(ツ)_/¯

With structured query logging:
  User reports: "The chatbot gave me a wrong answer."
  You: cat logs/queries/2026-04-17.jsonl | jq '.failure_category'
  → "hallucination" — the LLM fabricated an answer from irrelevant chunks.
  → Fix: improve chunking for that document type.
```

DE parallel: This is like adding structured task logs to an Airflow DAG. Without them, you're grepping stdout when something breaks at 3am. With them, you have `task_id`, `execution_date`, `status`, `duration`, `error_message` — all structured and queryable.

### Experiment 14a — Generate and inspect query logs

1. Start the chatbot:

```bash
CLOUD_PROVIDER=local QUERY_LOG_ENABLED=true python -m uvicorn src.main:app --reload
```

2. In **Swagger UI** → `POST /api/chat`, send a few questions:

```json
{"question": "What is the refund policy?"}
```
```json
{"question": "What is the capital of Mongolia?"}
```
```json
{"question": "How long?"}
```

3. Inspect the JSONL log file:

```bash
cat logs/queries/$(date +%Y-%m-%d).jsonl | python -m json.tool
```

📝 **What to look for in each record:**

| Field | What it tells you |
|---|---|
| `question` | What the user asked |
| `chunks` | Which documents were retrieved + relevance scores |
| `answer` | What the LLM responded |
| `retrieval_score` | How relevant the retrieved chunks were (0–1) |
| `faithfulness_score` | Did the answer stick to the chunks? (0–1) |
| `answer_relevance_score` | Did the answer address the question? (0–1) |
| `failure_category` | `none`, `bad_retrieval`, `hallucination`, `both_bad`, `off_topic`, `marginal` |
| `latency_ms` | How long the full pipeline took |

📝 **Expected results:**

| Question | Expected failure_category |
|---|---|
| "What is the refund policy?" | `none` (scores all high) |
| "What is the capital of Mongolia?" | `bad_retrieval` or `off_topic` (no relevant chunks) |
| "How long?" | `marginal` (ambiguous, low retrieval) |

### Experiment 14b — Query the failure API

1. List recent failures:

```
GET /api/queries/failures?category=hallucination
```

2. Get aggregate statistics:

```
GET /api/queries/stats
```

📝 **Expected stats response:**
```json
{
  "total_queries": 3,
  "pass_rate": 0.33,
  "avg_retrieval_score": 0.55,
  "avg_faithfulness_score": 0.60,
  "failure_breakdown": {
    "none": 1,
    "bad_retrieval": 1,
    "marginal": 1
  }
}
```

> ### 🔑 Key Learning
>
> The failure categories map directly to different fixes:
>
> | Failure Category | Root Cause | Fix |
> |---|---|---|
> | `bad_retrieval` | Wrong chunks returned | Better chunking, more documents, tune top_k |
> | `hallucination` | Good chunks, bad answer | Better system prompt, lower temperature |
> | `both_bad` | Wrong chunks AND bad answer | Both of the above |
> | `off_topic` | Question outside your document scope | Add documents or refuse gracefully |
> | `marginal` | Borderline scores | Monitor — may need prompt tuning |
>
> DE parallel: This is your data quality triage table. When a DQ check fails, you look at
> the category (null values, schema mismatch, duplicate keys) to know which fix to apply.
> Same principle, different domain.

> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "Users are complaining about wrong answers. How do you diagnose the problem?"**
>
> Lab 14 taught you to check query logs for the failure_category. If it's `bad_retrieval`,
> the vector store returned irrelevant chunks — fix the chunking or add documents. If it's
> `hallucination`, the LLM ignored the chunks — fix the system prompt or lower temperature.
> You don't guess — you check the structured logs.
>
> **Q: "How do you measure RAG quality over time?"**
>
> The `/api/queries/stats` endpoint gives you pass rate, average scores, and failure breakdown.
> Track these daily. If pass rate drops after a deployment, you know something regressed.

---

## Lab 15: OpenTelemetry & Prometheus Metrics — "What's happening right now?"

**Skill:** Metrics collection, Prometheus format, understanding counters vs gauges vs histograms

**Time:** 20 minutes

**Prerequisite story:** I31 (OpenTelemetry & Prometheus Metrics)

**What you'll understand after:** How real-time metrics complement structured logs — logs tell you WHAT happened to request X, metrics tell you HOW MUCH is happening across all requests.

### The concept

```
Three pillars of observability:

  Logs (I30):    "Request abc-123 failed with hallucination at 14:32:05"
                 → Debugging individual requests

  Metrics (I31): "Error rate = 12%, p95 latency = 4.2s, 847 requests today"
                 → Dashboards and alerting

  Traces (I31):  "Request abc-123: embed=120ms → search=340ms → llm=3800ms"
                 → Finding where time is spent
```

DE parallel: You already have this in your DE world:
- **Logs** = Airflow task logs (what happened to DAG run X)
- **Metrics** = CloudWatch metrics (how many tasks failed this hour)
- **Traces** = X-Ray traces (which step in the pipeline is slow)

### Experiment 15a — Read the /metrics endpoint

1. Start the chatbot and send a few chat requests first (so there's data).

2. Open the metrics endpoint:

```
GET /api/metrics
```

📝 **Expected output (Prometheus text format):**

```
# HELP chat_requests_total Total number of chat requests
# TYPE chat_requests_total counter
chat_requests_total 5

# HELP chat_errors_total Total number of chat errors
# TYPE chat_errors_total counter
chat_errors_total 0

# HELP chat_latency_p50_ms Chat latency 50th percentile
# TYPE chat_latency_p50_ms gauge
chat_latency_p50_ms 2340.0

# HELP chat_latency_p95_ms Chat latency 95th percentile
# TYPE chat_latency_p95_ms gauge
chat_latency_p95_ms 4120.0

# HELP evaluation_pass_rate Percentage of queries passing evaluation
# TYPE evaluation_pass_rate gauge
evaluation_pass_rate 0.67

# HELP failure_category_bad_retrieval Count of bad_retrieval failures
# TYPE failure_category_bad_retrieval counter
failure_category_bad_retrieval 1
```

### Experiment 15b — Understand metric types

📝 **Fill in this table:**

| Metric | Type | What it means | When it goes up |
|---|---|---|---|
| `chat_requests_total` | Counter | Total requests ever | Every chat request |
| `chat_errors_total` | Counter | Total errors ever | Every failed request |
| `chat_latency_p95_ms` | Gauge | Current 95th percentile latency | When slow requests happen |
| `evaluation_pass_rate` | Gauge | Current pass rate | Recalculated from query logs |
| `failure_category_*` | Counter | Failures by type | Each categorised failure |

> ### 🔑 Key Learning
>
> **Counters** only go up (total requests, total errors). You calculate rates from them:
> `error_rate = chat_errors_total / chat_requests_total`.
>
> **Gauges** can go up or down (current latency, current pass rate). They represent
> the current state.
>
> **Histograms** (used internally by OpenTelemetry) track distributions — how many
> requests took 0–100ms, 100–500ms, 500ms–1s, etc.
>
> DE parallel: CloudWatch has the same types. `NumberOfObjects` in S3 is a gauge.
> `GetRequests` is a counter. `Latency` in ALB is a histogram.

### Experiment 15c — Design an alert

Based on the metrics available, design alerts for these scenarios:

| Scenario | Which metric? | Threshold | Why? |
|---|---|---|---|
| System down | `chat_errors_total / chat_requests_total` | > 50% for 5 min | More errors than successes |
| Getting slow | `chat_latency_p95_ms` | > 10,000ms for 5 min | Users waiting > 10s |
| Quality dropping | `evaluation_pass_rate` | < 0.6 for 1 hour | More than 40% of answers are bad |
| Hallucinating | `failure_category_hallucination` | > 10 in 1 hour | Spike in fabricated answers |

> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "How would you set up monitoring for an AI chatbot in production?"**
>
> Three layers: (1) Structured query logs for debugging individual requests (Lab 14),
> (2) Prometheus metrics for dashboards and alerting (Lab 15), (3) OpenTelemetry traces
> for latency analysis. Alert on error rate > 50%, p95 latency > 10s, pass rate < 60%.
>
> **Q: "What's the difference between logs, metrics, and traces?"**
>
> Logs = what happened (text, per-request). Metrics = how much is happening (numbers, aggregated).
> Traces = where time is spent (spans across services). You need all three.

---

## Lab 16: Golden Dataset Regression Testing — "Did my change break anything?"

**Skill:** Regression testing, category-level analysis, dataset growth strategy

**Time:** 20 minutes

**Prerequisite story:** I32 (Expand Golden Dataset)

**What you'll understand after:** How a comprehensive golden dataset catches regressions that individual tests miss — and how it grows from real production failures.

### The concept

```
Golden dataset = your exam paper for the AI system.

5 questions (I15):  "Did you pass the midterm?"
                    Can't tell if the system handles edge cases.

25 questions (I32): "Did you pass the final exam with questions from all topics?"
                    Tests policy, logistics, products, PII, injections, ambiguity.
```

DE parallel: This is the difference between 5 DQ assertions (`row_count > 0`, `no nulls in pk`) and a comprehensive test suite (`row_count matches source`, `referential integrity`, `business rule: amounts > 0`, `no future dates`, `schema drift detection`).

### Experiment 16a — Run the golden dataset

1. Use the evaluate endpoint to test each category:

```bash
# Run evaluation against the golden dataset
python -c "
from src.evaluation.golden_dataset import GOLDEN_DATASET
from collections import Counter

categories = Counter(case['category'] for case in GOLDEN_DATASET)
print(f'Total cases: {len(GOLDEN_DATASET)}')
for cat, count in sorted(categories.items()):
    print(f'  {cat}: {count}')
"
```

📝 **Expected output:**
```
Total cases: 25
  contact: 3
  edge_case: 6
  logistics: 3
  multi_turn: 3
  pii: 4
  policy: 4
  product: 2
```

### Experiment 16b — Analyse edge cases

Look at the edge_case entries in the golden dataset:

| Case ID | What it tests | Why it matters |
|---|---|---|
| `no_context_available` | Question outside document scope | Should refuse, not hallucinate |
| `ambiguous_question` | "How long?" with no context | Should ask for clarification or give both answers |
| `prompt_injection_attempt` | "Ignore instructions..." | Must NOT leak system prompt |
| `completely_unrelated` | "Capital of Mongolia?" | Should refuse, not make up an answer |
| `negation_trick` | "Is it true refunds are NOT available?" | Must understand negation correctly |
| `multi_topic_question` | "Tell me about refunds, shipping, and exchanges" | Must address all topics |

📝 **Key insight:** The `expected_not_in_answer` field is as important as `expected_keywords`. For the prompt injection case, we check that the answer does NOT contain "system prompt" or "instructions."

### Experiment 16c — Add a new case (the flywheel in action)

Imagine you found a production failure: users asking "Can I cancel my order?" get a hallucinated answer because there's no cancellation policy document.

Add this case to `golden_dataset.py`:

```python
{
    "id": "order_cancellation",
    "category": "policy",
    "question": "Can I cancel my order?",
    "expected_keywords": ["don't have", "information", "cancellation"],
    "expected_not_in_answer": ["yes you can cancel", "within 24 hours"],
    "context_chunks": [
        ("Refunds are processed within 14 business days.", 0.35),
    ],
    "min_retrieval_score": 0.0,
    "min_faithfulness": 0.9,
},
```

📝 **Why this is important:** This case will FAIL if the system halluccinates a cancellation policy. Once you add the real cancellation policy document, you update the case with proper expected_keywords and context_chunks. The case stays in the dataset forever — ensuring future changes never regress.

> ### 🔑 Key Learning
>
> The golden dataset is a **living document**:
> - Every production bug → new test case
> - Every new document type → new test cases
> - Every model change → re-run all 25+ cases
>
> At 5 cases, you have a proof-of-concept. At 25, you have confidence.
> At 100+, you have production-grade regression testing.
>
> DE parallel: You don't ship a data pipeline with 5 DQ checks and call it done.
> Every data incident becomes a new check. Same principle for AI.

> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "How do you prevent AI quality regressions when you update the model or change chunking?"**
>
> Run the golden dataset (25+ cases across 7 categories) before and after every change.
> Compare pass rates by category. If `edge_case` pass rate drops from 100% to 60%, the
> change broke edge case handling. Revert and investigate.
>
> **Q: "How do you handle prompt injection in production?"**
>
> Two layers: (1) Guardrails (I23) block known injection patterns before they reach the LLM.
> (2) Golden dataset (I32) includes injection test cases that verify the system doesn't leak
> its system prompt. The `expected_not_in_answer` field checks for forbidden content.

---

## Summary — What You Learned in Phase 5

| Lab | Key Concept | DE Parallel |
|---|---|---|
| Lab 14 | Structured query logging with failure categories | Airflow task logs with structured error taxonomy |
| Lab 15 | Prometheus metrics (counters, gauges) for dashboards & alerts | CloudWatch metrics + alarms |
| Lab 16 | Golden dataset regression testing across 7 categories | Comprehensive DQ test suite that grows from incidents |

### The Three Pillars of AI Observability

After Phase 5, you have all three pillars implemented:

```
         ┌─────────────────────────────────────────────┐
         │           AI Observability Stack             │
         ├─────────────┬───────────────┬───────────────┤
         │   LOGS      │   METRICS     │   TRACES      │
         │  (I30)      │   (I31)       │   (I31)       │
         │             │               │               │
         │  JSONL per  │  Prometheus   │  OpenTelemetry │
         │  query with │  /metrics     │  spans per     │
         │  scores +   │  endpoint     │  request       │
         │  failure    │               │               │
         │  category   │  Counters,    │  embed_time,   │
         │             │  gauges,      │  search_time,  │
         │  Debug      │  histograms   │  llm_time      │
         │  individual │               │               │
         │  requests   │  Dashboard    │  Find where    │
         │             │  + alerting   │  time is spent │
         └─────────────┴───────────────┴───────────────┘
```

---

## Phase 5 Labs — Skills Checklist

| # | Skill | Lab | Can you explain it? |
|---|---|---|---|
| 1 | Structured query logging (JSONL format) | Lab 14 | [ ] Yes |
| 2 | Failure triage categories | Lab 14 | [ ] Yes |
| 3 | Prometheus metric types (counter, gauge, histogram) | Lab 15 | [ ] Yes |
| 4 | Alert design for AI systems | Lab 15 | [ ] Yes |
| 5 | Golden dataset regression testing | Lab 16 | [ ] Yes |
| 6 | Category-level quality analysis | Lab 16 | [ ] Yes |
| 7 | Growing golden dataset from production failures | Lab 16 | [ ] Yes |

---

> **Previous:** [Phase 4 Labs](hands-on-labs-phase-4.md) — Guardrails, re-ranking, hybrid search, bulk ingestion, HNSW tuning.
