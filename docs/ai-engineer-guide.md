# Thinking Like an AI Engineer — A Guide for Data Engineers

> **Your DE skills are your superpower.** You already know pipelines, monitoring,
> data quality, and infrastructure. This guide shows you how to apply that same
> thinking to AI systems — with specific examples from this project.

---

## Table of Contents

1. [The Core Mindset Shift](#the-core-mindset-shift)
2. [Data Quality Monitoring → AI Behaviour Monitoring](#1-data-quality-monitoring--ai-behaviour-monitoring)
3. [Batch Pipeline → RAG Pipeline](#2-batch-pipeline--rag-pipeline)
4. [Validating Transformations → Evaluating Model Outputs](#3-validating-transformations--evaluating-model-outputs)
5. [The Evaluation Framework (Code Walkthrough)](#the-evaluation-framework)
6. [The AI Engineering Checklist](#the-ai-engineering-checklist)
7. [Common Mistakes (And How DEs Avoid Them)](#common-mistakes)
8. [Daily Practices](#daily-practices)
9. [How to Talk About This in Interviews](#interview-guide)

---

## The Core Mindset Shift

As a Data Engineer, your job is to move data **correctly** from A to B.
As an AI Engineer, your job is to make AI give **good answers** to humans.

```
DATA ENGINEER                        AI ENGINEER
────────────────                     ──────────────
"Did the data arrive?"           →   "Did the AI answer correctly?"
"Is it in the right format?"     →   "Is the answer grounded in facts?"
"Did any rows get lost?"         →   "Did the AI hallucinate?"
"Is it fast enough?"             →   "Is the response latency acceptable?"
"How much did the job cost?"     →   "How many tokens did we spend?"
"Can we reprocess if it fails?"  →   "Can we retry with a different prompt?"
```

The fundamental difference:

- **DE outputs are deterministic**: same input → same output. Every time.
- **AI outputs are probabilistic**: same input → slightly different output each time.

This means you can't just `assert output == expected`. You need fuzzy evaluation.
That's exactly what the evaluation framework in `src/evaluation/` does.

---

## 1. Data Quality Monitoring → AI Behaviour Monitoring

### What you already do (DE)

```python
# Data Engineer monitors a Glue job:
def check_data_quality(dataframe):
    assert dataframe.count() > 0, "No rows loaded!"
    assert dataframe.filter(col("id").isNull()).count() == 0, "Null IDs found!"
    assert dataframe.select("date").distinct().count() == 1, "Multiple dates!"
    print("✅ Data quality checks passed")
```

### What you'll do now (AI Engineer)

```python
# AI Engineer monitors a RAG query (src/evaluation/evaluator.py):
def check_ai_quality(question, answer, chunks):
    evaluator = RAGEvaluator()
    result = evaluator.evaluate(question, answer, chunks)

    assert result.retrieval.avg_relevance_score > 0.7, "Bad retrieval!"
    assert not result.faithfulness.has_hallucination, "Hallucination detected!"
    assert result.answer_relevance.score > 0.6, "Answer is off-topic!"
    assert result.overall_score > 0.7, "Overall quality too low!"
    print("✅ AI quality checks passed")
```

### Where this lives in the project

| File | What it monitors | DE equivalent |
| --- | --- | --- |
| `src/evaluation/evaluator.py` | Answer quality (4 dimensions) | Data validation rules |
| `src/evaluation/golden_dataset.py` | Known good question-answer pairs | Test fixtures / seed data |
| `src/monitoring/metrics.py` | Runtime metrics (latency, tokens, cost) | Job duration, row counts |
| `src/api/middleware/logging.py` | Request logging with trace IDs | Pipeline run logging |
| `tests/test_evaluation.py` | Automated quality regression tests | Automated data quality tests |

### The 4 quality dimensions you monitor

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI QUALITY DIMENSIONS                         │
├─────────────────────┬───────────────────────────────────────────┤
│ 1. RETRIEVAL        │ Did we find the right chunks?             │
│    QUALITY          │ DE parallel: Did the JOIN return right    │
│                     │ rows? Check similarity scores.            │
│                     │ Code: evaluator._evaluate_retrieval()     │
├─────────────────────┼───────────────────────────────────────────┤
│ 2. FAITHFULNESS     │ Does the answer only use facts from       │
│                     │ the context? No made-up information?      │
│                     │ DE parallel: Referential integrity.       │
│                     │ Code: evaluator._evaluate_faithfulness()  │
├─────────────────────┼───────────────────────────────────────────┤
│ 3. ANSWER           │ Does the answer address the question?     │
│    RELEVANCE        │ DE parallel: Does the output have the     │
│                     │ columns the business asked for?           │
│                     │ Code: evaluator._evaluate_answer_relevance│
├─────────────────────┼───────────────────────────────────────────┤
│ 4. COMPLETENESS     │ Did the answer cover all important points?│
│    (future)         │ DE parallel: Are all expected rows present?│
│                     │ Requires ground truth to evaluate.        │
└─────────────────────┴───────────────────────────────────────────┘
```

---

## 2. Batch Pipeline → RAG Pipeline

### Side-by-side mapping

| Concept | DE Batch Pipeline | RAG Pipeline (this project) |
| --- | --- | --- |
| **Source** | Database / API / S3 files | Uploaded PDF / TXT / DOCX |
| **Extract** | Read from source system | `src/rag/ingestion.py` → `read_document()` |
| **Transform** | Clean, deduplicate, join | `src/rag/ingestion.py` → `chunk_document()` |
| **Load** | Write to DWH / Redshift | `src/vectorstore/` → `store_vectors()` |
| **Serve** | BI dashboard / SQL query | `src/rag/chain.py` → `query()` |
| **Orchestrator** | Airflow / Step Functions | `src/rag/chain.py` → `RAGChain` class |
| **Schema** | DDL / Glue Catalog | Index mapping (OpenSearch / AI Search) |
| **Data quality** | Great Expectations / dbt tests | `src/evaluation/evaluator.py` |
| **Monitoring** | CloudWatch metrics | `src/monitoring/metrics.py` |
| **Retry logic** | Airflow retries | `tenacity` library |
| **Idempotency** | Upsert / merge | Document re-ingestion (delete + re-ingest) |

### The key insight

```
DE Pipeline:   Extract → Transform → Load → Query → Dashboard
RAG Pipeline:  Read    → Chunk     → Embed → Store → Query → Generate → Answer
                                      ↑
                              THIS IS THE NEW PART
                              (everything else maps to DE skills)
```

The only truly new step is **embedding** — turning text into vectors. Everything
else (read, transform, store, query, serve) is the same pattern you already know.

---

## 3. Validating Transformations → Evaluating Model Outputs

### The hard part: answers aren't deterministic

```python
# DE validation — deterministic (always right or wrong):
assert total_revenue == sum(line_items)              # ✅ exact match
assert date_format_matches("2026-03-29", "YYYY-MM-DD")  # ✅ exact match
assert foreign_key_exists(order.customer_id)         # ✅ exists or not

# AI evaluation — probabilistic (good, okay, or bad):
answer = llm("What is the refund policy?")
# Could return:
#   "Refunds take 14 days"          ← good
#   "Refunds take two weeks"        ← also good (different words, same meaning!)
#   "Refunds take 14 business days" ← most accurate
#   "Our CEO founded the company"   ← BAD (hallucination / off-topic)
```

### How we handle this in the project

Instead of exact matching, we evaluate on multiple dimensions:

```python
# src/evaluation/evaluator.py — the evaluate() method:

overall_score = (
    retrieval_quality   * 0.3 +   # Were the right chunks found?
    faithfulness         * 0.4 +   # Is the answer grounded in context?
    answer_relevance     * 0.3     # Does it address the question?
)

# Weights explained:
#   Faithfulness gets 40% because hallucination is the WORST failure mode
#   Retrieval gets 30% because bad retrieval → bad answer (garbage in, garbage out)
#   Relevance gets 30% because an accurate but off-topic answer is still useless
```

### The Golden Dataset pattern

This is the AI Engineer's equivalent of regression tests:

```python
# src/evaluation/golden_dataset.py

GOLDEN_DATASET = [
    {
        "id": "refund_basic",
        "question": "What is the refund policy?",
        "expected_keywords": ["refund", "14", "days"],        # Must appear
        "expected_not_in_answer": ["helicopter", "unicorn"],   # Must NOT appear
        "context_chunks": [("Refunds take 14 days...", 0.95)],
        "min_retrieval_score": 0.8,
        "min_faithfulness": 0.8,
    },
    # Add more cases over time...
]
```

**Rule:** Every time you find a bad answer, fix the pipeline, then add that
question to the golden dataset. Now it's tested forever.

---

## The Evaluation Framework

### How to use it (step by step)

**Step 1: Run a query through RAG**

```python
result = await rag_chain.query("What is the refund policy?", session_id="test")
```

**Step 2: Evaluate the result**

```python
from src.evaluation.evaluator import RAGEvaluator

evaluator = RAGEvaluator()
eval_result = evaluator.evaluate(
    question="What is the refund policy?",
    answer=result["answer"],
    retrieved_chunks=[
        (source["text"], source["score"])
        for source in result["sources"]
    ],
)
```

**Step 3: Check the scores**

```python
print(eval_result.to_dict())
# {
#     "scores": {
#         "retrieval": 0.83,
#         "retrieval_quality": "good",
#         "faithfulness": 0.95,
#         "has_hallucination": False,
#         "answer_relevance": 0.88,
#         "overall": 0.89
#     },
#     "passed": True,
#     "notes": []
# }
```

**Step 4: If it fails, diagnose**

```python
if not eval_result.passed:
    # Check which dimension failed:
    if eval_result.retrieval.quality == "poor":
        print("FIX: Retrieval is bad → try different chunk_size or overlap")
    if eval_result.faithfulness.has_hallucination:
        print("FIX: Hallucination detected → strengthen the prompt constraints")
        print(f"  Suspicious: {eval_result.faithfulness.flagged_sentences}")
    if eval_result.answer_relevance.quality == "off-topic":
        print("FIX: Answer is off-topic → check if the right chunks are retrieved")
```

### When to run evaluations

| When | Why | How |
| --- | --- | --- |
| After changing `chunk_size` or `chunk_overlap` | Different chunking → different retrieval | `pytest tests/test_evaluation.py` |
| After changing the prompt (`src/rag/prompts.py`) | Different instructions → different answers | `pytest tests/test_evaluation.py` |
| After switching models (Claude → GPT-4o) | Different model → different quality | `pytest tests/test_evaluation.py` |
| After updating `top_k` | More/fewer chunks → different context | `pytest tests/test_evaluation.py` |
| After any code change to `src/rag/` | Safety net — catch regressions | CI pipeline runs tests |

---

## The AI Engineering Checklist

Use this checklist **before every PR** that touches the RAG pipeline:

### Before making changes

- [ ] Run `pytest tests/test_evaluation.py` — record baseline scores
- [ ] Note current chunk_size, overlap, top_k, model, and prompt

### After making changes

- [ ] Run `pytest tests/test_evaluation.py` — compare with baseline
- [ ] Check: Did retrieval quality change? (chunk_size / overlap / embeddings)
- [ ] Check: Did faithfulness change? (prompt / model)
- [ ] Check: Did relevance change? (prompt / top_k)
- [ ] Check: Did cost change? (model / max_tokens)
- [ ] Check: Did latency change? (model / chunk count)
- [ ] If any score dropped >5%, investigate before merging

### The AI Engineer's "Definition of Done"

A change is ready to merge when:

1. ✅ All golden dataset tests pass
2. ✅ No new hallucinations introduced
3. ✅ Retrieval quality is the same or better
4. ✅ Cost per query hasn't increased unexpectedly
5. ✅ Latency is within acceptable bounds (<5 seconds)
6. ✅ The change is documented (what changed and why)

---

## Common Mistakes (And How DEs Avoid Them)

### Mistake 1: "It seems to work" (no measurement)

```
❌ AI Beginner:  Change chunk_size, ask one question, "looks good" → merge
✅ AI Engineer:  Change chunk_size, run evaluation suite, compare scores → merge
✅ DE parallel:  You'd NEVER deploy a pipeline without checking row counts
```

### Mistake 2: Ignoring hallucination

```
❌ AI Beginner:  "The answer is long and detailed, it must be good"
✅ AI Engineer:  Check faithfulness score — long ≠ correct
✅ DE parallel:  A table with 1 million rows isn't useful if 500K are duplicates
```

### Mistake 3: Overfitting the prompt to one question

```
❌ AI Beginner:  Tweak the prompt until "What is the refund policy?" works perfectly
✅ AI Engineer:  Run ALL golden dataset questions — fixing one shouldn't break others
✅ DE parallel:  Fixing a bug for one customer shouldn't break other customers' data
```

### Mistake 4: Not monitoring costs

```
❌ AI Beginner:  Use GPT-4 for everything, get a $500 bill
✅ AI Engineer:  Track cost per query, set budget alerts, use cheaper models for testing
✅ DE parallel:  You monitor Glue DPU-hours and Redshift costs — same for tokens
```

### Mistake 5: Treating the LLM as a black box

```
❌ AI Beginner:  "The AI gave a weird answer, I don't know why"
✅ AI Engineer:  Check the logs:
                  - What chunks were retrieved? (retrieval issue)
                  - What prompt was sent? (prompt issue)
                  - What did the model return? (model issue)
✅ DE parallel:  When a job fails, you check: source data? transformation? target?
```

---

## Daily Practices

### What to do every day as an AI Engineer

1. **Check metrics** (`/api/metrics` endpoint or monitoring dashboard)
   - Are error rates normal?
   - Is latency stable?
   - Is token cost within budget?

2. **Review flagged responses** (when evaluation detects issues)
   - Why was faithfulness low?
   - What chunks were retrieved?
   - Was the prompt effective?

3. **Grow the golden dataset** (when you find new patterns)
   - Found a question the system handles poorly? Fix it, add the test.
   - New document type uploaded? Add test questions for it.

### What to do with every code change

```bash
# 1. Before changing anything — baseline
pytest tests/test_evaluation.py -v > baseline.txt

# 2. Make your change (chunk_size, prompt, model, etc.)

# 3. After changing — compare
pytest tests/test_evaluation.py -v > after.txt

# 4. Compare
diff baseline.txt after.txt
# If any test went from PASS to FAIL → investigate
```

---

## Interview Guide

### How to talk about this project

When asked "Tell me about an AI project you've built," structure your answer:

**1. The Problem (30 seconds)**

> "I built a RAG chatbot that lets users upload documents and ask questions.
> The system retrieves relevant information and generates answers using LLMs."

**2. The Architecture (60 seconds)**

> "Documents go through an ingestion pipeline — read, chunk, embed, store in a
> vector database. When a user asks a question, we embed the question, do
> similarity search, and send the relevant chunks to the LLM with the question."

**3. The AI Engineering Part (this is what sets you apart, 90 seconds)**

> "What I'm most proud of is the evaluation framework. I built a system that
> measures four dimensions of quality — retrieval relevance, faithfulness,
> answer relevance, and overall score. I maintain a golden dataset of test
> cases that runs on every change. This catches regressions — for example,
> when I changed chunk_size from 1000 to 500, retrieval quality improved
> from 0.78 to 0.85, but faithfulness dropped because smaller chunks lost
> context. So I adjusted the overlap parameter to compensate."

**4. The DE Bridge (30 seconds)**

> "My data engineering background was a huge advantage. ETL pipelines map
> directly to RAG pipelines — extract is document reading, transform is
> chunking, load is vector storage. Data quality monitoring maps to AI
> output evaluation. I applied the same engineering rigour."

### Questions they might ask (and your answers)

| Question | Your answer | Backed by |
| --- | --- | --- |
| "How do you prevent hallucination?" | "Prompt constraints + faithfulness evaluation" | `src/rag/prompts.py` + `src/evaluation/evaluator.py` |
| "How do you measure quality?" | "4-dimension evaluation: retrieval, faithfulness, relevance, overall" | `src/evaluation/evaluator.py` |
| "How do you handle regressions?" | "Golden dataset tests run on every change" | `tests/test_evaluation.py` |
| "How do you manage costs?" | "Token tracking, cost estimation, budget alerts" | `src/monitoring/metrics.py` + `docs/cost-analysis.md` |
| "Why multi-cloud?" | "Abstract interfaces, swap providers with one env var" | `src/llm/base.py` pattern |
| "How does chunking work?" | "RecursiveCharacterTextSplitter, 1000 chars, 200 overlap" | `src/rag/ingestion.py` |
| "What's the hardest part?" | "Evaluation — AI outputs are probabilistic, not deterministic" | This guide |
