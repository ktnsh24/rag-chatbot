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

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

---

## DE Parallel

This is identical to building a pipeline monitoring API:

| Concept | Data Engineering | RAG Chatbot | 🫏 Donkey |
| --- | --- | --- | --- |
| **Log source** | Airflow task logs, DAG run metadata | JSONL query logs from QueryLogger | Donkey's trip log — every delivery's details written to disk for later review |
| **Failure list** | `/pipeline/failures` — which DAGs failed and why | `/queries/failures` — which queries failed and why | Robot hand 🤖 |
| **Aggregate stats** | DAG success rate, avg duration, failure reasons | Pass rate, avg scores, failure categories | Hoof check 🔧 |
| **Triage** | "data_quality", "timeout", "permission_denied" | "bad_retrieval", "hallucination", "both_bad" | Memory drift ⚠️ |
| **Action** | Fix the DAG, re-run, verify | Fix retrieval/prompt, re-evaluate, verify | Delivery note 📋 |

**Bottom line:** The route code is pure CRUD over structured logs. The AI
complexity lives in how the logs were *produced* (by the evaluate pipeline), not
in how they're *served*.

- 🫏 **Donkey:** Running multiple donkeys on the same route to confirm that AI engineering and data engineering practices mirror each other.

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

| Parameter | Default | What it controls | 🫏 Donkey |
| --- | --- | --- | --- |
| `limit` | 20 | Max results to return (1–100) | Donkey-side view of limit — affects how the donkey loads, reads, or delivers the cargo |
| `days` | 7 | How far back to search (1–30 days) | Donkey-side view of days — affects how the donkey loads, reads, or delivers the cargo |
| `category` | None | Filter by failure type: `bad_retrieval`, `hallucination`, `both_bad`, `off_topic`, `marginal` | Memory drift ⚠️ |

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

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

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

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

---

## The Failure Triage Categories

When a query's overall score falls below 0.70, the QueryLogger assigns a failure
category based on which dimensions failed:

| Category | Retrieval | Faithfulness | Relevance | What it means | 🫏 Donkey |
| --- | --- | --- | --- | --- | --- |
| `bad_retrieval` | Low | OK | Low | Wrong chunks retrieved — the LLM couldn't answer because it got irrelevant context | Donkey arrived with the wrong backpack — couldn't write a useful note because the cargo had nothing to do with the question |
| `hallucination` | OK | Low | OK | Right chunks, but the LLM made things up instead of using them | Backpack was correct, but the donkey scribbled extras from memory instead of using what it was carrying |
| `both_bad` | Low | Low | — | Wrong chunks AND the LLM improvised — worst case | Wrong backpack and the donkey made things up on top — worst possible delivery |
| `off_topic` | OK | OK | Low | Chunks were relevant, LLM was faithful, but the answer missed the actual question | Right backpack, honest donkey, but the answer never reached the address the customer wrote on the question |
| `marginal` | — | — | — | Failed overall but no single dimension is terrible — borderline case | Hoof check 🔧 |

### DE parallel for triage

This is the same pattern as categorising pipeline failures:

- `bad_retrieval` → "data_quality" (wrong input data)
- `hallucination` → "logic_error" (code produced wrong output from correct input)
- `both_bad` → "cascade_failure" (bad data + bad logic)
- `off_topic` → "schema_mismatch" (correct processing, wrong target)

- 🫏 **Donkey:** When the donkey returns empty-hooved — use the trip log and bag inspection checklist to find what went wrong.

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

- 🫏 **Donkey:** The warehouse robot dispatched to find the right backpack shelf — it uses GPS coordinates (embeddings) to locate the nearest relevant chunks in ~9 hops.

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

- 🫏 **Donkey:** Checking the donkey's hooves, bag straps, and GPS signal before concluding it's lost — most delivery failures have a simple root cause.

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

- 🫏 **Donkey:** A quick quiz for the trainee stable hand — answer these to confirm the key donkey delivery concepts have landed.

---

## What to Study Next

- **Previous:** [Evaluate Endpoint](evaluate-endpoint-explained.md) — what produces the query logs
- **Next:** [Metrics Endpoint](metrics-endpoint-explained.md) — Prometheus metrics for dashboards
- **Reference:** [API Routes Overview](../api-routes-explained.md) — how all routes fit together

- 🫏 **Donkey:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
