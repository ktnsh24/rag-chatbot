# Architecture Overview

## Table of Contents

- [Architecture Overview](#architecture-overview)
  - [Table of Contents](#table-of-contents)
  - [System Design](#system-design)
  - [Data Flow — Chat Query](#data-flow--chat-query)
  - [Data Flow — Document Ingestion](#data-flow--document-ingestion)
  - [Cloud-Agnostic Pattern](#cloud-agnostic-pattern)
  - [Project Layer Map](#project-layer-map)
  - [Why this architecture?](#why-this-architecture)

---

## System Design

```
┌──────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                            │
│  Chat UI (HTML/JS)  ←→  Swagger UI  ←→  curl / Postman         │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼───────────────────────────────────────┐
│                       APPLICATION LAYER                          │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐   │
│  │  Middleware  │→ │  API Routes  │→ │     RAG Chain         │   │
│  │  (logging,  │  │  (chat,      │  │  (orchestrator that   │   │
│  │   CORS,     │  │   documents, │  │   ties everything     │   │
│  │   guardrails│  │   health,    │  │   together)           │   │
│  │   PII)      │  │   evaluate,  │  │                       │   │
│  │             │  │   queries,   │  │                       │   │
│  │             │  │   metrics)   │  │                       │   │
│  └─────────────┘  └──────────────┘  └───────┬───────────────┘   │
│                                              │                   │
│  ┌───────────────────────────────────────────▼─────────────────┐ │
│  │              ABSTRACTION LAYER (interfaces)                 │ │
│  │                                                             │ │
│  │  ┌──────────┐  ┌────────────────┐  ┌───────────┐          │ │
│  │  │ BaseLLM  │  │ BaseVectorStore│  │ (future)  │          │ │
│  │  │          │  │                │  │ BaseHistory│          │ │
│  │  └────┬─────┘  └──────┬─────────┘  └───────────┘          │ │
│  │       │               │                                     │ │
│  └───────┼───────────────┼─────────────────────────────────────┘ │
│          │               │                                       │
└──────────┼───────────────┼───────────────────────────────────────┘
           │               │
┌──────────▼───────────────▼───────────────────────────────────────┐
│               IMPLEMENTATION LAYER (Cloud + Local)                │
│                                                                   │
│  ┌─── AWS ────────────────┐  ┌─── Azure ──────────────┐  ┌─── Local ────────┐  │
│  │                        │  │                        │  │                  │  │
│  │  BedrockLLM            │  │  AzureOpenAILLM        │  │  OllamaLLM       │  │
│  │  (Claude 3.5 Sonnet)   │  │  (GPT-4o)              │  │  (llama3.2)      │  │
│  │                        │  │                        │  │                  │  │
│  │  OpenSearchVectorStore │  │  AzureAISearchVector   │  │  ChromaDBVector  │  │
│  │  (OpenSearch Serverless)│  │  Store (AI Search)     │  │  Store (SQLite)  │  │
│  │  DynamoDBVectorStore   │  │                        │  │                  │  │
│  │  (cheap: $0/month)     │  │                        │  │                  │  │
│  │                        │  │                        │  │                  │  │
│  │  S3 (documents)        │  │  Blob Storage (docs)   │  │  Local filesystem│  │
│  │  DynamoDB (history)    │  │  Cosmos DB (history)   │  │  (in-memory)     │  │
│  │                        │  │                        │  │                  │  │
│  └────────────────────────┘  └────────────────────────┘  └──────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

> 📖 **Want to understand the API Routes box in detail?** Start with the
> [API Routes — Overview](api-routes-explained.md) for how `main.py` wires everything together,
> then read each route's deep dive:
> [Health](api-routes/health-endpoint-explained.md) ·
> [Chat](api-routes/chat-endpoint-explained.md) (**start here** — this is where the RAG pipeline lives) ·
> [Documents](api-routes/documents-endpoint-explained.md) ·
> [Evaluate](api-routes/evaluate-endpoint-explained.md) ·
> Queries (I30 — failure debugging) ·
> Metrics (I31 — Prometheus endpoint).

- 🚚 **Courier:** Like a depot floor plan showing where the courier enters, where the parcels are loaded, and which route it takes to the customer.

---

## Data Flow — Chat Query

```
User asks: "What is the refund policy?"
    │
    ▼
1. POST /api/chat { "question": "What is the refund policy?" }
    │
    ▼
2. RequestLoggingMiddleware logs the request
    │
    ▼
3. chat() route handler receives ChatRequest (Pydantic validated)
    │
    ▼
4. RAGChain.query() starts the RAG pipeline:
    │
    ├── 4a. LLM.get_embedding("What is the refund policy?")
    │       → [0.12, -0.45, 0.78, 0.33, ...]  (1024/1536/768 floats depending on provider)
    │
    ├── 4b. VectorStore.search(embedding, top_k=5)
    │       → 5 most similar document chunks:
    │         [
    │           { text: "Refunds are processed within 14 days...", score: 0.92 },
    │           { text: "To request a refund, contact...", score: 0.87 },
    │           ...
    │         ]
    │
    ├── 4b½. (Optional — RERANKER_ENABLED=true to activate) Re-rank chunks using Bedrock Reranker / Azure Semantic Ranker
    │         → re-score for relevance, reorder top_k results
    │
    ├── 4c. LLM.generate(question, context_chunks)
    │       → "Based on the documents, the refund policy states that
    │          refunds are processed within 14 days..."
    │
    └── 4d. Build ChatResponse with answer, sources, token usage
    │
    ▼
5. Return JSON response to client
```

- 🚚 **Courier:** The warehouse robot dispatched to find the right parcel shelf — it uses GPS coordinates (embeddings) to locate the nearest relevant chunks in ~9 hops.

---

## Data Flow — Document Ingestion

```
User uploads: "refund-policy.pdf" (12 pages)
    │
    ▼
1. POST /api/documents/upload (multipart form)
    │
    ▼
2. upload_document() route handler:
    │
    ├── 2a. Validate file type (.pdf ✓)
    │
    ├── 2b. read_document("refund-policy.pdf", bytes)
    │       → Extract text from all 12 pages
    │       → "Page 1: Introduction to our refund policy..."
    │
    ├── 2c. chunk_document(text, chunk_size=1000, overlap=200)
    │       → Split into 45 overlapping chunks
    │       → step = chunk_size - overlap = 1000 - 200 = 800 chars
    │       → chunks = ~36,000 chars / 800 step = 45 chunks
    │       → See docs/rag-concepts.md → "How many chunks?" for full explanation
    │       → ["Page 1: Introduction to our...", "...refund within 14...", ...]
    │
    ├── 2d. LLM.get_embeddings_batch(45 chunks)
    │       → 45 vectors, each 1024/1536/768 floats (depends on provider)
    │       → [[0.12, -0.45, ...], [0.33, 0.67, ...], ...]
    │
    └── 2e. VectorStore.store_vectors(document_id, chunks, embeddings)
            → Stored in OpenSearch / AI Search / ChromaDB
    │
    ▼
3. Return: { document_id: "abc-123", chunk_count: 45, status: "ready" }
```

- 🚚 **Courier:** Post office pre-sorting: mail is split into parcel-sized chunks, stamped with GPS coordinates (embeddings), and shelved in the warehouse before the courier ever arrives.

---

## Cloud-Agnostic Pattern

The key architectural pattern is **abstraction through interfaces**:

```python
# Abstract interface — defines WHAT to do
class BaseLLM(ABC):
    async def generate(prompt, context) -> LLMResponse: ...
    async def get_embedding(text) -> list[float]: ...

# AWS implementation — defines HOW (using Bedrock)
class BedrockLLM(BaseLLM):
    async def generate(prompt, context):
        return self._runtime_client.converse(...)

# Azure implementation — defines HOW (using Azure OpenAI)
class AzureOpenAILLM(BaseLLM):
    async def generate(prompt, context):
        return await self._client.chat.completions.create(...)

# Local implementation — defines HOW (using Ollama on localhost)
class OllamaLLM(BaseLLM):
    async def generate(prompt, context):
        return await self._http.post("http://localhost:11434/api/chat", ...)

# Factory — picks the right implementation at startup
if settings.cloud_provider == "aws":
    llm = BedrockLLM(model_id="claude-3.5-sonnet")
elif settings.cloud_provider == "azure":
    llm = AzureOpenAILLM(deployment="gpt-4o")
elif settings.cloud_provider == "local":
    llm = OllamaLLM(model="llama3.2")

# RAG chain doesn't know or care which one it's using
rag_chain = RAGChain(llm=llm, vector_store=vector_store)
result = await rag_chain.query("What is the refund policy?")
```

**Why this matters for your portfolio:**
This demonstrates that you can design systems that aren't locked into one cloud provider — a key skill for enterprise architecture roles.

- 🚚 **Courier:** The modular gear room — each layer (LLM, vector store, storage) handles one job, so you can swap any piece out without touching the rest.

---

## Project Layer Map

| Layer | Directory | Responsibility | 🚚 Courier |
| --- | --- | --- | --- |
| **API** | `src/api/` | HTTP interface (routes, models, middleware) | Door the customer knocks on — API: src/api/ · HTTP interface (routes, models, middleware) |
| **Guardrails** | `src/api/middleware/` | Input/output safety, PII redaction, prompt injection defense | Note the courier carries — Guardrails: src/api/middleware/ · Input/output safety, PII redaction, prompt injection defense |
| **RAG** | `src/rag/` | RAG pipeline (chain, ingestion, prompts) | Instructions tucked in the pannier — RAG: src/rag/ · RAG pipeline (chain, ingestion, prompts) |
| **LLM** | `src/llm/` | LLM abstraction + implementations | Where the courier lives — swap stables (AWS / Azure / Ollama) without touching the rest of the code |
| **Vector Store** | `src/vectorstore/` | Vector DB abstraction + implementations | Abstraction over the GPS warehouse plus concrete implementations for ChromaDB, OpenSearch, and Azure AI Search. |
| **Storage** | `src/storage/` | Document storage abstraction | Depot design — courier doesn't care which warehouse brand it grabs from |
| **History** | `src/history/` | Conversation history abstraction | Trip log entry — History: src/history/ · Conversation history abstraction |
| **Monitoring** | `src/monitoring/` | Metrics, query logging (JSONL), OpenTelemetry tracing | Tally board on the dispatch board — Monitoring: src/monitoring/ · Metrics, query logging (JSONL), OpenTelemetry tracing |
| **Config** | `src/config.py` | Pydantic Settings (env vars) | The depot's shipping manifest — Pydantic Settings read env vars once and tell every courier which barn to work from. |
| **Entry Point** | `src/main.py` | FastAPI app factory, lifespan | Where parcels are dropped at the depot — Entry Point: src/main.py · FastAPI app factory, lifespan |
| **Infrastructure** | `infra/` | Terraform (AWS + Azure); Local needs no infra | Terraform depot blueprints for AWS and Azure; the local depot runs without any infra at all. |
| **CI/CD** | `.github/workflows/` | GitHub Actions | The robot dispatch clerk in `.github/workflows/` — runs tests, builds the crate, and ships the courier on every push. |
| **Tests** | `tests/` | Unit + integration tests | The courier's report card — unit checks every harness, integration runs full deliveries before any customer sees them. |
| **Docs** | `docs/` | You are here | Courier-side view of Docs — affects how the courier loads, reads, or delivers the parcels |

- 🚚 **Courier:** The modular gear room — each layer (LLM, vector store, storage) handles one job, so you can swap any piece out without touching the rest.

---

## Why this architecture?

| Decision | Reason | 🚚 Courier |
| --- | --- | --- |
| **Monolith (single FastAPI app)** | Simpler than microservices for a 1-person project. Can always split later. | Where parcels are dropped at the depot — Monolith (single FastAPI app): Simpler than microservices for a 1-person project. Can always split later. |
| **Abstract interfaces** | Cloud-agnostic. Can add GCP, local, or mock implementations without changing core logic. | Same interface lets the courier switch between local barn, AWS depot, Azure hub, or a mock without code changes. |
| **Factory pattern** | One env variable (`CLOUD_PROVIDER`) switches the entire backend — `aws`, `azure`, or `local`. | Amazon's loading dock — Factory pattern: One env variable (CLOUD_PROVIDER) switches the entire backend — aws, azure, or local. |
| **Pydantic everywhere** | Type safety, validation, documentation — all from type hints. | Depot gate rule — Pydantic everywhere: Type safety, validation, documentation — all from type hints. |
| **Poetry** | Better dependency management than pip. Lock files prevent "works on my machine" issues. | Supply shed manifest — Poetry: Better dependency management than pip. Lock files prevent "works on my machine" issues. |
| **FastAPI** | Async, fast, auto-generates API docs, native Pydantic support. | Entry gate to the depot — FastAPI: Async, fast, auto-generates API docs, native Pydantic support. |

- 🚚 **Courier:** Like a depot floor plan showing where the courier enters, where the parcels are loaded, and which route it takes to the customer.
