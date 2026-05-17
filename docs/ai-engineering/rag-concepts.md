# RAG Concepts — What is RAG, Explained Simply

## Table of Contents

- [What is RAG?](#what-is-rag)
- [The problem RAG solves](#the-problem-rag-solves)
- [How RAG works step by step](#how-rag-works-step-by-step)
- [The three components you must understand](#the-three-components-you-must-understand)
- [What are embeddings?](#what-are-embeddings)
- [What is a vector store?](#what-is-a-vector-store)
- [How vector search actually works](#how-vector-search-actually-works)
- [Two-stage retrieval: vector search + reranking](#two-stage-retrieval-vector-search--reranking)
- [Hybrid search: semantic + keyword](#hybrid-search-semantic--keyword)
- [What is semantic search?](#what-is-semantic-search)
- [What is chunking?](#what-is-chunking)
- [Chunks vs vectors — the key distinction](#chunks-vs-vectors--the-key-distinction)
- [What is cosine similarity?](#what-is-cosine-similarity)
- [What is a prompt?](#what-is-a-prompt)
- [What is a token?](#what-is-a-token)
- [RAG vs Fine-tuning](#rag-vs-fine-tuning)
- [Common RAG problems and solutions](#common-rag-problems-and-solutions)

---

## What is RAG?

**RAG** stands for **Retrieval-Augmented Generation**.

It's a technique where an LLM generates answers using **your own documents** as context, instead of relying only on its training data.

Simple analogy:

- **Without RAG**: You ask someone a question and they answer from memory (might be wrong or outdated)
- **With RAG**: You ask someone a question, they first look up relevant pages in a book, then answer based on what they found (grounded in facts)

> 🚚 **Courier analogy:** The LLM is the courier — it carries your question to an answer. Without RAG, the courier answers from memory — sometimes confidently wrong. With RAG, the courier checks the parcel full of your documents before speaking. The parcel is the retrieval system. No parcel = guessing. Full parcel = grounded answers.

---

## The problem RAG solves

LLMs like GPT-4o and Claude are trained on public internet data up to a cutoff date. They:

- Don't know your company's internal documents
- Don't know data created after their training date
- Can "hallucinate" — confidently make up facts
- Can't cite sources

RAG fixes all of these by:

1. Storing your documents in a searchable database
2. Finding relevant documents for each question
3. Giving those documents to the LLM as context
4. The LLM answers based on your actual data

> 🚚 **Courier analogy:** Imagine a courier that grew up reading only public newspapers (training data). Ask it about your company's internal refund policy — it will confidently make something up, because newspapers never covered that. RAG gives the courier a private courier bag of YOUR documents before every delivery. Now it reads from the bag first. Hallucination fixed.

---

## How RAG works step by step

### Phase 1: Ingestion (one-time per document)

```
Document → Read → Chunk → Embed → Store in Vector DB

"refund-policy.pdf"
    │
    ▼
Read: "Our refund policy allows returns within 14 days..."
    │
    ▼
Chunk: ["Our refund policy allows...", "To request a refund...", ...]
    │
    ▼
Embed: [[0.12, -0.45, 0.78, ...], [0.33, 0.67, -0.12, ...], ...]
    │
    ▼
Store: Each chunk + its vector saved in the vector database
```

### Phase 2: Query (every time a user asks)

```
Question → Embed → Search → Retrieve → Generate → Answer

"What is the refund policy?"
    │
    ▼
Embed: [0.11, -0.44, 0.79, ...]  (similar to refund-related chunks)
    │
    ▼
Search: Find top 5 most similar vectors in the database
    │
    ▼
Retrieve: Get the actual text of those 5 chunks
    │
    ▼
Generate: Send to LLM:
    "Context: [chunk 1] [chunk 2] [chunk 3] ...
     Question: What is the refund policy?"
    │
    ▼
Answer: "Based on the documents, refunds are processed within 14 days..."
```

> 🚚 **Courier analogy:** Phase 1 (ingestion) is like the post office sorting all your letters into labelled boxes before the courier arrives. Phase 2 (query) is the courier's actual delivery run — it reads the address (your question), checks the right box (vector search), picks up the most relevant letters (top-k chunks), and delivers them to the LLM to write the final reply. No pre-sorting = the courier has to read every letter on every delivery. Pre-sorted = instant pickup.

---

## The three components you must understand

RAG has three completely different components. Confusing them is the #1 beginner mistake:

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Embedding Model │ ──▶ │  Vector Store    │ ──▶ │  LLM             │
│  (the converter) │     │  (the database)  │     │  (the writer)    │
└──────────────────┘     └──────────────────┘     └──────────────────┘
  Titan / text-emb-3     OpenSearch / AI Search   Claude / GPT-4o
  / nomic-embed-text     / ChromaDB                / llama3.2
  Turns text → numbers     Stores & searches         Reads context,
  Nothing else             vectors. Not a model.     writes answers.
```

| | Embedding Model | Vector Store | LLM |
|---|---|---|---|
| **What it is** | A neural network | A database | A neural network |
| **Input** | Text (chunk or question) | A vector (to search) | Text (prompt + context) |
| **Output** | A vector (list of numbers) | Ranked results | Generated text |
| **Analogy** | Translator (English → coordinates) | Library catalogue | Author who writes answers |
| **Example** | Titan Embeddings v2, text-embedding-3-small, nomic-embed-text | OpenSearch, Azure AI Search, ChromaDB | Claude 3.5 Sonnet, GPT-4o, llama3.2 |
| **Runs when** | Ingestion + every query | Every query (search) | Every query (generation) |
| **🚚 Courier** | The translator who converts your text into GPS coordinates the warehouse understands | The GPS-indexed warehouse — finds the nearest shelf in milliseconds using stadium signs | The courier — picks up the retrieved packages, reads them, and writes the final answer |

**Key insight:** OpenSearch / Azure AI Search / ChromaDB is a **database**, not a model.
It doesn't understand text — it stores vectors and finds similar ones. The embedding
model is what converts text into vectors that the store can work with.

> 🚚 **Courier analogy:** Three workers, one delivery:
> - The **embedding model** is the translator — it converts your question from English into coordinates on a map.
> - The **vector store** is the warehouse with a GPS index — it finds the nearest box by coordinates instantly, without reading every label.
> - The **LLM** is the courier — it picks up those boxes, reads the contents, and writes the final answer.
> Mix them up and the whole system breaks. You wouldn't ask the warehouse to write the answer, or the courier to do the indexing.

---

## What are embeddings?

An **embedding** is a list of numbers (a vector) that represents the "meaning" of a text.

```
"What is the refund policy?"  →  [0.12, -0.45, 0.78, 0.33, -0.91, ...]
"How do I get my money back?" →  [0.11, -0.44, 0.79, 0.34, -0.90, ...]
"What's the weather today?"   →  [0.88, 0.23, -0.56, 0.12, 0.45, ...]
```

Notice:
- The first two sentences are about the same topic → their vectors are very similar
- The third sentence is about a different topic → its vector is very different

This is how the system knows which document chunks are relevant to your question.

**Technical details:**
- Amazon Titan Embeddings v2: produces 1024-dimensional vectors
- Azure text-embedding-3-small: produces 1536-dimensional vectors
- Local Ollama nomic-embed-text: produces 768-dimensional vectors
- Each number in the vector captures a different aspect of meaning

### Concrete example: 42 chunks → 42 vectors

Say a document gets split into 42 chunks. Here's exactly what happens:

```
Chunk 1:  "Our refund policy allows returns within 14 days..."  (200 chars)
    → Embedding model → [0.123, -0.456, 0.789, ..., 0.234]  (1024 numbers)

Chunk 2:  "To request a refund, visit the customer portal..."   (200 chars)
    → Embedding model → [0.345, -0.567, 0.891, ..., 0.456]  (1024 numbers)

Chunk 3:  "Digital product refunds take 5 business days..."      (200 chars)
    → Embedding model → [0.234, -0.478, 0.812, ..., 0.345]  (1024 numbers)

...

Chunk 42: "For international orders, refund processing..."       (200 chars)
    → Embedding model → [0.567, -0.123, 0.456, ..., 0.789]  (1024 numbers)
```

Result: 42 chunks → 42 vectors → 42 rows stored in the vector database.

### The output size is ALWAYS the same

This is a critical insight — the embedding model **always** produces the same number
of dimensions, regardless of input length:

```
"Hi"                          (2 chars)    → [0.12, -0.45, ..., 0.78]  = 1024 numbers
"What is the refund policy?"  (28 chars)   → [0.34, -0.67, ..., 0.91]  = 1024 numbers
"Our refund policy allows..." (200 chars)  → [0.56, -0.23, ..., 0.44]  = 1024 numbers
An entire paragraph           (2000 chars) → [0.78, -0.12, ..., 0.33]  = 1024 numbers
```

Short text or long text — always the same number of floats out: 1024 (Titan), 1536 (Azure), or 768 (Ollama).
The model compresses the **meaning** into a fixed-size representation.

### Dimensions must match between model and store

The vector store must be configured to accept vectors of the **same size** the
embedding model produces. This is a hard requirement:

| Embedding Model | Output Dimensions | Vector Store Config |
|---|---|---|
| Amazon Titan Embeddings v2 | 1024 | OpenSearch index: `"dimension": 1024` |
| Azure text-embedding-3-small | 1536 | AI Search index: `"dimensions": 1536` |
| Local nomic-embed-text (Ollama) | 768 | ChromaDB: auto-detects from first insert |

If these don't match, you get an error — like trying to put a square peg in a round hole.

> 🚚 **Courier analogy:** An embedding is the courier's internal address book — it converts the meaning of any text into a precise GPS coordinate in a 1024-dimensional city. "Refund policy" and "money back guarantee" end up on the same street corner (similar coordinates). "Pizza recipe" ends up in a completely different neighbourhood. The courier doesn't read words — it navigates by coordinates. That's why it finds related content even when you use different words.

---

## What is a vector store?

A **vector store** is a database optimized for storing and searching vectors.

Regular databases search by exact match:
```sql
SELECT * FROM documents WHERE topic = 'refund'
```

Vector databases search by **similarity**:
```
"Find the 5 vectors most similar to [0.12, -0.45, 0.78, ...]"
```

This is called **approximate nearest neighbor (ANN)** search.

### How it works internally

Most vector stores use **HNSW** (Hierarchical Navigable Small World) — a graph-based algorithm:

1. Vectors are organized in layers (like a highway system)
2. Top layer: few nodes, big jumps (highways)
3. Bottom layer: many nodes, small jumps (local roads)
4. To find nearest neighbors: start at top, narrow down layer by layer
5. Result: O(log N) search time instead of O(N) brute force

> 🚚 **Courier analogy:** A regular database is a courier that checks every house on every street to find your package — fine for 10 houses, impossibly slow for 1 million. A vector store with HNSW is a courier with a highway system: it jumps onto the motorway first (top layer, few exits), takes the right exit to a main road (middle layer), then navigates to the exact street (bottom layer). Instead of visiting 1,000,000 houses, it visits ~20 waypoints. That's why it answers in milliseconds.

---

## How vector search actually works

This section explains vector search at three depth levels — from interview-ready
to deep understanding.

### Level 1: What you must know (interview answer)

When a user asks a question:

1. The question gets converted to a vector (same embedding model used during ingestion)
2. That vector is sent to the vector database
3. The database finds the stored vectors most similar to the question vector
4. Returns the top-k chunks, ranked by similarity score

```
Question: "How do refunds work?"
    │
    ▼ (embedding model)
Question vector: [0.11, -0.44, 0.79, ...] (1024 numbers)
    │
    ▼ (send to vector store)
Vector store compares against all 42 stored vectors
    │
    ▼ (ranked results)
Chunk 1: score 0.92 — "Our refund policy allows returns within 14 days..."
Chunk 2: score 0.87 — "To request a refund, visit the customer portal..."
Chunk 3: score 0.81 — "Digital product refunds take 5 business days..."
```

The reason this works: the question "How do refunds work?" produces a vector
that's **close** to vectors of chunks that talk about refunds.

### Level 2: How similarity is calculated (should know)

The "score" is **cosine similarity** — a math formula that measures the angle
between two vectors:

```
score = cos(θ) = (A · B) / (|A| × |B|)
```

In plain English: if two vectors point in the same direction, they're similar.

```
Question vector:    [0.11, -0.44, 0.79, ...]     ─→  ↗  (pointing northeast)
Chunk 1 vector:     [0.12, -0.45, 0.78, ...]     ─→  ↗  (pointing nearly same way)
Chunk 42 vector:    [-0.88, 0.23, -0.56, ...]     ─→  ↙  (pointing opposite)

cos(question, chunk_1)  = 0.92  (nearly same direction = highly relevant)
cos(question, chunk_42) = 0.15  (very different direction = irrelevant)
```

The vector store calculates this for every stored vector, sorts by score,
and returns the top-k.

### Level 3: HNSW — how it searches fast (optional, deep knowledge)

With 42 vectors, brute-force comparison is fine. But with **millions** of vectors,
checking every one is too slow. Vector stores use **HNSW** (Hierarchical Navigable
Small World) — a graph-based index:

```
Layer 3 (top):     A ──────────── B              Few nodes, big jumps
                   │              │              (highway)
                   │              │
Layer 2:       A ──── C ──── B ──── D            More nodes, medium jumps
               │     │      │     │              (main roads)
               │     │      │     │
Layer 1:     A─E─C─F─G─B─H─I─D─J─K             Many nodes, small jumps
               │     │      │     │              (local streets)
               │     │      │     │
Layer 0:   A E C F G B H I D J K L M N O P Q    All nodes
                                                  (every house)
```

Search process:
1. Start at Layer 3 (highway) — jump to nearest node
2. Drop to Layer 2 — refine with more options
3. Drop to Layer 1 — get closer
4. Layer 0 — find exact nearest neighbors

Result: O(log N) comparisons instead of O(N). For 1 million vectors, that's ~20
comparisons instead of 1,000,000.

> 🚚 **Courier analogy — how does the vector database find results so fast?**
>
> The courier needs to find the closest matching document chunk — and there are **50,000 chunks** in the vector store (like 50,000 seats in a football stadium).
>
> ---
>
> **❌ Without HNSW (brute force):**
> The courier sniffs chunk #1... not a match. Chunk #2... not a match. Chunk #3...
> → 50,000 sniffs. The courier collapses before the answer is found.
>
> ---
>
> **✅ With HNSW — the courier follows the stadium signs:**
>
> The stadium has signs at every level. At each sign, the courier asks one question:
> *"Am I getting warmer or colder?"* — and moves only toward warmer.
>
> **Sign 1 — Stadium entrance: Sections A–Z**
> The courier checks 3 section signs:
> - Section A → too far from the target meaning
> - Section G → closer ✓ move here
> - Section M → exact section ✓ stop
> → **3 checks**
>
> **Sign 2 — Inside Section M: Rows 1–50**
> The courier checks 3 row markers:
> - Row 10 → getting warmer
> - Row 20 → warmer still
> - Row 23 → warmest ✓ stop
> → **3 checks**
>
> **Sign 3 — Row 23: Seats 1–30**
> The courier checks 3 seats:
> - Seat 5 → cold
> - Seat 10 → warmer
> - Seat 14 → hottest ✓ found it
> → **3 checks**
>
> **Total: 9 checks. Not 50,000.**
>
> ---
>
> Each "check" in real HNSW is: *measure cosine similarity between the query vector and this candidate vector — is it higher than the best so far?* If yes → move there and check its neighbours. If no → stop.
>
> The signs were built **at ingestion time** when you uploaded your documents. That's why uploading is slightly slower — the courier is mapping the stadium once. Every search after that is instant, because the signs are already there.
>
> Add 10× more chunks? The courier just reads one more sign per level. That's O(log N) — the work barely grows as the data grows.

> **For interviews:** Level 1 + Level 2 is sufficient. Level 3 is for senior
> roles or if the interviewer asks "how does the vector database find results so fast?"

---

## Two-stage retrieval: vector search + reranking

Vector search alone has a blind spot: the embedding model encodes the **query** and
the **chunk** separately, then compares the resulting vectors. It never sees them
together. Two chunks can point in roughly the same direction in vector space but
still differ a lot in how directly they answer the specific question.

Reranking fixes this by adding a second, slower, more accurate pass.

### Stage 1 — Vector search (bi-encoder, fast)

The embedding model is a **bi-encoder**: it encodes each text independently into
a fixed-size vector. At query time, it encodes the question the same way, then
compares vectors with cosine similarity.

- Fast: query and chunks are compared as pre-computed numbers
- Runs on DynamoDB (brute-force) or OpenSearch/Azure AI Search (HNSW)
- Returns **top 20 candidates** — broad net, some noise allowed

### Stage 2 — Reranker (cross-encoder, slow but accurate)

A **cross-encoder** takes the query and a chunk **together** as one input and
outputs a single relevance score. Because it sees both at once, it can model
subtle relationships the bi-encoder missed.

```
Bi-encoder:                    Cross-encoder:

Query → [embed] → vector Q     Query + Chunk → [model] → score 0.94
Chunk → [embed] → vector C                                score 0.41
                                                          score 0.87
cosine(Q, C) = 0.82            Re-ordered: 0.94, 0.87, 0.41
```

The reranker scores all 20 candidates, sorts by the new score, and keeps **top 5**.

### Why not use the cross-encoder for everything?

Because it's slow. A cross-encoder must run a full model pass for every
query-chunk pair. With 10,000 chunks, that's 10,000 forward passes — unusable
in real time. The bi-encoder narrows the field to 20 first, then the
cross-encoder polishes those 20.

```
Query
  → embed (bi-encoder)
  → vector store search → top 20 candidates    ← fast, broad
  → reranker cross-encoder → top 5             ← slow, precise
  → LLM prompt
  → Answer
```

### What rag-chatbot uses (from the code)

Three implementations, switched by `CLOUD_PROVIDER` env var:

| Provider | Model | Latency |
| --- | --- | --- |
| `local` | `cross-encoder/ms-marco-MiniLM-L-6-v2` (22M params) | ~50ms for 20 candidates on CPU |
| `aws` | `amazon.rerank-v1:0` via Bedrock | ~100–200ms (API call) |
| `azure` | Azure AI Search Semantic Ranker | ~100–200ms (API call) |

Disabled by default — enable with `RERANKER_ENABLED=true`.

The local reranker also applies a **sigmoid function** to normalize raw cross-encoder
logit scores (which can be any number) into a 0.0–1.0 range:

```
raw score from model: 3.7  (logit, unbounded)
sigmoid(3.7) = 1 / (1 + e^-3.7) = 0.976  (normalized probability)
```

The final `score` stored on each `VectorSearchResult` is this normalized value,
and the original bi-encoder score is kept in `metadata["original_score"]` for
comparison.

### When does reranking help most?

- Queries where **phrasing differs** from the document wording (bi-encoder struggles, cross-encoder doesn't)
- Large corpora (> 5,000 chunks) where the top-20 from HNSW may include noise
- Questions requiring **multi-sentence reasoning** across a chunk

### When to skip reranking

- Small corpora (< 1,000 chunks) — brute-force cosine already returns high-quality top-5
- Latency-sensitive paths where +100ms is unacceptable
- Costs — each AWS/Azure rerank call adds API cost

> 🚚 **Courier analogy:** The bi-encoder is the sorting depot computer — it groups
> parcels by rough destination (postcode) and picks the 20 closest to your address.
> Fast, but it picks by postcode alone and a few wrong parcels slip through.
> The reranker is the senior sorter who reads the actual label on each of those
> 20 parcels — full address, recipient name, special instructions — and keeps
> only the 5 that are truly correct. Slower per parcel, but far fewer misdeliveries.

---

## Hybrid search: semantic + keyword

Vector search is great at meaning — but it can miss **exact words**.

Example: query `"error code 5412"`
- Vector search finds chunks about "error handling", "troubleshooting" — semantically close
- But the chunk that literally contains `"5412"` in a table may rank low because its overall meaning vector is not that close to the query vector
- A keyword search finds `"5412"` instantly — exact token match

Hybrid search runs **both** and merges the results.

### What is BM25 (keyword search)?

BM25 is the algorithm behind Elasticsearch and classic search engines. It scores chunks by:
- How often the query words appear in the chunk
- How rare those words are across all chunks (rare words are more informative)
- Adjusted for chunk length (long chunks are not unfairly rewarded)

No embeddings, no vectors — pure word frequency math.

```
Query: "error code 5412"

BM25 score for chunk "Error code 5412 means disk full":  high  ← exact match
BM25 score for chunk "General error handling patterns":   low   ← no exact match
BM25 score for chunk "See section 5412 in the manual":    medium ← partial match
```

### How RRF merges the two ranked lists

After vector search and BM25 each return their top 20, the code merges them with
**Reciprocal Rank Fusion (RRF)**:

```
RRF score = alpha * 1/(60 + vector_rank) + (1-alpha) * 1/(60 + bm25_rank)
```

`alpha=0.7` means 70% weight to vector search, 30% to BM25. Default in rag-chatbot.

Concrete example:

```
Chunk                               vector_rank  bm25_rank  RRF score
"Error code 5412 means disk full"       8            1        0.0153  ← BM25 boost
"General error handling..."             1           15        0.0155  ← vector boost
"5412 triggers a rollback..."           3            2        0.0161  ← high in both → WINS
```

A chunk that ranks high in **both** systems wins. A chunk only found by one system
still gets credit — it's not discarded.

### What rag-chatbot uses (from the code)

| Provider | Vector search | Keyword search |
| --- | --- | --- |
| `local` | ChromaDB or DynamoDB | `rank-bm25` library (in-memory) |
| `aws` | OpenSearch k-NN | OpenSearch BM25 (native) |
| `azure` | Azure AI Search HNSW | Azure AI Search BM25 (native) |

Disabled by default — enable with `HYBRID_SEARCH_ENABLED=true`.

### The complete retrieval stack (all three layers)

```
Vector search (bi-encoder)   — ALWAYS on
Hybrid search (BM25 + RRF)   — optional: HYBRID_SEARCH_ENABLED=true
Reranker (cross-encoder)     — optional: RERANKER_ENABLED=true
```

You can mix and match — but the most common production setup is:
- Small corpus: vector search only
- Mixed queries (semantic + keyword): hybrid
- High accuracy needed: hybrid + reranker

> 🚚 **Courier analogy:** Vector search is the depot's GPS routing system — finds
> parcels in the same neighbourhood as your address. BM25 is the handwritten
> label scanner — finds parcels with your exact house number on the label.
> RRF is the supervisor who looks at both lists and promotes any parcel that
> appears on both. If only GPS found it → maybe. If only label scanner found it → maybe.
> If both found it → that parcel definitely goes first.

---

## What is semantic search?

"Semantic search" is the broad term for **searching by meaning** rather than by
exact keywords. Vector search is one implementation of semantic search.

### Keyword search vs semantic search

```
Query: "how do I get my money back?"

Keyword search (BM25):
  Looks for chunks containing: "money", "back"
  Misses: "refund policy", "return procedure", "reimbursement"
  Finds:  "the money flows back to the account" ← wrong context but keyword match

Semantic search (vector):
  Looks for chunks whose MEANING is close to "get money back"
  Finds:  "refund policy allows returns within 30 days" ← no shared words, but same meaning
  Finds:  "to request a reimbursement, visit the portal" ← same meaning, different words
  Misses: "error code 5412" ← no semantic overlap
```

Semantic search works because the embedding model was trained on billions of
sentences — it learned that "get money back", "refund", and "reimbursement"
all point in the same direction in vector space.

### Why RAG uses semantic search

Users ask questions in their own words. Documents are written by product teams
in different words. Keyword search fails this mismatch. Semantic search bridges it.

### Semantic search in rag-chatbot

Every query goes through `embed_text()` before hitting the vector store. The
embedding model (`amazon.titan-embed-text-v2:0` on AWS, `text-embedding-3-small`
on Azure) converts the question into a 1024-dimensional vector. The vector store
then finds the stored chunk vectors closest to it — that is semantic search.

> 🚚 **Courier analogy:** Keyword search is a courier who only delivers to
> addresses spelled exactly as written. "Jane Smith" and "J. Smith" are different
> addresses — no match. Semantic search is a courier who understands that both
> mean the same person and delivers to both. The embedding model is the courier's
> common sense — trained on so many addresses it knows the equivalences.

---

## What is chunking?

**Chunking** is splitting a large document into smaller pieces.

Why?
- LLMs have a maximum context size (200K tokens for Claude)
- But sending the entire document wastes tokens (and money)
- Smaller chunks are more precise — the LLM gets exactly the relevant part
- Embedding models work best on paragraph-sized text

### Chunking strategies

**Recursive paragraph → sentence → word (what we use):**
- Uses `RecursiveCharacterTextSplitter` — tries separators in order: paragraph (`\n\n`), line (`\n`), sentence (period+space), word (space), character
- Only falls to the next separator if a chunk is still too big after splitting on the current one
- Max chunk size = 1000 characters, overlap = 200 characters between consecutive chunks

```
Document: "AAAA BBBB CCCC DDDD EEEE FFFF GGGG HHHH"

Chunk 1: "AAAA BBBB CCCC DDDD"
Chunk 2: "CCCC DDDD EEEE FFFF"  ← overlap with chunk 1
Chunk 3: "EEEE FFFF GGGG HHHH"  ← overlap with chunk 2
```

### How many chunks? The math

The number of chunks is determined by a simple formula:

```
                    document_length - chunk_overlap
number_of_chunks ≈  ─────────────────────────────────
                      chunk_size - chunk_overlap
```

The key insight is **step size** — how far forward we move for each new chunk:

```
step = chunk_size - chunk_overlap
step = 1000 - 200 = 800 characters
```

So each chunk covers 1000 characters, but we only move forward 800 characters
before starting the next one (because 200 characters overlap with the previous chunk).

**Concrete example** — a 15-page PDF (~36,000 characters):

```
chunk_size    = 1000 characters
chunk_overlap =  200 characters
document      = 36,000 characters

step = 1000 - 200 = 800
chunks = 36,000 / 800 = 45 chunks
```

Visually, here's what happens across the document:

```
Document: |========================= 36,000 chars =========================|

Chunk  1: [---- 1000 ----]
Chunk  2:      [---- 1000 ----]           ← starts 800 chars later
Chunk  3:           [---- 1000 ----]      ← starts 800 chars later
...
Chunk 45:                                                  [---- 1000 ---]

          |←─ 200 ─→|
           overlap zone (shared between consecutive chunks)
```

**Why does overlap matter?** Without it, a sentence at the boundary gets cut:

```
NO OVERLAP (bad):
  Chunk 1: "...customers can request a"
  Chunk 2: "refund within 14 days..."
  → Searching for "refund" only finds Chunk 2, missing the full context

WITH OVERLAP (good):
  Chunk 1: "...customers can request a refund within 14"
  Chunk 2: "request a refund within 14 days of purchase..."
  → Both chunks contain the full sentence about refunds
```

**Quick reference** — chunk counts for different document sizes:

| Document size | Pages (approx) | Chunks (size=1000, overlap=200) |
| --- | --- | --- |
| 5,000 chars | ~2 pages | 7 |
| 10,000 chars | ~4 pages | 13 |
| 20,000 chars | ~8 pages | 25 |
| 36,000 chars | ~15 pages | 45 |
| 80,000 chars | ~30 pages | 100 |

> **Note:** The actual count may differ by ±2 because `RecursiveCharacterTextSplitter`
> tries to split at natural boundaries (paragraph breaks, sentence endings) rather
> than cutting mid-word. A chunk might end up at 950 characters instead of exactly
> 1000 to preserve a complete sentence.

**Other strategies (not used here, documented for reference):**

**Strategy 1 — Sentence-based:** split on sentence boundaries (`.!?`)

```text
text = "Returns take 5 days. Electronics have 14 days. Contact support."

chunks = [
    "Returns take 5 days.",
    "Electronics have 14 days.",
    "Contact support.",
]
```

Best for: short factual documents (FAQs, policies).
Weakness: very short chunks lose context — "Electronics have 14 days." — 14 days for WHAT?

---

**Strategy 2 — Paragraph-based:** split on double newlines (`\n\n`)

```text
text = "Returns policy:\n\nShopStream accepts returns within 30 days.
        Items must be in original condition.\n\nFor electronics,
        the return window is 14 days."

chunks = [
    "Returns policy:",
    "ShopStream accepts returns within 30 days. Items must be in original condition.",
    "For electronics, the return window is 14 days.",
]
```

Best for: documents with clear paragraph structure (reports, manuals).
Weakness: paragraph length varies wildly — one chunk may be 10 words, the next 500.

---

**Strategy 3 — Sliding window (what rag-chatbot uses):** fixed size with overlap

```text
text = "A B C D E F G H I J"   (size=6 words, overlap=2 words)

chunks = [
    "A B C D E F",       <- window 1
    "E F G H I J",       <- window 2 (E F overlap)
]
```

This is `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)` in the code.
Best for: dense technical text where every sentence matters equally.

---

**Strategy 4 — Semantic:** use an LLM to identify topic boundaries

```text
Step 1: split into sentences -> ["S1", "S2", "S3", "S4", "S5", "S6"]
Step 2: ask LLM "where does the topic change?" -> [3]
Step 3: merge into chunks:
    Chunk 1: "S1 S2 S3"   (topic A)
    Chunk 2: "S4 S5 S6"   (topic B)
```

Best for: long documents with mixed topics (50-page legal contracts).
Weakness: expensive — one LLM call per document.

---

**Decision table — which strategy to pick:**

| Content type | Best strategy |
| --- | --- |
| FAQs, policies, short docs | Sentence-based |
| Reports, manuals, structured | Paragraph-based |
| Dense technical text, code docs | **Sliding window ← rag-chatbot uses this** |
| Long contracts, mixed topics | Semantic (LLM) |

> 🚚 **Courier analogy:** Your document is a long parcels train — too heavy for one courier trip. You cut it into parcel-sized loads (chunks). The trick: each bag shares the last few items with the next bag (overlap). Why? Because the important clue might be "the refund window is..." at the end of bag 4 and "...14 days from purchase" at the start of bag 5. Without overlap, you'd retrieve one bag and miss the answer. With overlap, both bags contain the full sentence, so whichever one the courier retrieves has the complete thought.

---

## Chunks vs vectors — the key distinction

This is a common confusion: `chunk_size` and vector dimensions seem related but
are **completely different things**.

```
chunk_size = 200 characters  ← How big each text piece is (YOU choose this)
vector dimensions = 1024     ← How many numbers the model outputs (MODEL decides this)
```

They are independent:

| | chunk_size | Vector dimensions |
|---|---|---|
| **What** | Number of characters in each text piece | Number of numbers in each vector |
| **Unit** | Characters (text) | Floating-point numbers |
| **Who decides** | You (developer) | The embedding model |
| **Can you change it?** | Yes — config parameter | No — fixed by model architecture |
| **Typical values** | 200–2000 characters | 768, 1024, 1536, 3072 |
| **Affects** | How many chunks you get | How "detailed" the meaning representation is |
| **🚚 Courier** | Size of each parcel — you pack it bigger or smaller before the trip | The GPS label format printed on every bag — always 1024 numbers, the model decides, you can't change it |

### The relationship

chunk_size determines the **input** to the embedding model.
Vector dimensions are the **output** of the embedding model.
They're connected by the model, but their values are unrelated:

```
chunk_size=200 chars  ──→  Embedding Model  ──→  1024 numbers
chunk_size=500 chars  ──→  Embedding Model  ──→  1024 numbers  (same!)
chunk_size=2000 chars ──→  Embedding Model  ──→  1024 numbers  (same!)
```

Changing chunk_size changes **how many chunks** you get (more/fewer pieces),
but each chunk always produces a vector of the **same size**.

### Quick analogy

Think of it like writing a book summary:
- **chunk_size** = how long each chapter is (you decide: 5 pages or 20 pages)
- **vector dimensions** = the summary form (always a 5-star rating + 10-word headline)
- Short chapter or long chapter — the summary format stays the same

> 🚚 **Courier analogy:** The chunk size is the size of each package the courier carries — you can choose small (200 chars) or big (2000 chars) packages. The vector dimensions are the size of the GPS coordinate label printed on each package — always the same 1024 numbers, no matter how small or large the package. The warehouse sorts packages by their GPS label, not by how heavy they are. Different loads, same label format — they always fit the same GPS slot.

---

## What is cosine similarity?

**Cosine similarity** measures how similar two vectors are. Range: -1.0 to 1.0 (we normalize to 0.0 to 1.0).

- **1.0** = identical meaning
- **0.8+** = very similar
- **0.5** = somewhat related
- **0.0** = unrelated

```
cos_similarity("What is the refund policy?", "How to get a refund") = 0.92
cos_similarity("What is the refund policy?", "Company mission statement") = 0.23
cos_similarity("What is the refund policy?", "Pizza recipe") = 0.05
```

In this project, when you ask a question, the vector store returns chunks sorted by cosine similarity. The top-k chunks (highest scores) become the context for the LLM.

> 🚚 **Courier analogy:** Cosine similarity is the courier's compass bearing. Two couriers facing the same direction (same bearing = same semantic topic) are similar. The angle between them tells you how similar. If both face north-east (both about "refund policies") the angle is tiny → similarity near 1.0. If one faces north and one faces south-west ("pizza recipes"), the angle is huge → similarity near 0.0. The courier doesn't care about the distance between them — only the direction they're pointing. "Refund" and "money back" point the same direction even if they're written completely differently.

---

## What is a prompt?

A **prompt** is the text you send to the LLM. In RAG, the prompt has three parts:

```
[System instructions]
You are a helpful assistant. Only use the context below to answer.

[Context — the retrieved chunks]
Document chunk 1: "Refunds are processed within 14 days..."
Document chunk 2: "To request a refund, email support@..."

[User question]
What is the refund policy?
```

The quality of the prompt directly affects the quality of the answer. This is called **prompt engineering**.

> 🚚 **Courier analogy:** The prompt is the shipping manifest the courier reads before each trip. It has three sections: (1) standing instructions tattooed on the dispatch board ("only answer from your parcel, never make things up"), (2) today's shipping manifest — the retrieved document chunks, and (3) the customer's specific request. If the shipping manifest is unclear, the courier delivers to the wrong address. A precise, well-structured prompt = the courier delivers to exactly the right door every time.

---

## What is a token?

A **token** is the unit LLMs use to process text. It's **not** a word and **not** a character — it's a **subword piece**.

Roughly:
- 1 token ≈ 4 characters in English
- 1 token ≈ 0.75 words

### How text gets tokenized

The model uses a **tokenizer** (like `tiktoken` for GPT, `SentencePiece` for Claude) that splits text into subword pieces:

| Text | Tokens | Count |
|------|--------|-------|
| `"Hello"` | `["Hello"]` | 1 |
| `"refund"` | `["ref", "und"]` | 2 |
| `"How do refunds work?"` | `["How", " do", " ref", "unds", " work", "?"]` | 6 |
| `"authentication"` | `["auth", "ent", "ication"]` | 3 |

Common words → 1 token. Rare/long words → multiple tokens.

### Input tokens vs output tokens

The distinction is simple — it's based on **who wrote it**:

```
┌─────────────────────────────────────────────────┐
│  YOU send to the LLM (INPUT tokens):            │
│                                                 │
│  "You are a helpful assistant..."    ~50 tokens │  ← system prompt
│  "Our refund policy allows..."      ~800 tokens │  ← context chunks
│  "How do refunds work?"              ~10 tokens │  ← user question
│                                                 │
│  Total INPUT: ~860 tokens                       │
├─────────────────────────────────────────────────┤
│  LLM writes back (OUTPUT tokens):               │
│                                                 │
│  "Refunds can be requested through   ~70 tokens │  ← generated answer
│   the customer portal within 30                 │
│   days of purchase..."                          │
│                                                 │
│  Total OUTPUT: ~70 tokens                       │
└─────────────────────────────────────────────────┘

Total: 860 + 70 = 930 tokens
```

Everything you send = input tokens. Everything the LLM generates = output tokens.

### Who counts them? The API does.

You don't count tokens yourself — the LLM provider returns the counts in the API response:

```json
// AWS Bedrock (Claude)
{"usage": {"input_tokens": 860, "output_tokens": 70}}

// Azure OpenAI (GPT-4o) — same thing, different names
{"usage": {"prompt_tokens": 860, "completion_tokens": 70, "total_tokens": 930}}

// Local Ollama (llama3.2) — similar to Claude format
{"eval_count": 70, "prompt_eval_count": 860}
```

Your code just reads these numbers and passes them through to the `TokenUsage` model.

### Why output tokens cost more

| | Input tokens | Output tokens |
|---|---|---|
| **What** | Reading your prompt | Writing new text |
| **Work for LLM** | Easy — just encode | Hard — generate word by word |
| **AWS Claude 3.5** | $0.003 / 1K tokens | $0.015 / 1K tokens |
| **Azure GPT-4o** | $0.0025 / 1K tokens | $0.01 / 1K tokens |
| **Local Ollama** | **$0** (runs on your machine) | **$0** |
| **Ratio** | 1x | ~4-5x more expensive |
| **🚚 Courier** | Parcels the courier picks up and loads into its parcel — reading is easy | Words the courier writes on the delivery receipt — writing from scratch is harder work, so it costs more |

### Quick cost math for a RAG query

```
System prompt:      ~50 input tokens
3 chunks (200 chars): ~150 input tokens  (200 chars ÷ 4 ≈ 50 tokens × 3)
User question:      ~15 input tokens
Generated answer:   ~100 output tokens
────────────────────────────────
Total per question: ~$0.0015  (less than 0.2 cents)
→ 500+ questions per dollar
```

Tokens matter because:
- LLMs have a maximum context window (tokens they can process at once)
- You pay per token (input and output separately)
- More context chunks = more input tokens = higher cost

> 🚚 **Courier analogy:** A token is the smallest load the courier can carry — not a whole package, not a letter, but a word-chunk. Common words are one carry ("the", "and"). Long or rare words get split ("authentication" → "auth" + "ent" + "ication" = 3 carries). The courier has a maximum parcel size (context window) — it can only carry so many tokens per trip. Fill the bag with too many chunks and the last ones fall off. Each token costs a fraction of a cent: how many the courier picks up (input) plus how many the LLM writes (output).

---

## RAG vs Fine-tuning

| | RAG (what we build) | Fine-tuning | 🚚 Courier |
| --- | --- | --- | --- |
| **How** | Add documents at runtime | Retrain the model on your data | Pack today's map in the parcel vs. teach the courier a new route permanently |
| **Data updates** | Upload new documents instantly | Retrain the model (hours/days) | Swap the map tonight vs. send the courier back to school for months |
| **Cost** | Per-query (token costs) | Upfront training cost ($100–$10K+) | Pay a small fee per delivery vs. pay a large school fee upfront |
| **Accuracy** | Good with good retrieval | Better for specialized domains | Good if the map is accurate vs. courier memorised every back alley |
| **Sources** | Can cite exact documents | No source attribution | Courier shows you the exact page of the map it used vs. courier just knows, can't explain how |
| **Best for** | Knowledge bases, Q&A | Tone/style changes, specialized tasks | Maps that change over time vs. tasks needing a permanently specialist courier |

**For this project:** RAG is the right choice. Your documents change over time, you need source citations, and you don't want to pay for model training.

> 🚚 **Courier analogy:** Fine-tuning is like sending the courier to a 6-month school to memorise your town's entire map. Expensive, takes time, and if the town changes — back to school again. RAG is like giving the courier a fresh GPS map every morning before the delivery run. The courier stays the same smart courier it always was — but with the right map for today. Your knowledge base changes? Just update the map. No re-schooling. That's why RAG is the standard for document Q&A systems.

---

## Common RAG problems and solutions

| Problem | Cause | Solution | 🚚 Courier |
| --- | --- | --- | --- |
| Wrong answer | Irrelevant chunks retrieved | Increase `top_k`, improve chunking | Courier grabbed the wrong parcels — they looked similar but were from the wrong shelf |
| "I don't know" when answer exists | Chunk too small, question too vague | Increase chunk size, rephrase question | The answer was cut in half between two bags — neither bag had the full sentence |
| Hallucination | LLM ignores context | Stronger system prompt ("ONLY use context") | Courier ignored the parcel entirely and answered from memory — wrong, but confident |
| Slow responses | Too many chunks sent to LLM | Reduce `top_k`, use faster model | Courier is carrying 20 heavy bags when 3 would do — overloaded and slow |
| High cost | Too many tokens per query | Reduce chunk size, reduce `top_k` | Same overloading problem, but measured in money instead of sweat |
| Duplicate information | Overlapping chunks | Reduce `chunk_overlap` | Bag edges overlap too much — courier delivers the same letter twice in different bags |
