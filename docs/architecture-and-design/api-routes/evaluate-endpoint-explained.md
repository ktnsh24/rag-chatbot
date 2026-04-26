# Evaluate Endpoint — Deep Dive

> `POST /api/evaluate` — Evaluate a single question through the live RAG pipeline.
> `POST /api/evaluate/suite` — Run the golden dataset evaluation suite.

> **DE verdict: ★★★★★ — This is the AI Engineer's quality assurance endpoint.**
> It combines the RAG query pipeline (same as `/api/chat`) with the evaluation
> framework to give you quality scores alongside answers. This is what makes you
> an AI Engineer — not just building the pipeline, but measuring if it works well.

> **Related docs:**
> - [API Routes Overview](../api-routes-explained.md) — how all routes fit together
> - [Chat Endpoint Deep Dive](chat-endpoint-explained.md) — the RAG query pipeline this builds on
> - [Evaluation Framework](../../ai-engineering/evaluation-framework-deep-dive.md) — the scoring engine
> - [Golden Dataset](../../ai-engineering/golden-dataset-deep-dive.md) — the test cases
> - [API Reference → Evaluation](../../reference/api-reference.md) — request/response examples
> - [Pydantic Models](../../reference/pydantic-models.md) — model fields explained

---

## Table of Contents

1. [What This Endpoint Does — The 30-Second Version](#what-this-endpoint-does)
2. [DE Parallel — This Is Your dbt Test Suite](#de-parallel)
3. [Endpoint 1: POST /api/evaluate — Single Question](#endpoint-1-single-question)
4. [Endpoint 2: POST /api/evaluate/suite — Golden Dataset Suite](#endpoint-2-golden-dataset-suite)
5. [Reading the Scores — What Good Looks Like](#reading-the-scores--what-good-looks-like)
6. [The AI Engineering Workflow — Change → Evaluate → Compare](#the-ai-engineering-workflow)
7. [How to Use This in Practice](#how-to-use-this-in-practice)
8. [Self-Check Questions](#self-check-questions)

---

## Plain-English Walkthrough (Start Here)

> **Read this first if you're new to the chatbot.** Same courier analogy as the [Chat Walkthrough](./chat-endpoint-explained.md#plain-english-walkthrough-start-here). This explains what's specific about the evaluate endpoints.

### What these endpoints are for

The chatbot can answer questions. Fine. But how do you know whether the answers are *good*? `/api/chat` doesn't tell you — it just gives you whatever the LLM produced. The evaluate endpoints exist to **grade the chatbot's homework**: run a question (or a whole test suite) through the same RAG pipeline that `/api/chat` uses, then score the answer on retrieval quality, faithfulness, and relevance.

There are two routes:

| Route | Purpose |
| --- | --- |
| `POST /api/evaluate` | Grade one question. Useful for tuning ("did changing chunk size make this question score better?"). |
| `POST /api/evaluate/suite` | Grade the entire **golden dataset** — a built-in list of expected questions and their hand-picked good answers. Useful for regression testing. |

> **Courier version.** The first route is "send out one parcel, time the run, then have an inspector grade how well I did". The second is "run today's full delivery roster against a known-good route map and tell me my pass rate."

### Single-question evaluation — what really happens

The flow is identical to `/api/chat` for the first three steps, then diverges at the end:

```
1. Run the question through rag_chain.query()  ← same as /api/chat
2. Build (chunk, score) tuples from the sources
3. Run RAGEvaluator.evaluate(question, answer, chunks)
4. Return the answer + scores
```

The evaluator is the **same evaluator** that runs automatically on every `/api/chat` request (Step 7 of the chat walkthrough). The difference is that here it's the *point* of the call rather than a side effect — and the scores are returned to the client in full detail rather than only being written to the query log.

### What the three scores actually measure

| Score | Question it answers | How it's computed |
| --- | --- | --- |
| **Retrieval** | Did the warehouse give us relevant chunks? | Average relevance score across the retrieved chunks (0.0 to 1.0). |
| **Faithfulness** | Did the LLM stick to what was in the chunks? | Word-overlap heuristic between answer and chunks — high overlap suggests the LLM cited the source. |
| **Answer relevance** | Did the answer actually address the question? | Word-overlap heuristic between answer and question. |

These are **lightweight heuristics**, not LLM-graded judgements. They're fast (microseconds) and cheap (zero LLM calls) but they can be fooled. A truly faithful answer that paraphrases will score low on word-overlap; a hallucination that happens to share words with the chunks will score high. For higher-quality evaluation you'd plug in an LLM-as-judge — the code structure makes that swap straightforward but it's not the default today.

The four scores roll up:

- **`overall`** is the average of the three.
- **`passed`** is `overall ≥ 0.70`.

### Suite evaluation — the regression test

The suite endpoint runs the same single-question logic for every question in the **golden dataset** (a hard-coded list in `src/evaluation/golden_dataset.py`). The dataset has questions, expected ground-truth answers (used for stricter scoring if enabled), and category tags. The handler iterates over the whole list and aggregates:

- Per-case results (every question with its scores and pass/fail).
- Aggregate stats: total cases, passed, failed, average scores per dimension, total cost in USD, total runtime.

> **Courier version.** It's like a driving test. The depot manager hands the courier a sealed envelope of 30 questions, runs them through the full pipeline, grades each one, and at the end produces a single report card: "27/30 passed, average retrieval 0.83, total run cost $0.12, took 47 seconds."

### How the dataset works

The dataset is **baked into the code** — `GOLDEN_DATASET` is a Python list. There's no API to add questions, no CSV upload, no way to mark some questions as "smoke test only". To grow your eval set you edit the source and redeploy. This is fine when the eval set is small and stable; it's awkward as the chatbot matures and you want non-engineers to add edge cases.

### A worked example

You hit `POST /api/evaluate/suite` with `top_k: 5`. The dataset has 30 cases. The handler:

1. Sequentially runs each question through `rag_chain.query()` — that's 30 full RAG cycles (embed → search → LLM → response).
2. Scores each one with the heuristic evaluator.
3. Aggregates the results.

If your provider is Bedrock with Claude Sonnet, that's roughly 30 × ~2 seconds = ~60 seconds of wall-clock time, plus 30 × ~$0.005 = ~$0.15 of LLM cost. Worth knowing before you run it casually — and **definitely** worth knowing before you wire it into a CI/CD pipeline that runs on every commit. If you do that with paid LLMs, you'll spend real money quickly.

### The condition matrix

| Scenario | RAG init? | Per-case run | Aggregation | Status |
| --- | --- | --- | --- | --- |
| Single, happy path | yes | 1 RAG cycle + score | n/a | 200 |
| Single, RAG missing | no | — | — | 500 |
| Single, LLM fails | yes | RAG cycle fails | — | 500 |
| Suite, all pass | yes | N RAG cycles | yes | 200 |
| Suite, some fail | yes | N RAG cycles | yes (failed cases recorded) | 200 |
| Suite, mid-run LLM outage | yes | partial | depends on impl — likely 500 with no aggregate | 500 |

### The honest health check

1. **Heuristic scoring only.** Word-overlap is gameable; not a substitute for proper LLM-as-judge or human review.
2. **Suite is sequential** — no parallelism, no rate-limit awareness. A large dataset takes a long time and a sudden burst can trigger provider rate limits.
3. **Dataset is hard-coded** — no UI/API to add cases without a deploy.
4. **No partial-run resilience** — if case 17 of 30 fails, you may lose the partial result depending on the implementation of the suite endpoint.
5. **Cost can surprise** — every suite run pays for N full LLM calls. There's no caching of stable answers between runs.
6. **Same evaluator runs on every chat call too** — so you're effectively double-paying for grading whenever you also use this endpoint.

### TL;DR

- Two routes: grade-one-question and grade-the-whole-golden-dataset.
- Uses the same in-process heuristic scorer as `/api/chat`'s background evaluator.
- Word-overlap heuristics — fast and cheap but gameable.
- Suite runs are sequential, hard-coded, and pay for N real LLM calls each time.
- Great as a manual tuning loop; treat with care if you wire it into CI on a paid provider.

---

## What This Endpoint Does

**`/api/evaluate`** does everything `/api/chat` does (retrieve chunks → generate answer),
then **also** runs the RAG Evaluator on the result and returns quality scores.

**`/api/evaluate/suite`** runs the above for every question in the golden dataset
and returns a scorecard: total cases, passed, failed, average score.

```text
/api/chat                          /api/evaluate
─────────                          ──────────────
Question → RAG pipeline → Answer   Question → RAG pipeline → Answer
                                                           → Evaluator → Scores
                                                           → Notes (warnings)
```

- 🚚 **Courier:** The specific delivery address the courier is dispatched to — each route handles a different type of parcels drop-off.

---

## DE Parallel

```
DATA ENGINEER                              AI ENGINEER
────────────────                           ──────────────
dbt test --select my_model                 POST /api/evaluate
  → Tests one model                          → Tests one question
  → Returns pass/fail + details              → Returns pass/fail + scores

dbt test                                   POST /api/evaluate/suite
  → Tests ALL models                         → Tests ALL golden dataset cases
  → Returns: 42 passed, 3 failed             → Returns: 4 passed, 1 failed
  → Shows which tests failed                 → Shows which cases failed + why
```

- 🚚 **Courier:** Running multiple couriers on the same route to confirm that AI engineering and data engineering practices mirror each other.

---

## Endpoint 1: Single Question

### `POST /api/evaluate`

**When to use:** Testing a specific question to debug or tune quality.

**Request:**

```json
{
  "question": "What is the refund policy?",
  "expected_answer": "Refunds take 14 business days.",
  "top_k": 5
}
```

Only `question` is required. `expected_answer` and `top_k` are optional.

**What happens inside:**

```text
1. rag_chain.query(question) → answer + sources (same as /api/chat)
2. RAGEvaluator.evaluate(question, answer, chunks) → scores
3. Build EvaluateSingleResponse with both answer AND scores
```

**Response structure:**

| Field | Type | What it tells you | 🚚 Courier |
|---|---|---| --- |
| `question` | string | The question you asked | Courier-side view of question — affects how the courier loads, reads, or delivers the parcels |
| `answer` | string | The LLM's generated answer | What the courier wrote on the shipping manifest after reading the parcel |
| `scores.retrieval` | float | Did vector search find relevant chunks? (0.0–1.0) | Score for whether the GPS warehouse handed the courier parcels actually about the question — higher means closer-matching parcels. |
| `scores.faithfulness` | float | Did the LLM stick to context? (0.0–1.0) | Did the courier use only what was in the parcel, or did it invent things along the way? |
| `scores.answer_relevance` | float | Did the LLM answer the question? (0.0–1.0) | Did the courier actually deliver to the address on the question, or drop the parcel somewhere nearby? |
| `scores.overall` | float | Weighted average (ret 30% + faith 40% + rel 30%) | How confidently the warehouse says 'this parcel matches' — higher = closer GPS hit |
| `scores.passed` | bool | Overall ≥ 0.7 | How confidently the warehouse says 'this parcel matches' — higher = closer GPS hit |
| `scores.has_hallucination` | bool | True = answer has claims not in context | Flag raised when the courier's shipping manifest contains items it never picked up from any parcel — invented parcels. |
| `evaluation_notes` | list | Warnings (e.g. "⚠️ RETRIEVAL: Chunks have low relevance") | Notes the report-card grader scribbled — e.g. warning that the parcels the courier carried had weak relevance to the question. |
| `sources_used` | int | How many chunks were retrieved | Count of parcels the courier actually opened to write the answer — how many retrieved chunks fed the delivery. |

- 🚚 **Courier:** The specific delivery address the courier is dispatched to — each route handles a different type of parcels drop-off.

---

## Endpoint 2: Golden Dataset Suite

### `POST /api/evaluate/suite`

**When to use:** After changing any setting — run the full test suite.

**Request:**

```json
{
  "categories": ["policy"],
  "top_k": 3
}
```

Both fields are optional. Omit `categories` to run all cases.

**What happens inside:**

```text
For each case in GOLDEN_DATASET:
  1. Run rag_chain.query(case.question)
  2. Evaluate the answer
  3. Record pass/fail + scores
Aggregate: total, passed, failed, pass_rate, average_score
```

**Response structure:**

| Field | Type | What it tells you | 🚚 Courier |
|---|---|---| --- |
| `total_cases` | int | How many cases were run | What the depot charges this month — total_cases: int · How many cases were run |
| `passed` | int | Cases with overall ≥ 0.7 | Courier's report card — share of test deliveries that scored above the bar |
| `failed` | int | Cases with overall < 0.7 | Number of test deliveries that came back below the report-card pass mark — these need investigation |
| `pass_rate` | float | Percentage passed (e.g. 80.0) | Courier's report card — share of test deliveries that scored above the bar |
| `average_overall_score` | float | Average score across all cases | Average overall score across all 25 standard test deliveries — the headline grade on the courier's batch report card. |
| `cases` | list | Per-case results (same scores as single evaluate) | One row of the report card per test delivery — same score breakdown you'd get from evaluating a single question |

- 🚚 **Courier:** The 25 standard test deliveries the courier must pass every release — a fixed benchmark that never changes so you can compare runs fairly.

---

## Reading the Scores — What Good Looks Like

| Score | Excellent | Good | Needs work | Broken | 🚚 Courier |
|---|---|---|---|---| --- |
| **Retrieval** | ≥ 0.85 | ≥ 0.70 | ≥ 0.50 | < 0.50 | Courier grabs the nearest parcels from the GPS warehouse before writing the answer |
| **Faithfulness** | ≥ 0.95 | ≥ 0.80 | ≥ 0.60 | < 0.60 | Did the courier stick to the parcels it was carrying, or invent stuff on the way? |
| **Answer Relevance** | ≥ 0.80 | ≥ 0.60 | ≥ 0.40 | < 0.40 | Routing tag on the parcel — Answer Relevance: ≥ 0.80 · ≥ 0.60 · ≥ 0.40 · < 0.40 |
| **Overall** | ≥ 0.85 | ≥ 0.70 | ≥ 0.50 | < 0.50 | Courier-side view of Overall — affects how the courier loads, reads, or delivers the parcels |

**If a score is low, here's what to fix:**

| Low score | What to try | 🚚 Courier |
|---|---| --- |
| Retrieval < 0.7 | Smaller `chunk_size`, different embedding model, more overlap | GPS stamp on the parcel — Retrieval < 0.7: Smaller chunk_size, different embedding model, more overlap |
| Faithfulness < 0.8 | Stricter prompt instructions, lower temperature | Note the courier carries — Faithfulness < 0.8: Stricter prompt instructions, lower temperature |
| Relevance < 0.6 | Better prompt, check if question is ambiguous | Note the courier carries — Relevance < 0.6: Better prompt, check if question is ambiguous |
| Overall < 0.7 | Debug each sub-score individually | Whole report card slipped — work through retrieval, faithfulness, and relevance one by one to find the weakest link |

- 🚚 **Courier:** The quality inspector's stamp — each delivered answer is graded on retrieval accuracy, faithfulness, and relevance before the customer signs.

---

## The AI Engineering Workflow

This is the core loop that makes you an AI Engineer:

```text
1. BASELINE: Run /api/evaluate/suite → record scores
2. CHANGE: Modify a setting (chunk_size, model, prompt, top_k)
3. EVALUATE: Run /api/evaluate/suite again → record new scores
4. COMPARE: Did scores improve? Regress? Stay the same?
5. DECIDE: Keep the change? Revert? Try something else?
6. REPEAT: Go to step 2
```

**Example: Changing chunk_size from 1000 to 500**

```
Before (chunk_size=1000):
  Suite: 25 cases, 18 passed, 7 failed, avg=0.68

After (chunk_size=500):
  Suite: 25 cases, 22 passed, 3 failed, avg=0.78

→ Improvement! Smaller chunks give more precise retrieval.
→ Keep the change.
```

- 🚚 **Courier:** The step-by-step route map showing every checkpoint the courier passes from question intake to answer delivery.

---

## How to Use This in Practice

### During development (Swagger UI)

1. Start the server: `poetry run start`
2. Open `http://localhost:8000/docs`
3. Upload a document via `POST /api/documents/upload`
4. Test individual questions: `POST /api/evaluate`
5. Run the full suite: `POST /api/evaluate/suite`

### From Swagger UI

1. Open `http://localhost:8000/docs`
2. **Single question:** Find `POST /api/evaluate` → click "Try it out" → enter:
   ```json
   {"question": "What is the refund policy?"}
   ```
3. **Full suite:** Find `POST /api/evaluate/suite` → click "Try it out" → send `{}` for all cases, or:
   ```json
   {"categories": ["edge_case"]}
   ```
4. Click **"Execute"** and inspect the response.

### In automated testing

```python
import httpx

async def run_evaluation_suite():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.post("/api/evaluate/suite", json={})
        data = response.json()

        print(f"Pass rate: {data['pass_rate']}%")
        print(f"Average score: {data['average_overall_score']}")

        # Fail CI if pass rate drops below 70%
        assert data["pass_rate"] >= 70.0, f"Quality regression: {data['pass_rate']}%"
```

- 🚚 **Courier:** The mechanics of the depot — understanding how each piece fits so you can maintain and extend the system.

---

## Self-Check Questions

### Tier 1 — Must understand

- [ ] What's the difference between `/api/chat` and `/api/evaluate`?
- [ ] What does a `passed: false` result mean?
- [ ] Which score detects hallucinations?
- [ ] When should you run the suite endpoint?

### Tier 2 — Should understand

- [ ] Why is faithfulness weighted at 40% while others are 30%?
- [ ] How do you use evaluation scores to decide whether to keep a config change?
- [ ] What does `evaluation_notes` contain and when is it useful?
- [ ] Why does the suite endpoint catch per-case errors instead of failing the whole suite?

### Tier 3 — AI engineering territory

- [ ] How would you integrate `/api/evaluate/suite` into a CI/CD pipeline?
- [ ] When would rule-based evaluation (current) not be good enough?
- [ ] How would you add A/B testing support (compare two models)?

- 🚚 **Courier:** A quick quiz for the trainee dispatch clerk — answer these to confirm the key courier delivery concepts have landed.

---

## What to Study Next

- [Evaluation Framework Deep Dive](../../ai-engineering/evaluation-framework-deep-dive.md) — how the scoring works internally
- [Golden Dataset Deep Dive](../../ai-engineering/golden-dataset-deep-dive.md) — how to add test cases
- [Chat Endpoint Deep Dive](chat-endpoint-explained.md) — the RAG pipeline this builds on

- 🚚 **Courier:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
