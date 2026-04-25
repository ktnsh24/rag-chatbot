# 3-Way Lab Results Comparison: Local vs Azure vs AWS

> **Local run** (2026-04-21): Ollama llama3.2 (3.2B Q4) + ChromaDB + nomic-embed-text + CrossEncoder reranker + local guardrails + hybrid search (BM25 + vector).
>
> **Azure run** (2026-04-20): Azure OpenAI GPT-4o + Azure AI Search + text-embedding-3-small + Azure Content Safety guardrails + hybrid search.
>
> **AWS run** (2026-04-22): Claude Sonnet 4.6 + DynamoDB (brute-force cosine) + Titan Embed v2 + min-max normalization + no reranker + no guardrails.
>
> **Coverage:** All three runs executed all 58 API experiments across Labs 1–16 (Phases 1–5). 40 of them are comparable across all three providers (the rest are infra-only labs that don't produce a per-question score). Errors: Local 0 · Azure 2 · AWS 0.

---

## How to read the experiment IDs

Tables below use compact IDs like `1a`, `1b_topk5`, `3a_seq2`, `11c-1`. Decode them with the lab map first, then read the per-row "Question" column for the actual prompt.

| Lab | Name | Experiment IDs in this report |
| --- | --- | --- |
| Lab 1 | Retrieval Quality — "Did I find the right chunks?" | `1a`, `1b_topk1`, `1b_topk5`, `1b_topk10`, `1c` |
| Lab 2 | Faithfulness & Hallucination | `2a`, `2b`, `2c` |
| Lab 3 | Business-Aligned Metrics | `3a_seq1`, `3a_seq2` |
| Lab 4 | Guardrails (prompt-injection eval) | `4a_eval` |
| Lab 5 | Observability — traced + dashboard runs | `5a`, `5b_q1`…`5b_q5` |
| Lab 6 | Data Flywheel (before/after document upload) | `6a`, `6c` |
| Lab 10 | Re-ranking (CrossEncoder vs none) | `10a-1`, `10a-2`, `10a-3`, `10b-1`, `10b-2`, `10b-3` |
| Lab 11 | Hybrid Search (BM25 + vector) | `11a-1`…`11a-3`, `11b-1`…`11b-3`, `11c-1`, `11c-2` |
| Lab 12 | Bulk Ingestion (does topic 3 get retrieved?) | `12b` |
| Lab 13 | HNSW Tuning & Sharding | `13a`, `13b-1`…`13b-3`, `13c`, `13d` |

Labs 7–9 and 14–16 are present in the run logs but produce no per-question score (they're infra/process labs), so they don't appear in the head-to-head tables below.

---

## Executive Summary

| Metric | Local (Ollama) | Azure (GPT-4o) | AWS (Sonnet 4.6) | Winner |
| --- | --- | --- | --- | --- |
| **Experiments passed** | 18 / 58 | 16 / 58 | 25 / 58 | 🟠 AWS (+7) |
| **Errors** | 0 | 2 | 0 | 🟢 Local / 🟠 AWS |
| **Avg overall score** | 0.598 | 0.638 | 0.726 | 🟠 AWS (+0.088) |
| **Avg latency** | 21,329 ms | 2,176 ms | 3,790 ms | 🔵 Azure (~1.7× faster than AWS) |
| **Avg faithfulness** | 0.50 | 0.56 | 0.82 | 🟠 AWS (dominant) |
| **Cost per run** | $0.00 (free) | ~$0.87 | ~€0.21 | 🟢 Local |

**Bottom line:** AWS with Claude Sonnet 4.6 + score normalization wins convincingly — 25 passed vs Local's 18 and Azure's 16. The breakthrough wasn't the model: it was fixing the retrieval pipeline (min-max normalizing Titan similarity scores). Sonnet 4.6's faithfulness (0.82 avg) is remarkable — it almost never hallucinates, letting the retrieval improvement carry overall scores above the 0.7 pass threshold.

---

## Head-to-Head: 40 Comparable Experiments

Legend: 🟢 Local wins · 🔵 Azure wins · 🟠 AWS wins · 🟡 Tie (within 0.02). `L.Faith / A.Faith / W.Faith` = faithfulness score (0–1, higher = less hallucination).

### Phase 1 — Foundation (Lab 1: Retrieval Quality, Lab 2: Faithfulness)

| Lab | Exp | Question | Local | Azure | AWS | Winner | L.Faith | A.Faith | W.Faith |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1a | What is the refund policy? | 0.871 | 0.787 | 0.799 | 🟢 Local | 0.83 | 0.75 | 1.00 |
| 1 | 1b_topk1 | Refund policy (top_k=1) | 0.882 | 0.810 | 1.000 | 🟠 AWS | 0.71 | 0.69 | 1.00 |
| 1 | 1b_topk5 | Refund policy (top_k=5) | 0.871 | 0.787 | 0.799 | 🟢 Local | 0.83 | 0.75 | 1.00 |
| 1 | 1b_topk10 | Refund policy (top_k=10) | 0.700 | 0.779 | 0.772 | 🔵 Azure | 0.70 | 0.75 | 1.00 |
| 1 | 1c | Remote work policy? | 0.400 | 0.678 | 0.572 | 🔵 Azure | 0.00 | 0.75 | 0.33 |
| 2 | 2a | Refund after 30 days? | 0.473 | 0.511 | 0.809 | 🟠 AWS | 0.33 | 0.33 | 1.00 |
| 2 | 2b | How many days to return? | 0.911 | 0.803 | 0.733 | 🟢 Local | 1.00 | 1.00 | 1.00 |
| 2 | 2c | How long? (vague) | 0.451 | 0.162 | 0.617 | 🟠 AWS | 1.00 | 0.00 | 0.50 |

**Phase 1 score:** Local 3 · Azure 2 · AWS 3. AWS dominates on factual refund queries thanks to Sonnet's high faithfulness (1.00 on 5 of 8 rows). Local's llama3.2 still wins on "How many days to return?" with perfect retrieval.

### Phase 2 — Bridge Skills (Lab 3: Business Metrics, Lab 4: Guardrails, Lab 5: Observability)

| Lab | Exp | Question | Local | Azure | AWS | Winner | L.Faith | A.Faith | W.Faith |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 3a_seq1 | Refund policy for physical products? | 0.807 | 0.713 | 0.790 | 🟢 Local | 0.75 | 0.57 | 1.00 |
| 3 | 3a_seq2 | How do returns work? | 0.704 | 0.653 | 0.821 | 🟠 AWS | 0.83 | 0.82 | 1.00 |
| 4 | 4a_eval | Prompt-injection eval | 0.000 | 0.160 | 0.583 | 🟠 AWS | 0.00 | 0.00 | 0.67 |
| 5 | 5a | Refund policy (traced) | 0.871 | 0.787 | 0.799 | 🟢 Local | 0.83 | 0.75 | 1.00 |
| 5 | 5b_q1 | Refund policy (dashboard) | 0.871 | 0.781 | 0.799 | 🟢 Local | 0.83 | 0.73 | 1.00 |
| 5 | 5b_q2 | Return digital products? | 0.840 | 0.780 | 0.778 | 🟢 Local | 1.00 | 1.00 | 1.00 |
| 5 | 5b_q3 | Contact support? | 0.500 | 0.872 | 0.636 | 🔵 Azure | 0.50 | 1.00 | 0.50 |
| 5 | 5b_q4 | Remote work policy? | 0.400 | 0.678 | 0.572 | 🔵 Azure | 0.00 | 0.75 | 0.33 |
| 5 | 5b_q5 | How long? (vague) | 0.451 | 0.162 | 0.617 | 🟠 AWS | 1.00 | 0.00 | 0.50 |

**Phase 2 score:** Local 4 · Azure 2 · AWS 3. Local dominates on refund questions. AWS handles the prompt-injection eval better than both (0.583 vs 0.160 / 0.000). Azure wins on missing-context scenarios.

### Phase 3 — Production AI Engineering (Lab 6: Data Flywheel)

| Lab | Exp | Question | Local | Azure | AWS | Winner | L.Faith | A.Faith | W.Faith |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | 6a | Remote work policy? (before doc upload) | 0.400 | 0.678 | 0.572 | 🔵 Azure | 0.00 | 0.75 | 0.33 |
| 6 | 6c | Remote work policy? (after doc upload) | 0.400 | 0.691 | 0.779 | 🟠 AWS | 0.00 | 0.75 | 1.00 |

**Phase 3 score:** Azure 1 · AWS 1. After document upload, AWS overtakes Azure (0.779 vs 0.691). Sonnet leverages the uploaded remote-work doc with faith=1.00.

### Phase 4 — Advanced RAG (Labs 10–13)

#### Lab 10 — Re-ranking ("does CrossEncoder help?")

| Exp | Question | Local | Azure | AWS | Winner | L.Faith | A.Faith | W.Faith |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10a-1 | Benefits of remote work? | 0.573 | 0.177 | 0.775 | 🟠 AWS | 0.00 | 0.00 | 1.00 |
| 10a-2 | Equipment handling? | 0.735 | 0.691 | 0.738 | 🟠 AWS | 0.50 | 0.67 | 1.00 |
| 10a-3 | Vacation policy? | 0.200 | 0.178 | 0.544 | 🟠 AWS | 0.00 | 0.00 | 0.50 |
| 10b-1 | "policy" (single word) | 0.396 | 0.868 | 0.874 | 🟠 AWS | 0.00 | 1.00 | 1.00 |
| 10b-2 | What should I do? | 0.643 | 0.461 | 0.564 | 🟢 Local | 0.86 | 0.00 | 0.33 |
| 10b-3 | Remote equipment approval | 0.717 | 0.778 | 0.772 | 🔵 Azure | 0.50 | 0.75 | 1.00 |

**Lab 10:** AWS 4 · Azure 1 · Local 1.

#### Lab 11 — Hybrid Search ("BM25 + vector")

| Exp | Question | Local | Azure | AWS | Winner | L.Faith | A.Faith | W.Faith |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11a-1 | 500 euros equipment | 0.825 | 0.611 | 0.805 | 🟢 Local | 1.00 | 0.33 | 1.00 |
| 11a-2 | 3 days per week remote | 0.300 | 0.684 | 0.786 | 🟠 AWS | 0.00 | 0.50 | 1.00 |
| 11a-3 | Manager approval remote work | 0.525 | 0.608 | 0.704 | 🟠 AWS | 0.00 | 0.50 | 1.00 |
| 11b-1 | Work from home sometimes? | 0.714 | 0.781 | 0.690 | 🔵 Azure | 1.00 | 1.00 | 1.00 |
| 11b-2 | Financial support for home? | 0.265 | 0.535 | 0.593 | 🟠 AWS | 0.50 | 0.50 | 0.50 |
| 11b-3 | Who approves remote work? | 0.585 | 0.682 | 0.657 | 🔵 Azure | 1.00 | 0.50 | 1.00 |
| 11c-1 | Remote policy 3 days approval (hybrid path) | 0.500 | 0.593 | 0.786 | 🟠 AWS | 0.00 | 0.50 | 1.00 |
| 11c-2 | Home office money + approval? | 0.869 | 0.565 | 0.612 | 🟢 Local | 1.00 | 0.67 | 1.00 |

**Lab 11:** AWS 4 · Azure 2 · Local 2.

#### Lab 12 — Bulk Ingestion ("did topic 3 land in the index?")

| Exp | Question | Local | Azure | AWS | Winner | L.Faith | A.Faith | W.Faith |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 12b | What is topic 3 about? | 0.551 | 0.705 | 0.927 | 🟠 AWS | 0.00 | 0.50 | 1.00 |

**Lab 12:** AWS 1.

#### Lab 13 — HNSW Tuning & Sharding

| Exp | Question | Local | Azure | AWS | Winner | L.Faith | A.Faith | W.Faith |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 13a | Remote work policy? (HNSW index) | 0.600 | 0.792 | 0.779 | 🔵 Azure | 0.00 | 0.75 | 1.00 |
| 13b-1 | How many days remotely? | 0.725 | 0.610 | 0.708 | 🟢 Local | 0.50 | 0.50 | 1.00 |
| 13b-2 | Equipment provided? | 0.713 | 0.676 | 0.634 | 🟢 Local | 0.50 | 0.50 | 0.50 |
| 13b-3 | Manager reject remote work? | 0.761 | 0.882 | 0.784 | 🔵 Azure | 0.50 | 1.00 | 1.00 |
| 13c | Summarize remote work policy | 0.651 | 0.666 | 0.666 | 🟡 Tie | 0.50 | 0.75 | 1.00 |
| 13d | List everything from all docs | 0.253 | 0.697 | 0.791 | 🟠 AWS | 0.33 | 1.00 | 1.00 |

**Lab 13:** Azure 2 · Local 2 · AWS 1 · Tie 1.

**Phase 4 totals:** AWS 10 · Azure 5 · Local 5 · Tie 1. Sonnet's faithfulness (≥1.00 on 17 of 21 advanced rows) means it almost never hallucinates. AWS wins even on queries where both Local and Azure fail (10a-3 vacation, 12b topic 3).

---

## Key Insights

### 1. AWS wins on faithfulness — the secret weapon
Sonnet 4.6's average faithfulness (0.82) crushes Local (0.50) and Azure (0.56). On 30 of 40 experiments, AWS achieved faith ≥ 1.00 — meaning it only said what was in the retrieved chunks.

### 2. Retrieval pipeline matters more than the LLM
Before normalization, Sonnet 4.6 scored 22 % (Run 3). After min-max normalization on Titan similarity scores: 43 % (Run 4). Same model, same infra — only the retrieval scores were rescaled. The LLM upgrade Nova → Haiku → Sonnet was only +5 %; the normalization fix was +21 %.

### 3. Local still wins on focused factual queries
When the question clearly matches a specific chunk (e.g., "refund policy", "500 euros equipment"), llama3.2 outperforms both cloud models. ChromaDB + nomic-embed-text gives sharper embeddings for exact matches.

### 4. Azure wins on graceful degradation
GPT-4o handles missing-context scenarios best (faith=0.75 when info is missing). AWS scores higher overall but sometimes hallucinates on hard queries where Azure would politely decline.

### 5. Latency: Azure is fastest, Local is slowest

| Provider | Avg Latency | Notes |
| --- | --- | --- |
| Azure | 2,176 ms | Cloud + fast API |
| AWS | 3,790 ms | Cloud + Bedrock cold starts |
| Local | 21,329 ms | CPU inference (no GPU) |

### 6. Cost comparison

| Provider | Cost per run | Quality (pass rate) | Cost per passed lab |
| --- | --- | --- | --- |
| Local | $0.00 | 31 % (18 / 58) | $0.00 |
| AWS | ~€0.21 | 43 % (25 / 58) | ~€0.008 |
| Azure | ~$0.87 | 28 % (16 / 58) | ~$0.054 |

AWS offers the best quality-to-cost ratio: highest pass rate at ~1/4 the cost of Azure.

### 7. Universal failures — fixing these helps all providers

| Question | Local | Azure | AWS | Root cause |
| --- | --- | --- | --- | --- |
| Remote work policy? (before upload, exp `6a`) | 0.400 | 0.678 | 0.572 | Missing document in vector store |
| Vacation policy? (exp `10a-3`) | 0.200 | 0.178 | 0.544 | No vacation policy document exists |
| Financial support for home? (exp `11b-2`) | 0.265 | 0.535 | 0.593 | Info scattered across chunks |

---

## Recommendations

1. **Add missing documents** (support info, vacation policy) — fixes failures on all providers.
2. **Enable AWS reranker** with the `numberOfResults` bug fix — may push AWS past 50 %.
3. **Try Sonnet 4.6 on Azure** (if available) — the model-quality gap is significant.
4. **Try a larger Ollama model** (e.g. `llama3.1:8b`) — may close the faithfulness gap locally.
5. **Run AWS with Haiku 4.5 + normalization** — untested combo, could be best cost/quality.

---

> **Generated:** 2026-04-22 · 3-way comparison · 58 experiments per provider · errors: Local 0 / Azure 2 / AWS 0 · 40 rows shown above are the comparable subset (Labs 1–13 with per-question scores).
