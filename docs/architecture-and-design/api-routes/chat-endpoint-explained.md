# Chat Endpoint — Deep Dive

> `POST /api/chat` — Ask a question, get an AI-generated answer grounded in your documents.

> **DE verdict: ★★★★★ — This is where the AI lives.** The route code itself is
> standard FastAPI, but it triggers a 5-step AI pipeline inside `rag_chain.query()`.
> This document explains every step — from the HTTP request to the LLM response —
> including what happens inside the code you can't see from the route alone.

> **Related docs:**
> - [API Routes Overview](../api-routes-explained.md) — how all routes fit together
> - [Health Endpoint Deep Dive](health-endpoint-explained.md) — the simplest route ★☆☆☆☆
> - [Documents Endpoint Deep Dive](documents-endpoint-explained.md) — the ingestion route ★★★★☆
> - [API Reference → Chat](../reference/api-reference.md) — request/response examples
> - [Pydantic Models → ChatRequest/ChatResponse](../reference/pydantic-models.md) — model fields
> - [RAG Concepts](../ai-engineering/rag-concepts.md) — embeddings, vectors, chunking explained
> - [Cost Analysis](../ai-engineering/cost-analysis.md) — token costs and optimisation techniques

---

## Table of Contents

1. [What This Endpoint Does — The 30-Second Version](#what-this-endpoint-does)
2. [The Complete Request Flow (End to End)](#the-complete-request-flow)
3. [Part 1: The Route Layer — What chat.py Does](#part-1-the-route-layer)
4. [Part 2: The AI Pipeline — What rag_chain.query() Does](#part-2-the-ai-pipeline)
   - [Step 1: EMBED the Question](#step-1-embed-the-question)
   - [Step 2: SEARCH the Vector Store](#step-2-search-the-vector-store)
   - [Step 3: BUILD the Prompt](#step-3-build-the-prompt)
   - [Step 4: GENERATE the Answer](#step-4-generate-the-answer)
   - [Step 5: BUILD the Response](#step-5-build-the-response)
5. [Part 3: Back in the Route — Unpacking the Result](#part-3-back-in-the-route)
   - [Source Chunks — What They Are and Why They Matter](#source-chunks)
   - [Token Usage — Why You Track Every Token](#token-usage)
   - [Metrics — Monitoring the AI Pipeline](#metrics)
   - [Building the Final Response](#building-the-final-response)
6. [The Cost of One Chat Request](#the-cost-of-one-chat-request)
7. [DE vs AI Engineer — What Each Sees in This Route](#de-vs-ai-engineer)
8. [What Could Go Wrong — Error Scenarios](#what-could-go-wrong)
9. [Self-Check Questions](#self-check-questions)

---

## What This Endpoint Does

In plain English:

1. User sends a question: *"What is the refund policy?"*
2. The app finds the most relevant paragraphs from uploaded documents
3. The app sends those paragraphs + the question to an AI model (Claude/GPT-4)
4. The AI writes an answer based **only** on those paragraphs
5. The app returns the answer, the source paragraphs, and the cost

**DE parallel:** Think of it as a search engine + a writer combined:
- **Search:** Find the 5 most relevant rows in a database (but by *meaning*, not by SQL WHERE)
- **Writer:** Feed those rows to an AI that writes a human-readable summary

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

---

## The Complete Request Flow

This is what happens from the moment the HTTP request hits the server to the moment
the response goes back. Every box below is explained in detail in this document.

```
User sends: POST /api/chat
Body: { "question": "What is the refund policy?", "top_k": 5 }
    │
    ▼
┌─── MIDDLEWARE ────────────────────────────────────────────────────────┐
│ CORSMiddleware → RequestLoggingMiddleware → Logs "[abc] → POST"      │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
    ▼
┌─── ROUTE: chat.py ───────────────────────────────────────────────────┐
│                                                                       │
│  1. Pydantic validates ChatRequest (question min 1 char, max 5000)    │
│  2. Start timer                                                       │
│  3. Check rag_chain exists on app.state                               │
│  4. Determine session_id and top_k                                    │
│                                                                       │
│  5. Call rag_chain.query(question, session_id, top_k) ──────────┐    │
│                                                                  │    │
│  ┌─── RAG CHAIN: chain.py ────────────────────────────────────┐  │    │
│  │                                                             │  │    │
│  │  Step 1: EMBED the question                                 │  │    │
│  │    llm.get_embedding("What is the refund policy?")          │  │    │
│  │    → [0.023, -0.841, 0.112, ..., 0.394]  (1024 numbers)    │  │    │
│  │            │                                                │  │    │
│  │            ▼                                                │  │    │
│  │  Step 2: SEARCH the vector store                            │  │    │
│  │    vector_store.search(query_embedding, top_k=5)            │  │    │
│  │    → 5 VectorSearchResult objects (text + score + metadata) │  │    │
│  │            │                                                │  │    │
│  │            ▼                                                │  │    │
│  │  Step 3: BUILD prompt with context                          │  │    │
│  │    context_texts = [result.text for result in results]      │  │    │
│  │            │                                                │  │    │
│  │            ▼                                                │  │    │
│  │  Step 4: GENERATE answer                                    │  │    │
│  │    llm.generate(question, context_texts)                    │  │    │
│  │    → LLMResponse(text="Refunds are...", tokens=1430)        │  │    │
│  │            │                                                │  │    │
│  │            ▼                                                │  │    │
│  │  Step 5: BUILD response dict                                │  │    │
│  │    → { answer, sources, token_usage }                       │  │    │
│  │                                                             │  │    │
│  └─────────────────────────────────────────────────────────────┘  │    │
│                                                                  │    │
│  6. Unpack result → build SourceChunk models   ◄─────────────────┘    │
│  7. Build TokenUsage model                                            │
│  8. Record metrics                                                    │
│  9. Build ChatResponse and return                                     │
│                                                                       │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
    ▼
┌─── MIDDLEWARE ────────────────────────────────────────────────────────┐
│ RequestLoggingMiddleware → Logs "[abc] ← 200 (450ms)"                │
│ Adds headers: X-Request-ID, X-Latency-Ms                            │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
    ▼
Response: {
    "answer": "According to the policy document, refunds are processed within 14 days...",
    "sources": [{ "document_name": "refund-policy.pdf", "relevance_score": 0.95, ... }],
    "token_usage": { "input_tokens": 1250, "output_tokens": 180, "cost": 0.0065 },
    "latency_ms": 450
}
```

- 🫏 **Donkey:** The step-by-step route map showing every checkpoint the donkey passes from question intake to answer delivery.

---

## Part 1: The Route Layer

### File: `src/api/routes/chat.py`

The route itself is standard FastAPI. It does 9 things:

#### 1. Pydantic validates the request (automatic — you don't write this code)

```python
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
```

When FastAPI sees `body: ChatRequest`, it automatically:
1. Reads the JSON body from the HTTP request
2. Passes it to `ChatRequest(**body_dict)`
3. Pydantic validates every field:
   - `question` must be a string, 1–5000 characters
   - `session_id` is optional (will be `None` if missing)
   - `top_k` is optional, must be 1–20 if provided
4. If validation fails → FastAPI returns `422 Unprocessable Entity` automatically

**DE parallel:** Same as any FastAPI route. You never write the validation logic
yourself — Pydantic does it.

#### 2–3. Start timer + check rag_chain

```python
    start_time = time.time()
    settings = get_settings()
    request_id = uuid4()

    logger.info(f"[{request_id}] Chat request: {body.question[:100]}...")

    rag_chain = getattr(request.app.state, "rag_chain", None)
    if rag_chain is None:
        raise HTTPException(
            status_code=500,
            detail="RAG chain not initialized. Check your cloud credentials and restart the app.",
        )
```

**What each line does:**

| Line | Purpose | 🫏 Donkey |
| --- | --- | --- |
| `start_time = time.time()` | Start a stopwatch to measure total latency | Feed bill 🌾 |
| `settings = get_settings()` | Load config (for default `top_k`, cloud provider, etc.) | 🫏 On the route |
| `request_id = uuid4()` | Generate unique ID for this request (for log tracing) | 🫏 On the route |
| `body.question[:100]` | Log only first 100 chars of question (privacy + log size) | 🫏 On the route |
| `getattr(..., None)` | Safely get rag_chain — returns None if it failed to init | Saddlebag check 🫏 |
| `raise HTTPException(500)` | If rag_chain is None, tell the user the system is broken | Saddlebag check 🫏 |

#### 4. Determine session_id and top_k

```python
    session_id = body.session_id or str(uuid4())
    top_k = body.top_k or settings.rag_top_k
```

| Variable | If user provided it | If user didn't provide it | 🫏 Donkey |
| --- | --- | --- | --- |
| `session_id` | Use theirs (for multi-turn conversations) | Generate a new UUID (new conversation) | Trip log 📒 |
| `top_k` | Use theirs (1–20) | Use default from settings (usually 5) | 🫏 On the route |

**What is `top_k`?** It's how many document chunks to retrieve from the vector store.
More chunks = more context for the LLM = better answers, but also more tokens = higher cost.

**DE parallel:** `top_k` is like `LIMIT 5` in SQL. "Give me the top 5 most relevant results."

#### 5. THE AI CALL — this is where the magic happens

```python
    result = await rag_chain.query(
        question=body.question,
        session_id=session_id,
        top_k=top_k,
    )
```

**This single line triggers the entire 5-step AI pipeline.** Everything that happens
inside is explained in [Part 2](#part-2-the-ai-pipeline) below.

**DE parallel:** This is like calling `await pipeline.run(input_data)` — a single
function that orchestrates multiple steps (extract, transform, load). Here it's
embed, search, generate.

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

---

## Part 2: The AI Pipeline

### File: `src/rag/chain.py` → `RAGChain.query()`

When the route calls `rag_chain.query()`, five things happen in sequence. Let's
trace each step with a concrete example.

**Example question:** *"What is the refund policy?"*

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

### Step 1: EMBED the Question

```python
# chain.py line
query_embedding = await self._llm.get_embedding(question)
```

**What "embed" means:**

The question is text. The vector store stores numbers. You can't compare text to
numbers. So first, you convert the text into numbers — specifically, a list of
1024 floating-point numbers called an **embedding vector**.

```
Input:  "What is the refund policy?"  (a string — 6 words)
    │
    ▼
Amazon Titan Embeddings v2 model (on AWS Bedrock)
    │
    ▼
Output: [0.023, -0.841, 0.112, 0.567, ..., 0.394]  (1024 numbers)
```

**How does it work under the hood?**

1. Your code calls `self._llm.get_embedding("What is the refund policy?")`
2. This calls `BedrockLLM.get_embedding()` in `src/llm/aws_bedrock.py`
3. That calls `self._runtime_client.invoke_model()` — a boto3 call to AWS Bedrock
4. AWS Bedrock runs the Titan Embeddings v2 model on a GPU
5. The model has been trained on billions of sentences to understand meaning
6. It outputs 1024 numbers that represent the *meaning* of your question
7. Those numbers come back as `list[float]`

**The key insight:** Sentences with similar meaning get similar numbers.

```
"What is the refund policy?"         → [0.023, -0.841, 0.112, ...]
"How do I get a refund?"             → [0.021, -0.839, 0.115, ...]  ← VERY similar
"Tell me about return procedures"    → [0.019, -0.835, 0.108, ...]  ← Similar
"What color is the sky?"             → [0.891, 0.234, -0.567, ...]  ← COMPLETELY different
```

**DE parallel:** Think of it like a hash function, but for meaning instead of
uniqueness. A hash function turns data into a fixed-size number for deduplication.
An embedding turns text into a fixed-size vector for meaning comparison.

| Concept | Hash function | Embedding function | 🫏 Donkey |
| --- | --- | --- | --- |
| **Input** | Any data | Text | 🫏 On the route |
| **Output** | Fixed-size number | Fixed-size vector (1024 numbers) | GPS warehouse 🗺️ |
| **Purpose** | Check if two things are identical | Check if two things mean the same | 🫏 On the route |
| **Similar input** | Completely different hash | Similar vector | GPS warehouse 🗺️ |
| **Example** | `md5("hello") → 5d41...` | `embed("hello") → [0.1, 0.2, ...]` | 🫏 On the route |

**Cost of this step:** Extremely cheap. Titan Embeddings costs $0.00002 per 1K tokens.
For a 10-word question (~13 tokens), this costs $0.00000026 — essentially free.

**Time:** ~50ms (one network round-trip to Bedrock).

> **☁️ Azure path — how embedding differs:**
>
> On Azure, the same `self._llm.get_embedding()` call routes to `AzureOpenAILLM.get_embedding()`
> in `src/llm/azure_openai.py`. Here's what changes:
>
> | Aspect | AWS | Azure |
> | --- | --- | --- |
> | **Class** | `BedrockLLM` | `AzureOpenAILLM` |
> | **SDK** | `boto3` (`invoke_model`) | `openai` (`AsyncAzureOpenAI`) |
> | **Model** | Amazon Titan Embeddings v2 | text-embedding-3-small |
> | **Dimensions** | 1024 | **1536** (50% more numbers per vector) |
> | **Auth** | IAM roles / SigV4 | API key or Managed Identity |
> | **API call** | `self._runtime_client.invoke_model(body=json)` | `self._client.embeddings.create(model=..., input=text)` |
> | **Cost** | $0.00002 / 1K tokens | $0.00002 / 1K tokens (same) |
>
> **The 1536 vs 1024 dimension difference matters** — it means the vector store
> index schema must match the embedding model. You can't embed with Titan (1024)
> and search in an Azure AI Search index configured for 1536 dimensions. The
> factory pattern in `main.py` ensures the right LLM + vector store pair is created
> together.
>
> ```
> AWS:   "What is the refund policy?" → Titan → [0.023, -0.841, ..., 0.394]  (1024 numbers)
> Azure: "What is the refund policy?" → text-embedding-3-small → [0.018, -0.792, ..., 0.412, ..., 0.203]  (1536 numbers)
> ```

> **🏠 Local path — how embedding differs:**
>
> On Local, the same `self._llm.get_embedding()` call routes to `OllamaLLM.get_embedding()`
> in `src/llm/local_ollama.py`. Instead of a cloud SDK, it uses plain HTTP:
>
> | Aspect | AWS | Azure | Local |
> | --- | --- | --- | --- |
> | **Class** | `BedrockLLM` | `AzureOpenAILLM` | `OllamaLLM` |
> | **SDK** | `boto3` | `openai` | `httpx` (plain HTTP) |
> | **Model** | Amazon Titan v2 | text-embedding-3-small | nomic-embed-text |
> | **Dimensions** | 1024 | 1536 | **768** |
> | **Auth** | IAM roles | API key | None (localhost) |
> | **API call** | `invoke_model(body=json)` | `embeddings.create(...)` | `POST /api/embed` |
> | **Cost** | $0.00002 / 1K tokens | $0.00002 / 1K tokens | **$0** |
>
> ```
> Local: "What is the refund policy?" → nomic-embed-text → [0.031, -0.654, ..., 0.187]  (768 numbers)
> ```

---

### Step 2: SEARCH the Vector Store

```python
# chain.py line
search_results = await self._vector_store.search(
    query_embedding=query_embedding,
    top_k=k,
)
```

**What "search" means:**

Now you have a vector (1024 numbers) representing the question's meaning. The
vector store has thousands of vectors (one per document chunk) that were stored
during ingestion. This step finds the `top_k` (e.g., 5) chunks whose vectors are
most similar to the question vector.

```
Question vector: [0.023, -0.841, 0.112, ...]
    │
    ▼
OpenSearch k-NN search
    │
    ├── Compare against Chunk 1 vector → similarity = 0.95 ← HIGH
    ├── Compare against Chunk 2 vector → similarity = 0.91 ← HIGH
    ├── Compare against Chunk 3 vector → similarity = 0.88
    ├── Compare against Chunk 4 vector → similarity = 0.72
    ├── Compare against Chunk 5 vector → similarity = 0.65
    ├── Compare against Chunk 6 vector → similarity = 0.31 ← LOW (not returned)
    ├── ... (hundreds more chunks)
    │
    ▼
Returns top 5: [Chunk1(0.95), Chunk2(0.91), Chunk3(0.88), Chunk4(0.72), Chunk5(0.65)]
```

**How does it work under the hood?**

1. Your code calls `self._vector_store.search(query_embedding, top_k=5)`
2. This calls `OpenSearchVectorStore.search()` in `src/vectorstore/aws_opensearch.py`
3. That sends a k-NN (k-nearest-neighbours) query to OpenSearch:
   ```python
   body = {
       "size": top_k,
       "query": {
           "knn": {
               "embedding": {
                   "vector": query_embedding,
                   "k": top_k,
               }
           }
       },
   }
   ```
4. OpenSearch uses the HNSW algorithm to efficiently find the closest vectors
5. "Closest" is measured by **cosine similarity** — how similar the directions are

**Cosine similarity explained with a DE analogy:**

```
Imagine two columns in a spreadsheet, each with 1024 numbers.
Cosine similarity measures "are these two columns pointing in the same direction?"

Score 1.0 = identical direction (identical meaning)
Score 0.0 = perpendicular (unrelated)
Score -1.0 = opposite direction (opposite meaning — rare in practice)
```

In practice:
- 0.90+ = highly relevant (this chunk definitely answers the question)
- 0.70–0.89 = relevant (useful context)
- 0.50–0.69 = somewhat relevant (might help, might not)
- Below 0.50 = probably noise

> **☁️ Azure path — how search differs:**
>
> On Azure, the same `self._vector_store.search()` call routes to
> `AzureAISearchVectorStore.search()` in `src/vectorstore/azure_ai_search.py`.
>
> Instead of a raw k-NN JSON body, Azure uses typed Python objects:
>
> ```python
> # Azure AI Search query (Python SDK)
> vector_query = VectorizedQuery(
>     vector=query_embedding,
>     k_nearest_neighbors=top_k,
>     fields="embedding",
> )
> results = self._search_client.search(
>     search_text=None,          # No keyword search — pure vector
>     vector_queries=[vector_query],
>     top=top_k,
> )
> ```
>
> Compare with the OpenSearch approach:
>
> | Aspect | AWS (OpenSearch) | Azure (AI Search) |
> | --- | --- | --- |
> | **SDK** | `opensearch-py` | `azure-search-documents` |
> | **Query format** | Raw JSON body with `knn.embedding.vector` | `VectorizedQuery` Python object |
> | **Algorithm** | HNSW via nmslib engine | HNSW (built-in) |
> | **Score field** | `_score` | `@search.score` |
> | **Hybrid search** | Requires custom scripting | Native — just set `search_text` alongside `vector_queries` |
> | **Infra cost** | ~$350/month (2 OCU minimum) | ~$75/month (Basic tier) |
>
> **Same result:** Both return a ranked list of `VectorSearchResult` objects with
> text, score, document_name, and metadata. The route layer doesn't know which
> cloud ran the search.
>
> **Bonus — Azure hybrid search:** Azure AI Search can combine vector search with
> keyword search in one query. You'd set `search_text="refund policy"` alongside
> `vector_queries` to get results that are both semantically AND textually relevant.
> OpenSearch can do this too, but requires more manual setup.

> **🏠 Local path — how search differs:**
>
> On Local, the same `self._vector_store.search()` call routes to
> `ChromaDBVectorStore.search()` in `src/vectorstore/local_chromadb.py`.
>
> ```python
> # ChromaDB query (Python SDK)
> results = self._collection.query(
>     query_embeddings=[query_embedding],
>     n_results=top_k,
> )
> ```
>
> | Aspect | AWS (OpenSearch) | Azure (AI Search) | Local (ChromaDB) |
> | --- | --- | --- | --- |
> | **SDK** | `opensearch-py` | `azure-search-documents` | `chromadb` |
> | **Query format** | Raw JSON body | `VectorizedQuery` object | `collection.query()` |
> | **Algorithm** | HNSW via nmslib | HNSW (built-in) | HNSW (built-in) |
> | **Storage** | Managed cloud service | Managed cloud service | In-memory or SQLite |
> | **Infra cost** | ~$350/month | ~$75/month | **$0** |
>
> **Same result:** All three return ranked `VectorSearchResult` objects. The route
> layer doesn't know which backend ran the search.

**What each search result contains:**

```python
@dataclass
class VectorSearchResult:
    text: str              # The actual chunk text ("Refunds are processed within 14 days...")
    document_name: str     # "refund-policy.pdf"
    score: float           # 0.95
    page_number: int | None  # 3
    metadata: dict         # {"document_id": "abc", "chunk_index": 7}
```

**DE parallel:** This is like `SELECT text, document_name, score FROM chunks ORDER BY similarity(embedding, ?) DESC LIMIT 5`. But instead of SQL, it's a vector similarity search. Instead of exact matching (`WHERE column = value`), it's meaning matching ("find rows that *mean* something similar").

| SQL query | Vector search | 🫏 Donkey |
| --- | --- | --- |
| `WHERE title = 'refund policy'` | Find vectors similar to embed("refund policy") | GPS warehouse 🗺️ |
| Exact string match | Meaning match | 🫏 On the route |
| Returns rows where title equals exactly | Returns chunks that are *about* refunds | Saddlebag piece 📦 |
| Misses "return procedure" (different words) | Finds "return procedure" (same meaning!) | 🫏 On the route |

**This is the key breakthrough of RAG:** It finds relevant documents by meaning, not
by keywords. A user asking "How do I get my money back?" will find a document titled
"Refund Policy" — even though they share zero words.

**Cost of this step:** OpenSearch charges per OCU-hour, not per query. The marginal
cost of one search is essentially $0.

**Time:** ~30ms (one network round-trip to OpenSearch).

**What if no results are found?**

```python
if not search_results:
    return {
        "answer": "I don't have any documents to answer your question. Please upload documents first.",
        "sources": [],
        "token_usage": None,
    }
```

If the vector store is empty (no documents have been ingested), the chain returns a
helpful error message without calling the LLM. This saves money — no LLM call means
no tokens means no cost.

---

### Step 3: BUILD the Prompt

```python
# chain.py line
context_texts = [result.text for result in search_results]
```

**What "build the prompt" means:**

You now have the question and the 5 most relevant document chunks. Before sending
them to the LLM, you combine them into a **prompt** — the full text that the LLM
will read.

In `chain.py` this looks simple — just extract the text from each result. But inside
`llm.generate()` (the next step), the prompt gets assembled like this:

```
┌─── System Prompt (instructions for the LLM) ──────────────────────────────┐
│ "You are a helpful assistant that answers questions based on the           │
│  provided context."                                                        │
│ "Rules: 1. ONLY use information from the context..."                       │
│ "2. If the context doesn't contain the answer, say so..."                  │
│ "3. Cite which document(s) you used..."                                    │
└────────────────────────────────────────────────────────────────────────────┘

┌─── User Message (question + context) ──────────────────────────────────────┐
│ "Context:                                                                  │
│                                                                            │
│  [Document chunk 1]:                                                       │
│  Our refund policy states that all purchases can be returned within        │
│  30 days of the original purchase date. The item must be in its original   │
│  packaging and unused condition...                                         │
│                                                                            │
│  ---                                                                       │
│                                                                            │
│  [Document chunk 2]:                                                       │
│  Refunds are processed within 14 business days of receiving the returned   │
│  item. The refund will be issued to the original payment method...         │
│                                                                            │
│  ---                                                                       │
│                                                                            │
│  [Document chunk 3]:                                                       │
│  For international orders, the refund timeline may be extended by an       │
│  additional 5-7 business days due to currency conversion...                │
│                                                                            │
│  ---                                                                       │
│                                                                            │
│  [Document chunk 4]:                                                       │
│  Digital purchases (e-books, software licenses) are non-refundable         │
│  after download. Contact support for exceptions...                         │
│                                                                            │
│  ---                                                                       │
│                                                                            │
│  [Document chunk 5]:                                                       │
│  Customers who purchased items during a promotional sale may receive       │
│  store credit instead of a cash refund, depending on the promotion terms...│
│                                                                            │
│  Question: What is the refund policy?"                                     │
└────────────────────────────────────────────────────────────────────────────┘
```

**DE parallel:** Think of this like building a SQL query from parts:

```
Traditional:  Build a SQL query → send to database → get rows back
RAG:          Build a text prompt → send to LLM → get answer back
```

The "prompt" is to an LLM what a "query" is to a database. The quality of the prompt
determines the quality of the answer, just like the quality of your SQL determines
the quality of your query results.

**Why the system prompt matters:**

The system prompt is like the LLM's job description. Without rules, the LLM might:
- Make up information not in the context (hallucinate)
- Forget to cite sources
- Give a 2000-word answer when a bullet list would be better

The rules force the LLM to:
1. **ONLY** use the provided context (no hallucination)
2. Say "I don't know" if the context doesn't cover it (honesty)
3. Cite `[Document chunk N]` (traceability)
4. Use bullet points (readability)

**Cost of this step:** $0 — this is just string concatenation in Python. No API calls.

**Time:** <1ms.

---

### Step 4: GENERATE the Answer

```python
# chain.py line
llm_response = await self._llm.generate(
    prompt=question,
    context=context_texts,
)
```

**What "generate" means:**

This is the actual AI call. You send the assembled prompt to a Large Language Model
(Claude on AWS, GPT-4o on Azure), and it generates a human-readable answer.

**How it works under the hood (AWS path):**

1. Your code calls `self._llm.generate(prompt, context)`
2. This calls `BedrockLLM.generate()` in `src/llm/aws_bedrock.py`
3. That builds the system prompt and user message (see Step 3)
4. Then calls `self._runtime_client.converse()` — a boto3 call to AWS Bedrock:
   ```python
   response = self._runtime_client.converse(
       modelId=self.model_id,                    # "anthropic.claude-3-5-sonnet-..."
       messages=[{"role": "user", "content": [{"text": user_message}]}],
       system=[{"text": system_prompt}],
       inferenceConfig={
           "maxTokens": 2048,       # Maximum answer length
           "temperature": 0.1,      # Low = factual, High = creative
           "topP": 0.9,             # Nucleus sampling parameter
       },
   )
   ```
5. AWS Bedrock sends this to the Claude model running on AWS GPUs
6. Claude reads the system prompt, reads the context chunks, reads the question
7. Claude generates an answer token by token (like typing one word at a time)
8. The full answer comes back as a string

**What the parameters mean:**

| Parameter | Value | What it does | DE parallel | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| `modelId` | `anthropic.claude-3-5-sonnet-...` | Which AI model to use | Like choosing which database engine (Postgres vs MySQL) | The donkey 🐴 |
| `maxTokens` | `2048` | Maximum answer length (~1500 words) | Like `LIMIT` on output size | Cargo unit ⚖️ |
| `temperature` | `0.1` | How deterministic vs creative (0.0–1.0) | No real parallel — unique to AI | 🫏 On the route |
| `topP` | `0.9` | Probability threshold for word choices | No real parallel — unique to AI | 🫏 On the route |

**Temperature explained:**

```
temperature = 0.0 → Always picks the most likely next word
    "The refund policy states that..." → deterministic, repeatable

temperature = 0.1 → Almost always the most likely (our setting)
    Good for factual answers — slight variation but stays on topic

temperature = 0.7 → More variety in word choices
    Better for creative writing, brainstorming

temperature = 1.0 → Maximum randomness
    Unpredictable, might go off-topic
```

We use 0.1 because RAG needs **factual, grounded answers** — not creative writing.
The answer should come from the documents, not from the LLM's imagination.

**What comes back:**

```python
@dataclass
class LLMResponse:
    text: str          # "According to the policy document, refunds are processed within 14..."
    input_tokens: int  # 1250 (how many tokens the prompt was)
    output_tokens: int # 180 (how many tokens the answer was)
    model_id: str      # "anthropic.claude-3-5-sonnet-20241022-v2:0"
```

**DE parallel:** This is like calling an external API — you send a request (the prompt),
you get a response (the answer), and you get metadata (how much it cost in tokens).
Like calling the Google Maps API and getting back a route + the number of API units consumed.

**Cost of this step:** This is the most expensive step.
- Input tokens: ~1250 × $0.003/1K = $0.00375
- Output tokens: ~180 × $0.015/1K = $0.00270
- **Total: ~$0.0065 per question** (~€0.006)

**Time:** ~300–400ms (the LLM needs time to "think" and generate text).

> **☁️ Azure path — how generation differs:**
>
> On Azure, `self._llm.generate()` calls `AzureOpenAILLM.generate()` in
> `src/llm/azure_openai.py`. Instead of Bedrock's `converse()` API, it uses the
> standard OpenAI ChatCompletion API:
>
> ```python
> # Azure OpenAI call (standard OpenAI SDK)
> response = await self._client.chat.completions.create(
>     model=self.deployment_name,               # "gpt-4o" (your deployment label)
>     messages=[
>         {"role": "system", "content": system_prompt},
>         {"role": "user", "content": user_message},
>     ],
>     temperature=0.1,
>     max_tokens=2048,
>     top_p=0.9,
> )
> ```
>
> | Aspect | AWS (Bedrock) | Azure (OpenAI) |
> | --- | --- | --- |
> | **Model** | Claude 3.5 Sonnet (Anthropic) | GPT-4o (OpenAI) |
> | **SDK** | `boto3` → `converse()` | `openai` → `chat.completions.create()` |
> | **Model identifier** | `modelId="anthropic.claude-3-5-sonnet-..."` (full ARN) | `model="gpt-4o"` (your deployment name) |
> | **Message format** | `messages=[{"role":"user","content":[{"text":...}]}]` | `messages=[{"role":"user","content":"..."}]` |
> | **Token fields** | `inputTokens` / `outputTokens` | `prompt_tokens` / `completion_tokens` |
> | **Input cost** | $0.003 / 1K tokens | $0.0025 / 1K tokens |
> | **Output cost** | $0.015 / 1K tokens | $0.01 / 1K tokens |
> | **Cost per query** | ~$0.0065 | **~$0.005** (23% cheaper) |
>
> **Key takeaway:** Azure/GPT-4o is cheaper per query. But model quality
> varies — Claude tends to follow instructions more precisely, GPT-4o tends to be
> more creative. For RAG (factual, grounded answers), both work well at
> temperature 0.1. The choice is usually driven by which cloud your company uses,
> not model quality.

> **🏠 Local path — how generation differs:**
>
> On Local, `self._llm.generate()` calls `OllamaLLM.generate()` in
> `src/llm/local_ollama.py`. It uses plain HTTP to the Ollama REST API:
>
> ```python
> # Ollama call (plain httpx)
> response = await self._http.post(
>     f"{self.base_url}/api/chat",
>     json={
>         "model": self.model,                     # "llama3.2"
>         "messages": [
>             {"role": "system", "content": system_prompt},
>             {"role": "user", "content": user_message},
>         ],
>         "stream": False,
>         "options": {"temperature": 0.1},
>     },
> )
> ```
>
> | Aspect | AWS (Bedrock) | Azure (OpenAI) | Local (Ollama) |
> | --- | --- | --- | --- |
> | **Model** | Claude 3.5 Sonnet | GPT-4o | llama3.2 |
> | **SDK** | `boto3` | `openai` | `httpx` (plain HTTP) |
> | **Auth** | IAM roles | API key | None (localhost) |
> | **Input cost** | $0.003 / 1K tokens | $0.0025 / 1K | **$0** |
> | **Output cost** | $0.015 / 1K tokens | $0.01 / 1K | **$0** |
> | **Cost per query** | ~$0.0065 | ~$0.005 | **$0** |
> | **Quality** | Highest | High | Good (smaller model) |
>
> **Key takeaway:** Local is free but uses a smaller model (8B params vs 175B+).
> Answers are less sophisticated but perfectly adequate for development and testing.
> Use `CLOUD_PROVIDER=local` to experiment without spending a cent.

---

### Step 5: BUILD the Response

```python
# chain.py lines
sources = [
    {
        "document_name": result.document_name,
        "text": result.text[:500],     # Truncate long chunks for the response
        "score": round(result.score, 4),
        "page_number": result.page_number,
    }
    for result in search_results
]

token_usage = {
    "input_tokens": llm_response.input_tokens,
    "output_tokens": llm_response.output_tokens,
    "total_tokens": llm_response.input_tokens + llm_response.output_tokens,
    "estimated_cost_usd": self._estimate_cost(
        llm_response.input_tokens, llm_response.output_tokens
    ),
}

return {
    "answer": llm_response.text,
    "sources": sources,
    "token_usage": token_usage,
}
```

**What's happening:**

1. **Sources list:** Takes the search results from Step 2 and formats them for the
   API response. Truncates chunk text to 500 chars (no need to send the full chunk
   back to the user — they just need to see what was referenced).

2. **Token usage:** Packs the token counts from the LLM response into a dict, plus
   calculates the estimated cost.

3. **Cost estimation:**
   ```python
   def _estimate_cost(self, input_tokens, output_tokens):
       if self._settings.cloud_provider == CloudProvider.AWS:
           # Claude 3.5 Sonnet v2
           input_cost = (input_tokens / 1000) * 0.003
           output_cost = (output_tokens / 1000) * 0.015
       elif self._settings.cloud_provider == CloudProvider.AZURE:
           # GPT-4o
           input_cost = (input_tokens / 1000) * 0.0025
           output_cost = (output_tokens / 1000) * 0.01
       else:
           # Local (Ollama) — $0
           return 0.0
       return round(input_cost + output_cost, 6)
   ```
   Notice: output tokens are ~5x more expensive than input tokens. The LLM's
   "thinking" (generating new text) costs more than just "reading" (processing
   the prompt).

4. **Returns a plain dict** — not a Pydantic model. The route layer (Part 3)
   converts this into the proper `ChatResponse` model.

**DE parallel:** This is just data formatting — transforming internal representations
into the API contract format. Same as mapping database rows to API response models.

---

## Part 3: Back in the Route

After `rag_chain.query()` returns the dict, the route handler unpacks it into
Pydantic models for the API response.

### Source Chunks

```python
sources = [
    SourceChunk(
        document_name=chunk.get("document_name", "unknown"),
        chunk_text=chunk.get("text", ""),
        relevance_score=chunk.get("score", 0.0),
        page_number=chunk.get("page_number"),
    )
    for chunk in result.get("sources", [])
]
```

**What each field means:**

| Field | Example value | Why it's there | 🫏 Donkey |
| --- | --- | --- | --- |
| `document_name` | `"refund-policy.pdf"` | User can verify *which* document was used | 🫏 On the route |
| `chunk_text` | `"Refunds are processed within 14 days..."` | User can verify the LLM didn't hallucinate | The donkey 🐴 |
| `relevance_score` | `0.95` | How confident we are this chunk is relevant | Saddlebag piece 📦 |
| `page_number` | `3` | User can go find the original in the PDF | 🫏 On the route |

**Why sources matter — the anti-hallucination pattern:**

Without sources, an AI chatbot can make things up and you'd never know. With sources,
the user can:
1. Read the answer
2. Check the source chunks
3. Verify: "Did the AI accurately represent what the document says?"

This is what makes RAG trustworthy for enterprise use. A hallucinating chatbot is
useless in a business context — you need to know where the answer came from.

### Token Usage

```python
token_usage = None
if usage := result.get("token_usage"):
    token_usage = TokenUsage(
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        estimated_cost_usd=usage.get("estimated_cost_usd", 0.0),
    )
```

**What is a token?**

A token is roughly ¾ of a word. The LLM doesn't read words — it reads tokens.

```
"What is the refund policy?" = 7 tokens
"Refunds are processed within 14 business days" = 9 tokens
A 5-chunk context of 500 chars each ≈ 1000 tokens
```

**Why track every token?**

LLMs charge **per token**. If your app handles 1000 questions per day:
- 1000 × $0.0065 = **$6.50/day** = **$195/month**
- If you're sloppy with chunk sizes: 1000 × $0.02 = $20/day = **$600/month**

Token tracking is the AI equivalent of monitoring your Redshift query costs.

**DE parallel:** This is like AWS billing per byte scanned in Athena or per RCU in
DynamoDB. You track it so you can optimise it.

### Metrics

```python
metrics = getattr(request.app.state, "metrics", None)
if metrics:
    metrics.record_chat_request(latency_ms=latency_ms, token_usage=token_usage)
```

Records the request for monitoring dashboards. Tracks:
- Latency (how fast are we?)
- Token usage (how much are we spending?)

### Building the Final Response

```python
response = ChatResponse(
    answer=result.get("answer", "I could not generate an answer."),
    sources=sources,
    session_id=session_id,
    request_id=request_id,
    cloud_provider=CloudProvider(settings.cloud_provider.value),
    latency_ms=latency_ms,
    token_usage=token_usage,
)

logger.info(f"[{request_id}] Response generated in {latency_ms}ms — {len(sources)} sources used")
return response
```

FastAPI receives the `ChatResponse` Pydantic model and automatically serialises it to JSON.

### Query Logging — What Happens After the Response (I30)

After building the response (but before returning it), the chat route now runs an
**inline heuristic evaluation** and logs a structured record:

```python
# Added in I30 — non-fatal, wrapped in try/except
try:
    evaluator = RAGEvaluator()
    eval_result = evaluator.evaluate(
        question=question,
        answer=response.answer,
        retrieved_chunks=[(s.chunk_text, s.relevance_score) for s in sources],
    )
    failure_category = classify_failure(eval_result)

    query_logger = getattr(request.app.state, "query_logger", None)
    if query_logger:
        await query_logger.log_query(
            QueryLogRecord(
                request_id=str(request_id),
                question=question,
                answer=response.answer,
                retrieval_score=eval_result.retrieval.average_score,
                faithfulness_score=eval_result.faithfulness.score,
                answer_relevance_score=eval_result.relevance.score,
                overall_score=eval_result.overall_score,
                failure_category=failure_category,
                latency_ms=latency_ms,
                ...
            )
        )
except Exception:
    pass  # Query logging must never break the chat endpoint
```

**Why this matters:**

| Aspect | What it does | DE parallel | 🫏 Donkey |
|---|---|---| --- |
| **Inline evaluation** | Scores every answer in real-time (< 5ms, no LLM call) | DQ check after every pipeline run | The donkey 🐴 |
| **Failure classification** | Categories: `bad_retrieval`, `hallucination`, `off_topic`, etc. | Error taxonomy in Airflow | Memory drift ⚠️ |
| **JSONL logging** | One structured record per query in `logs/queries/YYYY-MM-DD.jsonl` | Structured task logs | Gate guard 🔐 |
| **Non-fatal** | If logging fails, user still gets their answer | Airflow: logging fails ≠ task fails | Hoof check 🔧 |

📖 **See:** [Monitoring Reference](../../reference/monitoring.md) · [API Reference → Queries](../../reference/api-reference.md#query-debugging-i30)

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

---

## The Cost of One Chat Request

Here's a breakdown of what one question costs across all 5 steps:

| Step | What happens | AWS cost | Azure cost | Local cost | Time | 🫏 Donkey |
| --- | --- | --- | --- | --- | --- | --- |
| 1. EMBED | Question → vector | $0.0000003 (Titan) | $0.0000003 (text-embedding-3-small) | **$0** | ~50ms | GPS stamp 📍 |
| 2. SEARCH | Find top 5 chunks | ~$0 (OpenSearch, per-OCU) | ~$0 (AI Search, per-tier) | **$0** | ~30ms | AWS search hub 🔍 |
| 3. BUILD | Assemble prompt | $0 | $0 | $0 | <1ms | Delivery note 📋 |
| 4. GENERATE | LLM generates answer | **$0.0065** (Claude) | **$0.005** (GPT-4o) | **$0** (llama3.2) | ~350ms | The donkey 🐴 |
| 5. BUILD | Format response | $0 | $0 | $0 | <1ms | Free hay 🌿 |
| **Total per query** | | **~$0.0065** | **~$0.005** | **$0** | **~430ms** | Feed bill 🌾 |
| **Monthly infra** | | ~$350 (OpenSearch 2 OCU) | ~$75 (AI Search Basic) | **$0** | — | AWS search hub 🔍 |

**Key insight:** 99.9% of the cost is in Step 4 (the LLM call). The embedding is
essentially free. Optimising costs means reducing what you send to the LLM:
- Fewer chunks (lower `top_k`)
- Smaller chunks (lower `chunk_size`)
- Filter out low-scoring chunks before sending to the LLM

See [Cost Analysis](../ai-engineering/cost-analysis.md) for cost optimisation techniques.

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.

---

## DE vs AI Engineer

What does each role see when they look at this endpoint?

| Aspect | DE sees | AI engineer sees | 🫏 Donkey |
| --- | --- | --- | --- |
| `rag_chain.query()` | "Async service call" | "What embedding model? Is 1024 dimensions enough? Should I use cosine or dot product?" | GPS stamp 📍 |
| `top_k=5` | "Like LIMIT 5" | "Is 5 optimal? Should I use 3 for simple questions and 10 for complex ones?" | 🫏 On the route |
| `sources` | "List of dicts" | "Are low-scoring chunks diluting the context? Should I filter below 0.5 before sending to the LLM?" | The donkey 🐴 |
| `token_usage: 1250 input` | "A counter" | "That's 5 chunks × ~250 tokens each. Can I use 200-token chunks to save 20%?" | Cargo unit ⚖️ |
| `latency_ms: 450` | "Acceptable latency" | "350ms is the LLM. Can I use Claude Haiku ($0.00025/1K) for simple questions?" | The donkey 🐴 |
| `temperature: 0.1` | "A config parameter" | "0.1 is good for factual. If we add summarisation, we'd want 0.3-0.5" | 🫏 On the route |
| Error handling | "Standard try/except" | "If the LLM hallucinates despite context, how do I detect and prevent that?" | The donkey 🐴 |

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## What Could Go Wrong

| Error scenario | What happens | HTTP status | 🫏 Donkey |
| --- | --- | --- | --- |
| Invalid question (empty or >5000 chars) | Pydantic rejects it before the route runs | `422` | Stable door 🚪 |
| RAG chain not initialised | Route returns error immediately (no AI call) | `500` | Saddlebag check 🫏 |
| Embedding API fails (Bedrock / Azure OpenAI / Ollama down) | Exception in Step 1 → caught by try/except | `500` | The donkey 🐴 |
| Vector store empty (no documents) | Step 2 returns [] → friendly "upload docs first" message | `200` (not an error) | GPS warehouse 🗺️ |
| LLM API fails (Bedrock / Azure OpenAI / Ollama down) | Exception in Step 4 → caught by try/except | `500` | The donkey 🐴 |
| LLM generates bad answer | Returns successfully — no way to detect this automatically | `200` | The donkey 🐴 |
| LLM exceeds maxTokens | Answer is truncated (Claude stops at 2048 tokens) | `200` | The donkey 🐴 |

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Self-Check Questions

### Tier 1 — Must understand

- [ ] What are the 5 steps of `rag_chain.query()`?
- [ ] What is an embedding and why do you need it?
- [ ] What is cosine similarity and what does a score of 0.95 mean?
- [ ] What is `top_k` and what's the DE equivalent?
- [ ] Why does the response include `sources`?

### Tier 2 — Should understand

- [ ] Why is Step 4 (GENERATE) the most expensive step?
- [ ] Why are output tokens more expensive than input tokens?
- [ ] What does `temperature=0.1` mean and why is it low?
- [ ] What happens if the vector store is empty?
- [ ] How does `session_id` enable multi-turn conversations?

### Tier 3 — AI engineering territory

- [ ] How would you decide the optimal `top_k` value?
- [ ] When would you filter out low-scoring chunks before sending to the LLM?
- [ ] How would you reduce input tokens without losing answer quality?
- [ ] How would you detect if the LLM hallucinated despite having good context?
- [ ] When would you use a cheaper/faster model (like Claude Haiku) vs the full model?

- 🫏 **Donkey:** A quick quiz for the trainee stable hand — answer these to confirm the key donkey delivery concepts have landed.
