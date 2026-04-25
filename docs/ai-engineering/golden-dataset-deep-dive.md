# Deep Dive: Golden Dataset — `src/evaluation/golden_dataset.py`

> **Study order:** #15 · **Difficulty:** ★★★☆☆ (mostly data structures — the AI concept is "regression testing for LLMs")  
> **File:** [`src/evaluation/golden_dataset.py`](../../src/evaluation/golden_dataset.py)  
> **Prerequisite:** [#14 — Evaluation Framework](evaluation-framework-deep-dive.md)  
> **Part of:** [Architecture Overview](../architecture-and-design/architecture.md)

---

## Table of Contents

1. [Why This File Matters](#why-this-file-matters)
2. [DE Parallel — Golden Datasets Are Regression Test Fixtures](#de-parallel--golden-datasets-are-regression-test-fixtures)
3. [Structure of a Test Case](#structure-of-a-test-case)
4. [The 25 Test Cases Across 7 Categories](#the-25-test-cases-across-7-categories)
5. [Case 1: `refund_basic` — Happy Path](#case-1-refund_basic--happy-path)
6. [Case 2: `refund_digital` — Subset Policy](#case-2-refund_digital--subset-policy)
7. [Case 3: `shipping_return` — Cross-Topic](#case-3-shipping_return--cross-topic)
8. [Case 4: `no_context_available` — Edge Case, Empty Context](#case-4-no_context_available--edge-case-empty-context)
9. [Case 5: `ambiguous_question` — Edge Case, Vague Query](#case-5-ambiguous_question--edge-case-vague-query)
10. [How the Golden Dataset Drives Evaluation](#how-the-golden-dataset-drives-evaluation)
11. [Cloud vs Local — Same Dataset, Different Baselines](#cloud-vs-local--same-dataset-different-baselines)
12. [How to Add New Test Cases](#how-to-add-new-test-cases)
13. [Self-Test Questions](#self-test-questions)
14. [What to Study Next](#what-to-study-next)

---

## Why This File Matters

You can't improve what you can't measure. The golden dataset is a **fixed set of known-good test cases** that the evaluation framework (#14) runs against. When you change a prompt, a model, or a chunking strategy, you run the golden dataset to check: *"Did anything break?"*

Without a golden dataset, you'd have to manually test every change — ask questions, read answers, judge quality. That doesn't scale. This file makes evaluation **automated, repeatable, and objective**.

| What you'll learn | DE parallel | 🫏 Donkey |
|---|---| --- |
| Fixed test inputs with expected outputs | Seed data / test fixtures | Test delivery 🧪 |
| Categories of test cases (happy path, edge case) | Test pyramid: happy path → edge cases → error cases | Test delivery 🧪 |
| Score thresholds per test case | SLA definitions per data pipeline | Test delivery 🧪 |
| Context chunks pre-loaded (no search needed) | Mock data for integration tests | Test case pre-loads three known backpacks so evaluation doesn't depend on warehouse GPS search |
| Negative test cases | `expected_not_in_answer` = forbidden values | Test delivery 🧪 |

- 🫏 **Donkey:** Think of this as the orientation briefing given to a new donkey before its first delivery run — it sets the context for everything that follows.

---

## DE Parallel — Golden Datasets Are Regression Test Fixtures

```
DATA ENGINEER                              AI ENGINEER
────────────────                           ──────────────
Test fixture:                              Golden dataset entry:
  input_csv = "test_data/orders.csv"         question = "What is the refund policy?"
  expected_output = "test_data/expected.csv"  expected_keywords = ["14 days", "refund"]
                                             context_chunks = [("Refunds...", 0.95)]

Run pipeline on input_csv                  Run chain.query() with golden question
Compare output to expected.csv             Evaluate answer with evaluator.py
If mismatch → pipeline is broken           If score < threshold → model is broken

When do you run this?                      When do you run this?
  ✅ Before every deploy                     ✅ Before every deploy
  ✅ After changing transformations           ✅ After changing prompts/models
  ✅ In CI/CD                                ✅ In CI/CD
```

- 🫏 **Donkey:** The 25 standard test deliveries the donkey must pass every release — a fixed benchmark that never changes so you can compare runs fairly.

---

## Structure of a Test Case

Each entry in `GOLDEN_DATASET` is a dictionary with these fields:

```python
{
    "id": "refund_basic",              # Unique identifier
    "category": "refund_policy",       # Test category (for grouping)
    "question": "What is the ...",     # The user's question
    "expected_keywords": [...],        # Words that MUST appear in the answer
    "expected_not_in_answer": [...],   # Words that MUST NOT appear (negative test)
    "context_chunks": [                # Pre-loaded chunks (bypasses vector search)
        ("chunk text...", 0.95),       #   (text, similarity_score)
        ("chunk text...", 0.88),
    ],
    "min_retrieval_score": 0.7,        # Minimum acceptable retrieval score
    "min_faithfulness": 0.8,           # Minimum acceptable faithfulness score
}
```

**Why pre-loaded context chunks?** Because the golden dataset tests the **LLM + evaluation** pipeline, not the vector search. By pre-loading chunks with known scores, we isolate what we're testing:

```
                   ┌─────────────── NOT tested by golden dataset
                   │
User question → [Embed] → [Search] → [Context] → [LLM] → [Evaluate]
                                         │           │          │
                                         └───────────┴──────────┘
                                         ↑
                                    Tested by golden dataset
```

- 🫏 **Donkey:** Sending the donkey on 25 standard test deliveries (golden dataset) to verify it returns the right packages every time.

---

## The 25 Test Cases Across 7 Categories

| Category | Count | Purpose | 🫏 Donkey |
|---|---|---| --- |
| `policy` | 4 | Refund, digital refund, exchange, warranty | Stable keys — only authorised callers may ask the donkey to deliver |
| `logistics` | 3 | Return shipping, delivery time, order tracking | Donkey-side view of logistics — affects how the donkey loads, reads, or delivers the cargo |
| `contact` | 3 | Support channels, hours, escalation | Donkey-side view of contact — affects how the donkey loads, reads, or delivers the cargo |
| `product` | 2 | Compatibility, specifications | Donkey-side view of product — affects how the donkey loads, reads, or delivers the cargo |
| `multi_turn` | 3 | Follow-up questions needing context | Donkey-side view of multi_turn — affects how the donkey loads, reads, or delivers the cargo |
| `edge_case` | 6 | Ambiguous, out-of-scope, prompt injection, negation, multi-topic | Delivery note 📋 |
| `pii` | 4 | PII in input, PII request, phone number, GDPR deletion | Gate rule 🚧 |

The cases below are representative examples. See [`golden_dataset.py`](../../src/evaluation/golden_dataset.py) for all 25.

### Key cases by category

- 🫏 **Donkey:** Sending the donkey on 25 standard test deliveries (golden dataset) to verify it returns the right packages every time.

---

## Case 1: `refund_basic` — Happy Path

```python
{
    "id": "refund_basic",
    "category": "refund_policy",
    "question": "What is the refund policy?",
    "expected_keywords": ["14", "days", "refund", "email"],
    "expected_not_in_answer": ["cryptocurrency", "bitcoin"],
    "context_chunks": [
        ("Our refund policy allows customers to request a full refund within "
         "14 business days of purchase. To initiate a refund, send an email to "
         "support@example.com with your order number.", 0.95),
        ("Refunds are processed back to the original payment method. Please "
         "allow 3-5 business days for the refund to appear in your account.", 0.88),
        ("For items purchased during a sale, the refund amount will be the "
         "discounted price, not the original price.", 0.82),
    ],
    "min_retrieval_score": 0.7,
    "min_faithfulness": 0.8,
}
```

**What this tests:**

| Aspect | Check | Why | 🫏 Donkey |
|---|---|---| --- |
| **Keywords present** | "14", "days", "refund", "email" | Core facts must appear in the answer | What the donkey wrote and brought back to the customer |
| **Keywords absent** | "cryptocurrency", "bitcoin" | The LLM must not invent payment methods | The donkey must never write words that weren't in the backpack — no inventing payment methods |
| **Retrieval scores** | 0.95, 0.88, 0.82 (avg 0.88) | All chunks are relevant — high quality retrieval | GPS warehouse fetched three highly relevant backpacks — scores near 0.9 mean excellent match |
| **Faithfulness** | ≥ 0.8 | Answer must be grounded in the 3 chunks | Donkey's answer must cite the three backpacks — 0.8 faithfulness means no invented facts |

**A passing answer:** *"According to the documents, customers can request a full refund within 14 business days. Send an email to support@example.com with your order number. Refunds are returned to the original payment method within 3-5 business days. [Document chunk 1]"*

**A failing answer:** *"Refunds take 14 days. You can also get a refund via Bitcoin."* — mentions "bitcoin" (in `expected_not_in_answer`) and hallucinated payment method.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Case 2: `refund_digital` — Subset Policy

```python
{
    "id": "refund_digital",
    "category": "refund_policy",
    "question": "Can I get a refund for a digital product?",
    "expected_keywords": ["digital", "non-refundable"],
    "expected_not_in_answer": ["14 days"],
    "context_chunks": [
        ("Digital products such as e-books, software licenses, and online "
         "courses are non-refundable once the download or access link has "
         "been activated.", 0.93),
        ("If a digital product is defective or not as described, customers "
         "may request a review by contacting support@example.com.", 0.85),
    ],
    "min_retrieval_score": 0.7,
    "min_faithfulness": 0.85,
}
```

**Why "14 days" is in `expected_not_in_answer`:** The general refund policy (14 days) does NOT apply to digital products. If the LLM mentions "14 days" here, it's mixing up policies — a subtle form of hallucination.

**DE parallel:** This is like testing that your pipeline filters correctly — the `WHERE category = 'digital'` should NOT return physical product rules.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Case 3: `shipping_return` — Cross-Topic

```python
{
    "id": "shipping_return",
    "category": "shipping_and_returns",
    "question": "How do I return an item that was shipped?",
    "expected_keywords": ["return", "shipping", "label"],
    "expected_not_in_answer": ["digital"],
    "context_chunks": [
        ("To return a shipped item, print the prepaid return shipping label "
         "from your order confirmation email.", 0.91),
        ("Pack the item in its original packaging and drop it off at any "
         "authorized carrier location.", 0.87),
        ("Return shipping is free for orders over $50. For orders under $50, "
         "a $5.99 return shipping fee applies.", 0.78),
    ],
    "min_retrieval_score": 0.65,
    "min_faithfulness": 0.8,
}
```

**Why lower `min_retrieval_score` (0.65)?** The third chunk (0.78) is about return fees, not the return process itself. The question is about *how* to return, and the fee chunk is tangential. A lower threshold acknowledges that not every chunk will be perfectly relevant.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Case 4: `no_context_available` — Edge Case, Empty Context

```python
{
    "id": "no_context_available",
    "category": "edge_case",
    "question": "What is the company's stock price?",
    "expected_keywords": ["don't have enough information"],
    "expected_not_in_answer": ["$", "stock", "price", "NYSE"],
    "context_chunks": [
        ("Our office is located at 123 Business Street, Amsterdam.", 0.15),
    ],
    "min_retrieval_score": 0.0,  # Expected to be very low
    "min_faithfulness": 0.9,     # Must not hallucinate!
}
```

**This is the most important test case.** It verifies:

1. **The LLM refuses correctly** — "I don't have enough information" matches `expected_keywords`
2. **The LLM doesn't guess** — "$", "stock", "price", "NYSE" are in `expected_not_in_answer`
3. **The context is irrelevant** — office address has nothing to do with stock price (score 0.15)
4. **Faithfulness is high** — even though context is bad, the LLM should refuse, not hallucinate

**DE parallel:** This is like sending an empty file to your ETL pipeline. The correct behaviour is to log "no data found" — not to generate fake rows.

**Why `min_faithfulness` is 0.9 (highest of all cases):** When context is irrelevant, the faithfulness test is actually testing the *refusal detector*. A refusal gets a 1.0 faithfulness score. If the LLM tries to answer instead of refusing, faithfulness drops below 0.9.

- 🫏 **Donkey:** A practice delivery run — the donkey completes a structured exercise to build muscle memory before real production routes.

---

## Case 5: `ambiguous_question` — Edge Case, Vague Query

```python
{
    "id": "ambiguous_question",
    "category": "edge_case",
    "question": "How long?",
    "expected_keywords": [],  # Can't predict exact answer for vague question
    "expected_not_in_answer": [],
    "context_chunks": [
        ("Refund processing takes 14 business days.", 0.45),
        ("Shipping typically takes 5-7 business days.", 0.42),
    ],
    "min_retrieval_score": 0.3,
    "min_faithfulness": 0.6,  # Lower threshold — ambiguity makes grounding harder
}
```

**Why relaxed thresholds?**

| Threshold | Value | Why | 🫏 Donkey |
|---|---|---| --- |
| `min_retrieval_score` | 0.3 | "How long?" is vague — chunks will have low relevance | Vague question yields low GPS scores — don't expect the backpack to perfectly match ambiguity |
| `min_faithfulness` | 0.6 | The LLM might mention both refunds AND shipping — hard to ground precisely | Lower the bar — when the question is vague, the donkey may legitimately weave together two backpacks |
| `expected_keywords` | `[]` | Can't predict what the LLM will say for a vague question | No keyword checklist — for ambiguous orders nobody can predict which words the donkey will choose |

**What a good answer looks like:** *"Your question 'How long?' is ambiguous. Based on the documents: refund processing takes 14 business days, and shipping takes 5-7 business days."*

**What Prompt Rule #6 says:** *"If the question is ambiguous, state your interpretation before answering."*

- 🫏 **Donkey:** The warehouse robot dispatched to find the right backpack shelf — it uses GPS coordinates (embeddings) to locate the nearest relevant chunks in ~9 hops.

---

## How the Golden Dataset Drives Evaluation

```python
from src.evaluation.evaluator import RAGEvaluator
from src.evaluation.golden_dataset import GOLDEN_DATASET

evaluator = RAGEvaluator()

for case in GOLDEN_DATASET:
    # Simulate what chain.query() would produce
    answer = chain.query(case["question"], context_chunks=case["context_chunks"])

    # Evaluate the answer
    result = evaluator.evaluate(
        question=case["question"],
        answer=answer,
        retrieved_chunks=case["context_chunks"],
    )

    # Check against thresholds
    assert result.retrieval.average_score >= case["min_retrieval_score"], \
        f"{case['id']}: retrieval too low"
    assert result.faithfulness.score >= case["min_faithfulness"], \
        f"{case['id']}: faithfulness too low"

    # Check required keywords
    for kw in case["expected_keywords"]:
        assert kw.lower() in answer.lower(), \
            f"{case['id']}: missing keyword '{kw}'"

    # Check forbidden keywords
    for kw in case["expected_not_in_answer"]:
        assert kw.lower() not in answer.lower(), \
            f"{case['id']}: forbidden keyword '{kw}' found"

    print(f"✅ {case['id']}: overall={result.overall_score:.2f}")
```

**When to run this:**

| Trigger | Why | 🫏 Donkey |
|---|---| --- |
| Changed a prompt template | Prompts affect every answer — regression test ALL cases | Delivery note 📋 |
| Switched LLM model | Different models behave differently — baseline them | Re-run the 25 standard test deliveries with the new donkey breed to see how its writing differs |
| Changed chunking strategy | Affects retrieval quality — test #1, #2, #3 | Backpack size changes (chunk_size) affect which cargo pieces the warehouse robot fetches |
| Changed `top_k` or `chunk_size` | Affects context quality — test all cases | Top_k controls backpack count; chunk_size controls cargo size — both impact donkey's reading material |
| Before deploying to production | Final sanity check | Robot hand 🤖 |
| In CI/CD pipeline | Automated regression on every PR | Robot hand 🤖 |

### Running the Golden Dataset via the API

The easiest way to run the golden dataset is through the evaluation API endpoints:

**Run the full suite (all cases):**

In **Swagger UI** (`http://localhost:8000/docs`) → `POST /api/evaluate/suite` → **"Try it out"**, send:

```json
{}
```

**Run only specific categories:**

```json
{"categories": ["policy"]}
```

Click **"Execute"** to see the scorecard.

The suite runs each golden dataset case through the **live RAG pipeline** (not mock data) and returns a scorecard with per-case pass/fail results.

📖 **See:** [Evaluate Endpoint Deep Dive](../architecture-and-design/api-routes/evaluate-endpoint-explained.md) · [API Reference → Evaluation](../reference/api-reference.md)

- 🫏 **Donkey:** The 25 standard test deliveries the donkey must pass every release — a fixed benchmark that never changes so you can compare runs fairly.

---

## Cloud vs Local — Same Dataset, Different Baselines

The golden dataset is **identical** across providers. The test cases, questions, expected keywords, and context chunks don't change. But the **scores will differ** because models behave differently:

| Test case | Claude 3.5 (AWS) | GPT-4o (Azure) | llama3.2 (Local) | 🫏 Donkey |
|---|---|---|---| --- |
| `refund_basic` | ~0.92 | ~0.90 | ~0.80 | Donkey-side view of refund_basic — affects how the donkey loads, reads, or delivers the cargo |
| `refund_digital` | ~0.91 | ~0.88 | ~0.75 | Donkey-side view of refund_digital — affects how the donkey loads, reads, or delivers the cargo |
| `shipping_return` | ~0.88 | ~0.86 | ~0.78 | Donkey-side view of shipping_return — affects how the donkey loads, reads, or delivers the cargo |
| `no_context_available` | ~0.95 | ~0.93 | ~0.70 ⚠️ | Donkey-side view of no_context_available — affects how the donkey loads, reads, or delivers the cargo |
| `ambiguous_question` | ~0.80 | ~0.78 | ~0.60 | Donkey-side view of ambiguous_question — affects how the donkey loads, reads, or delivers the cargo |

⚠️ **Local models may struggle with case #4** — smaller models sometimes try to answer instead of refusing. If `no_context_available` fails locally:
- Lower `min_faithfulness` to 0.7 for local testing
- Or improve the system prompt with stronger refusal instructions
- Don't deploy to production until a cloud model passes the full suite

**Development workflow:**

```bash
# 1. Develop and iterate locally (free)
CLOUD_PROVIDER=local python -m pytest tests/test_golden_dataset.py

# 2. Validate on cloud before deploying (costs ~$0.03 per run)
CLOUD_PROVIDER=aws python -m pytest tests/test_golden_dataset.py

# 3. Deploy only if cloud tests pass
```

- 🫏 **Donkey:** Running the donkey on rented pasture — AWS or Azure provides the stable so you only pay for the hay consumed.

---

## How to Add New Test Cases

When you encounter a bug in production (e.g., the LLM gives a wrong answer), add it to the golden dataset:

```python
# Step 1: Document the failure
{
    "id": "warranty_confusion",            # Descriptive ID
    "category": "warranty_policy",         # New or existing category
    "question": "Is my warranty still valid?",
    "expected_keywords": ["warranty", "12 months"],
    "expected_not_in_answer": ["lifetime", "forever"],  # Previous hallucination
    "context_chunks": [
        ("Product warranty covers defects for 12 months from purchase date.", 0.90),
        ("Extended warranty can be purchased for an additional 24 months.", 0.84),
    ],
    "min_retrieval_score": 0.7,
    "min_faithfulness": 0.85,
}
```

**Guidelines for new cases:**

| Guideline | Why | 🫏 Donkey |
|---|---| --- |
| At least 1 happy path per category | Baseline behaviour | Donkey-side view of At least 1 happy path per category — affects how the donkey loads, reads, or delivers the cargo |
| At least 1 edge case | Boundary behaviour | Donkey-side view of At least 1 edge case — affects how the donkey loads, reads, or delivers the cargo |
| Put previous hallucinations in `expected_not_in_answer` | Regression-proof the fix | List forbidden words the donkey invented last time — catch memory drift before it happens again |
| Use realistic similarity scores (0.4–0.95) | Don't use 1.0 — real search is never perfect | Compass bearing 🧭 |
| Set thresholds based on cloud model performance | Don't set to 0.99 — allow natural variation | Manifest template 📋 |

- 🫏 **Donkey:** Sending the donkey on 25 standard test deliveries (golden dataset) to verify it returns the right packages every time.

---

## Self-Test Questions

### Tier 1 — Must understand

- [ ] What is a golden dataset and why does RAG need one?
- [ ] What's the purpose of `expected_not_in_answer`?
- [ ] Why does `no_context_available` have the highest `min_faithfulness` threshold?
- [ ] Why are context chunks pre-loaded instead of retrieved by vector search?

### Tier 2 — Should understand

- [ ] Why does `ambiguous_question` have empty `expected_keywords`?
- [ ] How do you know when a golden dataset needs more test cases?
- [ ] What's the relationship between this file and the evaluator (#14)?
- [ ] Why might the same test case pass on AWS but fail on Local?

### Tier 3 — AI engineering territory

- [ ] How would you generate golden datasets automatically from production logs?
- [ ] When does a golden dataset become too large to run on every PR?
- [ ] How would you weight test case failures? (Is `no_context_available` failing worse than `ambiguous_question`?)
- [ ] How would you version golden datasets alongside model versions?

- 🫏 **Donkey:** Sending the donkey on 25 standard test deliveries (golden dataset) to verify it returns the right packages every time.

---

## What to Study Next

You now understand how to build test suites for AI systems. Last file:

- **File #16:** [`src/monitoring/metrics.py`](metrics-deep-dive.md) — turning evaluation scores into operational dashboards

📖 **Related docs:**
- [Evaluation Framework Deep Dive (#14)](evaluation-framework-deep-dive.md) — the scorer that uses this dataset
- [RAG Chain Deep Dive (#13)](rag-chain-deep-dive.md) — the pipeline being tested
- [CI/CD Explained](../architecture-and-design/cicd-explained.md) — where golden dataset tests run automatically

- 🫏 **Donkey:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
