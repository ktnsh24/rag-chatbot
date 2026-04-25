# Deep Dive: Evaluation Framework — `src/evaluation/evaluator.py`

> **Study order:** #14 · **Difficulty:** ★★★★☆ (this is how you measure if AI is working — the concepts are new)
> **File:** [`src/evaluation/evaluator.py`](../../src/evaluation/evaluator.py)
> **Prerequisite:** [#13 — RAG Chain](rag-chain-deep-dive.md) · [#12 — Prompts](prompts-deep-dive.md)
> **Part of:** [Architecture Overview](../architecture-and-design/architecture.md)

---

## Table of Contents

1. [Why This File Matters](#why-this-file-matters)
2. [DE Parallel — Evaluation Is Data Quality Testing](#de-parallel--evaluation-is-data-quality-testing)
3. [Architecture Overview — The Four Scores](#architecture-overview--the-four-scores)
4. [Concept 1: Retrieval Quality — Did Search Find the Right Chunks?](#concept-1-retrieval-quality)
5. [Concept 2: Faithfulness — Did the LLM Stick to the Context?](#concept-2-faithfulness)
6. [Concept 3: Answer Relevance — Did the LLM Answer the Question?](#concept-3-answer-relevance)
7. [Concept 4: Weighted Overall Score](#concept-4-weighted-overall-score)
8. [The Refusal Detector — Knowing When "I Don't Know" Is Correct](#the-refusal-detector--knowing-when-i-dont-know-is-correct)
9. [Helper Methods — Sentence Splitting and Keyword Extraction](#helper-methods)
10. [How It Fits in the Pipeline](#how-it-fits-in-the-pipeline)
11. [Cloud vs Local — Provider-Agnostic by Design](#cloud-vs-local--provider-agnostic-by-design)
12. [Common Evaluation Failures and How to Debug Them](#common-evaluation-failures-and-how-to-debug-them)
13. [Self-Test Questions](#self-test-questions)
14. [What to Study Next](#what-to-study-next)

---

## Why This File Matters

In traditional software you write unit tests that pass or fail. In AI engineering, answers are **on a spectrum** — they can be mostly right, partially wrong, or completely hallucinated. You need a **scoring system**, not just pass/fail.

This file implements a rule-based evaluation framework that scores every RAG response on three dimensions. **No LLM is needed for evaluation** — it's pure Python string analysis. This means evaluation is **free, fast, and deterministic**.

| What you'll learn | DE parallel | 🫏 Donkey |
|---|---| --- |
| Retrieval quality scoring | Data freshness and completeness checks | Saddlebag fetch 🎒 |
| Faithfulness scoring (anti-hallucination) | Referential integrity validation | Memory drift ⚠️ |
| Answer relevance scoring | Output schema validation | Report card 📝 |
| Weighted composite scores | Data quality dashboards (Great Expectations) | 🫏 On the route |
| Rule-based evaluation (no LLM needed) | SQL-based data quality checks (no ML needed) | The donkey 🐴 |

- 🫏 **Donkey:** Think of this as the orientation briefing given to a new donkey before its first delivery run — it sets the context for everything that follows.

---

## DE Parallel — Evaluation Is Data Quality Testing

```
DATA ENGINEER                              AI ENGINEER
────────────────                           ──────────────
Great Expectations suite:                  RAG Evaluator:
  expect_column_values_to_not_be_null      retrieval_score ≥ 0.7
  expect_column_values_to_be_between       faithfulness_score ≥ 0.8
  expect_column_unique_value_count         answer_relevance ≥ 0.6
  ────────                                 ────────
  Returns: success/failure + metrics       Returns: pass/fail + scores

dbt test:                                  Golden dataset test:
  unique, not_null, accepted_values          known Q&A pairs + expected scores
  ────────                                   ────────
  Runs on every pipeline execution           Runs on demand or in CI
```

**The key difference:** In DE, you check *data* against *rules*. In AI, you check *generated text* against *reference text*. Both answer the same question: **"Is the output good enough?"**

- 🫏 **Donkey:** The donkey's report card — did it grab the right saddlebags and write an accurate answer?

---

## Architecture Overview — The Four Scores

```python
# 4 dataclasses = 4 types of scores
@dataclass
class RetrievalScore:        # Did search find good chunks?
    average_score: float     # Mean similarity score of retrieved chunks
    top_score: float         # Best match
    min_score: float         # Worst match
    chunks_above_threshold: int  # How many scored above the threshold
    quality: str             # "excellent" / "good" / "fair" / "poor"

@dataclass
class FaithfulnessScore:     # Did the LLM stick to context?
    score: float             # 0.0–1.0 ratio of grounded claims
    claims_in_context: int   # Sentences found in context
    claims_not_in_context: int  # Sentences NOT found (potential hallucination)
    has_hallucination: bool  # True if score < threshold

@dataclass
class AnswerRelevanceScore:  # Did the LLM answer the actual question?
    score: float             # 0.0–1.0 ratio of question keywords in answer
    keywords_found: int      # How many question keywords appear in answer
    keywords_missing: int    # How many question keywords are absent

@dataclass
class EvaluationResult:      # Combined result
    retrieval: RetrievalScore
    faithfulness: FaithfulnessScore
    relevance: AnswerRelevanceScore
    overall_score: float     # Weighted combination
    passed: bool             # overall_score ≥ 0.7
```

**Visualised:**

```
                    ┌─────────────────────────────┐
                    │        EvaluationResult      │
                    │                              │
                    │   retrieval:     ████░ 0.82  │──→ Did search work?
                    │   faithfulness:  █████ 0.95  │──→ Any hallucination?
                    │   relevance:     ███░░ 0.71  │──→ On-topic?
                    │   ─────────────────────      │
                    │   overall:       ████░ 0.84  │──→ Weighted average
                    │   passed:        ✅ True      │──→ ≥ 0.7
                    └─────────────────────────────┘
```

- 🫏 **Donkey:** Like a stable floor plan showing where the donkey enters, where the saddlebags are loaded, and which route it takes to the customer.

---

## Concept 1: Retrieval Quality

**Question this answers:** *"Did the vector store return relevant chunks?"*

```python
def _evaluate_retrieval(
    self, retrieved_chunks: list[tuple[str, float]]
) -> RetrievalScore:
    """Evaluate the quality of retrieved chunks based on similarity scores."""
    if not retrieved_chunks:
        return RetrievalScore(
            average_score=0.0, top_score=0.0, min_score=0.0,
            chunks_above_threshold=0, quality="poor"
        )

    scores = [score for _, score in retrieved_chunks]
    avg = sum(scores) / len(scores)
    above = sum(1 for s in scores if s >= self.relevance_threshold)

    quality = (
        "excellent" if avg >= 0.85
        else "good" if avg >= 0.7
        else "fair" if avg >= 0.5
        else "poor"
    )

    return RetrievalScore(
        average_score=round(avg, 4),
        top_score=round(max(scores), 4),
        min_score=round(min(scores), 4),
        chunks_above_threshold=above,
        quality=quality,
    )
```

**How it works:**

```
Input: [("Refunds take 14 days...", 0.95),
        ("Return policy states...", 0.88),
        ("Shipping info...", 0.42)]

Output: RetrievalScore(
    average_score=0.75,     ← (0.95 + 0.88 + 0.42) / 3
    top_score=0.95,         ← best match
    min_score=0.42,         ← worst match
    chunks_above_threshold=2, ← 2 of 3 are ≥ 0.7
    quality="good"          ← 0.75 ≥ 0.7
)
```

**DE parallel:** This is like checking your JOIN hit rate. If you join `orders` to `customers` and only 60% match, your join quality is "fair." If 95% match, it's "excellent."

**Why this matters:** If retrieval quality is poor, it doesn't matter how good the LLM is — it's working with irrelevant context. **Fix retrieval before fixing prompts.**

- 🫏 **Donkey:** The warehouse robot dispatched to find the right saddlebag shelf — it uses GPS coordinates (embeddings) to locate the nearest relevant chunks in ~9 hops.

---

## Concept 2: Faithfulness

**Question this answers:** *"Did the LLM only say things that are in the context?"*

This is the **anti-hallucination check** — the most important score for production RAG.

```python
def _evaluate_faithfulness(
    self, answer: str, context_chunks: list[str]
) -> FaithfulnessScore:
    """Check if the answer is grounded in the context."""
    if self._is_refusal(answer):
        return FaithfulnessScore(
            score=1.0, claims_in_context=0,
            claims_not_in_context=0, has_hallucination=False
        )

    sentences = self._split_sentences(answer)
    context_text = " ".join(context_chunks).lower()
    context_keywords = self._extract_keywords(context_text)

    in_context = 0
    not_in_context = 0

    for sentence in sentences:
        if self._is_meta_sentence(sentence):
            in_context += 1  # Citations don't need to be verified
            continue

        sentence_keywords = self._extract_keywords(sentence.lower())
        if not sentence_keywords:
            continue

        overlap = len(sentence_keywords & context_keywords)
        ratio = overlap / len(sentence_keywords)

        if ratio >= 0.5:
            in_context += 1
        else:
            not_in_context += 1

    total = in_context + not_in_context
    score = in_context / total if total > 0 else 1.0

    return FaithfulnessScore(
        score=round(score, 4),
        claims_in_context=in_context,
        claims_not_in_context=not_in_context,
        has_hallucination=score < self.faithfulness_threshold,
    )
```

**The algorithm, step by step:**

```
Answer: "Refunds are processed within 14 days. Digital products cannot be refunded.
         The CEO was born in Amsterdam."

Context: "Refunds take 14 business days. Digital products are non-refundable."

Step 1: Split answer into sentences
  → ["Refunds are processed within 14 days.",
     "Digital products cannot be refunded.",
     "The CEO was born in Amsterdam."]

Step 2: For each sentence, extract keywords and check overlap with context
  → Sentence 1: keywords {refunds, processed, 14, days}
                 context has {refunds, 14, days} → overlap 3/4 = 0.75 ≥ 0.5 → ✅ in context
  → Sentence 2: keywords {digital, products, refunded}
                 context has {digital, products, refundable} → overlap 2/3 = 0.67 ≥ 0.5 → ✅
  → Sentence 3: keywords {CEO, born, Amsterdam}
                 context has NONE → overlap 0/3 = 0.0 < 0.5 → ❌ NOT in context

Result: FaithfulnessScore(
    score=0.6667,           ← 2 of 3 sentences grounded
    claims_in_context=2,
    claims_not_in_context=1,  ← "The CEO was born in Amsterdam" is hallucinated
    has_hallucination=True  ← 0.67 < 0.8 threshold
)
```

**DE parallel — referential integrity:**

```sql
-- Check: every order references an existing customer
SELECT COUNT(*) as orphaned_orders
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id
WHERE c.id IS NULL;

-- If orphaned_orders > 0, you have a data quality problem.
-- If claims_not_in_context > 0, you have a hallucination problem.
```

**Why the 0.5 keyword overlap threshold?** A sentence doesn't need to be a word-for-word copy — it just needs to be *about the same thing*. "Refunds are processed within 14 days" and "Refunds take 14 business days" share enough keywords to be considered grounded.

- 🫏 **Donkey:** Checking whether the donkey's answer matches the cargo in its saddlebag — if it drifts from the documents, it's hallucinating.

---

## Concept 3: Answer Relevance

**Question this answers:** *"Did the LLM actually answer what was asked?"*

```python
def _evaluate_answer_relevance(
    self, question: str, answer: str
) -> AnswerRelevanceScore:
    """Check if the answer addresses the question."""
    question_keywords = self._extract_keywords(question.lower())
    answer_lower = answer.lower()

    found = sum(1 for kw in question_keywords if kw in answer_lower)
    missing = len(question_keywords) - found

    score = found / len(question_keywords) if question_keywords else 1.0

    return AnswerRelevanceScore(
        score=round(score, 4),
        keywords_found=found,
        keywords_missing=missing,
    )
```

**Example:**

```
Question: "What is the refund policy for digital products?"
Keywords: {refund, policy, digital, products}

Answer: "Digital products are non-refundable according to our policy."
Found in answer: {refund → no, policy → yes, digital → yes, products → yes}
Score: 3/4 = 0.75

Answer: "The weather today is sunny."
Found in answer: {refund → no, policy → no, digital → no, products → no}
Score: 0/4 = 0.00  ← completely off-topic
```

**DE parallel:** This is like output schema validation. If the user asks for `customer_id, name, email` and you return `order_id, total, date`, the output is valid SQL but answers the wrong question.

- 🫏 **Donkey:** Verifying the donkey delivered to the right address — the answer should match what the customer actually asked for.

---

## Concept 4: Weighted Overall Score

```python
def evaluate(self, question, answer, retrieved_chunks, expected_answer=None):
    retrieval = self._evaluate_retrieval(retrieved_chunks)
    faithfulness = self._evaluate_faithfulness(answer, [c[0] for c in retrieved_chunks])
    relevance = self._evaluate_answer_relevance(question, answer)

    overall = (
        retrieval.average_score * 0.3 +
        faithfulness.score * 0.4 +
        relevance.score * 0.3
    )

    return EvaluationResult(
        retrieval=retrieval,
        faithfulness=faithfulness,
        relevance=relevance,
        overall_score=round(overall, 4),
        passed=overall >= 0.7,
    )
```

**The weights tell you what matters most:**

```
Faithfulness:  0.4  ← Most important — hallucination is the #1 risk
Retrieval:     0.3  ← Second — garbage in = garbage out
Relevance:     0.3  ← Third — answering the wrong question is bad, but not as bad as lying

Example calculation:
  retrieval  = 0.82 × 0.3 = 0.246
  faithfulness = 0.95 × 0.4 = 0.380
  relevance  = 0.71 × 0.3 = 0.213
  ─────────────────────────
  overall    = 0.839 ≥ 0.7 → PASSED ✅
```

**Why faithfulness gets the highest weight:** A system that says *"I don't know"* is better than one that confidently gives wrong information. In production, hallucination can cause legal, financial, or reputational damage. That's why detecting and preventing it gets 40% of the score.

- 🫏 **Donkey:** The quality inspector's stamp — each delivered answer is graded on retrieval accuracy, faithfulness, and relevance before the customer signs.

---

## The Refusal Detector — Knowing When "I Don't Know" Is Correct

```python
def _is_refusal(self, answer: str) -> bool:
    """Detect if the answer is a refusal to answer."""
    refusal_patterns = [
        "i don't have enough information",
        "the uploaded documents don't contain",
        "i cannot find",
        "based on the provided documents, i cannot",
        "no relevant information",
    ]
    answer_lower = answer.lower()
    return any(pattern in answer_lower for pattern in refusal_patterns)
```

**Why refusals get a perfect faithfulness score (1.0):** If the LLM says "I don't know" when the context doesn't have the answer, that's the **correct behaviour** — it's not hallucinating. The prompt rules (#2) tell it to do exactly this.

**DE parallel:** This is like a query returning zero rows. The query is correct — there's simply no matching data. You don't flag that as a data quality issue.

- 🫏 **Donkey:** Small utility workers in the stable — they handle sentence-splitting and keyword extraction so the main donkey stays focused on delivery.

---

## Helper Methods

### `_split_sentences()`

```python
def _split_sentences(self, text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
```

Filters out fragments shorter than 10 characters (noise like "Yes." or "OK.").

### `_extract_keywords()`

```python
def _extract_keywords(self, text: str) -> set[str]:
    """Extract meaningful keywords (remove stop words)."""
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                  "being", "have", "has", "had", "do", "does", "did", "will",
                  "would", "could", "should", "may", "might", "can", "shall",
                  "to", "of", "in", "for", "on", "with", "at", "by", "from",
                  "as", "into", "through", "during", "before", "after", "above",
                  "below", "between", "and", "but", "or", "nor", "not", "so",
                  "yet", "both", "either", "neither", "each", "every", "all",
                  "this", "that", "these", "those", "i", "you", "he", "she",
                  "it", "we", "they", "what", "which", "who", "whom"}
    words = re.findall(r'\b\w+\b', text.lower())
    return {w for w in words if w not in stop_words and len(w) > 2}
```

**DE parallel:** Stop words are like common columns (`id`, `created_at`, `updated_at`) that you'd exclude from a similarity comparison between tables.

### `_is_meta_sentence()`

```python
def _is_meta_sentence(self, sentence: str) -> bool:
    """Detect citation sentences that don't need grounding check."""
    meta_patterns = [
        r'\[Document chunk \d+\]',
        r'according to the documents?',
        r'based on the provided',
    ]
    return any(re.search(p, sentence, re.IGNORECASE) for p in meta_patterns)
```

Sentences like *"According to [Document chunk 1]..."* are structural — they cite sources, not make claims. They're automatically counted as "in context."

- 🫏 **Donkey:** Small utility workers in the stable — they handle sentence-splitting and keyword extraction so the main donkey stays focused on delivery.

---

## How It Fits in the Pipeline

```
                           ┌──────────────┐
                           │  chain.py    │
                           │  query()     │
                           └──────┬───────┘
                                  │
                                  ▼
                      { answer, sources, chunks }
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
              Return to user            evaluator.py
              (POST /chat)              evaluate()
                                           │
                              ┌─────────────┼─────────────┐
                              ▼             ▼             ▼
                         Retrieval    Faithfulness    Relevance
                          Score          Score         Score
                              └─────────────┬─────────────┘
                                            ▼
                                   EvaluationResult
                                   (overall ≥ 0.7?)
                                            │
                                            ▼
                                    metrics.py
                                   record_evaluation()
```

The evaluator doesn't block the response — it runs **after** the answer is returned (or in a background task). This keeps latency low while still collecting quality metrics.

### Running Evaluation via the API

The evaluation framework is exposed through two API endpoints:

| Endpoint | Purpose | When to use | 🫏 Donkey |
|---|---|---| --- |
| `POST /api/evaluate` | Evaluate a single question | Testing specific questions, debugging low scores | Report card 📝 |
| `POST /api/evaluate/suite` | Run the full golden dataset | After any setting change, before deploying | Report card 📝 |

**Single question** — in **Swagger UI** (`http://localhost:8000/docs`) → `POST /api/evaluate` → **"Try it out"**:

```json
{"question": "What is the refund policy?"}
```

**Full suite** — in **Swagger UI** → `POST /api/evaluate/suite` → **"Try it out"**:

```json
{}
```

Or use Swagger UI at `http://localhost:8000/docs` → find the **Evaluation** section.

📖 **See:** [Evaluate Endpoint Deep Dive](../architecture-and-design/api-routes/evaluate-endpoint-explained.md) for the full walkthrough.

- 🫏 **Donkey:** The mechanics of the stable — understanding how each piece fits so you can maintain and extend the system.

---

## Cloud vs Local — Provider-Agnostic by Design

**The evaluator doesn't use any cloud services.** It's pure Python string analysis:

| Component | Uses cloud? | Why | 🫏 Donkey |
|---|---|---| --- |
| `_evaluate_retrieval()` | ❌ | Just math on similarity scores | Report card 📝 |
| `_evaluate_faithfulness()` | ❌ | Keyword overlap — pure string comparison | Saddlebag piece 📦 |
| `_evaluate_answer_relevance()` | ❌ | Keyword presence check | Report card 📝 |
| `_split_sentences()` | ❌ | Regex splitting | 🫏 On the route |
| `_extract_keywords()` | ❌ | Stop word removal | 🫏 On the route |

**This means:**
- Evaluation costs **$0** on all providers
- Evaluation is **deterministic** — same input always produces same score
- You can evaluate **offline** — store answers and evaluate later
- You can evaluate **locally** even if the LLM is cloud-based

**Trade-off:** Rule-based evaluation is simpler and cheaper than LLM-based evaluation (e.g., using GPT-4 to judge GPT-4's answers), but it's also less nuanced. It can't detect subtle semantic errors — only keyword-level problems.

- 🫏 **Donkey:** Choosing which stable to work with — AWS Bedrock, Azure OpenAI, or a local Ollama barn each offer different donkeys at different prices.

---

## Common Evaluation Failures and How to Debug Them

| Score too low? | Likely cause | How to debug | 🫏 Donkey |
|---|---|---| --- |
| **Retrieval < 0.5** | Chunks are irrelevant | Check chunk content — is the right document ingested? | Saddlebag piece 📦 |
| **Retrieval < 0.5** | Embedding quality poor | Try different embedding model (local: `nomic-embed-text` → `all-minilm`) | GPS stamp 📍 |
| **Faithfulness < 0.8** | LLM is hallucinating | Tighten prompt rules, lower temperature | The donkey 🐴 |
| **Faithfulness < 0.8** | Keyword extraction too strict | Check if answer uses synonyms not in context | Saddlebag match 🫏 |
| **Relevance < 0.6** | LLM answered different question | Check if question is ambiguous | The donkey 🐴 |
| **Relevance < 0.6** | Answer is a refusal | Check if context was empty (correct behaviour) | Right address 🎯 |
| **Overall < 0.7** | Multiple issues | Debug each score individually | Hoof check 🔧 |

**Debugging workflow:**

```bash
# 1. Run evaluation
python -c "
from src.evaluation.evaluator import RAGEvaluator
e = RAGEvaluator()
result = e.evaluate(
    question='What is the refund policy?',
    answer='Refunds take 14 days.',
    retrieved_chunks=[('Refunds take 14 business days...', 0.92)]
)
print(result.to_dict())
"

# 2. Check individual scores
# If retrieval is low → fix vector store / embeddings
# If faithfulness is low → fix prompt / temperature
# If relevance is low → fix prompt / chunking
```

- 🫏 **Donkey:** Checking the donkey's hooves, saddle straps, and GPS signal before concluding it's lost — most delivery failures have a simple root cause.

---

## Self-Test Questions

### Tier 1 — Must understand

- [ ] What are the three evaluation dimensions and what does each measure?
- [ ] Why does faithfulness get 40% weight while others get 30%?
- [ ] What happens when the LLM says "I don't have enough information"? (Hint: refusal detection)
- [ ] Why is this evaluator provider-agnostic?

### Tier 2 — Should understand

- [ ] How does the keyword overlap ratio (≥ 0.5) determine if a sentence is grounded?
- [ ] What's the difference between a retrieval score of 0.5 and 0.85? In quality terms?
- [ ] Why are meta sentences (citations) automatically counted as "in context"?
- [ ] What are the limitations of rule-based evaluation vs LLM-based evaluation?

### Tier 3 — AI engineering territory

- [ ] How would you add a 4th evaluation dimension (e.g., "completeness")?
- [ ] When would you switch from rule-based to LLM-based evaluation?
- [ ] How would you use evaluation scores to auto-tune `top_k` or `chunk_size`?
- [ ] If faithfulness is 0.65 and you need to reach 0.8, what do you try first?

- 🫏 **Donkey:** Sending the donkey on 25 standard test deliveries (golden dataset) to verify it returns the right packages every time.

---

## What to Study Next

You now understand how to measure RAG quality. Next:

- **File #15:** [`src/evaluation/golden_dataset.py`](golden-dataset-deep-dive.md) — the test cases that drive this evaluator
- **File #16:** [`src/monitoring/metrics.py`](metrics-deep-dive.md) — where evaluation scores become operational metrics

📖 **Related docs:**
- [RAG Chain Deep Dive (#13)](rag-chain-deep-dive.md) — the pipeline being evaluated
- [RAG Concepts → Evaluation](rag-concepts.md)

- 🫏 **Donkey:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
