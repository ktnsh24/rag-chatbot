# Module 4: Tuning and Trade-offs

**Question this module answers:** "How do I improve quality and speed by changing config?"

**Labs in this module:** 5 hands-on experiments
- Lab 9: Chunk Size Tuning
- Lab 10: Top-K Tuning
- Lab 11: Re-Ranking
- Lab 12: Hybrid Search
- Lab 13: HNSW Tuning

**Time:** 150 minutes total

**Prerequisite:** Module 1-3 (understand what each metric means).

---

## Lab 9: Chunk Size Tuning

### Goal

Test how chunk size affects retrieval quality and latency.

### Current setting

In `.env`:

```bash
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=50
```

### Run in Swagger UI

Ask the same question 3 times, comparing chunk sizes in backend logs.

`POST /api/chat`:

```json
{
  "question": "What is the refund policy for digital products?"
}
```

Change `RAG_CHUNK_SIZE` in `.env` to 300, restart, run same question. Then try 1000.

### Sample results table

| Chunk Size | Latency (ms) | Retrieval Score | Faithfulness | Overall | Observation |
| --- | --- | --- | --- | --- | --- |
| 300 (small) | 1200 | 0.65 | 0.72 | 0.71 | Fast but fragmented; may miss context. |
| 500 (default) | 1800 | 0.74 | 0.82 | 0.80 | Balanced. |
| 1000 (large) | 2200 | 0.79 | 0.88 | 0.85 | Better context but slower. |

### Action table

| If you see this | Change to | Why |
| --- | --- | --- |
| Low retrieval + normal faithfulness | Increase chunk_size to 750 | Chunks are too fragmented; losing context. |
| High latency but good quality | Decrease chunk_size to 300 | Chunks too large; trade quality for speed. |
| Normal retrieval + low faithfulness | Keep chunk_size, fix prompt | Problem is answer generation, not chunks. |

---

## Lab 10: Top-K Tuning

### Goal

Test how many chunks to send to the LLM (trade precision vs safety).

### Current setting

In `.env`:

```bash
RAG_TOP_K=5
```

### Run in Swagger UI

`POST /api/evaluate`:

```json
{
  "question": "What is the refund policy?",
  "top_k": 1
}
```

Then repeat with `top_k: 3, 5, 10`.

### Sample results table

| top_k | Retrieval Score | Faithfulness | Answer Quality | Latency | Observation |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.92 | 0.70 | Good | 1200ms | Precise but risky if answer spans contexts. |
| 5 | 0.74 | 0.82 | Best | 1800ms | Balanced default. |
| 10 | 0.68 | 0.88 | Safe | 2500ms | More context but noisier; slower. |

### Action table

| If retrieval is low | Try | Why |
| --- | --- | --- |
| < 0.60 | Increase top_k to 10 | Grab more chunks; one might be irrelevant. |
| 0.70–0.80 (okay) | Keep at 5 | Default is fine; don't over-tune. |

---

## Lab 11: Re-Ranking

### Goal

Test re-ranking: a second pass that sorts retrieved chunks by relevance before sending to LLM.

### Current setting

In `.env`:

```bash
RERANKER_ENABLED=false
```

### Run in Swagger UI

With RERANKER_ENABLED=false:

`POST /api/evaluate`:

```json
{
  "question": "What is the refund policy for digital products?"
}
```

Note retrieval and faithfulness scores. Then set `RERANKER_ENABLED=true`, restart, run again.

### Sample results table

| Re-ranking | Top chunk quality | Time added | Retrieval | Faithfulness | Overall |
| --- | --- | --- | --- | --- | --- |
| Off (default) | Good | 0ms | 0.74 | 0.82 | 0.80 |
| On | Better | +300ms | 0.81 | 0.85 | 0.84 |

### Action table

| If you have this | Enable re-ranking? | Why |
| --- | --- | --- |
| Good retrieval (> 0.75) and fast p95 (< 5s) | No | Already working; cost/benefit not worth it. |
| Weak retrieval (< 0.65) | Yes | Re-ranker might salvage near-misses. |
| Hallucination spiking | No | Re-ranking won't help; fix prompt instead. |

---

## Lab 12: Hybrid Search (Semantic + Keyword)

### Goal

Combine vector search (meaning-based) with keyword search (exact terms) for better recall.

### Current setting

In `.env`:

```bash
HYBRID_SEARCH_ENABLED=false
HYBRID_ALPHA=0.7
```

### Run in Swagger UI

With HYBRID_SEARCH_ENABLED=false, test a question with exact terms:

`POST /api/evaluate`:

```json
{
  "question": "What email should I use to request a refund?"
}
```

Then enable `HYBRID_SEARCH_ENABLED=true`, restart, run again.

### Sample results table

| Search mode | Latency | Retrieval | Finds exact terms? | Observation |
| --- | --- | --- | --- | --- |
| Semantic only | 1800ms | 0.72 | Maybe | Good for meaning but may miss exact matches. |
| Semantic + keyword | 2200ms | 0.84 | Yes | Better if queries mention specific words/IDs. |

### Action table

| If your queries mention | Enable hybrid? | Why |
| --- | --- | --- |
| Email addresses, IDs, dates | Yes | Keywords matter; semantic search alone will miss them. |
| Descriptions, paraphrases | No | Semantic search is enough; hybrid adds latency. |

---

## Lab 13: HNSW Tuning (Vector Index)

### Goal

Tune the vector index speed-vs-recall trade-off.

### Current setting

In `.env`:

```bash
HNSW_M=16
HNSW_EF_SEARCH=40
```

(These are ChromaDB/Chroma defaults. Different providers have different knobs.)

### Run in Swagger UI

Test with default settings first:

`POST /api/evaluate`:

```json
{
  "question": "What is the refund policy?"
}
```

Note latency and retrieval. Change `HNSW_EF_SEARCH` to 100 (deeper search), restart, run again.

### Sample results table

| EF_SEARCH | Search Depth | Latency | Retrieval | Recall |
| --- | --- | --- | --- | --- |
| 40 (default) | Shallow | 1200ms | 0.74 | ~85% |
| 100 (deep) | Deep | 1600ms | 0.78 | ~95% |

### Action table

| If you have this | Tune | Why |
| --- | --- | --- |
| Fast queries but low retrieval | Increase `EF_SEARCH` to 80 | Deepen search; find better matches. |
| Slow queries but high retrieval | Decrease `EF_SEARCH` to 20 | Speed up; acceptable retrieval at lower cost. |
| Default is fine | Don't tune | HNSW is last resort; tune cheaper knobs first. |

---

## Tuning Order (Fastest to Most Expensive)

1. **top_k** (free, instant impact)
2. **chunk_size** (free, requires re-ingest)
3. **hybrid_search** (adds ~300ms)
4. **reranker** (adds ~300ms)
5. **HNSW settings** (most expensive, last resort)

---

## What You've Learned

- **chunk_size:** 300–1000 (smaller = fast but fragmented, larger = slow but complete)
- **top_k:** 1–10 (1 = precise but risky, 5 = balanced, 10 = safe but noisy)
- **reranker:** add only if retrieval is weak (0.6–0.7)
- **hybrid_search:** enable if queries use exact terms (emails, IDs)
- **HNSW:** tune last; usually default is fine

---

## Next Steps

- Move to [Module 5: Regression Testing](module-5-regression.md) to lock in improvements
- Or revisit [Module 2](module-2-observability.md) to set monitoring thresholds
