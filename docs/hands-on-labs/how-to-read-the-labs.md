# How to Read the Hands-On Labs

> **Read this BEFORE opening Phase 1.** It's the missing intro that explains why every lab seems to talk about the same metrics. Without this mental model, the labs feel repetitive and confusing. With it, they click immediately.

---

## Table of Contents

- [The thing nobody told you upfront](#the-thing-nobody-told-you-upfront)
- [The yardstick (3 core metrics + 2 operational)](#the-yardstick-3-core-metrics--2-operational)
- [How to read any lab — the 5-question method](#how-to-read-any-lab--the-5-question-method)
- [Worked example: reading Lab 11 (hybrid search)](#worked-example-reading-lab-11-hybrid-search)
- [Suggested study order (not phase order)](#suggested-study-order-not-phase-order)
- [Which knob does each lab turn?](#which-knob-does-each-lab-turn)
- [What to do if a lab still confuses you](#what-to-do-if-a-lab-still-confuses-you)

---

## The thing nobody told you upfront

The 16 labs are **NOT 16 different metrics**. They are **16 different things you change in the system**, all measured against **the same small set of metrics**.

```
                    ┌─────────────────────────────────────┐
                    │   THE YARDSTICK (3-4 core metrics)  │
                    │   • retrieval                       │
                    │   • faithfulness                    │
                    │   • answer_relevance                │
                    │   • latency / cost                  │
                    └─────────────────────────────────────┘
                                    ▲
                                    │ (every lab measures against this)
                                    │
   ┌────────────┬─────────────┬────┴─────┬─────────────┬────────────┐
   │  Lab 1     │  Lab 2      │ Lab 10   │  Lab 11     │  Lab 13    │
   │  top_k     │ system      │ rerank   │ hybrid      │ HNSW ef    │
   │  knob      │ prompt knob │ on/off   │ search knob │ tuning     │
   └────────────┴─────────────┴──────────┴─────────────┴────────────┘
```

So when you see Lab 11 (hybrid search) reporting `retrieval = 0.825, faithfulness = 1.00`, those numbers exist because that's how we tell whether **turning hybrid search ON** made the system better or worse than the Lab 1 baseline. The metrics are the ruler. The labs are the experiments. **The ruler doesn't change between labs — only the knob you're turning does.**

🚚 **The courier way:** the report card always grades the same 4 subjects. Each lab is a different lesson plan. The report card is how you know if the lesson worked.

---

## The yardstick (3 core metrics + 2 operational)

Every lab in this repo reports against these 5 numbers. Memorise them once and the labs will feel half as long.

| Metric | Score range | Higher / Lower | What it answers | Where it's defined |
| --- | --- | --- | --- | --- |
| **retrieval** | 0.0 – 1.0 | higher = better | Did the vector store grab the right chunks? | `src/evaluation/evaluator.py` → `RetrievalScore` |
| **faithfulness** | 0.0 – 1.0 | higher = better | Did the answer use only the retrieved chunks (no hallucination)? | `src/evaluation/evaluator.py` → `FaithfulnessScore` |
| **answer_relevance** | 0.0 – 1.0 | higher = better | Did the answer actually address the question? | `src/evaluation/evaluator.py` → `AnswerRelevanceScore` |
| **latency** | ms | lower = better | How long did the round-trip take? | logged on every API call |
| **cost** | € or $/1k requests | lower = better | How much did the LLM call cost? | logged from token counts |

There is also a **composite `overall_score`** = `0.4 × retrieval + 0.4 × faithfulness + 0.2 × answer_relevance`. Pass threshold = **0.70**. That's the single number you'll see at the top of every results table.

For the full cross-repo metrics catalogue (including knowledge-engine extras like ContextPrecision, ContextRecall, etc.), see the portfolio cheatsheet (kept locally). For a per-metric description in this repo's own language, see `docs/ai-engineering/evaluation-metrics.md`.

---

## How to read any lab — the 5-question method

For every lab in every phase, ask these 5 questions in order:

1. **What knob are we turning?** — `top_k`, `system_prompt`, reranker on/off, HNSW `ef`, hybrid alpha, guardrail mode, etc. The knob is the whole point of the lab.
2. **What's the hypothesis?** — A one-sentence prediction: "smaller `top_k` should improve precision but hurt recall." If the lab doesn't make this explicit, write it down before reading the result.
3. **What's the baseline?** — Almost always the previous lab's result, OR Lab 1's defaults. The lab is meaningful only as a *delta* against the baseline.
4. **What did the same yardstick measure?** — Check the 5 metrics above. *Same metrics every lab.* If a lab introduces a new metric (e.g., Lab 4 adds `block_rate`), that's a *replacement* knob for guardrails, not a new yardstick.
5. **What's the takeaway?** — When would I turn this knob in production? What would force me to turn it back? This is the answer the lab is really teaching.

If you can answer those 5 in 2 minutes, you understood the lab. If not, re-read steps 1 and 3 — confusion almost always lives there.

---

## Worked example: reading Lab 11 (hybrid search)

Applying the 5-question method to one of the trickier labs:

| # | Question | Answer for Lab 11 |
| --- | --- | --- |
| 1 | What knob? | `HYBRID_SEARCH_ENABLED=true` and `HYBRID_ALPHA=0.5` (50 % vector / 50 % BM25 keyword) |
| 2 | Hypothesis? | "Adding BM25 should help when the question contains exact phrases ('500 euros equipment') that pure vector search misses." |
| 3 | Baseline? | Lab 1 + Lab 10 numbers — vector-only, with reranker on. |
| 4 | Yardstick? | Same 5 metrics. Look for: retrieval up, faithfulness flat, latency slightly up. |
| 5 | Takeaway? | Turn hybrid ON when users frequently search for exact strings (numbers, codes, product names). Leave it OFF for purely conceptual queries — adds latency for no gain. |

Now when you read row `11a-1: 500 euros equipment | retrieval=0.825 | faithfulness=1.00`, those numbers tell you: ✅ hybrid worked exactly where the hypothesis predicted (numeric query). And `11b-1: Work from home sometimes? | retrieval=0.714` shows it adds nothing on a conceptual query — proving the takeaway.

---

## Suggested study order (not phase order)

Phase order (1 → 2 → 3 → 4 → 5) is fine for reference. For *learning*, this order builds intuition fastest:

| Step | Lab | Why this order |
| --- | --- | --- |
| 1 | **Lab 1** Retrieval Quality | Learn the first ruler |
| 2 | **Lab 2** Faithfulness | Learn the second ruler |
| 3 | **Lab 1b** top_k sweep | First real experiment using the rulers |
| 4 | **Lab 10** Re-ranking | Big retrieval improvement → see the ruler move dramatically |
| 5 | **Lab 11** Hybrid search | Another retrieval lever → compare delta vs Lab 10 |
| 6 | **Lab 13** HNSW tuning | Latency vs recall trade-off → adds 2 more dimensions |
| 7 | **Lab 4 + Lab 9** Guardrails | New knob (`block_rate`) but the original yardstick still applies |
| 8 | **Lab 3** Business metrics | Translate the yardstick into exec language |
| 9 | **Lab 5 + Lab 14 + Lab 15** Observability | How the yardstick gets visualized in production |
| 10 | **Lab 6 + Lab 16** Data flywheel & regression | How the yardstick *prevents* regressions |
| 11 | **Lab 8 + Lab 12** Scaling & bulk ingestion | Operational labs — yardstick shifts to latency / cost / throughput |
| 12 | **Lab 7** RLHF | Conceptual only — read last |

After Lab 1 + Lab 2, **every other lab is "what happens to those numbers when I change X?"** That's the whole game.

---

## Which knob does each lab turn?

The single sentence summary of every lab. Bookmark this table.

| Lab | Knob | Yardstick metrics primarily affected |
| --- | --- | --- |
| 1 | `top_k` (1, 5, 10) | retrieval, latency |
| 2 | system prompt strictness | faithfulness, hallucination_rate |
| 3 | business KPIs (follow-up rate, resolution rate) | translates 1+2 into exec view |
| 4 | input guardrail patterns | adds `block_rate`, `false_positive_rate` |
| 5 | OpenTelemetry tracing on/off | observability of the same yardstick |
| 6 | document upload (data flywheel) | retrieval (post-upload should jump) |
| 7 | (conceptual) RLHF feedback loops | future faithfulness improvement |
| 8 | infra autoscaling knobs | latency under load, cost per 1k requests |
| 9 | output guardrails (PII, profanity, topic) | adds `output_block_rate` |
| 10 | reranker on/off (CrossEncoder) | retrieval (precision↑), latency (slight↑) |
| 11 | hybrid search alpha (vector ↔ BM25) | retrieval on exact-string queries |
| 12 | bulk-ingest batch size | throughput (docs/min), failure rate |
| 13 | HNSW `ef`, `M`, shard count | retrieval, latency trade-off |
| 14 | query log triage filters | finds bad queries the yardstick already flagged |
| 15 | Prometheus / OpenTelemetry exports | makes the yardstick visible in Grafana |
| 16 | golden-dataset regression run | runs the *whole* yardstick on the 25 golden questions |

---

## What to do if a lab still confuses you

1. **Re-read the lab's "What it controls" cell.** If that cell is unclear, the rest of the lab can't make sense.
2. **Find the baseline value.** If the lab claims "retrieval improved from 0.62 → 0.78", but you can't find where 0.62 came from, the lab is missing context — open the previous lab's results.
3. **Run the lab yourself.** Every lab is a `.env` change + `pytest scripts/run_all_labs.py` away. Numbers from your own machine settle confusion faster than any doc.
4. **Compare against Local vs Azure vs AWS** in `scripts/lab_results/local-vs-azure-comparison.md`. Seeing the same lab across 3 providers makes the *what changed?* question concrete.
5. **Ask:** "is this lab telling me a *number*, or a *trade-off*?" Most labs are trade-offs. The number is just one half of the story.

🚚 **Final courier wisdom:** every lab is one of these two questions, dressed differently:
- "I changed knob X. Is the report card better or worse?" (Labs 1, 2, 6, 10, 11, 13)
- "I changed knob X. Did the courier now refuse / crash / answer slower?" (Labs 4, 8, 9, 12, 14, 15)

Once you see this, the labs stop feeling repetitive. They become a series of small, controlled experiments — exactly what production AI engineering actually is.
