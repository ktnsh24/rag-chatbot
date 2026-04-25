# RAG Concepts — What is RAG, Explained Simply

## Table of Contents

- [What is RAG?](#what-is-rag)
- [The problem RAG solves](#the-problem-rag-solves)
- [How RAG works step by step](#how-rag-works-step-by-step)
- [The three components you must understand](#the-three-components-you-must-understand)
- [What are embeddings?](#what-are-embeddings)
- [What is a vector store?](#what-is-a-vector-store)
- [How vector search actually works](#how-vector-search-actually-works)
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

> 🫏 **Donkey analogy:** The LLM is the donkey — it carries your question to an answer. Without RAG, the donkey answers from memory — sometimes confidently wrong. With RAG, the donkey checks the backpack full of your documents before speaking. The backpack is the retrieval system. No backpack = guessing. Full backpack = grounded answers.

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

> 🫏 **Donkey analogy:** Imagine a donkey that grew up reading only public newspapers (training data). Ask it about your company's internal refund policy — it will confidently make something up, because newspapers never covered that. RAG gives the donkey a private courier bag of YOUR documents before every delivery. Now it reads from the bag first. Hallucination fixed.

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

> 🫏 **Donkey analogy:** Phase 1 (ingestion) is like the post office sorting all your letters into labelled boxes before the donkey arrives. Phase 2 (query) is the donkey's actual delivery run — it reads the address (your question), checks the right box (vector search), picks up the most relevant letters (top-k chunks), and delivers them to the LLM to write the final reply. No pre-sorting = the donkey has to read every letter on every delivery. Pre-sorted = instant pickup.

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
| **🫏 Donkey** | The translator who converts your text into GPS coordinates the warehouse understands | The GPS-indexed warehouse — finds the nearest shelf in milliseconds using stadium signs | The donkey — picks up the retrieved packages, reads them, and writes the final answer |

**Key insight:** OpenSearch / Azure AI Search / ChromaDB is a **database**, not a model.
It doesn't understand text — it stores vectors and finds similar ones. The embedding
model is what converts text into vectors that the store can work with.

> 🫏 **Donkey analogy:** Three workers, one delivery:
> - The **embedding model** is the translator — it converts your question from English into coordinates on a map.
> - The **vector store** is the warehouse with a GPS index — it finds the nearest box by coordinates instantly, without reading every label.
> - The **LLM** is the donkey — it picks up those boxes, reads the contents, and writes the final answer.
> Mix them up and the whole system breaks. You wouldn't ask the warehouse to write the answer, or the donkey to do the indexing.

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

> 🫏 **Donkey analogy:** An embedding is the donkey's internal address book — it converts the meaning of any text into a precise GPS coordinate in a 1024-dimensional city. "Refund policy" and "money back guarantee" end up on the same street corner (similar coordinates). "Pizza recipe" ends up in a completely different neighbourhood. The donkey doesn't read words — it navigates by coordinates. That's why it finds related content even when you use different words.

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

> 🫏 **Donkey analogy:** A regular database is a donkey that checks every house on every street to find your package — fine for 10 houses, impossibly slow for 1 million. A vector store with HNSW is a donkey with a highway system: it jumps onto the motorway first (top layer, few exits), takes the right exit to a main road (middle layer), then navigates to the exact street (bottom layer). Instead of visiting 1,000,000 houses, it visits ~20 waypoints. That's why it answers in milliseconds.

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

> 🫏 **Donkey analogy — how does the vector database find results so fast?**
>
> The donkey needs to find the closest matching document chunk — and there are **50,000 chunks** in the vector store (like 50,000 seats in a football stadium).
>
> ---
>
> **❌ Without HNSW (brute force):**
> The donkey sniffs chunk #1... not a match. Chunk #2... not a match. Chunk #3...
> → 50,000 sniffs. The donkey collapses before the answer is found.
>
> ---
>
> **✅ With HNSW — the donkey follows the stadium signs:**
>
> The stadium has signs at every level. At each sign, the donkey asks one question:
> *"Am I getting warmer or colder?"* — and moves only toward warmer.
>
> **Sign 1 — Stadium entrance: Sections A–Z**
> The donkey checks 3 section signs:
> - Section A → too far from the target meaning
> - Section G → closer ✓ move here
> - Section M → exact section ✓ stop
> → **3 checks**
>
> **Sign 2 — Inside Section M: Rows 1–50**
> The donkey checks 3 row markers:
> - Row 10 → getting warmer
> - Row 20 → warmer still
> - Row 23 → warmest ✓ stop
> → **3 checks**
>
> **Sign 3 — Row 23: Seats 1–30**
> The donkey checks 3 seats:
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
> The signs were built **at ingestion time** when you uploaded your documents. That's why uploading is slightly slower — the donkey is mapping the stadium once. Every search after that is instant, because the signs are already there.
>
> Add 10× more chunks? The donkey just reads one more sign per level. That's O(log N) — the work barely grows as the data grows.

> **For interviews:** Level 1 + Level 2 is sufficient. Level 3 is for senior
> roles or if the interviewer asks "how does the vector database find results so fast?"

---

## What is chunking?

**Chunking** is splitting a large document into smaller pieces.

Why?
- LLMs have a maximum context size (200K tokens for Claude)
- But sending the entire document wastes tokens (and money)
- Smaller chunks are more precise — the LLM gets exactly the relevant part
- Embedding models work best on paragraph-sized text

### Chunking strategies

**Fixed-size chunks (what we use):**
- Split every 1000 characters with 200 character overlap
- Simple and effective
- Overlap prevents sentences from being cut in half

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
- Sentence-based: split on sentence boundaries
- Paragraph-based: split on double newlines
- Semantic: use an LLM to identify topic boundaries
- Sliding window: fixed size with variable overlap

> 🫏 **Donkey analogy:** Your document is a long cargo train — too heavy for one donkey trip. You cut it into backpack-sized loads (chunks). The trick: each bag shares the last few items with the next bag (overlap). Why? Because the important clue might be "the refund window is..." at the end of bag 4 and "...14 days from purchase" at the start of bag 5. Without overlap, you'd retrieve one bag and miss the answer. With overlap, both bags contain the full sentence, so whichever one the donkey retrieves has the complete thought.

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
| **🫏 Donkey** | Size of each backpack — you pack it bigger or smaller before the trip | The GPS label format printed on every bag — always 1024 numbers, the model decides, you can't change it |

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

> 🫏 **Donkey analogy:** The chunk size is the size of each package the donkey carries — you can choose small (200 chars) or big (2000 chars) packages. The vector dimensions are the size of the GPS coordinate label printed on each package — always the same 1024 numbers, no matter how small or large the package. The warehouse sorts packages by their GPS label, not by how heavy they are. Different loads, same label format — they always fit the same GPS slot.

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

> 🫏 **Donkey analogy:** Cosine similarity is the donkey's compass bearing. Two donkeys facing the same direction (same bearing = same semantic topic) are similar. The angle between them tells you how similar. If both face north-east (both about "refund policies") the angle is tiny → similarity near 1.0. If one faces north and one faces south-west ("pizza recipes"), the angle is huge → similarity near 0.0. The donkey doesn't care about the distance between them — only the direction they're pointing. "Refund" and "money back" point the same direction even if they're written completely differently.

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

> 🫏 **Donkey analogy:** The prompt is the delivery note the donkey reads before each trip. It has three sections: (1) standing instructions tattooed on the stable wall ("only answer from your backpack, never make things up"), (2) today's cargo manifest — the retrieved document chunks, and (3) the customer's specific request. If the delivery note is unclear, the donkey delivers to the wrong address. A precise, well-structured prompt = the donkey delivers to exactly the right door every time.

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
| **🫏 Donkey** | Cargo the donkey picks up and loads into its backpack — reading is easy | Words the donkey writes on the delivery receipt — writing from scratch is harder work, so it costs more |

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

> 🫏 **Donkey analogy:** A token is the smallest load the donkey can carry — not a whole package, not a letter, but a word-chunk. Common words are one carry ("the", "and"). Long or rare words get split ("authentication" → "auth" + "ent" + "ication" = 3 carries). The donkey has a maximum backpack size (context window) — it can only carry so many tokens per trip. Fill the bag with too many chunks and the last ones fall off. Each token costs a fraction of a cent: how many the donkey picks up (input) plus how many the LLM writes (output).

---

## RAG vs Fine-tuning

| | RAG (what we build) | Fine-tuning | 🫏 Donkey |
| --- | --- | --- | --- |
| **How** | Add documents at runtime | Retrain the model on your data | Pack today's map in the backpack vs. teach the donkey a new route permanently |
| **Data updates** | Upload new documents instantly | Retrain the model (hours/days) | Swap the map tonight vs. send the donkey back to school for months |
| **Cost** | Per-query (token costs) | Upfront training cost ($100–$10K+) | Pay a small fee per delivery vs. pay a large school fee upfront |
| **Accuracy** | Good with good retrieval | Better for specialized domains | Good if the map is accurate vs. donkey memorised every back alley |
| **Sources** | Can cite exact documents | No source attribution | Donkey shows you the exact page of the map it used vs. donkey just knows, can't explain how |
| **Best for** | Knowledge bases, Q&A | Tone/style changes, specialized tasks | Maps that change over time vs. tasks needing a permanently specialist donkey |

**For this project:** RAG is the right choice. Your documents change over time, you need source citations, and you don't want to pay for model training.

> 🫏 **Donkey analogy:** Fine-tuning is like sending the donkey to a 6-month school to memorise your town's entire map. Expensive, takes time, and if the town changes — back to school again. RAG is like giving the donkey a fresh GPS map every morning before the delivery run. The donkey stays the same smart donkey it always was — but with the right map for today. Your knowledge base changes? Just update the map. No re-schooling. That's why RAG is the standard for document Q&A systems.

---

## Common RAG problems and solutions

| Problem | Cause | Solution | 🫏 Donkey |
| --- | --- | --- | --- |
| Wrong answer | Irrelevant chunks retrieved | Increase `top_k`, improve chunking | Donkey grabbed the wrong backpacks — they looked similar but were from the wrong shelf |
| "I don't know" when answer exists | Chunk too small, question too vague | Increase chunk size, rephrase question | The answer was cut in half between two bags — neither bag had the full sentence |
| Hallucination | LLM ignores context | Stronger system prompt ("ONLY use context") | Donkey ignored the backpack entirely and answered from memory — wrong, but confident |
| Slow responses | Too many chunks sent to LLM | Reduce `top_k`, use faster model | Donkey is carrying 20 heavy bags when 3 would do — overloaded and slow |
| High cost | Too many tokens per query | Reduce chunk size, reduce `top_k` | Same overloading problem, but measured in money instead of sweat |
| Duplicate information | Overlapping chunks | Reduce `chunk_overlap` | Bag edges overlap too much — donkey delivers the same letter twice in different bags |
