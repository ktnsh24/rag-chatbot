# Deep Dive: The Vector Store Interface — `src/vectorstore/base.py`

> **Study order:** #9 · **Difficulty:** ★☆☆☆☆ (another abstract class — the new part is *what* it stores)  
>
> **File:** [`src/vectorstore/base.py`](../../src/vectorstore/base.py)  
>
> **Prerequisite:** [#7 — The LLM Interface](llm-interface-deep-dive.md) (especially Concept 4: Embeddings)  
>
> **Part of:** [Architecture Overview](../architecture-and-design/architecture.md)

---

## Table of Contents

1. [Why This File Matters](#why-this-file-matters)
2. [DE Parallel — What You Already Know](#de-parallel--what-you-already-know)
3. [Concept 1: VectorSearchResult — What Comes Back from a Semantic Search](#concept-1-vectorsearchresult--what-comes-back-from-a-semantic-search)
4. [Concept 2: `store_vectors()` — Writing Embeddings to the Database](#concept-2-store_vectors--writing-embeddings-to-the-database)
5. [Concept 3: `search()` — Finding Similar Vectors (Not Exact Matches)](#concept-3-search--finding-similar-vectors-not-exact-matches)
6. [Concept 4: `delete_document()` — Removing Vectors by Document](#concept-4-delete_document--removing-vectors-by-document)
7. [The Key Difference: Exact Match vs Semantic Search](#the-key-difference-exact-match-vs-semantic-search)
8. [Where `base.py` Sits in the RAG Pipeline](#where-basepy-sits-in-the-rag-pipeline)
9. [Self-Test Questions](#self-test-questions)
10. [What to Study Next](#what-to-study-next)

---

## Why This File Matters

In file #7 you learned that `get_embedding()` converts text into a vector (list of 1024 floats). This file answers the next question: **where do those vectors go?**

The vector store is the **"database" of the RAG system**. But unlike a regular DynamoDB table or PostgreSQL, it doesn't search by key or by SQL — it searches by **similarity**. You give it a vector and ask "what's close to this?" That's the fundamental shift.

> **Fun twist:** One of our implementations (`aws_dynamodb.py`) actually *uses* DynamoDB as a vector store by storing embeddings as JSON and computing cosine similarity in Python. It proves that any database can be a vector store — the difference is performance (brute-force vs HNSW indexing). See the [DynamoDB deep dive](vectorstore-providers-deep-dive.md#aws-dynamodb-the-cheap-alternative--0month-vector-store).

| What you'll learn | DE parallel | 🫏 Donkey |
|---|---| --- |
| How embeddings are stored | How rows are inserted into DynamoDB | AWS-side stable yard — How embeddings are stored: How rows are inserted into DynamoDB |
| How semantic search works (conceptually) | How key-based or index-based lookups work | Donkey-side view of How semantic search works (conceptually) — affects how the donkey loads, reads, or delivers the cargo |
| What a similarity score means | What a query result set means | Compass bearing — What a similarity score means: What a query result set means |
| How documents are managed (store + delete) | How records are managed (put + delete) | Donkey-side view of How documents are managed (store + delete) — affects how the donkey loads, reads, or delivers the cargo |

- 🫏 **Donkey:** Think of this as the orientation briefing given to a new donkey before its first delivery run — it sets the context for everything that follows.

---

## DE Parallel — What You Already Know

```
┌─────────────────────────────────────────┐    ┌─────────────────────────────────────────┐
│  YOUR DE CODE (DynamoDB)                │    │  THIS AI CODE (Vector Store)            │
│                                         │    │                                         │
│  class BaseStorage(ABC):                │    │  class BaseVectorStore(ABC):             │
│      def put_item(key, data)            │    │      def store_vectors(id, texts, vecs)  │
│      def query(key) → items             │    │      def search(vector, k) → results     │
│      def delete_item(key)               │    │      def delete_document(id)              │
│                                         │    │                                         │
│  Stores: rows with attributes           │    │  Stores: text chunks with vectors        │
│  Searches by: exact key match           │    │  Searches by: vector similarity          │
│  Returns: exact matches                 │    │  Returns: ranked by closeness (score)    │
└─────────────────────────────────────────┘    └─────────────────────────────────────────┘
```

The interface pattern is identical — ABC with abstract methods for CRUD operations. The *data* it stores and the *way* it searches are what's new.

- 🫏 **Donkey:** Running multiple donkeys on the same route to confirm that AI engineering and data engineering practices mirror each other.

---

## Concept 1: VectorSearchResult — What Comes Back from a Semantic Search

**The code (lines 18–37):**
```python
@dataclass
class VectorSearchResult:
    text: str                          # The original text chunk
    document_name: str                 # Which document it came from
    score: float                       # Cosine similarity (0.0 to 1.0)
    page_number: int | None = None     # Page in original document
    metadata: dict = field(default_factory=dict)
```

### What each field means

| Field | What it is | DE parallel | 🫏 Donkey |
|---|---|---| --- |
| `text` | The actual chunk text — what the LLM will read | The row data | The cargo inside the backpack — what the donkey actually reads to write its answer |
| `document_name` | Source document (e.g., "refund-policy.pdf") | The table or source name | Stable keys — only authorised callers may ask the donkey to deliver |
| `score` | How similar this chunk is to the query (0.0–1.0) | ❌ **No DE parallel** — this is new | GPS warehouse calculates score by measuring angle between question and backpack coordinates |
| `page_number` | Where in the original document | Like a row number or partition | Which page of the original mail the backpack came from |
| `metadata` | Anything extra (document_id, chunk_index) | Additional attributes | Extra labels on the backpack — document ID and chunk position for tracking |

### The `score` field — the new concept

In DynamoDB, a query either matches or doesn't. There's no "how close is this match?" In vector search, **every result has a score**:

```
Query: "What is the refund policy?"

Results:
  Chunk 7:  "Our refund policy allows returns within 14 days..."    score: 0.92  ← very relevant
  Chunk 12: "Returns for international orders may take 30 days..."  score: 0.78  ← somewhat relevant
  Chunk 3:  "We offer free shipping on all orders..."               score: 0.31  ← barely relevant
```

| Score range | Meaning | Action | 🫏 Donkey |
|---|---|---| --- |
| 0.85–1.0 | Highly relevant — almost certainly the right chunk | Send to LLM ✅ | A near-perfect GPS match — load this backpack onto the donkey without hesitation |
| 0.70–0.85 | Relevant — probably useful context | Send to LLM ✅ | A close-enough GPS match — pack this backpack too, the donkey can probably use it |
| 0.50–0.70 | Marginal — might add noise | Consider filtering ⚠️ | How confidently the warehouse says 'this backpack matches' — higher = closer GPS hit |
| 0.0–0.50 | Irrelevant — wastes tokens and confuses the LLM | Filter out ❌ | A wrong-shelf GPS hit — leave this backpack behind or the donkey will eat hay reading junk |

**Key insight:** Score thresholds are not universal — they depend on your data, your embedding model, and your use case. An AI engineer experiments with different thresholds and measures the impact using the [Evaluation Framework](evaluation-framework-deep-dive.md).

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Concept 2: `store_vectors()` — Writing Embeddings to the Database

**The code (lines 52–73):**
```python
@abstractmethod
async def store_vectors(
    self,
    document_id: str,              # Unique ID for the document
    document_name: str,            # Original filename
    texts: list[str],              # The text of each chunk
    embeddings: list[list[float]], # The vector for each chunk
    metadatas: list[dict] | None,  # Optional extra data
) -> int:                          # Returns count of vectors stored
```

### What goes in vs what you're used to

```
DynamoDB put_item:                       Vector store store_vectors:
────────────────                         ────────────────────────────
Key:   {"pk": "customer_123"}            document_id: "doc_abc"
Data:  {"name": "Jan", "age": 35}        texts: ["Refund policy allows...", "Returns must be..."]
                                         embeddings: [[0.12, -0.45, ...], [0.34, -0.67, ...]]

What's stored:                           What's stored:
  One row with attributes                  Multiple vectors (one per chunk)
                                           Each vector = 1024 floats + the original text
```

**DE parallel:** This is a batch insert — one call stores multiple "rows" (vectors). Like DynamoDB's `batch_write_item` but for embedding vectors instead of key-value pairs.

**Key insight:** The `texts` and `embeddings` lists are paired by index. `texts[0]` is the original text, `embeddings[0]` is its vector representation. Both are stored together so that when you search and find a matching vector, you can return the original text to the LLM.

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Concept 3: `search()` — Finding Similar Vectors (Not Exact Matches)

**The code (lines 75–92):**
```python
@abstractmethod
async def search(
    self,
    query_embedding: list[float],   # The question, as a vector
    top_k: int = 5,                 # How many results to return
) -> list[VectorSearchResult]:      # Ranked by similarity
```

### This is the biggest conceptual shift

```
DYNAMODB QUERY (exact match):               VECTOR SEARCH (similarity):
─────────────────────────────                ───────────────────────────
Input:  Key = "customer_123"                 Input:  Vector = [0.12, -0.45, ...]
Logic:  Find rows WHERE pk = key             Logic:  Find vectors CLOSEST to this vector
Output: Exact matches (0 or more)            Output: Top K nearest neighbors (always K results)
Score:  N/A — it matched or it didn't        Score:  0.0 to 1.0 (how close)
```

### How vector search works (simplified)

```
Your question: "What is the refund policy?"
  → get_embedding() → [0.12, -0.45, 0.78, ...]   (1024 floats)

Stored vectors (from ingestion):
  Chunk 1: [0.88, 0.23, -0.56, ...]  ← about shipping    → distance: FAR
  Chunk 2: [0.11, -0.44, 0.79, ...]  ← about refunds     → distance: CLOSE  ✅
  Chunk 3: [0.67, -0.12, 0.34, ...]  ← about pricing     → distance: MEDIUM
  Chunk 4: [0.13, -0.43, 0.77, ...]  ← about returns     → distance: CLOSE  ✅
  ...

search(query_embedding=[0.12, -0.45, 0.78, ...], top_k=2)
  → Returns: [Chunk 2 (score=0.98), Chunk 4 (score=0.91)]
```

### What `top_k` means

`top_k=5` means "return the 5 most similar vectors." It's like `LIMIT 5` in SQL, but:
- SQL `LIMIT` returns any 5 rows (unless you `ORDER BY`)
- Vector `top_k` **always returns the K closest** — it's inherently ordered by similarity

**Trade-offs:**

| top_k | Pros | Cons | 🫏 Donkey |
|---|---|---| --- |
| 3 | Less noise, cheaper (fewer tokens to LLM) | Might miss relevant context | Donkey carries only three backpacks — light load, less hay, but might leave the right one behind |
| **5** | **Good balance (this repo's default)** | **Some noise possible** | Donkey-side view of 5 — affects how the donkey loads, reads, or delivers the cargo |
| 10 | More context, less likely to miss relevant info | More tokens = more cost + noise | Ten backpacks is heavy — the donkey might find the right one but wastes hay reading extras |

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Concept 4: `delete_document()` — Removing Vectors by Document

**The code (lines 94–104):**
```python
@abstractmethod
async def delete_document(self, document_id: str) -> int:
    """Delete all vectors belonging to a document."""
    ...
```

**DE parallel:** This is exactly `DELETE FROM table WHERE document_id = ?`. When a document is updated, you:
1. Delete all old vectors for that document
2. Re-ingest the new version (chunk → embed → store)

Same pattern as deleting old records before re-loading in an ETL pipeline.

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## The Key Difference: Exact Match vs Semantic Search

This is the single most important concept to internalise:

```
DynamoDB:    "Give me the row with pk = 'customer_123'"
             → Either finds it (exact match) or returns empty

Vector DB:   "Give me the 5 chunks most similar to this meaning"
             → ALWAYS returns 5 results, ranked by how similar they are
             → Even if nothing is truly relevant, you still get 5 results
```

**Why this matters:** In DynamoDB, no result = "data doesn't exist." In vector search, **low scores mean "nothing relevant exists" but you still get results**. This is why filtering by score is important:

```python
# DynamoDB: no result means not found
item = table.get_item(Key={"pk": "123"})
if "Item" not in item:
    return "Not found"

# Vector search: results always come back, but check the score
results = await store.search(query_embedding, top_k=5)
if results[0].score < 0.5:
    return "I don't have relevant information about that"  # Low confidence
```

- 🫏 **Donkey:** The warehouse robot dispatched to find the right backpack shelf — it uses GPS coordinates (embeddings) to locate the nearest relevant chunks in ~9 hops.

---

## Where `base.py` Sits in the RAG Pipeline

```
INGESTION (one-time per document):
  Document → chunks → get_embedding() each → store_vectors() ← THIS FILE
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │ Vector Store │ (OpenSearch / AI Search)
                                         │  1024-dim    │
                                         │  vectors     │
                                         └──────┬──────┘
                                                │
QUERY (every user question):                    │
  Question → get_embedding() → search() ← THIS FILE
                                   │
                                   ▼
                           Top K chunks → generate() → Answer
```

- 🫏 **Donkey:** The donkey checks its backpack full of retrieved document chunks before answering — no guessing from memory.

---

## Self-Test Questions

| Question | Answer | Concept it tests | 🫏 Donkey |
|---|---|---| --- |
| "What does a score of 0.3 mean?" | The chunk is semantically far from the query — probably not relevant. It's like a SQL query returning a row that doesn't match your intent. | Similarity scores | Score 0.3 means the backpack's GPS is far from the question — probably the wrong shelf |
| "Why does `search()` always return K results even when nothing is relevant?" | Vector search finds the K **nearest** vectors regardless. "Nearest" doesn't mean "relevant" — just closest in the vector space. | Semantic search vs exact match | Where parcels are dropped at the stable — "Why does search() always return K results even when nothing is relevant?": Vector search finds the K |
| "Why store the original `text` alongside the `embedding`?" | Embeddings are one-way (can't reverse vector → text). You need the original text to send as context to the LLM. | Embedding properties | GPS coordinates can't be unstamped back into cargo, so the warehouse keeps the original text on every shelf |
| "What happens if `texts` and `embeddings` have different lengths?" | Bug — they must be paired by index. text[i] matches embedding[i]. | Store contract | Every backpack text must have its matching GPS stamp — misaligned lists break the warehouse |
| "Why is `document_id` important?" | It lets you delete all vectors for a document when re-ingesting. Without it, you'd have orphaned old vectors. | Document management | Loading-bay pre-sort — "Why is document_id important?": It lets you delete all vectors for a document when re-ingesting. Without it, you'd have orphaned old vectors.… |

- 🫏 **Donkey:** Sending the donkey on 25 standard test deliveries (golden dataset) to verify it returns the right packages every time.

---

## What to Study Next

Now that you understand the **interface**, study the **implementations**:
- **File #10:** [`src/vectorstore/aws_opensearch.py`](vectorstore-providers-deep-dive.md) + `azure_ai_search.py` — the cloud vector store implementations. You'll see k-NN queries, HNSW indexing, and cosine similarity in action.
- **File #12:** [`src/vectorstore/local_chromadb.py`](../../src/vectorstore/local_chromadb.py) — the local ChromaDB implementation. Runs in-memory or persists to SQLite, no cloud credentials needed.

📖 **Related docs:**
- [Deep Dive: Vector Store Providers (AWS OpenSearch + Azure AI Search + Local ChromaDB)](vectorstore-providers-deep-dive.md)

- 🫏 **Donkey:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
