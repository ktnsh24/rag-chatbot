# Evaluation Metrics — rag-chatbot

> **Purpose:** the metrics-only reference for THIS repo. If you want to know "what does `faithfulness=0.75` mean for this lab?", this is the doc.
>
> **Scope:** rag-chatbot only. For the cross-repo catalogue (knowledge-engine extras, agent metrics, gateway metrics), see `~/maestro/ai-portfolio/personal/evaluation-metrics-cheatsheet.md`.
>
> **Source of truth:** `src/evaluation/evaluator.py`. When code disagrees with this doc, code wins — update this doc.

---

## Table of Contents

- [The 3 + 2 metrics this repo uses](#the-3--2-metrics-this-repo-uses)
- [Metric details](#metric-details)
  - [retrieval](#retrieval)
  - [faithfulness](#faithfulness)
  - [answer_relevance](#answer_relevance)
  - [latency](#latency)
  - [cost](#cost)
- [Composite overall_score and pass threshold](#composite-overall_score-and-pass-threshold)
- [Reading a result row](#reading-a-result-row)
- [Where to change the thresholds](#where-to-change-the-thresholds)
- [What this repo deliberately does NOT measure](#what-this-repo-deliberately-does-not-measure)

---

## The 3 + 2 metrics this repo uses

Every result table in this repo (`scripts/lab_results/**`, evaluation API responses, dashboards) reports the same 5 numbers. Memorise them once.

| Metric | Class in code | Range | Direction | One-line meaning | 🫏 Donkey |
| --- | --- | --- | --- | --- | --- |
| **retrieval** | `RetrievalScore` | 0.0 – 1.0 | higher is better | Average similarity score of the chunks the vector store returned | The donkey returns from the warehouse with 5 backpacks. The GPS shows a confidence reading on each one — this score is the average. High = right shelf, low = wrong aisle. |
| **faithfulness** | `FaithfulnessScore` | 0.0 – 1.0 | higher is better | Fraction of answer sentences whose keywords appear in the retrieved chunks | Open the parcel at the customer's door and check every item against the original backpack contents. Items the donkey added "from its own pocket" drop the score. |
| **answer_relevance** | `AnswerRelevanceScore` | 0.0 – 1.0 | higher is better | Fraction of question keywords present in the answer | Customer asked "what's the return window?". The donkey delivers a parcel about shipping costs. Faithful, but answered a question nobody asked. |
| **latency** | logged per request | milliseconds | lower is better | Wall-clock time from API call to response | Stopwatch starts when the customer rings the stable bell, stops when the parcel hits their hand. |
| **cost** | logged per request | € or $ per 1k requests | lower is better | Token count × per-token price | Weigh the cargo in (prompt) + cargo back (completion). Stable charges per kilo. |

That's the entire yardstick. Every lab in `docs/hands-on-labs/` measures itself against these 5 numbers. Nothing more, nothing less.

---

## Metric details

### retrieval

- **What it measures:** how relevant the chunks the vector store returned are to the question.
- **How it's calculated:** `avg(cosine_similarity)` across all retrieved chunks. Each chunk gets a 0.0 – 1.0 similarity score from the vector store. Example: 5 chunks scoring `[0.92, 0.85, 0.71, 0.45, 0.19]` → `retrieval = 3.12 / 5 = 0.624`.
- **Threshold note:** chunks below `RetrievalScore.threshold = 0.5` are flagged "low confidence" — that's why `top_k = 1` often scores higher than `top_k = 10` (only the best chunk counts).
- **Knob that moves it most:** `top_k` (Lab 1), reranker on/off (Lab 10), hybrid search (Lab 11), HNSW `ef` (Lab 13).
- **🫏 Failure mode:** retrieval = 0.4 means the donkey is grabbing backpacks from the wrong aisle. Don't blame the LLM — fix the embedding model, chunking, or `top_k` first.

### faithfulness

- **What it measures:** whether the answer contains ONLY information from the retrieved chunks (no hallucination).
- **How it's calculated:** split the answer into sentences → extract keywords per sentence (skip stop words) → check if ≥ 50 % of those keywords appear in the retrieved chunks → `grounded_sentences / total_sentences`. Example: 3 of 4 sentences have keywords in context → `0.750`. Score `0.000` means every sentence was hallucinated.
- **Mode toggle:** the rag-chatbot version is keyword-based (cheap, deterministic). The knowledge-engine version upgrades this to LLM-as-judge (`EVAL_MODE=llm_judge`).
- **Knob that moves it most:** system prompt strictness (Lab 2), guardrails (Lab 4 / Lab 9), retrieval quality (because no chunks = nothing to ground on).
- **🫏 Failure mode:** faithfulness = 0.0 with retrieval = 0.85 is the worst case — the donkey had the right backpack but invented the delivery note anyway.

### answer_relevance

- **What it measures:** whether the answer actually addresses the question asked (not just any plausible-sounding answer).
- **How it's calculated:** extract keywords from the question → count how many appear in the answer. `found_keywords / total_keywords`. Example: question "What is the refund policy?" has keywords `[refund, policy]`, both found → `1.000`.
- **Knob that moves it most:** prompt template clarity, business-metric labels (Lab 3).
- **🫏 Failure mode:** faithful + correct + irrelevant = the donkey delivered the right parcel to the wrong house. Common when the question is vague ("How long?").

### latency

- **What it measures:** wall-clock round-trip time from `POST /api/chat` to response.
- **How it's calculated:** timer started in middleware, stopped in response writer. Logged per request, aggregated to `avg`, `p50`, `p95`, `p99`.
- **Typical numbers** (from `scripts/lab_results/local-vs-azure-comparison.md`):
  - Local Ollama on CPU: ~21,000 ms
  - Azure GPT-4o: ~2,200 ms
  - AWS Bedrock Sonnet 4.6: ~3,800 ms
- **🫏 Failure mode:** if `p99 > 3 × p50`, the donkey is occasionally collapsing — usually a cold-start or rate-limit issue.

### cost

- **What it measures:** money spent per query (or per 1,000 queries for aggregates).
- **How it's calculated:** `prompt_tokens × price_in + completion_tokens × price_out + embedding_tokens × price_embed`. Per-token prices live in `src/llm/pricing.py`.
- **Typical numbers** (per 1,000 queries):
  - Local Ollama: €0.00
  - AWS Sonnet 4.6: ~€0.21
  - Azure GPT-4o: ~$0.87
- **🫏 Failure mode:** cost = €10 / day from a side project. Look for runaway retries, over-large `top_k`, or a forgotten loop in a notebook.

---

## Composite `overall_score` and pass threshold

Every result row also reports a single composite score so you don't have to read 5 numbers to decide pass/fail.

```
overall_score = 0.4 × retrieval
              + 0.4 × faithfulness
              + 0.2 × answer_relevance
```

| Threshold | Default | Env var | Meaning |
| --- | --- | --- | --- |
| `OVERALL_PASS_THRESHOLD` | 0.70 | yes | Composite ≥ this = lab passes |
| `RetrievalScore.threshold` | 0.50 | no (constant) | Chunks below = "low confidence" |

🫏 The composite is the one number on the daily report card. Faithfulness and retrieval each carry 40 % because a parcel with wrong contents is the cardinal sin — answer-relevance is only a tiebreaker. A 0.0 on faithfulness alone almost always drags the composite below 0.70.

---

## Reading a result row

Example row from `scripts/lab_results/local-vs-azure-comparison.md`:

```
| 11a-1 | 500 euros equipment | 0.825 | 0.611 | 0.805 | 🟢 Local | 1.00 | 0.33 | 1.00 |
```

Decoded:

| Column | Value | Meaning |
| --- | --- | --- |
| Exp | `11a-1` | Lab 11 (hybrid search), variant a, query 1 |
| Question | `500 euros equipment` | The actual prompt sent |
| Local / Azure / AWS | 0.825 / 0.611 / 0.805 | `overall_score` per provider |
| Winner | 🟢 Local | Highest overall_score |
| L.Faith / A.Faith / W.Faith | 1.00 / 0.33 / 1.00 | `faithfulness` per provider |

Two-second read: Local won this row because Azure invented something (faith = 0.33) while Local stayed grounded (faith = 1.00). The hybrid-search knob helped Local because the query had an exact string ("500 euros") — proving Lab 11's hypothesis.

---

## Where to change the thresholds

| Setting | File | Default |
| --- | --- | --- |
| `OVERALL_PASS_THRESHOLD` | `.env` | `0.70` |
| Faithfulness keyword-overlap cutoff | `src/evaluation/evaluator.py` (constant) | `0.50` |
| `RetrievalScore.threshold` | `src/evaluation/evaluator.py` (`@dataclass`) | `0.50` |
| Composite weights (0.4 / 0.4 / 0.2) | `src/evaluation/evaluator.py` → `RAGEvaluator.compute_overall` | hardcoded |

If you tune any of these, update this doc in the same commit and re-run the golden-set evaluation in `scripts/lab_results/`.

---

## What this repo deliberately does NOT measure

- **ContextPrecision / ContextRecall** — needs labelled "expected chunk IDs". Lives in knowledge-engine instead.
- **AnswerCorrectness** — needs gold-standard answer embeddings. Lives in knowledge-engine.
- **Completeness** — needs LLM-as-judge. Lives in knowledge-engine.
- **Tool-selection / handoff scores** — agent-only metrics. Live in ai-agent and ai-multi-agent.
- **Cache-hit rate / rate-limit reject rate** — gateway concerns. Live in ai-gateway.

If you need any of those, see the cross-repo cheatsheet:
`~/maestro/ai-portfolio/personal/evaluation-metrics-cheatsheet.md`.

---

> **Last updated:** 2026-04-25 · pairs with `docs/hands-on-labs/how-to-read-the-labs.md` and the cross-repo cheatsheet in `~/maestro/ai-portfolio/personal/`.
