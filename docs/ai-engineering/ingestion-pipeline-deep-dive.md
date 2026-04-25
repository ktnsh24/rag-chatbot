# Deep Dive: The Ingestion Pipeline — `src/rag/ingestion.py`

> **Study order:** #11 · **Difficulty:** ★★☆☆☆ (this IS your ETL — just with different transforms)  
> **File:** [`src/rag/ingestion.py`](../../src/rag/ingestion.py)  
> **Prerequisite:** [#7 — Embeddings](llm-interface-deep-dive.md#concept-4-embeddings--turning-meaning-into-math-get_embedding) · [#9 — store_vectors()](vectorstore-interface-deep-dive.md#concept-2-store_vectors--writing-embeddings-to-the-database)  
> **Part of:** [Architecture Overview](../architecture-and-design/architecture.md)

---

## Table of Contents

1. [Why This File Matters](#why-this-file-matters)
2. [DE Parallel — This IS Your ETL Pipeline](#de-parallel--this-is-your-etl-pipeline)
3. [The Three Stages: Read → Chunk → Embed](#the-three-stages-read--chunk--embed)
4. [Stage 1: `read_document()` — The Extract](#stage-1-read_document--the-extract)
5. [Stage 2: `chunk_document()` — The Transform](#stage-2-chunk_document--the-transform)
6. [Concept 1: Why Chunking Matters — The Core AI Decision](#concept-1-why-chunking-matters--the-core-ai-decision)
7. [Concept 2: Chunk Overlap — Preventing Broken Sentences](#concept-2-chunk-overlap--preventing-broken-sentences)
8. [Concept 3: RecursiveCharacterTextSplitter — Smart Splitting](#concept-3-recursivecharactertextsplitter--smart-splitting)
9. [The Full Pipeline: End to End](#the-full-pipeline-end-to-end)
10. [Self-Test Questions](#self-test-questions)
11. [What to Study Next](#what-to-study-next)

---

## Why This File Matters

This is the file where **your DE skills apply most directly.** The ingestion pipeline is an **ETL pipeline** — it reads data (Extract), transforms it (chunk + embed), and loads it (store vectors). The only difference from your daily DE work is *what* the transform does.

| What you'll learn | DE parallel | 🫏 Donkey |
|---|---| --- |
| Reading multiple file formats | Reading CSV, JSON, Parquet | Stable inspector — checks the code is tidy before letting the donkey out |
| Chunking text into pieces | Partitioning data into batches | backpack piece 📦 |
| Why chunk size matters | Why partition size matters | backpack piece 📦 |
| Why overlap exists | Why you keep boundary records in adjacent partitions | backpack piece 📦 |
| The full ingest pipeline | The full ETL pipeline | Pre-sort 📮 |

- 🫏 **Donkey:** Think of this as the orientation briefing given to a new donkey before its first delivery run — it sets the context for everything that follows.

---

## DE Parallel — This IS Your ETL Pipeline

```
YOUR DE ETL:                                 THIS AI PIPELINE:
───────────────                              ──────────────────

EXTRACT                                      EXTRACT
  Read from S3/Kinesis/API                     Read from uploaded file (PDF/Word/TXT)
  → raw data (JSON, CSV)                       → raw text (string)

TRANSFORM                                    TRANSFORM
  Clean: remove nulls, fix types               Chunk: split into ~1000-char pieces
  Enrich: add timestamps, derive fields        Embed: convert each chunk → 1024-float vector
  Aggregate: group by, count, sum              (no aggregation — each chunk is independent)

LOAD                                         LOAD
  Write to DynamoDB / S3 / Redshift            Write to OpenSearch (vector store)
  → rows in a table                            → vectors in an index
```

**The pattern is identical.** The domain is different.

- 🫏 **Donkey:** Running multiple donkeys on the same route to confirm that AI engineering and data engineering practices mirror each other.

---

## The Three Stages: Read → Chunk → Embed

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  READ            │    │  CHUNK           │    │  EMBED           │    │  STORE           │
│  (Extract)       │───▶│  (Transform 1)   │───▶│  (Transform 2)   │───▶│  (Load)          │
│                  │    │                  │    │                  │    │                  │
│  PDF/Word/TXT    │    │  Split into      │    │  Each chunk →    │    │  Vectors →       │
│  → plain text    │    │  ~1000-char      │    │  vector (1024/   │    │  OpenSearch /    │
│                  │    │  pieces          │    │  1536/768 floats)│    │  AI Search /     │
│                  │    │                  │    │                  │    │  ChromaDB        │
└──────────────────┘    └──────────────────┘    └──────────────────┘    └──────────────────┘
  read_document()         chunk_document()        get_embeddings_batch()   store_vectors()
  (this file)             (this file)             (llm provider)           (vectorstore/)
```

- 🫏 **Donkey:** backpack-sized pieces of cargo with overlapping edges, so no sentence is cut off at a seam.

---

## Stage 1: `read_document()` — The Extract

**The code (lines 30–49):**
```python
def read_document(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()

    if extension == ".pdf":
        return _read_pdf(content)
    elif extension in (".txt", ".md", ".csv"):
        return content.decode("utf-8", errors="replace")
    elif extension == ".docx":
        return _read_docx(content)
    else:
        raise ValueError(f"Unsupported file type: {extension}")
```

### What this does

Takes raw file bytes and extracts plain text. That's it.

| File type | How it's read | DE parallel | 🫏 Donkey |
|---|---|---| --- |
| `.pdf` | `pypdf` library → extracts text per page | Like reading Parquet → extract columns | Post office sorting raw mail into GPS-labelled boxes before the donkey's first trip |
| `.txt`, `.md`, `.csv` | `content.decode("utf-8")` | Like reading a CSV as text | The actual cargo text inside the backpack the donkey is carrying |
| `.docx` | `python-docx` library → extracts paragraphs | Like reading Excel → extract cells | Post office sorting raw mail into GPS-labelled boxes before the donkey's first trip |

**DE parallel:** This is your "source connector." In DE work, you have connectors for Kinesis, DynamoDB, S3. Here, you have connectors for PDF, Word, text. Same pattern — abstract away the source format, output a standard format (plain text / rows).

### The PDF reader (lines 52–60)

```python
def _read_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    text_parts = []
    for page_num, page in enumerate(reader.pages, 1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            text_parts.append(f"[Page {page_num}]\n{page_text}")
    return "\n\n".join(text_parts)
```

**Key detail:** It adds `[Page N]` markers. This means chunks will carry page references — so the LLM can cite "according to Page 3" in its answer.

- 🫏 **Donkey:** The parcels being ingested — split into backpack-sized chunks, GPS-stamped, and shelved in the warehouse for the donkey to retrieve later.

---

## Stage 2: `chunk_document()` — The Transform

**The code (lines 79–112):**
```python
def chunk_document(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return chunks
```

### What this does

Takes one long text string and splits it into multiple smaller pieces (chunks).

```
INPUT:  One big string (e.g., 15,000 characters from a PDF)

OUTPUT: List of smaller strings (e.g., 18 chunks of ~1000 characters each)

"Our company refund policy states that all customers who purchased a product
 within the Netherlands are eligible for a full refund within 14 business
 days of purchase. To request a refund, visit the customer portal at..."
 [... 15,000 characters total ...]

                              ↓ chunk_document(text, chunk_size=1000, chunk_overlap=200)

 Chunk 1: "Our company refund policy states that all customers who..."   (~1000 chars)
 Chunk 2: "...within 14 business days of purchase. To request a..."      (~1000 chars)
 Chunk 3: "...refund, visit the customer portal at portal.example.com..."(~1000 chars)
 ...
 Chunk 18: "...for international orders, processing may take longer."    (~600 chars)
```

- 🫏 **Donkey:** backpack-sized pieces of cargo with overlapping edges, so no sentence is cut off at a seam.

---

## Concept 1: Why Chunking Matters — The Core AI Decision

**Why not send the whole document to the LLM?**

Three reasons:

```
Reason 1: PRECISION
  The LLM answers about refunds. The document has 50 pages.
  If you send all 50 pages (60,000 tokens), the LLM has to find the relevant
  paragraph in a sea of text → more likely to miss it or get confused.
  If you send just the 2 relevant chunks (500 tokens), the LLM focuses on
  exactly the right content → better answers.

Reason 2: CONTEXT WINDOW
  Claude's limit: 200,000 tokens.
  One large document: 60,000 tokens — fits, but uses 30% of the window.
  If the user has chat history + multiple documents → might exceed the limit.
  Small chunks = only send what's relevant = stay within limits.

Reason 3: COST
  You pay per token. Sending 60,000 tokens vs 500 tokens is 120× more expensive.
  At $0.003/1K tokens: $0.18 per query vs $0.0015 per query.
  At 1000 queries/day: $180/day vs $1.50/day.
```

**DE parallel:** This is the same reasoning behind partitioning. You don't scan a full table when you need one row. You partition by date/key so your query only reads the relevant partition. Chunking is partitioning for AI.

### Chunk size — the most important AI tuning parameter

| chunk_size | Effect on retrieval | Effect on answers | Effect on cost | 🫏 Donkey |
|---|---|---|---| --- |
| 200 | Very precise — finds exact sentences | May lose context (split between chunks) | Cheapest per query | backpack piece 📦 |
| 500 | Precise — paragraph-level | Usually enough context | Cheap | Stable broke down — donkey couldn't complete the trip, customer sees an error |
| **1000** | **Good balance (this repo's default)** | **Full paragraphs with context** | **Moderate** | Donkey-side view of 1000 — affects how the donkey loads, reads, or delivers the cargo |
| 2000 | Less precise — section-level | Always has full context | More expensive | How big each backpack-piece of cargo is — bigger = more context, fewer matches |
| 5000 | Imprecise — chapter-level | Too much noise | Expensive | Stable broke down — donkey couldn't complete the trip, customer sees an error |

**There is no universally correct chunk_size.** An AI engineer experiments with different values and measures the impact using the [Evaluation Framework](evaluation-framework-deep-dive.md).

- 🫏 **Donkey:** backpack-sized pieces of cargo with overlapping edges, so no sentence is cut off at a seam.

---

## Concept 2: Chunk Overlap — Preventing Broken Sentences

**The parameter:** `chunk_overlap=200`

Without overlap, sentences at chunk boundaries get cut in half:

```
chunk_overlap=0 (NO overlap):
─────────────────────────────
Chunk 1: "...customers are eligible for a full refund within"
Chunk 2: "14 business days of purchase. To request a refund..."
          ↑ sentence is BROKEN — "within 14" is split across chunks

chunk_overlap=200 (WITH overlap):
──────────────────────────────────
Chunk 1: "...customers are eligible for a full refund within 14 business days of purchase."
Chunk 2: "...full refund within 14 business days of purchase. To request a refund..."
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  ← this text appears in BOTH chunks
```

### Why 200?

The overlap means the last 200 characters of chunk N appear again at the start of chunk N+1. This ensures:
- No sentence is cut in half
- The LLM always gets complete sentences
- Context that spans a boundary isn't lost

**Trade-off:** More overlap = more chunks = more vectors = more storage + embedding cost. But `200/1000 = 20%` overhead is a good balance.

**DE parallel:** This is like partition overlap in streaming systems. When processing time windows, you often include events from the edge of the previous window to avoid missing events that span the boundary.

- 🫏 **Donkey:** backpack-sized pieces of cargo with overlapping edges, so no sentence is cut off at a seam.

---

## Concept 3: RecursiveCharacterTextSplitter — Smart Splitting

**The key parameter:** `separators=["\n\n", "\n", ". ", " ", ""]`

The splitter doesn't just cut at exactly 1000 characters. It tries to split at natural boundaries, in priority order:

```
Priority 1: "\n\n" — paragraph break (best split point)
Priority 2: "\n"   — line break
Priority 3: ". "   — sentence end
Priority 4: " "    — word break
Priority 5: ""     — character (last resort)
```

**How it works:**

```
Step 1: Try to split on "\n\n" (paragraphs)
  → If each paragraph is < 1000 chars → done ✅
  → If a paragraph is > 1000 chars → go to step 2

Step 2: Try to split on "\n" (lines) within that paragraph
  → If each section is < 1000 chars → done ✅
  → If still too big → go to step 3

Step 3: Try to split on ". " (sentences)
  → Usually this works for normal text

Step 4: Split on " " (words) — if a sentence is > 1000 chars
Step 5: Split on "" (characters) — emergency fallback
```

**DE parallel:** This is like a smart partition strategy. Instead of blindly partitioning every 1000 rows, you partition at natural boundaries (by date, by customer, by category). The splitter partitions at natural text boundaries (paragraphs, sentences).

**Why "recursive"?** Because it tries each separator in order, recursing to the next one if the chunks are still too big. It's a hierarchy of split strategies, not a single rule.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## The Full Pipeline: End to End

When a user uploads a document, here's what happens (combining all files you've studied):

```
User uploads: "refund-policy.pdf" (15,000 characters)
│
├─ Stage 1: READ  (ingestion.py → read_document)
│  └─ PDF → plain text (15,000 chars)
│
├─ Stage 2: CHUNK  (ingestion.py → chunk_document)
│  └─ 15,000 chars → 18 chunks (~1000 chars each, 200 overlap)
│
├─ Stage 3: EMBED  (llm/aws_bedrock.py → get_embeddings_batch)
│  └─ 18 chunks → 18 vectors (each 1024 floats)
│  └─ Cost: 18 × ~250 tokens × $0.00002/1K = $0.00009 (fraction of a cent)
│
├─ Stage 4: STORE  (vectorstore/aws_opensearch.py → store_vectors)
│  └─ 18 vectors → indexed in OpenSearch
│  └─ Each vector stored with: text, document_id, document_name, page_number
│
└─ DONE: Document is now searchable
   Total time: ~3 seconds
   Total cost: ~$0.0001

Later, when user asks "What is the refund policy?":
│
├─ search() finds chunks with scores [0.92, 0.87, 0.76, 0.45, 0.31]
├─ Top 3 chunks sent to generate() as context
└─ LLM answers: "The refund policy allows returns within 14 business days..."
```

### The numbers for a real scenario

| Metric | Value | 🫏 Donkey |
|---|---| --- |
| Document size | 15,000 characters (5 pages) | Donkey-side view of Document size — affects how the donkey loads, reads, or delivers the cargo |
| Chunks created | 18 (chunk_size=1000, overlap=200) | backpack piece 📦 |
| Vectors stored | 18 × 1024 floats = 18,432 numbers | GPS warehouse 🗺️ |
| Embedding cost | $0.00009 | Feed bill 🌾 |
| Storage size | ~74 KB (18 × 4096 bytes per vector) | How the warehouse measures which backpacks are nearest to the customer's question |
| Ingestion time | ~3 seconds | Pre-sort 📮 |
| If 500 documents | 500 × 18 = 9,000 vectors, ~$0.045 total, ~25 minutes | Feed bill 🌾 |

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Self-Test Questions

| Question | Answer | Concept it tests | 🫏 Donkey |
|---|---|---| --- |
| "Why chunk_size=1000 and not 500 or 2000?" | Trade-off: 500 is more precise but loses context. 2000 has more context but less precise retrieval. 1000 is the default balance — but you should TEST with your data. | Chunk size tuning | backpack piece 📦 |
| "What happens if chunk_overlap=0?" | Sentences at chunk boundaries get cut in half. The LLM gets incomplete information. Answers degrade at boundary points. | Overlap purpose | Without overlapping cargo edges, sentences get sliced in half and the donkey gets garbled backpacks |
| "Why use RecursiveCharacterTextSplitter instead of just slicing every 1000 chars?" | Blind slicing cuts words and sentences in half. Recursive splitter finds natural boundaries (paragraphs → sentences → words). | Smart splitting | Donkey-side view of "Why use RecursiveCharacterTextSplitter instead of just slicing every 1000 chars?" — affects how the donkey loads, reads, or delivers the cargo |
| "What happens if a PDF has tables?" | `pypdf` extracts table text as plain text — rows become lines, columns become spaces. Structure is mostly lost. This is a known limitation. | Document parsing | Post office sorting raw mail into GPS-labelled boxes before the donkey's first trip |
| "How is this different from an ETL pipeline?" | It's NOT different in structure. Extract (read file) → Transform (chunk + embed) → Load (store vectors). Only the transform step is AI-specific. | DE → AI bridge | backpack piece 📦 |
| "What's the most expensive step?" | Embedding is cheap ($0.00002/1K tokens). The expensive part is storing in OpenSearch (~$350/month minimum) and later sending chunks to the LLM for generation. | Cost awareness | GPS-stamping is cheap; the costly bits are warehouse rent (OpenSearch) and feeding the donkey hay |

- 🫏 **Donkey:** Sending the donkey on 25 standard test deliveries (golden dataset) to verify it returns the right packages every time.

---

## What to Study Next

You've now completed all 5 Phase 2 "bridge" files. You understand:
- ✅ The LLM interface and its concepts (#7)
- ✅ The concrete Bedrock implementation (#8)
- ✅ The vector store interface (#9)
- ✅ The concrete OpenSearch implementation (#10)
- ✅ The ingestion pipeline that ties them together (#11)

**Phase 3** is where data engineering ends and AI engineering begins:

- **File #12:** [`src/rag/prompts.py`](prompts-deep-dive.md) — prompt engineering (writing instructions that control the LLM's behaviour)
- **File #13:** [`src/rag/chain.py`](rag-chain-deep-dive.md) — the RAG orchestrator (the query pipeline: embed → search → generate)
- **File #14:** [`src/evaluation/evaluator.py`](evaluation-framework-deep-dive.md) — evaluation framework (measuring answer quality)
- **File #15:** [`src/evaluation/golden_dataset.py`](golden-dataset-deep-dive.md) — golden dataset (test fixtures for AI)
- **File #16:** [`src/monitoring/metrics.py`](metrics-deep-dive.md) — metrics and monitoring (token usage, cost, latency)

📖 **Related docs:**

- [RAG Concepts → Chunking](rag-concepts.md#what-is-chunking)
- [RAG Concepts → Chunks vs Vectors](rag-concepts.md#chunks-vs-vectors--the-key-distinction)
- [Documents Endpoint](../architecture-and-design/api-routes/documents-endpoint-explained.md)
- [The LLM Interface (file #7)](llm-interface-deep-dive.md)
- [The Vector Store Interface (file #9)](vectorstore-interface-deep-dive.md)

- 🫏 **Donkey:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
