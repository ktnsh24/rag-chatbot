# Module 3: Failure Diagnosis

**Question this module answers:** "Why did this query fail and what do I fix?"

**Labs in this module:** 2 hands-on experiments
- Lab 7: Query Logs Deep Dive
- Lab 8: Failure Pattern Analysis

**Time:** 60 minutes total

**Prerequisite:** Module 2 (understand failure categories first).

---

## Lab 7: Query Logs Deep Dive

### Goal

Read structured query logs to debug individual failures.

### Run in Swagger UI

`GET /api/queries/failures` → "Try it out" → "Execute"

### Sample output with numbers

```json
[
  {
    "query_id": "q_001",
    "question": "What is the refund policy for digital products?",
    "retrieved_chunks": 5,
    "retrieval_score": 0.62,
    "faithfulness_score": 0.91,
    "answer_relevance_score": 0.88,
    "overall_score": 0.80,
    "passed": true,
    "failure_category": "none"
  },
  {
    "query_id": "q_002",
    "question": "Can I return items from Amazon?",
    "retrieved_chunks": 5,
    "retrieval_score": 0.45,
    "faithfulness_score": 0.78,
    "answer_relevance_score": 0.72,
    "overall_score": 0.65,
    "passed": false,
    "failure_category": "bad_retrieval"
  },
  {
    "query_id": "q_003",
    "question": "Do I have to pay for shipping back?",
    "retrieved_chunks": 5,
    "retrieval_score": 0.81,
    "faithfulness_score": 0.68,
    "answer_relevance_score": 0.91,
    "overall_score": 0.79,
    "passed": false,
    "failure_category": "hallucination"
  }
]
```

### Interpret each failure

| Query | Scores | Failure reason | What went wrong | What the model said vs reality |
| --- | --- | --- | --- | --- |
| q_002 (Amazon question) | retrieval 0.45 ← LOW | `bad_retrieval` | Vector search didn't find "Amazon" in the policy. | Model tried to answer about Amazon (not in docs). |
| q_003 (return shipping) | faithfulness 0.68 ← LOW | `hallucination` | Answer added info not in chunks. | Model said "X costs Y euros" but policy says "customer pays" without amount. |

### Action table

| Symptom | First action | Fix |
| --- | --- | --- |
| Query failed with `bad_retrieval` | Read question → does it mention a term NOT in documents? | Add the term to documents or accept this question can't be answered. |
| Query failed with `hallucination` | Read the answer → does it state facts not in retrieved chunks? | Tighten system prompt: "Answer only with facts from provided text." |
| Query passed but score is 0.68 (marginal) | Read scores individually. Which is lowest? | Lowest score category needs fixing (retrieval → tune, faithfulness → prompt). |

---

## Lab 8: Failure Pattern Analysis

### Goal

Spot trends in failures (are bad_retrieval failures clustered? Why?).

### Run in Swagger UI

`GET /api/queries/stats` → check failure breakdown.

Then manually group recent failures:

| Failure type | Example queries | Pattern | Root cause | Fix priority |
| --- | --- | --- | --- | --- |
| bad_retrieval | "Amazon refund?", "PayPal returns?", "cancel order?" | Questions ask about external services not in policy. | Scope mismatch (users expect coverage). | Document: add FAQ about out-of-scope questions. |
| hallucination | "return costs €5?", "calls free?", "3-day warranty?" | Model invents specific numbers or policies. | Prompt too permissive. | Tighten: "Cite exact text from policy." |
| off_topic | (none in this sample) | N/A | N/A | (No action needed.) |

### Action table

| If you see this pattern | First action |
| --- | --- |
| bad_retrieval dominating (> 50% of failures) | Documents don't cover what users ask. Either expand documents or set user expectations. |
| hallucination spike after code deploy | New prompt is too creative. Revert or tighten phrasing. |
| off_topic failures increasing | Questions are ambiguous. Add clarification prompts to system message. |
| All failures are "marginal" (just under 0.70) | System is close to passing. Small tuning (increase `top_k` by 1, tighten prompt slightly) fixes many. |

---

## What You've Learned

- **Query logs are per-request forensics** (query ID, scores, failure reason)
- **Failure categories point to fixes:** bad_retrieval → documents, hallucination → prompt, off_topic → routing
- **Patterns matter:** if 10 different queries all fail with bad_retrieval on "Amazon", it's a scope issue, not random noise
- **Marginal failures are easy wins:** small tuning bumps many to pass

---

## Next Steps

- Move to [Module 4: Tuning](module-4-tuning.md) to fix bad_retrieval and hallucination
- Or go back to [Module 2](module-2-observability.md) to monitor trends over time
