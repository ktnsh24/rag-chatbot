# Hands-On Labs — Learning RAG Quality

**Welcome.** These labs teach you how to build, measure, debug, and improve a RAG system using concrete experiments and real metric numbers.

**Structure:** 5 modules, 15 labs, ~6 hours total.

**Approach:** Swagger UI examples, sample outputs with numbers, interpretation tables, action tables. No tutorials or narratives.

---

## Quick Path

| If you want to learn | Start with | Time |
| --- | --- | --- |
| "Is my RAG working?" | [Module 1: Quality](module-1-quality.md) | 60 min |
| "What is it doing in production?" | [Module 2: Observability](module-2-observability.md) | 90 min |
| "Why did this fail?" | [Module 3: Diagnosis](module-3-diagnosis.md) | 60 min |
| "How do I make it better?" | [Module 4: Tuning](module-4-tuning.md) | 150 min |
| "How do I prevent regressions?" | [Module 5: Regression](module-5-regression.md) | 90 min |
| All of the above | Start at Module 1, work through sequentially | 450 min (~6 hrs) |

---

## Lab Index

### Module 1: Quality Fundamentals (60 min)

Learn what quality means and how to measure it with real numbers.

- **Lab 1:** Retrieval Quality — "Did I find the right chunks?"
  - Try 3 questions with different `top_k` values, compare retrieval scores.
- **Lab 2:** Faithfulness — "Did the answer stay grounded?"
  - Ask trick questions to catch hallucinations.

**Metrics introduced:** retrieval, faithfulness, answer_relevance, overall, latency

[→ Module 1](module-1-quality.md)

---

### Module 2: Observability Fundamentals (90 min)

Learn what happens in production: metrics, health checks, failure trends.

- **Lab 4:** Counter vs Gauge — Understanding metric types
  - Read `/api/metrics` endpoint, interpret each metric.
- **Lab 5:** Quality and Reliability Metrics
  - Health scorecard: error rate, latency, pass rate, cost.
- **Lab 6:** Failure Category Triage
  - When quality drops, which fix to apply first.

**Metrics introduced:** requests_total, errors_total, error_rate, latency p50/p95/p99, pass_rate, failure_categories

[→ Module 2](module-2-observability.md)

---

### Module 3: Failure Diagnosis (60 min)

When things break, read logs and spot patterns.

- **Lab 7:** Query Logs Deep Dive
  - Debug individual failures: was it retrieval, hallucination, or routing?
- **Lab 8:** Failure Pattern Analysis
  - Are 50 failures all the same type? Root cause.

**Tools introduced:** `/api/queries/failures`, `/api/queries/stats`, failure categorization

[→ Module 3](module-3-diagnosis.md)

---

### Module 4: Tuning and Trade-offs (150 min)

Improve quality, speed, and cost by changing configuration.

- **Lab 9:** Chunk Size Tuning
  - How big should each context chunk be?
- **Lab 10:** Top-K Tuning
  - How many chunks should we send to the LLM?
- **Lab 11:** Re-Ranking
  - Add a second-pass relevance sort before LLM generation?
- **Lab 12:** Hybrid Search
  - Mix semantic + keyword retrieval?
- **Lab 13:** HNSW Tuning
  - How deep should vector index search go?

**Knobs introduced:** RAG_CHUNK_SIZE, RAG_TOP_K, RERANKER_ENABLED, HYBRID_SEARCH_ENABLED, HNSW_M, HNSW_EF_SEARCH

[→ Module 4](module-4-tuning.md)

---

### Module 5: Regression and Release Gate (90 min)

Prevent quality regressions before deploying.

- **Lab 14:** Golden Dataset Basics
  - Build a curated test suite from production failures.
- **Lab 15:** Regression Testing as Release Gate
  - Check pass rate before each deployment.

**Concept introduced:** golden dataset, regression testing, release criteria

[→ Module 5](module-5-regression.md)

---

## Prerequisites

1. Repo is running locally: `docker-compose up`
2. Swagger UI available at `http://localhost:8000/docs`
3. One test document uploaded (instructions in Module 1)

---

## Common Patterns You'll See

### Swagger UI examples

Every lab includes 1-2 copy-paste examples:

```json
{
  "question": "What is the refund policy for digital products?"
}
```

Paste into Swagger UI, click "Execute", read the output.

### Sample output with numbers

Every lab shows realistic numbers so you know what to expect:

```json
{
  "retrieval_score": 0.74,
  "faithfulness_score": 0.82,
  "overall_score": 0.84
}
```

### Interpretation table

Every lab has a table explaining what each number means:

| Metric | Value | Meaning |
| --- | --- | --- |
| retrieval_score | 0.74 | Chunks are relevant (0=wrong, 1=perfect). |

### Action table

Every lab ends with what to do based on results:

| If you see this | First action |
| --- | --- |
| retrieval_score < 0.60 | Increase top_k to 10. |

---

## Metrics Reference

For quick lookup of what each metric means, see [evaluation-metrics.md](../ai-engineering/evaluation-metrics.md).

---

## Tips

- **One lab per session:** Pick a module that matches your question; spend 30–90 min.
- **Compare before/after:** Every tuning lab shows a table with 2-3 settings; the diff is the insight.
- **Use combined mode:** Most labs default to `EVAL_MODE=combined` so you see both rule-based and judge scores.
- **Add your own cases to golden dataset:** When something fails in "prod" (local testing), capture it as a regression test.

---

## Questions?

- "What's the difference between retrieval and faithfulness?" → [Module 1, Lab 2](module-1-quality.md#lab-2-faithfulness--)
- "Which metric should I alert on?" → [Module 2, Lab 5](module-2-observability.md#lab-5-quality-and-reliability-metrics)
- "Why is my pass rate dropping?" → [Module 3, Lab 8](module-3-diagnosis.md#lab-8-failure-pattern-analysis)
- "How do I make it faster?" → [Module 4, Lab 9](module-4-tuning.md#lab-9-chunk-size-tuning)
- "How do I prevent regressions?" → [Module 5, Lab 15](module-5-regression.md#lab-15-regression-testing-as-release-gate)
