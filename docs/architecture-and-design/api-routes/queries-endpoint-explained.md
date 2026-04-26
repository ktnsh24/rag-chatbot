# Queries Endpoint — Deep Dive

> `GET /api/queries/failures` — List recent failed queries with triage categories.
> `GET /api/queries/stats` — Aggregate pass rate, average scores, failure breakdown.

> **DE verdict: ★★★☆☆ — Structured log analysis, same as pipeline failure dashboards.**
> Nothing AI-specific in the route code itself — it reads JSONL logs, filters,
> and aggregates. The AI part is what *wrote* those logs (the evaluate pipeline).
> If you've built a `/pipeline/failures` endpoint for Airflow DAGs, you already
> know this pattern.

> **Related docs:**
> - [API Routes Overview](../api-routes-explained.md) — how all routes fit together
> - [Evaluate Endpoint Deep Dive](evaluate-endpoint-explained.md) — what produces the query logs
> - [API Reference → Queries](../../reference/api-reference.md) — request/response examples
> - [Pydantic Models](../../reference/pydantic-models.md) — model fields explained

---

## Table of Contents

1. [What These Endpoints Do — The 30-Second Version](#what-these-endpoints-do)
2. [DE Parallel — Pipeline Failure Dashboards](#de-parallel)
3. [Endpoint 1: GET /api/queries/failures — Failed Query List](#endpoint-1-failed-query-list)
4. [Endpoint 2: GET /api/queries/stats — Aggregate Statistics](#endpoint-2-aggregate-statistics)
5. [The Failure Triage Categories](#the-failure-triage-categories)
6. [How QueryLogger Works Behind the Scenes](#how-querylogger-works)
7. [The Production Debugging Workflow](#the-production-debugging-workflow)
8. [Self-Check Questions](#self-check-questions)

---

## Plain-English Walkthrough (Start Here)

> **Read this first if you're new to the chatbot.** Same courier analogy as the [Chat Walkthrough](./chat-endpoint-explained.md#plain-english-walkthrough-start-here). This explains what's specific about the queries endpoints.

### What these endpoints are for

Every time `/api/chat` answers a question, it also runs a built-in evaluator that scores the answer (Step 7 in the chat walkthrough) and writes a row to a **query log**. These two endpoints are the read side of that log:

| Route | Purpose |
| --- | --- |
| `GET /api/queries/failures` | List recent low-scoring queries with their chunks, answer, and a triage category. |
| `GET /api/queries/stats` | Aggregate: pass rate, average scores, failure breakdown by category. |

> **Courier version.** Every delivery the courier makes goes into a trip-log book with a self-graded report card. These two endpoints are how the depot manager flicks through the failures (which deliveries went wrong and why) and reads the weekly scoreboard (how many made the grade).

### Why this matters

Without these endpoints, the only way to know your chatbot is degrading is to read every log line by hand or notice angry users. With them, you can:

1. Watch `pass_rate` over time — if it drops from 90% to 70%, something is wrong.
2. Hit `/api/queries/failures` to see exactly *which* queries failed and *why*.
3. Read the chunks the warehouse returned for each failure — was the data missing? Was the LLM hallucinating?
4. Fix the root cause, redeploy, and watch the pass rate recover.

This is the **production debugging workflow** for a RAG system. It's the difference between "the chatbot feels worse this week" and "vector store recall on `policy.*` questions dropped to 0.42 because someone uploaded a malformed PDF on Tuesday."

### Failures endpoint — what really happens

`GET /api/queries/failures` returns a list of failed query records. A query is considered failed if its overall evaluator score is below 0.70.

Three query parameters control the view:

- **`limit`** (1–100, default 20) — how many rows to return.
- **`days`** (1–30, default 7) — how far back to look.
- **`category`** (optional) — filter to one of the failure categories.

The handler delegates to `query_logger.get_failures(limit, days, category)` which runs a SELECT against the query log table. There's no expensive computation in the route itself — it's a thin reader.

### The five failure categories

Every failed query is automatically classified into one of these buckets when it's logged:

| Category | What it means | What to investigate |
| --- | --- | --- |
| **`bad_retrieval`** | Chunks were irrelevant; LLM had nothing useful to work with. | Vector store quality — chunk size, embedding model, or missing data. |
| **`hallucination`** | Chunks were good; LLM made stuff up anyway. | Prompt template, model temperature, model choice. |
| **`both_bad`** | Wrong chunks **and** the LLM improvised on top of them. | The whole pipeline — start with retrieval. |
| **`off_topic`** | Good chunks, faithful answer, but didn't address the question. | Prompt template — the LLM is summarising rather than answering. |
| **`marginal`** | Failed overall but no single dimension is terrible. | Often a borderline case; not worth deep investigation individually. |

The classification is computed by `QueryLogger.classify_failure(scores)` based on which sub-scores are below threshold. You don't have to know the rules — just look at the categories in `/api/queries/failures` to triage faster.

### Stats endpoint — what really happens

`GET /api/queries/stats` returns a single dictionary aggregating the last `days` (default 1) of query log activity:

```jsonc
{
  "total_queries": 412,
  "passed": 360,
  "failed": 52,
  "pass_rate": 87.4,
  "avg_retrieval": 0.81,
  "avg_faithfulness": 0.79,
  "avg_relevance": 0.84,
  "failure_breakdown": {
    "bad_retrieval": 18,
    "hallucination": 11,
    "both_bad": 3,
    "off_topic": 14,
    "marginal": 6
  }
}
```

This is what `/api/metrics` reads internally to expose pass rate and per-category counts to Prometheus.

### A worked debugging session

1. You hit `/api/queries/stats?days=7` and notice `pass_rate` dropped from 91% (last week) to 73% (this week).
2. You hit `/api/queries/failures?days=7&limit=50&category=bad_retrieval` to focus on the most common failure type.
3. Each record shows the question, the chunks the warehouse returned (with their relevance scores), and the LLM's answer. You spot a pattern: every failure is asking about a specific product line.
4. You check the document upload log — that product's PDF was re-ingested on Tuesday with a different chunk size. The smaller chunks no longer contain enough context for the embedder to match.
5. You revert the chunk-size change and reprocess. Pass rate climbs back over the next few hours as new traffic arrives.

This is the loop the queries endpoints are designed to support.

### Quirks worth knowing

1. **Returns 503 if the query logger isn't initialised.** Both endpoints depend on `app.state.query_logger`. If it failed to initialise (database creds missing, etc.) you get `503 Query logger not initialized` rather than empty results. That makes the failure mode obvious but means you can't get a "yes the table is just empty" response.
2. **No auth.** Anyone hitting the URL can read every recent failed question, including the original user text. If users ask sensitive questions, those become readable here. Lock down at the network layer.
3. **The `category` parameter is unvalidated.** You can pass any string and the handler will happily filter by it — likely returning zero results for typos.
4. **Stats are computed on every request.** No caching. On a large log table this can be slow; index `(created_at, scores_overall)`.
5. **`marginal` is a heuristic catch-all** — it doesn't mean anything specific is wrong. Don't spend time on these one by one.

### TL;DR

- Two read-only endpoints over the query log table that gets written on every chat call.
- Failures endpoint lets you list low-scoring queries by category with full chunks + answer.
- Stats endpoint produces the aggregate dashboard view (pass rate, averages, failure breakdown).
- Together they form the production debugging workflow: watch the rate, drill into failures, fix root causes.
- No auth — sensitive questions become readable. Lock down at the network layer if needed.

---

## What These Endpoints Do

Every time `/api/evaluate` runs, the QueryLogger writes a structured JSONL record
with the question, retrieved chunks, LLM answer, evaluation scores, and a failure
category (if the score is below threshold).

These two endpoints **read those logs** and present them for debugging:

```text
/api/evaluate runs → QueryLogger writes JSONL → /api/queries/* reads JSONL
```

**`/api/queries/failures`** returns recent failed queries so you can see *what*
went wrong — bad retrieval, hallucination, or both.

**`/api/queries/stats`** returns aggregate numbers — total queries, pass rate,
average scores per dimension, and failure breakdown by category.

- 🚚 **Courier:** The specific delivery address the courier is dispatched to — each route handles a different type of parcels drop-off.

---

## DE Parallel

This is identical to building a pipeline monitoring API:

| Concept | Data Engineering | RAG Chatbot | 🚚 Courier |
| --- | --- | --- | --- |
| **Log source** | Airflow task logs, DAG run metadata | JSONL query logs from QueryLogger | Courier's trip log — every delivery's details written to disk for later review |
| **Failure list** | `/pipeline/failures` — which DAGs failed and why | `/queries/failures` — which queries failed and why | Robot dispatch clerk — Failure list: /pipeline/failures — which DAGs failed and why · /queries/failures — which queries failed and why |
| **Aggregate stats** | DAG success rate, avg duration, failure reasons | Pass rate, avg scores, failure categories | Depot-wide summary of how many courier trips passed, average scores, and which reason codes dominated failures |
| **Triage** | "data_quality", "timeout", "permission_denied" | "bad_retrieval", "hallucination", "both_bad" | Reason codes stamped on failed deliveries so the dispatch clerk knows which courier-trip failure to investigate first. |
| **Action** | Fix the DAG, re-run, verify | Fix retrieval/prompt, re-evaluate, verify | Instructions tucked in the pannier — Action: Fix the DAG, re-run, verify · Fix retrieval/prompt, re-evaluate, verify |

**Bottom line:** The route code is pure CRUD over structured logs. The AI
complexity lives in how the logs were *produced* (by the evaluate pipeline), not
in how they're *served*.

- 🚚 **Courier:** Running multiple couriers on the same route to confirm that AI engineering and data engineering practices mirror each other.

---

## Endpoint 1: Failed Query List

### Route definition

```python
@router.get(
    "/queries/failures",
    response_model=list[QueryLogRecord],
    summary="List Failed Queries",
)
async def list_failures(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    days: int = Query(default=7, ge=1, le=30),
    category: str | None = Query(default=None),
) -> list[QueryLogRecord]:
```

### What each parameter does

| Parameter | Default | What it controls | 🚚 Courier |
| --- | --- | --- | --- |
| `limit` | 20 | Max results to return (1–100) | Courier-side view of limit — affects how the courier loads, reads, or delivers the parcels |
| `days` | 7 | How far back to search (1–30 days) | Courier-side view of days — affects how the courier loads, reads, or delivers the parcels |
| `category` | None | Filter by failure type: `bad_retrieval`, `hallucination`, `both_bad`, `off_topic`, `marginal` | Filters the trip log to only show deliveries flagged with a chosen failure code such as hallucination or bad_retrieval. |

### Example response

```json
[
  {
    "timestamp": "2026-04-18T14:30:00Z",
    "question": "What is the remote work policy?",
    "answer": "The refund policy allows returns within 30 days...",
    "scores": {
      "overall": 0.42,
      "retrieval": 0.25,
      "faithfulness": 0.85,
      "relevance": 0.15
    },
    "failure_category": "bad_retrieval",
    "chunks": [
      {"content": "Refund policy excerpt...", "score": 0.31}
    ]
  }
]
```

### How to read this

The example above shows a classic **bad_retrieval** failure: the user asked about
remote work policy, but the vector store returned refund policy chunks (retrieval
score 0.25). The LLM faithfully summarised *what it was given* (faithfulness 0.85),
but the answer is irrelevant (relevance 0.15). Fix: upload the remote work policy
document, or tune chunk size/overlap.

- 🚚 **Courier:** The specific delivery address the courier is dispatched to — each route handles a different type of parcels drop-off.

---

## Endpoint 2: Aggregate Statistics

### Route definition

```python
@router.get(
    "/queries/stats",
    summary="Query Quality Stats",
)
async def query_stats(
    request: Request,
    days: int = Query(default=1, ge=1, le=30),
) -> dict:
```

### Example response

```json
{
  "total_queries": 48,
  "passed": 42,
  "failed": 6,
  "pass_rate": 87.5,
  "avg_retrieval": 0.72,
  "avg_faithfulness": 0.85,
  "avg_relevance": 0.78,
  "failure_breakdown": {
    "bad_retrieval": 3,
    "hallucination": 1,
    "both_bad": 1,
    "off_topic": 0,
    "marginal": 1
  }
}
```

### How to use this

- **Pass rate dropping?** → Check `/queries/failures` to see which queries failed
- **Low avg_retrieval?** → Documents may be missing, chunks too large, or embeddings stale
- **Low avg_faithfulness?** → LLM is hallucinating — consider tighter prompts or guardrails
- **High bad_retrieval count?** → Vector store needs more/better documents

- 🚚 **Courier:** The specific delivery address the courier is dispatched to — each route handles a different type of parcels drop-off.

---

## The Failure Triage Categories

When a query's overall score falls below 0.70, the QueryLogger assigns a failure
category based on which dimensions failed:

| Category | Retrieval | Faithfulness | Relevance | What it means | 🚚 Courier |
| --- | --- | --- | --- | --- | --- |
| `bad_retrieval` | Low | OK | Low | Wrong chunks retrieved — the LLM couldn't answer because it got irrelevant context | Courier arrived with the wrong parcel — couldn't write a useful note because the parcels had nothing to do with the question |
| `hallucination` | OK | Low | OK | Right chunks, but the LLM made things up instead of using them | Parcel was correct, but the courier scribbled extras from memory instead of using what it was carrying |
| `both_bad` | Low | Low | — | Wrong chunks AND the LLM improvised — worst case | Wrong parcel and the courier made things up on top — worst possible delivery |
| `off_topic` | OK | OK | Low | Chunks were relevant, LLM was faithful, but the answer missed the actual question | Right parcel, honest courier, but the answer never reached the address the customer wrote on the question |
| `marginal` | — | — | — | Failed overall but no single dimension is terrible — borderline case | Borderline courier trip — nothing was outright bad, but the report card's overall score still slipped under the bar |

### DE parallel for triage

This is the same pattern as categorising pipeline failures:

- `bad_retrieval` → "data_quality" (wrong input data)
- `hallucination` → "logic_error" (code produced wrong output from correct input)
- `both_bad` → "cascade_failure" (bad data + bad logic)
- `off_topic` → "schema_mismatch" (correct processing, wrong target)

- 🚚 **Courier:** When the courier returns empty-hooved — use the trip log and bag inspection checklist to find what went wrong.

---

## How QueryLogger Works

The QueryLogger is initialised at app startup and stored on `app.state`:

```text
App startup:
    query_logger = QueryLogger(log_dir="data/query_logs/")
    app.state.query_logger = query_logger

/api/evaluate runs:
    result = await rag_chain.evaluate(question, expected_answer)
    await query_logger.log(result)          # ← writes JSONL

/api/queries/failures:
    records = await query_logger.get_failures(limit=20, days=7)
    return records                          # ← reads JSONL
```

Log files are stored as JSONL (one JSON record per line) in `data/query_logs/`,
rotated daily. This is the same pattern as structured application logs — no
database needed, just append-only files.

- 🚚 **Courier:** The warehouse robot dispatched to find the right parcel shelf — it uses GPS coordinates (embeddings) to locate the nearest relevant chunks in ~9 hops.

---

## The Production Debugging Workflow

```text
1. Dashboard shows pass rate dropped from 92% to 75%
       │
       ▼
2. GET /api/queries/stats?days=1
   → "failed: 12, failure_breakdown: {bad_retrieval: 8, hallucination: 4}"
       │
       ▼
3. GET /api/queries/failures?category=bad_retrieval&limit=5
   → See the actual questions that failed + what chunks were retrieved
       │
       ▼
4. Root cause: new questions about a policy that hasn't been uploaded
       │
       ▼
5. POST /api/documents/upload → upload the missing policy document
       │
       ▼
6. POST /api/evaluate/suite → re-run golden dataset → pass rate back to 90%+
```

This is the **data flywheel** in action: detect failure → diagnose → fix → verify.

- 🚚 **Courier:** Checking the courier's hooves, bag straps, and GPS signal before concluding it's lost — most delivery failures have a simple root cause.

---

## Self-Check Questions

### Tier 1 — Must understand

- [ ] What do the two queries endpoints return?
- [ ] Where does the query log data come from? (which endpoint writes it?)
- [ ] What does `failure_category: bad_retrieval` mean in practice?

### Tier 2 — Should understand

- [ ] How would you use `/queries/stats` to detect a regression?
- [ ] Why is JSONL used instead of a database for query logs?
- [ ] What's the debugging workflow when pass rate drops?

### Tier 3 — Go deeper

- [ ] How would you add a new failure category (e.g., `token_limit_exceeded`)?
- [ ] How would you build a Grafana dashboard from `/queries/stats`?

- 🚚 **Courier:** A quick quiz for the trainee dispatch clerk — answer these to confirm the key courier delivery concepts have landed.

---

## What to Study Next

- **Previous:** [Evaluate Endpoint](evaluate-endpoint-explained.md) — what produces the query logs
- **Next:** [Metrics Endpoint](metrics-endpoint-explained.md) — Prometheus metrics for dashboards
- **Reference:** [API Routes Overview](../api-routes-explained.md) — how all routes fit together

- 🚚 **Courier:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
