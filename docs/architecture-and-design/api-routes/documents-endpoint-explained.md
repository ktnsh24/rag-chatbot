# Documents Endpoint — Deep Dive

> **Three endpoints for managing the knowledge base:**
> - `POST /api/documents/upload` — Upload and ingest a document
> - `GET /api/documents` — List all ingested documents
> - `DELETE /api/documents/{document_id}` — Remove a document

> **DE verdict: ★★★★☆ — The route is familiar, but the ingestion pipeline is new.**
> The upload endpoint triggers a 4-step AI pipeline inside `rag_chain.ingest_document()`.
> The list and delete endpoints are pure CRUD — nothing new there.

> **Related docs:**
> - [API Routes Overview](../api-routes-explained.md) — how all routes fit together
> - [Health Endpoint Deep Dive](health-endpoint-explained.md) — the simplest route ★☆☆☆☆
> - [Chat Endpoint Deep Dive](chat-endpoint-explained.md) — the RAG query route ★★★★★
> - [API Reference → Documents](../reference/api-reference.md) — request/response examples
> - [Pydantic Models → DocumentUploadResponse](../reference/pydantic-models.md) — model fields
> - [RAG Concepts](../ai-engineering/rag-concepts.md) — chunking and embeddings explained

---

## Table of Contents

- [Documents Endpoint — Deep Dive](#documents-endpoint--deep-dive)
  - [Table of Contents](#table-of-contents)
  - [What These Endpoints Do](#what-these-endpoints-do)
  - [Endpoint 1: Upload](#endpoint-1-upload)
    - [`POST /api/documents/upload`](#post-apidocumentsupload)
    - [Upload Request Flow](#upload-request-flow)
    - [Upload Part 1: The Route Layer](#upload-part-1-the-route-layer)
      - [File: `src/api/routes/documents.py`](#file-srcapiroutesdocumentspy)
      - [Module-level setup](#module-level-setup)
      - [File validation](#file-validation)
      - [Reading the file and checking rag\_chain](#reading-the-file-and-checking-rag_chain)
      - [THE AI CALL — this triggers the ingestion pipeline](#the-ai-call--this-triggers-the-ingestion-pipeline)
    - [Upload Part 2: The AI Pipeline](#upload-part-2-the-ai-pipeline)
    - [File: `src/rag/chain.py` → `RAGChain.ingest_document()`](#file-srcragchainpy--ragchainingest_document)
    - [Step 1: READ the Document](#step-1-read-the-document)
    - [Step 2: CHUNK the Text](#step-2-chunk-the-text)
    - [Step 3: EMBED Every Chunk](#step-3-embed-every-chunk)
    - [Step 4: STORE in the Vector Database](#step-4-store-in-the-vector-database)
    - [Upload Part 3: Back in the Route](#upload-part-3-back-in-the-route)
      - [Document registry](#document-registry)
      - [Error handling](#error-handling)
      - [Response](#response)
  - [Endpoint 2: List](#endpoint-2-list)
    - [`GET /api/documents`](#get-apidocuments)
  - [Endpoint 3: Delete](#endpoint-3-delete)
    - [`DELETE /api/documents/{document_id}`](#delete-apidocumentsdocument_id)
  - [The ETL Parallel](#the-etl-parallel)
  - [The Cost of Ingesting One Document](#the-cost-of-ingesting-one-document)
  - [What Could Go Wrong](#what-could-go-wrong)
  - [Self-Check Questions](#self-check-questions)
    - [Tier 1 — Must understand](#tier-1--must-understand)
    - [Tier 2 — Should understand](#tier-2--should-understand)
    - [Tier 3 — AI engineering territory](#tier-3--ai-engineering-territory)

---

## What These Endpoints Do

In plain English:

**Upload:** User sends a PDF/TXT/DOCX file → the app reads it, splits it into small
pieces (chunks), converts each piece into numbers (embeddings), and stores those
numbers in a vector database. Now when someone asks a question, the chat endpoint can
find these pieces by meaning.

**List:** User asks "what documents have I uploaded?" → returns the full list with
status and chunk counts.

**Delete:** User removes a document → deletes it from the registry (and eventually
from the vector store).

**DE parallel:** Upload is an ETL pipeline. Extract (read the file) → Transform
(chunk + embed) → Load (store in vector DB). List and Delete are standard CRUD.

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

---

## Endpoint 1: Upload

### `POST /api/documents/upload`

This is the second most important endpoint in the entire application (after `/chat`).
Before you can ask questions, you need to feed documents into the system. This
endpoint handles that.

### Upload Request Flow

```
User sends: POST /api/documents/upload
Content-Type: multipart/form-data
Body: file=@refund-policy.pdf
    │
    ▼
┌─── MIDDLEWARE ────────────────────────────────────────────────────────┐
│ CORSMiddleware → RequestLoggingMiddleware → Logs "[abc] → POST"      │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
    ▼
┌─── ROUTE: documents.py ─────────────────────────────────────────────────┐
│                                                                          │
│  1. Validate file extension (.pdf ✓, .exe ✗)                            │
│  2. Generate document_id (UUID)                                          │
│  3. Read file bytes from the upload                                      │
│  4. Check rag_chain exists on app.state                                  │
│                                                                          │
│  5. Call rag_chain.ingest_document(id, filename, bytes) ─────────┐      │
│                                                                   │      │
│  ┌─── RAG CHAIN: chain.py ─────────────────────────────────────┐  │      │
│  │                                                              │  │      │
│  │  Step 1: READ the document                                   │  │      │
│  │    read_document("refund-policy.pdf", raw_bytes)             │  │      │
│  │    → "Our refund policy states that... [Page 2] Returns..."  │  │      │
│  │            │                                                 │  │      │
│  │            ▼                                                 │  │      │
│  │  Step 2: CHUNK the text                                      │  │      │
│  │    chunk_document(text, chunk_size=1000, overlap=200)        │  │      │
│  │    → ["Our refund policy...", "Returns must be...", ...]     │  │      │
│  │    → 42 chunks                                               │  │      │
│  │            │                                                 │  │      │
│  │            ▼                                                 │  │      │
│  │  Step 3: EMBED every chunk                                   │  │      │
│  │    llm.get_embeddings_batch(42 chunks)                       │  │      │
│  │    → 42 vectors, each 1024/1536/768 numbers (depends on provider) │  │      │
│  │            │                                                 │  │      │
│  │            ▼                                                 │  │      │
│  │  Step 4: STORE in vector database                            │  │      │
│  │    vector_store.store_vectors(texts, embeddings, metadata)   │  │      │
│  │    → 42 documents indexed                                    │  │      │
│  │                                                              │  │      │
│  └──────────────────────────────────────────────────────────────┘  │      │
│                                                                   │      │
│  6. Create DocumentInfo record in registry ◄──────────────────────┘      │
│  7. Return DocumentUploadResponse (chunk_count=42, status=READY)         │
│                                                                          │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
    ▼
Response: {
    "document_id": "a1b2c3...",
    "filename": "refund-policy.pdf",
    "status": "ready",
    "chunk_count": 42,
    "message": "Successfully ingested refund-policy.pdf into 42 searchable chunks."
}
```

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

---

### Upload Part 1: The Route Layer

#### File: `src/api/routes/documents.py`

#### Module-level setup

```python
router = APIRouter()

# In-memory document registry (in production, this would be in DynamoDB/CosmosDB)
_documents: dict[str, DocumentInfo] = {}

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".docx"}
```

**What each line does:**

| Line | Purpose | DE parallel | 🫏 Donkey |
| --- | --- | --- | --- |
| `_documents: dict[str, DocumentInfo] = {}` | In-memory storage for document metadata | Like a cache dict — in prod you'd use DynamoDB | AWS depot 🏭 |
| `SUPPORTED_EXTENSIONS` | Allowlist of file types we can parse | Input validation — same as any upload endpoint | Stable door 🚪 |

**Why in-memory?** This is a portfolio project. In production, you'd store this in
DynamoDB (AWS) or CosmosDB (Azure) so it survives app restarts. The pattern is the
same — `_documents[id] = info` vs `dynamodb.put_item(item=info)`.

#### File validation

```python
    filename = file.filename or "unknown"
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )
```

**Step by step:**

1. `file.filename` — FastAPI's `UploadFile` gives you the original filename
2. `rsplit(".", 1)[-1]` — extract the extension ("pdf" from "refund-policy.pdf")
3. `.lower()` — normalise ("PDF" → "pdf")
4. Check against `SUPPORTED_EXTENSIONS` — reject anything we can't parse

**Why these specific formats?**

| Format | Parser used | Why supported | 🫏 Donkey |
| --- | --- | --- | --- |
| `.pdf` | `pypdf` (PdfReader) | Most common document format in enterprises | 🫏 On the route |
| `.txt` | Built-in `.decode("utf-8")` | Plain text, simplest case | 🫏 On the route |
| `.md` | Built-in `.decode("utf-8")` | Documentation, READMEs | 🫏 On the route |
| `.csv` | Built-in `.decode("utf-8")` | Tabular data (each row becomes text) | 🫏 On the route |
| `.docx` | `python-docx` | Microsoft Word — common in enterprises | 🫏 On the route |

**Not supported:** `.xlsx` (Excel), `.pptx` (PowerPoint), `.html` — each would need
its own parser. These could be added later.

#### Reading the file and checking rag_chain

```python
    document_id = str(uuid4())
    logger.info(f"[{document_id}] Uploading document: {filename}")

    content = await file.read()
    file_size = len(content)

    rag_chain = getattr(request.app.state, "rag_chain", None)
    if rag_chain is None:
        raise HTTPException(
            status_code=500,
            detail="RAG chain not initialized. Cannot ingest documents.",
        )
```

**What's happening:**

1. Generate a unique ID for this document (UUID)
2. `await file.read()` — read the entire file into memory as bytes
3. `len(content)` — track file size for the document registry
4. Check if the RAG chain exists (same pattern as the chat endpoint)

**DE parallel:** This is exactly what you'd do for any file upload endpoint:
generate an ID, read the bytes, check dependencies, proceed.

#### THE AI CALL — this triggers the ingestion pipeline

```python
    chunk_count = await rag_chain.ingest_document(
        document_id=document_id,
        filename=filename,
        content=content,
    )
```

**This single line triggers the entire 4-step AI pipeline.** Everything that happens
inside is explained in [Part 2](#upload-part-2-the-ai-pipeline) below.

---

### Upload Part 2: The AI Pipeline

### File: `src/rag/chain.py` → `RAGChain.ingest_document()`

When the route calls `rag_chain.ingest_document()`, four things happen in sequence.
Let's trace each step with a concrete example.

**Example document:** A 12-page PDF called `refund-policy.pdf` (~8000 words).

---

### Step 1: READ the Document

```python
# chain.py line
text = read_document(filename, content)
```

**What "read" means:**

The uploaded file is raw bytes. Before you can chunk it, you need to extract the
actual text content. Different file formats need different parsers.

**How it works under the hood:**

1. Your code calls `read_document("refund-policy.pdf", raw_bytes)`
2. This calls the function in `src/rag/ingestion.py`
3. It checks the file extension and routes to the right parser:

```python
def read_document(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()

    if extension == ".pdf":
        return _read_pdf(content)          # Uses pypdf
    elif extension in (".txt", ".md", ".csv"):
        return content.decode("utf-8")     # Direct decode
    elif extension == ".docx":
        return _read_docx(content)         # Uses python-docx
```

**For PDFs:**

```python
def _read_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))     # Parse the PDF bytes
    text_parts = []
    for page_num, page in enumerate(reader.pages, 1):
        page_text = page.extract_text() or ""   # Extract text from each page
        if page_text.strip():                    # Skip blank pages
            text_parts.append(f"[Page {page_num}]\n{page_text}")
    return "\n\n".join(text_parts)              # Join all pages with double newlines
```

**What comes out:**

```
Input:  b'%PDF-1.7...' (raw PDF bytes — binary, unreadable)

Output: "[Page 1]\nOur refund policy states that all purchases can be returned
         within 30 days...\n\n[Page 2]\nReturns must be initiated within...\n\n
         [Page 3]\nRefunds are processed within 14 business days..."

         → 8000 words of plain text
```

**DE parallel:** This is the **Extract** step in ETL. You read data from a source
format (PDF/CSV/DOCX) into a common format (plain text). Same as reading a CSV from
S3 and loading it into a Pandas DataFrame — the output format is always the same
regardless of input format.

| ETL Extract | RAG Extract | 🫏 Donkey |
| --- | --- | --- |
| Read CSV from S3 → DataFrame | Read PDF from upload → string | Parcel shelf 📦 |
| Read JSON from API → DataFrame | Read DOCX from upload → string | Stable door 🚪 |
| Read Parquet from S3 → DataFrame | Read TXT from upload → string | Parcel shelf 📦 |

**Why `[Page N]` markers?** When the document is later chunked, these markers help
track which page each chunk came from. This is how `page_number` ends up in the
search results (so the user knows "the answer came from page 3").

**Cost of this step:** $0 — pure Python computation, no API calls.

**Time:** ~10–100ms depending on document size and format.

---

### Step 2: CHUNK the Text

```python
# chain.py lines
chunks = chunk_document(
    text,
    chunk_size=self._settings.rag_chunk_size,    # default: 1000 chars
    chunk_overlap=self._settings.rag_chunk_overlap,  # default: 200 chars
)
```

**What "chunk" means:**

You now have one big string of text (e.g., 8000 words). But you can't store this as
one giant vector — it would be too vague to match specific questions. Instead, you
split it into small, focused pieces called **chunks**.

**How it works under the hood:**

```python
# ingestion.py
def chunk_document(text, chunk_size=1000, chunk_overlap=200):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)
```

This uses LangChain's `RecursiveCharacterTextSplitter`. Here's how it works:

**The algorithm — "split on the biggest break that fits":**

```
Try to split on "\n\n" (paragraph breaks) first
    → If a chunk is still too big, split on "\n" (line breaks)
        → If still too big, split on ". " (sentences)
            → If still too big, split on " " (words)
                → Last resort: split on "" (characters)
```

**Concrete example with a 12-page document:**

```
Full text: 8000 words (~32,000 characters)
chunk_size: 1000 characters
chunk_overlap: 200 characters

Result: 42 chunks

Chunk 1:  chars 0–1000     "Our refund policy states that all purchases..."
Chunk 2:  chars 800–1800   "...returned within 30 days. Returns must be..."
Chunk 3:  chars 1600–2600  "...initiated within the return window. Refunds are..."
...
Chunk 42: chars 31200–32000 "For international orders, the refund timeline..."
                 ↑
                 overlap zone (200 chars shared with previous chunk)
```

**Why chunk at all? (3 reasons)**

**Reason 1 — Precision:** If you embed the entire 12-page document as one vector,
the vector represents the "average meaning" of everything. A question about refunds
would get a mediocre score because the document also talks about shipping, warranties,
etc. Smaller chunks = more specific vectors = better matches.

```
Whole-document embedding:
    "refund policy" question → score 0.6 (doc is about many topics)

Chunk embedding:
    "refund policy" question → score 0.95 (chunk is specifically about refunds!)
```

**Reason 2 — Context window:** LLMs have a maximum input size. If you try to send 5
full documents (each 12 pages), that's 40,000 words ≈ 53,000 tokens. Claude's limit
is 200K tokens, but you'd be wasting money sending irrelevant content. With chunks,
you send only the 5 most relevant paragraphs — maybe 2,500 tokens total.

**Reason 3 — Cost:** Every token you send to the LLM costs money. Sending 5 small
chunks ($0.0065) is much cheaper than sending 5 full documents ($0.50+).

**Why overlap?**

Without overlap, a sentence at the boundary of two chunks gets split:

```
❌ No overlap:
    Chunk 1: "...returns must be initiated within"
    Chunk 2: "30 days of the original purchase."
    → Searching for "return window" finds neither chunk well

✅ With 200-char overlap:
    Chunk 1: "...returns must be initiated within 30 days of the original purchase."
    Chunk 2: "within 30 days of the original purchase. Refunds are processed..."
    → Searching for "return window" finds Chunk 1 with high score
```

**DE parallel:** This is the **Transform** step in ETL — but instead of cleaning
and aggregating data, you're splitting and sizing it. Think of it like partitioning
a large file into smaller files for parallel processing, but with overlapping
boundaries so you don't lose context at the edges.

| ETL Transform | RAG Transform (chunking) | 🫏 Donkey |
| --- | --- | --- |
| Split large CSV into 100 row batches | Split document into 1000 char chunks | Saddlebag piece 📦 |
| Partitioning with no overlap | Partitioning WITH overlap (200 chars) | Saddlebag piece 📦 |
| Purpose: parallel processing | Purpose: precise vector matching | GPS warehouse 🗺️ |

**Cost of this step:** $0 — pure Python computation, no API calls.

**Time:** ~5ms for a typical document.

---

### Step 3: EMBED Every Chunk

```python
# chain.py line
embeddings = await self._llm.get_embeddings_batch(chunks)
```

**What "embed" means:**

Each of the 42 text chunks needs to be converted into a vector (a list of
numbers — 1024 for AWS Titan, 1536 for Azure, or 768 for Local Ollama).
This is the same embedding process as in the chat endpoint's Step 1, but
applied to every chunk instead of just the question.

**How it works under the hood:**

1. Your code calls `self._llm.get_embeddings_batch(chunks)` — passes all 42 chunks
2. This calls `BedrockLLM.get_embeddings_batch()` in `src/llm/aws_bedrock.py`
3. Currently, Titan doesn't have a batch API, so it calls `get_embedding()` in a loop:
   ```python
   async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
       embeddings = []
       for text in texts:
           embedding = await self.get_embedding(text)  # One API call per chunk
           embeddings.append(embedding)
       return embeddings
   ```
4. Each call sends one chunk to Titan Embeddings v2 via `invoke_model()`
5. Each call returns 1024 floating-point numbers

**What happens for our 42 chunks:**

```
Chunk 1:  "Our refund policy states that..."    → [0.023, -0.841, 0.112, ..., 0.394]
Chunk 2:  "...returned within 30 days..."       → [0.021, -0.839, 0.115, ..., 0.401]
Chunk 3:  "Refunds are processed within..."     → [0.019, -0.835, 0.108, ..., 0.387]
...
Chunk 42: "For international orders..."         → [0.045, -0.722, 0.089, ..., 0.318]

→ 42 vectors, each with 1024 numbers
→ Total: 42 × 1024 = 43,008 floating-point numbers
```

**Why this matters:**

These vectors capture the *meaning* of each chunk. Later, when someone asks a question:
1. The question is also embedded → becomes a vector
2. The vector store compares the question vector against all 42 chunk vectors
3. The chunks with the most similar vectors are returned

**Chunks about similar topics will have similar vectors:**

```
"Our refund policy states..."     → [0.023, -0.841, ...]  ←┐
"Refunds are processed within..." → [0.019, -0.835, ...]  ←┤ Similar — both about refunds
                                                            │
"Shipping takes 3-5 days..."      → [0.567, 0.123, ...]   ← Different — about shipping
```

**DE parallel:** This is still the **Transform** step in ETL — but the second
transformation. First you chunked (split), now you embed (convert format). Think of
it like:

| ETL Transform | RAG Transform (embedding) | 🫏 Donkey |
| --- | --- | --- |
| Convert CSV strings to typed columns | Convert text chunks to number vectors | Saddlebag piece 📦 |
| Parse dates, cast integers | Run through neural network to get floats | 🫏 On the route |
| Output: structured rows | Output: vectors — 1024-dim (AWS Titan), 1536-dim (Azure), or 768-dim (Local Ollama) | The donkey 🐴 |
| Purpose: make data queryable by SQL | Purpose: make text searchable by meaning | 🫏 On the route |

**Cost of this step:**

Titan Embeddings v2 costs $0.00002 per 1K tokens.
- 42 chunks × ~200 tokens each = ~8400 tokens
- 8400 / 1000 × $0.00002 = **$0.000168** (less than 1 cent)
- Embedding is extremely cheap. The LLM generation (in chat) is what costs money.

**Time:** 42 API calls × ~50ms each = ~2100ms (~2 seconds). This is the slowest
step in ingestion. In production, you'd parallelise these calls.

> **☁️ Azure path — how batch embedding differs (this is a BIG difference):**
>
> On Azure, `self._llm.get_embeddings_batch()` routes to `AzureOpenAILLM.get_embeddings_batch()`
> in `src/llm/azure_openai.py`. The critical difference: **Azure sends all 42 chunks in
> ONE API call**.
>
> ```python
> # AWS path (sequential — 42 API calls)
> async def get_embeddings_batch(self, texts):
>     embeddings = []
>     for text in texts:                          # Loop: 1 call per chunk
>         embedding = await self.get_embedding(text)
>         embeddings.append(embedding)
>     return embeddings
>
> # Azure path (native batch — 1 API call)
> async def get_embeddings_batch(self, texts):
>     response = await self._client.embeddings.create(
>         model=self.embedding_deployment,
>         input=texts,                              # Send ALL 42 texts at once!
>     )
>     return [item.embedding for item in response.data]
> ```
>
> | Aspect | AWS (Titan) | Azure (text-embedding-3-small) |
> | --- | --- | --- |
> | **API calls for 42 chunks** | 42 sequential calls | **1 batch call** |
> | **Time** | ~2100ms (42 × 50ms) | **~100–200ms** (single round-trip) |
> | **Speedup** | — | **~10x faster** |
> | **Dimensions** | 1024 | 1536 |
> | **Total numbers stored** | 42 × 1024 = 43,008 | 42 × 1536 = **64,512** |
> | **Cost** | $0.000168 | $0.000168 (same price) |
>
> **DE parallel:** This is like batch INSERT (1 call) vs row-by-row INSERT (42 calls).
> Any DE knows batch operations are faster. The Titan SDK doesn't support batch
> embedding natively, so AWS requires a loop. Azure's OpenAI SDK handles it in one call.
>
> **This matters for production:** If you're ingesting 100 documents (4200 chunks),
> AWS takes ~210 seconds just for embeddings. Azure takes ~20 seconds. Same cost,
> 10x faster.

> **🏠 Local path — how batch embedding differs:**
>
> On Local, `self._llm.get_embeddings_batch()` routes to `OllamaLLM.get_embeddings_batch()`
> in `src/llm/local_ollama.py`. Ollama's `/api/embed` endpoint supports native batch:
>
> ```python
> # Local path (native batch — 1 HTTP call)
> async def get_embeddings_batch(self, texts):
>     response = await self._http.post(
>         f"{self.base_url}/api/embed",
>         json={"model": self.embedding_model, "input": texts},
>     )
>     return response.json()["embeddings"]
> ```
>
> | Aspect | AWS (Titan) | Azure (text-embedding-3) | Local (Ollama) |
> | --- | --- | --- | --- |
> | **API calls for 42 chunks** | 42 sequential | 1 batch | **1 batch** |
> | **Time** | ~2100ms | ~100–200ms | ~200–500ms |
> | **Dimensions** | 1024 | 1536 | 768 |
> | **Cost** | $0.000168 | $0.000168 | **$0** |

---

### Step 4: STORE in the Vector Database

```python
# chain.py lines
stored = await self._vector_store.store_vectors(
    document_id=document_id,
    document_name=filename,
    texts=chunks,
    embeddings=embeddings,
)
```

**What "store" means:**

You now have 42 text chunks and 42 corresponding vectors. This step saves them in
the vector store (OpenSearch, AI Search, or ChromaDB) so they can be searched later.

**How it works under the hood:**

1. Your code calls `self._vector_store.store_vectors(...)`
2. This calls `OpenSearchVectorStore.store_vectors()` in `src/vectorstore/aws_opensearch.py`
3. For each chunk, it creates an OpenSearch document:
   ```python
   for i, (text, embedding) in enumerate(zip(texts, embeddings)):
       doc = {
           "embedding": embedding,         # The 1024-number vector
           "text": text,                   # The original chunk text
           "document_id": document_id,     # Links back to the parent document
           "document_name": document_name, # "refund-policy.pdf"
           "chunk_index": i,               # Which chunk (0, 1, 2, ...)
           "page_number": metadata.get("page_number"),
       }
       self._client.index(
           index=self.index_name,
           body=doc,
           id=f"{document_id}_{i}",       # Unique ID: "abc123_0", "abc123_1", ...
       )
   ```
4. After all chunks are stored, it refreshes the index:
   ```python
   self._client.indices.refresh(self.index_name)
   ```
   This makes the new vectors searchable immediately.

**What gets stored in OpenSearch:**

```
Index: "rag-chatbot-vectors"

Document abc123_0:
{
    "embedding": [0.023, -0.841, 0.112, ..., 0.394],   ← 1024 numbers
    "text": "Our refund policy states that...",          ← Original text
    "document_id": "abc123",                             ← Parent document
    "document_name": "refund-policy.pdf",                ← Filename
    "chunk_index": 0,                                    ← Position in document
    "page_number": 1                                     ← Page in PDF
}

Document abc123_1:
{
    "embedding": [0.021, -0.839, 0.115, ..., 0.401],
    "text": "...returned within 30 days...",
    "document_id": "abc123",
    "document_name": "refund-policy.pdf",
    "chunk_index": 1,
    "page_number": 1
}

... (40 more documents)
```

**The OpenSearch index schema:**

```python
"mappings": {
    "properties": {
        "embedding": {
            "type": "knn_vector",          # Special vector type for similarity search
            "dimension": 1024,             # Matches Titan Embeddings output size
            "method": {
                "name": "hnsw",            # Algorithm: Hierarchical Navigable Small World
                "space_type": "cosinesimil", # Distance metric: cosine similarity
                "engine": "nmslib",        # Library: Non-Metric Space Library
            },
        },
        "text": {"type": "text"},          # Full-text searchable
        "document_id": {"type": "keyword"},# Exact match (for delete-by-document)
        "document_name": {"type": "keyword"},
        "page_number": {"type": "integer"},
        "chunk_index": {"type": "integer"},
    }
}
```

**What is HNSW?** It stands for "Hierarchical Navigable Small World" — an algorithm
that makes vector search fast. Without it, searching would require comparing the
query vector against every stored vector (slow for millions of vectors). HNSW builds
a graph structure that lets you jump to the most similar vectors in ~O(log N) time.

**DE parallel:** This is the **Load** step in ETL. You're writing transformed data
into a database. The difference is the data type — instead of rows in Redshift,
you're storing vectors in OpenSearch.

| ETL Load | RAG Load | 🫏 Donkey |
| --- | --- | --- |
| Write rows to Redshift | Write vectors to OpenSearch / Azure AI Search | AWS search hub 🔍 |
| CREATE TABLE with columns | CREATE INDEX with knn_vector mapping (AWS) or SearchIndex (Azure) | GPS warehouse 🗺️ |
| INSERT INTO table VALUES | `client.index(body=doc)` (AWS) or `upload_documents(batch)` (Azure) | AWS depot 🏭 |
| Each row has typed columns | Each doc has text + vector + metadata | GPS warehouse 🗺️ |
| Queried with SQL WHERE | Queried with k-NN vector search | GPS warehouse 🗺️ |

**Why `document_id` is stored with every chunk:**

Each chunk stores its parent `document_id`. This is important for:
1. **Delete:** When you delete a document, you need to delete all its chunks:
   `DELETE WHERE document_id = "abc123"` removes all 42 chunks at once
2. **Tracing:** When a search result comes back, you can show "this came from
   refund-policy.pdf" because the document name is stored alongside the vector

**Cost of this step:** OpenSearch charges per OCU-hour, not per document stored.
The marginal cost of storing 42 vectors is essentially $0.

**Time:** 42 index operations × ~10ms each = ~420ms.

> **☁️ Azure path — how vector storage differs:**
>
> On Azure, `self._vector_store.store_vectors()` routes to
> `AzureAISearchVectorStore.store_vectors()` in `src/vectorstore/azure_ai_search.py`.
>
> ```python
> # Azure — batch upload (up to 1000 docs per call)
> documents = []
> for i, (text, embedding) in enumerate(zip(texts, embeddings)):
>     documents.append({
>         "id": f"{document_id}_{i}",
>         "text": text,
>         "embedding": embedding,             # 1536-number vector
>         "document_id": document_id,
>         "document_name": document_name,
>         "chunk_index": i,
>         "page_number": metadata.get("page_number", 0),
>     })
>
> # Upload in batches of 1000 (Azure limit)
> batch_size = 1000
> for start in range(0, len(documents), batch_size):
>     batch = documents[start : start + batch_size]
>     self._search_client.upload_documents(batch)    # One call for all 42!
> ```
>
> | Aspect | AWS (OpenSearch) | Azure (AI Search) |
> | --- | --- | --- |
> | **Store method** | `client.index()` — one doc at a time | `upload_documents(batch)` — **up to 1000 at once** |
> | **Refresh needed** | Yes — `indices.refresh()` after writes | No — indexed immediately |
> | **Time (42 chunks)** | ~420ms (42 calls + refresh) | **~50ms** (1 batch call) |
> | **Vector dimensions** | 1024 (Titan) | 1536 (text-embedding-3-small) |
> | **Index config** | JSON mapping with `knn_vector` type, `nmslib` engine | Python SDK: `SearchField`, `HnswAlgorithmConfiguration` |
> | **Delete by document** | Term query + bulk delete | `filter="document_id eq 'abc123'"` + `delete_documents()` |
> | **Infra cost** | ~$350/month (2 OCU minimum) | **~$75/month** (Basic tier) |
>
> **Azure AI Search index schema** (for comparison with the OpenSearch schema above):
>
> ```python
> # Defined in _ensure_index() using typed Python objects
> fields = [
>     SimpleField(name="id", type=String, key=True),
>     SearchableField(name="text", type=String),
>     SimpleField(name="document_id", type=String, filterable=True),
>     SimpleField(name="document_name", type=String, filterable=True),
>     SimpleField(name="page_number", type=Int32, filterable=True),
>     SearchField(
>         name="embedding",
>         type=Collection(Single),              # Vector of floats
>         vector_search_dimensions=1536,         # Matches text-embedding-3-small
>         vector_search_profile_name="vector-profile",
>     ),
> ]
> ```
>
> **DE parallel:** OpenSearch `client.index()` one-by-one is like row-by-row INSERT.
> Azure `upload_documents(batch)` is like `COPY INTO` or bulk INSERT. Any DE knows
> which is faster.

---

### Upload Part 3: Back in the Route

After `rag_chain.ingest_document()` returns the chunk count, the route creates a
registry entry and returns the response.

#### Document registry

```python
    doc_info = DocumentInfo(
        document_id=document_id,
        filename=filename,
        status=DocumentStatus.READY,
        chunk_count=chunk_count,
        uploaded_at=datetime.now(timezone.utc),
        file_size_bytes=file_size,
    )
    _documents[document_id] = doc_info
```

**What each field means:**

| Field | Example | Purpose | 🫏 Donkey |
| --- | --- | --- | --- |
| `document_id` | `"a1b2c3d4-..."` | Unique identifier | 🫏 On the route |
| `filename` | `"refund-policy.pdf"` | Original filename | 🫏 On the route |
| `status` | `DocumentStatus.READY` | Lifecycle stage | 🫏 On the route |
| `chunk_count` | `42` | How many searchable pieces it became | Saddlebag piece 📦 |
| `uploaded_at` | `2026-04-07T10:30:00Z` | When it was uploaded | 🫏 On the route |
| `file_size_bytes` | `1048576` | File size (1 MB) | 🫏 On the route |

**Status lifecycle:**

```
User uploads file
    │
    ▼
PENDING  →  "Received, not yet processed"
    │
    ▼
PROCESSING  →  "Currently being chunked + embedded"
    │
    ├── Success → READY  →  "All chunks stored, searchable"
    │
    └── Failure → FAILED  →  "Something went wrong during ingestion"
```

Currently the code goes straight to READY because ingestion is synchronous (it waits
for all 4 steps to complete). In production, you'd make it async:
1. Return PENDING immediately
2. Process in the background (Lambda, Step Functions, Celery)
3. Update to READY when done

**DE parallel:** Same as tracking a batch job status — SUBMITTED → RUNNING → SUCCEEDED/FAILED.

#### Error handling

```python
    except Exception as e:
        logger.error(f"[{document_id}] Ingestion failed: {e}")
        _documents[document_id] = DocumentInfo(
            document_id=document_id,
            filename=filename,
            status=DocumentStatus.FAILED,
            chunk_count=0,
            uploaded_at=datetime.now(timezone.utc),
            file_size_bytes=0,
        )
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {e}")
```

**Key behaviour:** Even if ingestion fails, the document is recorded with `FAILED`
status. This way the user can see "I tried to upload refund-policy.pdf and it failed"
instead of it silently disappearing. They can then retry or investigate.

#### Response

```python
    return DocumentUploadResponse(
        document_id=document_id,
        filename=filename,
        status=DocumentStatus.READY,
        chunk_count=chunk_count,
        message=f"Successfully ingested {filename} into {chunk_count} searchable chunks.",
    )
```

The user gets back the document ID (to reference later), the chunk count (so they
know how many searchable pieces it became), and a human-readable message.

---

## Endpoint 2: List

### `GET /api/documents`

```python
@router.get("/documents", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    docs = list(_documents.values())
    return DocumentListResponse(documents=docs, total_count=len(docs))
```

**That's the entire endpoint.** Three lines of code.

1. Get all values from the in-memory dict
2. Wrap in a response model
3. Return

**DE parallel:** `SELECT * FROM documents` — nothing AI-specific here.

**Example response:**

```json
{
    "documents": [
        {
            "document_id": "a1b2c3...",
            "filename": "refund-policy.pdf",
            "status": "ready",
            "chunk_count": 42,
            "uploaded_at": "2026-04-07T10:30:00Z",
            "file_size_bytes": 1048576
        },
        {
            "document_id": "d4e5f6...",
            "filename": "faq.md",
            "status": "ready",
            "chunk_count": 5,
            "uploaded_at": "2026-04-07T11:00:00Z",
            "file_size_bytes": 4096
        }
    ],
    "total_count": 2
}
```

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

---

## Endpoint 3: Delete

### `DELETE /api/documents/{document_id}`

```python
@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, request: Request) -> dict:
    if document_id not in _documents:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

    doc = _documents[document_id]
    logger.info(f"Deleting document: {doc.filename} ({document_id})")

    # TODO: Delete from vector store and cloud storage
    del _documents[document_id]

    return {"message": f"Document '{doc.filename}' deleted successfully", "document_id": document_id}
```

**What it does:** Removes the document from the in-memory registry.

**What it SHOULD do (the TODO):** In a complete implementation, it would also:
1. Call `vector_store.delete_document(document_id)` — remove all 42 vectors from
   OpenSearch
2. Delete the original file from cloud storage (S3 / Blob Storage)
3. Then remove from the registry

Without step 1, the vectors are still in OpenSearch and will still appear in search
results. This is a known limitation documented in the code.

**DE parallel:** `DELETE FROM documents WHERE id = ?` + `DELETE FROM chunks WHERE document_id = ?`
— cascading deletes. Nothing AI-specific here.

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

---

## The ETL Parallel

This is the most important mental model for understanding document ingestion as a DE:

```
Traditional ETL Pipeline                    RAG Ingestion Pipeline
──────────────────────                      ──────────────────────

EXTRACT                                     EXTRACT (Step 1: READ)
  Read CSV from S3                            Read PDF from upload
  Read JSON from API                          Read DOCX from upload
  → Raw data in memory                        → Raw text in memory

TRANSFORM                                   TRANSFORM (Step 2: CHUNK + Step 3: EMBED)
  Clean: remove nulls, fix types              Chunk: split into 1000-char pieces
  Deduplicate: remove duplicates              Overlap: 200-char overlap at boundaries
  Aggregate: SUM, AVG, GROUP BY               Embed: convert each chunk → 1024-number vector
  → Structured, clean rows                    → Vectors that capture meaning

LOAD                                        LOAD (Step 4: STORE)
  Write to Redshift (columnar)                Write to OpenSearch (vector index)
  Write to DynamoDB (key-value)               Each doc = vector + text + metadata
  Create indexes for querying                 Create k-NN index for similarity search
  → Data ready for SQL queries                → Data ready for semantic search
```

**What's the same:**
- A pipeline with clear stages
- Input format varies, output format is standardised
- Errors at any stage should be handled and tracked
- You'd monitor throughput, latency, and failures

**What's different:**
- Transform doesn't clean data — it chunks and embeds
- Load isn't a SQL database — it's a vector store
- Querying isn't SQL WHERE — it's cosine similarity
- "Quality" isn't data completeness — it's embedding accuracy and chunk granularity

- 🫏 **Donkey:** Running multiple donkeys on the same route to confirm that AI engineering and data engineering practices mirror each other.

---

## The Cost of Ingesting One Document

For a 12-page PDF (~8000 words, ~42 chunks):

| Step | What happens | AWS cost | Azure cost | AWS time | Azure time | 🫏 Donkey |
| --- | --- | --- | --- | --- | --- | --- |
| 1. READ | Parse PDF → text | $0 | $0 | ~50ms | ~50ms | Free hay 🌿 |
| 2. CHUNK | Split into 42 pieces | $0 | $0 | ~5ms | ~5ms | Saddlebag piece 📦 |
| 3. EMBED | Convert chunks → vectors | $0.000168 (Titan, 42 calls) | $0.000168 (text-embedding-3-small, 1 call) | **~2100ms** | **~150ms** | GPS stamp 📍 |
| 4. STORE | Write to vector database | ~$0 (OpenSearch) | ~$0 (AI Search) | **~420ms** | **~50ms** | AWS search hub 🔍 |
| **Total per doc** | | **~$0.0002** | **~$0.0002** | **~2.6s** | **~0.25s** | Feed bill 🌾 |
| **Monthly infra** | | ~$350 (OpenSearch 2 OCU) | ~$75 (AI Search Basic) | — | — | AWS search hub 🔍 |

**Key insight:** Same cost, but **Azure is ~10x faster for ingestion** due to native
batch support in both embedding and storage. The per-document cost is negligible on
both clouds — the expensive part is the monthly infrastructure.

**Comparison with chat:** Ingesting a document costs $0.0002. Asking one question
costs $0.0065. After ~30 questions about that document, the query costs have exceeded
the ingestion cost 1000x.

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.

---

## What Could Go Wrong

| Error scenario | What happens | HTTP status | 🫏 Donkey |
| --- | --- | --- | --- |
| Unsupported file type (.exe, .xlsx) | Validation rejects before any AI call | `400` | 🫏 On the route |
| RAG chain not initialised | Route returns error immediately | `500` | Saddlebag check 🫏 |
| PDF is corrupted / unparseable | `read_document()` throws → caught by try/except | `500` | 🫏 On the route |
| PDF is scanned images (no text) | `read_document()` returns empty string → 0 chunks | `200` (with chunk_count=0) | Saddlebag piece 📦 |
| Embedding API fails (Bedrock / Azure OpenAI down) | Exception in Step 3 → document saved as FAILED | `500` | The donkey 🐴 |
| Vector store down (OpenSearch / Azure AI Search) | Exception in Step 4 → document saved as FAILED | `500` | AWS search hub 🔍 |
| File is too large (out of memory) | `await file.read()` fails → exception | `500` | Trip log 📒 |

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Self-Check Questions

### Tier 1 — Must understand

- [ ] What are the 4 steps of `rag_chain.ingest_document()`?
- [ ] What is chunking and why do you need it? (3 reasons)
- [ ] Why do chunks overlap?
- [ ] What does embedding do to a chunk?
- [ ] What is stored in OpenSearch for each chunk?

### Tier 2 — Should understand

- [ ] How does `RecursiveCharacterTextSplitter` decide where to split?
- [ ] Why is `chunk_size=1000` and `chunk_overlap=200` the default?
- [ ] What is HNSW and why does OpenSearch use it?
- [ ] Why is the document still saved with FAILED status when ingestion fails?
- [ ] What's missing in the delete endpoint? (vector store cleanup)

### Tier 3 — AI engineering territory

- [ ] What happens if chunk_size is too small (100 chars)? Too big (10000 chars)?
- [ ] How would you handle scanned PDFs (images, not text)?
- [ ] How would you make the 42 embedding API calls parallel instead of sequential?
- [ ] When would you make ingestion async (background job) instead of synchronous?
- [ ] How would you handle duplicate documents (re-uploading the same file)?

- 🫏 **Donkey:** A quick quiz for the trainee stable hand — answer these to confirm the key donkey delivery concepts have landed.
