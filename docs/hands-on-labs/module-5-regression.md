# Module 5: Regression and Release Gate

**Question this module answers:** "How do I prevent quality regressions before deploying?"

**Labs in this module:** 2 hands-on experiments
- Lab 14: Golden Dataset Basics
- Lab 15: Regression Testing as Release Gate

**Time:** 90 minutes total

**Prerequisite:** Module 1-4 (you've tuned the system to ≥ 70% pass rate).

---

## Lab 14: Golden Dataset Basics

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

## Lab 15: Regression Testing as Release Gate

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
5. ✅ **Module 5:** Regression Testing (golden dataset, release gate)

You now know:
- How RAG quality works and what each metric means
- How to measure it in production
- How to diagnose why it fails
- How to improve it systematically
- How to prevent regressions before shipping

**Next:** Apply this framework to your own RAG system. Start with Module 1, run the labs, then pick which Module 4 tuning lever to pull first based on your failure categories.
