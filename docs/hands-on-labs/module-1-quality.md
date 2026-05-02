# Module 1: Quality Fundamentals

**Question this module answers:** "Is my RAG returning correct answers?"

**Labs in this module:** 2 hands-on experiments
- Lab 1: Retrieval Quality (did we find the right chunks?)
- Lab 2: Faithfulness (did the answer stay grounded?)

**Time:** 60 minutes total

**Prerequisite:** Upload [test-policy.txt](../../setup.md) via Swagger UI.

---

## Setup: Upload Test Document

Create `test-policy.txt` with this content:

```text
REFUND POLICY

Section 1: General Returns
All products can be returned within 14 business days of purchase.
Products must be in original, unopened packaging.
To request a refund, email support@example.com with your order number.

Section 2: Digital Products
Digital products and gift cards are non-refundable.
All sales of downloadable content are final.
If a digital product is defective, contact support for a replacement.

Section 3: Shipping Returns
Return shipping costs are the customer's responsibility.
Free shipping on orders over 50 euros does not apply to returns.
International returns must include a customs declaration form.
```

Upload via **Swagger UI** (`http://localhost:8000/docs`):
- Find `POST /api/documents/upload`
- Click "Try it out" → "Choose File" → select `test-policy.txt` → "Execute"

---

## Lab 1: Retrieval Quality — "Did I find the right chunks?"

### Goal

Understand how `top_k` (number of chunks retrieved) affects quality scores.

### Run in Swagger UI

`POST /api/evaluate` → "Try it out" → copy this JSON:

```json
{
  "question": "What is the refund policy for digital products?",
  "top_k": 5
}
```

Click "Execute".

### Sample output with numbers

```json
{
  "question": "What is the refund policy for digital products?",
  "retrieved_chunks": 5,
  "retrieval_score": 0.74,
  "faithfulness_score": 0.82,
  "answer_relevance_score": 0.95,
  "overall_score": 0.84,
  "latency_ms": 3200,
  "answer": "Digital products and gift cards are non-refundable. All sales of downloadable content are final. If a digital product is defective, contact support for a replacement.",
  "failure_category": "none",
  "passed": true
}
```

### Interpret results

| Metric | Value | Meaning | Action if score is low |
| --- | --- | --- | --- |
| `retrieval_score` | 0.74 | Quality of fetched chunks (0=wrong shelf, 1=perfect match). | Increase `top_k` to grab more chunks, or re-ingest documents. |
| `faithfulness_score` | 0.82 | Answer sticks to retrieved text (0=full hallucination, 1=only facts from context). | Tighten system prompt to enforce grounding. |
| `answer_relevance_score` | 0.95 | Answer addresses the question (0=off-topic, 1=perfectly relevant). | Improve question routing or prompt intent framing. |
| `overall_score` | 0.84 | Combined score (≥ 0.70 = pass). | Check which component is lowest first. |
| `latency_ms` | 3200 | End-to-end time in milliseconds. | Reduce `top_k` or disable expensive stages if > SLO. |

### Now try with different top_k

Run the same question with `top_k=1` and `top_k=10`. Compare scores:

| top_k | retrieval | faithfulness | answer_relevance | overall | latency_ms |
| --- | --- | --- | --- | --- | --- |
| 1 | ___ | ___ | ___ | ___ | ___ |
| 5 (from above) | 0.74 | 0.82 | 0.95 | 0.84 | 3200 |
| 10 | ___ | ___ | ___ | ___ | ___ |

**What you should see:** Higher `top_k` usually lowers retrieval (more noise), but can improve faithfulness if the extra context helps. Watch latency rise with higher `top_k`.

### Action table

| If you see this | First action |
| --- | --- |
| `retrieval_score < 0.60` | Chunks are irrelevant. Increase `top_k` to 10 and re-test. |
| `faithfulness_score < 0.70` | Answer adds unsupported claims. Tighten the system prompt before trying tuning. |
| `answer_relevance_score < 0.80` | User question not understood. Check if question wording is ambiguous. |
| `overall_score < 0.70` | System failing. Check which component is lowest, fix that first. |
| `latency_ms > 5000` | Too slow. Lower `top_k` from 5 to 3 and re-test. |

---

## Lab 2: Faithfulness — "Did the answer stay grounded in facts?"

### Goal

Test if the AI answers only facts from retrieved context or makes things up.

### Run in Swagger UI

`POST /api/evaluate` → "Try it out" → copy this JSON:

```json
{
  "question": "Do I pay for return shipping on orders over 50 euros?"
}
```

Click "Execute".

### Sample output with numbers

```json
{
  "question": "Do I pay for return shipping on orders over 50 euros?",
  "retrieved_chunks": 5,
  "retrieval_score": 0.81,
  "faithfulness_score": 0.88,
  "answer_relevance_score": 0.98,
  "overall_score": 0.89,
  "latency_ms": 2900,
  "answer": "Yes, you pay for return shipping even if your original order was over 50 euros. Free shipping on orders over 50 euros does not apply to returns. Return shipping costs are the customer's responsibility.",
  "failure_category": "none",
  "passed": true
}
```

### Now ask a trick question (contains false assumptions)

`POST /api/evaluate`:

```json
{
  "question": "What is the refund window for digital products if I bought them on Amazon?"
}
```

### Compare results

| Question type | retrieval | faithfulness | answer_relevance | overall | Answer behavior |
| --- | --- | --- | --- | --- | --- |
| Grounded question | 0.81 | 0.88 | 0.98 | 0.89 | Stays in context ✅ |
| Trick question (contains false assumption) | ___ | ___ | ___ | ___ | Does it hallucinate or refuse? |

**What you should see:** Faithfulness drops if the model tries to answer about "Amazon" (not mentioned in context). A good grounded system should either refuse or say "Not found in policy."

### Action table

| If you see this | First action |
| --- | --- |
| Trick question gets `faithfulness < 0.70` | System is hallucinating. **Good sign** — it means the evaluator caught it. Tighten the system prompt to refuse rather than guess. |
| Trick question gets `faithfulness ≥ 0.70` | System grounded well. It refused or said "not mentioned," which is correct behavior. |
| Grounded question gets `faithfulness < 0.80` | Evaluator is flagging real uncertainty. Read the answer — does it include caveats like "I don't have information about…"? That's not hallucination, it's caution. |

---

## What You've Learned

- **Retrieval score = quality of chunks** (0.60–1.0 is realistic; local models score lower than cloud)
- **Faithfulness score = answer stays grounded** (high = good, low = hallucination or caution)
- **Answer relevance = answer answers the question** (usually highest score)
- **Overall = weighted combination** (faithfulness weighted highest because it's the most dangerous to get wrong)
- **top_k trade-off:** lower = precise but risky, higher = safer but slower and noisier
- **Test trick questions to catch hallucination** early before production

---

## Next Steps

- Move to [Module 2: Observability Fundamentals](module-2-observability.md) to learn what metrics matter in production
- Or jump to [Module 4: Tuning and Trade-offs](module-4-tuning.md) to change `top_k`, chunking, and reranking
