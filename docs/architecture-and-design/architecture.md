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
    ├── 4b½. (Planned) Re-rank chunks using Bedrock Reranker / Azure Semantic Ranker
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

---

## Project Layer Map

| Layer | Directory | Responsibility |
| --- | --- | --- |
| **API** | `src/api/` | HTTP interface (routes, models, middleware) |
| **Guardrails** | `src/api/middleware/` | Input/output safety, PII redaction, prompt injection defense |
| **RAG** | `src/rag/` | RAG pipeline (chain, ingestion, prompts) |
| **LLM** | `src/llm/` | LLM abstraction + implementations |
| **Vector Store** | `src/vectorstore/` | Vector DB abstraction + implementations |
| **Storage** | `src/storage/` | Document storage abstraction |
| **History** | `src/history/` | Conversation history abstraction |
| **Monitoring** | `src/monitoring/` | Metrics, query logging (JSONL), OpenTelemetry tracing |
| **Config** | `src/config.py` | Pydantic Settings (env vars) |
| **Entry Point** | `src/main.py` | FastAPI app factory, lifespan |
| **Infrastructure** | `infra/` | Terraform (AWS + Azure); Local needs no infra |
| **CI/CD** | `.github/workflows/` | GitHub Actions |
| **Tests** | `tests/` | Unit + integration tests |
| **Docs** | `docs/` | You are here |

---

## Why this architecture?

| Decision | Reason |
| --- | --- |
| **Monolith (single FastAPI app)** | Simpler than microservices for a 1-person project. Can always split later. |
| **Abstract interfaces** | Cloud-agnostic. Can add GCP, local, or mock implementations without changing core logic. |
| **Factory pattern** | One env variable (`CLOUD_PROVIDER`) switches the entire backend — `aws`, `azure`, or `local`. |
| **Pydantic everywhere** | Type safety, validation, documentation — all from type hints. |
| **Poetry** | Better dependency management than pip. Lock files prevent "works on my machine" issues. |
| **FastAPI** | Async, fast, auto-generates API docs, native Pydantic support. |
