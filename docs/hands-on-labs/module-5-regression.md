# Module 5: Regression and Release Gate

**Question this module answers:** "How do I prevent quality regressions before deploying?"

**Labs in this module:** 3 hands-on experiments
- Lab 15: Golden Dataset Basics
- Lab 16: Regression Testing as Release Gate
- Lab 17: LLM-as-a-Judge Validation

**Time:** 120 minutes total

**Prerequisite:** Module 1-4 (you've tuned the system to ≥ 70% pass rate).

---

## Lab 15: Golden Dataset Basics

### Goal

Build a golden dataset: a curated set of test cases that capture edge cases and production failures.

### Run in Swagger UI

Check the golden dataset:

`GET /api/golden-dataset` → "Try it out" → "Execute"

### Sample output with numbers

```json
{
  "total_cases": 25,
  "by_category": {
    "refund_policy": 8,
    "shipping": 6,
    "digital_products": 5,
    "edge_cases": 6
  },
  "sample_cases": [
    {
      "case_id": "g_001",
      "question": "What is the refund policy for digital products?",
      "expected_category": "digital_products",
      "expected_failure_category": "none",
      "status": "passing"
    },
    {
      "case_id": "g_023",
      "question": "Can I return items I bought from Amazon?",
      "expected_category": "edge_case",
      "expected_failure_category": "bad_retrieval",
      "status": "passing"
    }
  ]
}
```

### Interpret coverage

| Category | Count | Coverage | Observation |
| --- | --- | --- | --- |
| refund_policy | 8 | 32% | Main policy variations. |
| shipping | 6 | 24% | Return costs, international. |
| digital_products | 5 | 20% | Non-refundable edge case. |
| edge_cases | 6 | 24% | Out-of-scope, ambiguous, trick questions. |

### Action table

| If dataset has this | Add more cases | Why |
| --- | --- | --- |
| Mostly happy-path cases | 5-10 trick/edge questions | Edge cases catch regressions first. |
| One category > 50% | Rebalance into other categories | Imbalanced dataset misses whole areas. |
| All passing consistently | Keep as regression baseline | Good; now use for release gate. |

---

## Lab 16: Regression Testing as Release Gate

### Goal

Run the golden dataset before deployment. If pass rate drops, block the release.

### Run in Swagger UI

`POST /api/evaluate-batch`:

```json
{
  "test_cases": "golden_dataset",
  "eval_mode": "combined"
}
```

### Sample output with numbers

```json
{
  "total_cases": 25,
  "passed": 24,
  "failed": 1,
  "pass_rate_percent": 96,
  "before_changes": {
    "pass_rate_percent": 96,
    "timestamp": "2026-05-01T14:00:00Z"
  },
  "change": {
    "delta_percent": 0,
    "status": "PASS_RELEASE_GATE"
  },
  "failed_cases": [
    {
      "case_id": "g_023",
      "question": "Can I return items from Amazon?",
      "overall_score": 0.68,
      "failure_category": "bad_retrieval",
      "expected_failure_category": "bad_retrieval",
      "matches_expectation": true
    }
  ]
}
```

### Interpret regression test results

| Scenario | Pass rate now | Pass rate before | Action |
| --- | --- | --- | --- |
| Good release | 96% | 96% | ✅ Deploy. No regression. |
| Minor regression | 92% | 96% | ⚠️ Review. If failure is known/accepted, deploy. Else revert. |
| Major regression | 80% | 96% | ❌ Block. Revert code changes. Find root cause. |
| Unexpected improvement | 98% | 96% | ✅ Deploy. + test why it improved (good side effect). |

### Action table

| Result | First action |
| --- | --- |
| `pass_rate drops > 5%` | Revert the commit. Run regression test on main to confirm it passes. |
| `expected_failure_category matches` | Passing test case that's *supposed* to fail; OK if count doesn't change. |
| `new failure_category appears` | Unknown failure type; investigate before deploying. |
| All cases passing | ✅ Safe to deploy. |

### Scenario: Add a case to golden dataset

When a production failure happens:

1. Create a test case for it:

```json
{
  "case_id": "g_new",
  "question": "User's exact failing question",
  "expected_failure_category": "the failure reason you discovered",
  "status": "should_pass_after_fix"
}
```

2. Fix the system (tune knobs, update documents, etc.).

3. Run regression test. New case should now pass.

4. Add to golden dataset permanently.

**Key insight:** Golden dataset grows from real production failures, not theoretical edge cases. Each failure becomes a regression test.

---

## Lab 17: LLM-as-a-Judge Validation

### Goal

Run evaluation with `llm_judge`, compare it with `rule_based`, and confirm the recommended `combined` behavior.

### Run in Swagger UI

Open Swagger UI -> `POST /api/evaluate` -> "Try it out" -> run the same question in these 3 modes.

Run 1 (`rule_based`):

```json
{
  "question": "What is the refund policy for digital products?",
  "eval_mode": "rule_based"
}
```

Run 2 (`llm_judge`):

```json
{
  "question": "What is the refund policy for digital products?",
  "eval_mode": "llm_judge"
}
```

Run 3 (`combined`):

```json
{
  "question": "What is the refund policy for digital products?",
  "eval_mode": "combined"
}
```

### Sample output with numbers

```json
{
  "question": "What is the refund policy for digital products?",
  "eval_mode": "combined",
  "rule_based": {
    "retrieval_score": 0.74,
    "faithfulness_score": 0.82,
    "answer_relevance_score": 0.95,
    "overall_score": 0.84,
    "passed": true
  },
  "llm_judge": {
    "faithfulness": 0.8,
    "answer_relevance": 0.9,
    "notes": [
      "Answer is grounded in retrieved context.",
      "Could include more detail about exclusions."
    ]
  },
  "final_overall": 0.86,
  "passed": true,
  "latency_ms": 39541
}
```

### Calculate the judge metrics (worked example)

Use the numbers above and calculate these metrics explicitly:

| Metric | Formula | Example calculation | Result |
| --- | --- | --- | --- |
| Judge proxy overall | `(judge_faithfulness + judge_answer_relevance) / 2` | `(0.80 + 0.90) / 2` | `0.85` |
| Faithfulness delta | `abs(rule_faithfulness - judge_faithfulness)` | `abs(0.82 - 0.80)` | `0.02` |
| Relevance delta | `abs(rule_relevance - judge_relevance)` | `abs(0.95 - 0.90)` | `0.05` |
| Lane delta | `abs(rule_overall - judge_proxy_overall)` | `abs(0.84 - 0.85)` | `0.01` |
| Agreement percent | `(1 - ((faithfulness_delta + relevance_delta) / 2)) * 100` | `(1 - ((0.02 + 0.05)/2)) * 100` | `96.5%` |
| Combined gain | `final_overall - rule_overall` | `0.86 - 0.84` | `+0.02` |

### Calculate latency and parser reliability

Run the same query 3 times (`rule_based`, `llm_judge`, `combined`) and record `latency_ms` from each response.

Sample timing sheet:

| Mode | latency_ms |
| --- | --- |
| rule_based | 31000 |
| llm_judge | 39000 |
| combined | 39541 |

Derived metrics:

| Metric | Formula | Example |
| --- | --- | --- |
| Judge overhead vs rule-based | `llm_judge_latency - rule_based_latency` | `39000 - 31000 = 8000 ms` |
| Combined overhead vs rule-based | `combined_latency - rule_based_latency` | `39541 - 31000 = 8541 ms` |
| Overhead percent | `((combined_latency - rule_based_latency) / rule_based_latency) * 100` | `(8541 / 31000) * 100 = 27.6%` |

Parser reliability metric (from logs):

| Metric | Formula | Example |
| --- | --- | --- |
| Judge parse error rate | `(invalid_json_warnings / llm_judge_runs) * 100` | `(1 / 10) * 100 = 10%` |

Target guidance:

- Agreement percent: prefer `>= 90%`
- Lane delta: prefer `<= 0.10`
- Judge parse error rate: prefer `< 5%`
- Combined overhead: team-defined, typically keep `< 30%`

### Interpret results

| Comparison | Meaning | First action |
| --- | --- | --- |
| `rule_based` high + `llm_judge` high | Stable quality by both methods | Keep as release baseline |
| `rule_based` high + `llm_judge` low | Semantically weak answer despite overlap | Improve grounding/prompt clarity |
| `rule_based` low + `llm_judge` high | Heuristic thresholds may be strict | Review rubric and thresholds |
| Judge parse warnings in logs | Judge returned malformed JSON | Tighten judge output schema prompt |

### Action table

| If you see this | First action |
| --- | --- |
| `Judge response was not valid JSON` warning | Force strict JSON schema in judge prompt and keep parser fallback enabled |
| Judge latency dominates total latency | Use `combined` for regression suites, not every interactive chat |
| Judge scores fluctuate heavily run-to-run | Run 3 repeats and compare variance; tune rubric wording |
| Judge gives high scores to weak answers | Add negative examples and stricter faithfulness rubric |

---

## Release Gate Checklist

Before deploying code or tuning changes:

- [ ] Run `POST /api/evaluate-batch` on golden dataset
- [ ] Verify `pass_rate_percent` ≥ 95% (or your team's threshold)
- [ ] Check that failed cases are expected (match `expected_failure_category`)
- [ ] If regression detected (drop > 5%), revert and investigate
- [ ] Log the result for monitoring

---

## What You've Learned

- **Golden dataset = regression test suite** (prevents backwards-slip)
- **Source: production failures** (each bug becomes a test case)
- **Size: 20-50 cases** (usually enough to catch regressions)
- **Coverage: balanced** (don't overweight happy path)
- **Release gate: pass_rate >= 95%** (or your SLO threshold)
- **Trend: golden dataset grows over time** (add 1-2 cases per quarter from prod bugs)

---

## Congratulations

You've completed all 5 modules:

1. ✅ **Module 1:** Quality Fundamentals (retrieval, faithfulness, relevance)
2. ✅ **Module 2:** Observability (metrics, counters, gauges)
3. ✅ **Module 3:** Failure Diagnosis (logs, categories, patterns)
4. ✅ **Module 4:** Tuning (top_k, chunk_size, reranker, hybrid, HNSW)
5. ✅ **Module 5:** Regression Testing (golden dataset, release gate, llm-as-a-judge)

You now know:
- How RAG quality works and what each metric means
- How to measure it in production
- How to diagnose why it fails
- How to improve it systematically
- How to prevent regressions before shipping
- How to validate quality with `llm_judge` vs `rule_based`

**Next:** Apply this framework to your own RAG system. Start with Module 1, run the labs, then pick which Module 4 tuning lever to pull first based on your failure categories.
