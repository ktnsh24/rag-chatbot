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

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

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

- 🫏 **Donkey:** Running multiple donkeys on the same route to confirm that AI engineering and data engineering practices mirror each other.

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

| Field | Type | What it tells you | 🫏 Donkey |
|---|---|---| --- |
| `question` | string | The question you asked | Donkey-side view of question — affects how the donkey loads, reads, or delivers the cargo |
| `answer` | string | The LLM's generated answer | What the donkey wrote on the delivery note after reading the backpack |
| `scores.retrieval` | float | Did vector search find relevant chunks? (0.0–1.0) | Score for whether the GPS warehouse handed the donkey backpacks actually about the question — higher means closer-matching cargo. |
| `scores.faithfulness` | float | Did the LLM stick to context? (0.0–1.0) | Did the donkey use only what was in the backpack, or did it invent things along the way? |
| `scores.answer_relevance` | float | Did the LLM answer the question? (0.0–1.0) | Did the donkey actually deliver to the address on the question, or drop the parcel somewhere nearby? |
| `scores.overall` | float | Weighted average (ret 30% + faith 40% + rel 30%) | How confidently the warehouse says 'this backpack matches' — higher = closer GPS hit |
| `scores.passed` | bool | Overall ≥ 0.7 | How confidently the warehouse says 'this backpack matches' — higher = closer GPS hit |
| `scores.has_hallucination` | bool | True = answer has claims not in context | Flag raised when the donkey's delivery note contains items it never picked up from any backpack — invented cargo. |
| `evaluation_notes` | list | Warnings (e.g. "⚠️ RETRIEVAL: Chunks have low relevance") | Notes the report-card grader scribbled — e.g. warning that the backpacks the donkey carried had weak relevance to the question. |
| `sources_used` | int | How many chunks were retrieved | Count of backpacks the donkey actually opened to write the answer — how many retrieved chunks fed the delivery. |

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

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

| Field | Type | What it tells you | 🫏 Donkey |
|---|---|---| --- |
| `total_cases` | int | How many cases were run | Feed bill 🌾 |
| `passed` | int | Cases with overall ≥ 0.7 | Donkey's report card — share of test deliveries that scored above the bar |
| `failed` | int | Cases with overall < 0.7 | Number of test deliveries that came back below the report-card pass mark — these need investigation |
| `pass_rate` | float | Percentage passed (e.g. 80.0) | Donkey's report card — share of test deliveries that scored above the bar |
| `average_overall_score` | float | Average score across all cases | Average overall score across all 25 standard test deliveries — the headline grade on the donkey's batch report card. |
| `cases` | list | Per-case results (same scores as single evaluate) | One row of the report card per test delivery — same score breakdown you'd get from evaluating a single question |

- 🫏 **Donkey:** The 25 standard test deliveries the donkey must pass every release — a fixed benchmark that never changes so you can compare runs fairly.

---

## Reading the Scores — What Good Looks Like

| Score | Excellent | Good | Needs work | Broken | 🫏 Donkey |
|---|---|---|---|---| --- |
| **Retrieval** | ≥ 0.85 | ≥ 0.70 | ≥ 0.50 | < 0.50 | Donkey grabs the nearest backpacks from the GPS warehouse before writing the answer |
| **Faithfulness** | ≥ 0.95 | ≥ 0.80 | ≥ 0.60 | < 0.60 | Did the donkey stick to the cargo it was carrying, or invent stuff on the way? |
| **Answer Relevance** | ≥ 0.80 | ≥ 0.60 | ≥ 0.40 | < 0.40 | Right address 🎯 |
| **Overall** | ≥ 0.85 | ≥ 0.70 | ≥ 0.50 | < 0.50 | Donkey-side view of Overall — affects how the donkey loads, reads, or delivers the cargo |

**If a score is low, here's what to fix:**

| Low score | What to try | 🫏 Donkey |
|---|---| --- |
| Retrieval < 0.7 | Smaller `chunk_size`, different embedding model, more overlap | GPS stamp 📍 |
| Faithfulness < 0.8 | Stricter prompt instructions, lower temperature | Delivery note 📋 |
| Relevance < 0.6 | Better prompt, check if question is ambiguous | Delivery note 📋 |
| Overall < 0.7 | Debug each sub-score individually | Whole report card slipped — work through retrieval, faithfulness, and relevance one by one to find the weakest link |

- 🫏 **Donkey:** The quality inspector's stamp — each delivered answer is graded on retrieval accuracy, faithfulness, and relevance before the customer signs.

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

- 🫏 **Donkey:** The step-by-step route map showing every checkpoint the donkey passes from question intake to answer delivery.

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

- 🫏 **Donkey:** The mechanics of the stable — understanding how each piece fits so you can maintain and extend the system.

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

- 🫏 **Donkey:** A quick quiz for the trainee stable hand — answer these to confirm the key donkey delivery concepts have landed.

---

## What to Study Next

- [Evaluation Framework Deep Dive](../../ai-engineering/evaluation-framework-deep-dive.md) — how the scoring works internally
- [Golden Dataset Deep Dive](../../ai-engineering/golden-dataset-deep-dive.md) — how to add test cases
- [Chat Endpoint Deep Dive](chat-endpoint-explained.md) — the RAG pipeline this builds on

- 🫏 **Donkey:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
