# API Routes — Overview

> **Who is this for?** You're a Data Engineer who builds FastAPI APIs at work (e.g.
> shared-proxy services). You can read route code. But this RAG app has routes that
> do things you haven't seen before — they call an LLM, track tokens, and embed
> documents. This doc gives you the overview — the per-route deep dives are in
> separate documents linked below.

> **Related docs:**
> - [API Reference](../reference/api-reference.md) — endpoint specs, request/response examples
> - [Pydantic Models Guide](../reference/pydantic-models.md) — every model field explained
> - [Architecture Overview](architecture.md) — where routes fit in the overall system
> - [How Services Work](how-services-work.md) — what happens when routes call cloud services

---

## Table of Contents

1. [The Big Picture — How Routes Fit in the App](#the-big-picture)
2. [How main.py Wires Everything Together](#how-mainpy-wires-everything)
3. [The Middleware Layer — What Runs Before Every Route](#the-middleware-layer)
4. [The Route Files — Overview and Deep Dives](#the-route-files)
5. [The app.state Pattern — Dependency Injection Without a Framework](#the-appstate-pattern)
6. [Comparing: Shared-Proxy Routes vs RAG Routes](#comparing-shared-proxy-routes-vs-rag-routes)
7. [What You Should Understand After Reading This](#what-you-should-understand-after-reading-this)

---

## The Big Picture

In any FastAPI app, routes are **thin**. They receive HTTP requests, call business
logic, and return HTTP responses. That's the same here. The difference is what they
call:

```text
A Typical FastAPI API                 RAG Chatbot
─────────────────────                 ────────────────────
Route receives request                Route receives request
    │                                     │
    ▼                                     ▼
Calls a service class                 Calls rag_chain
    │                                     │
    ▼                                     ▼
Service talks to DynamoDB/S3          rag_chain talks to:
    │                                   - Embedding model (to vectorise the question)
    ▼                                   - Vector store (to find relevant chunks)
Returns rows/records                    - LLM (to generate an answer)
                                          │
                                          ▼
                                        Returns answer + sources + token usage
```

**Key insight:** The routes themselves are almost identical in complexity. The
intelligence lives in `rag_chain`, not in the routes. Routes are just the front door.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## How main.py Wires Everything

File: `src/main.py`

Before looking at individual routes, understand how they get registered. This is
the same pattern as any FastAPI app:

```python
# src/main.py — relevant lines

from src.api.routes import chat, documents, health

def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Chatbot API",
        version="0.1.0",
        lifespan=lifespan,          # ← startup/shutdown logic
    )

    # Middleware (order matters — last added = first executed)
    app.add_middleware(RequestLoggingMiddleware)  # ← runs on EVERY request
    app.add_middleware(CORSMiddleware, ...)       # ← allows browser access

    # Routes
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(chat.router, prefix="/api", tags=["Chat"])
    app.include_router(documents.router, prefix="/api", tags=["Documents"])
    app.include_router(evaluate.router, prefix="/api", tags=["Evaluation"])
    app.include_router(queries.router, prefix="/api", tags=["Queries"])     # I30
    app.include_router(metrics.router, prefix="/api", tags=["Metrics"])     # I31
```

### What to notice

| Line | What it does | DE parallel | 🫏 Donkey |
| --- | --- | --- | --- |
| `lifespan=lifespan` | Runs startup/shutdown code (initialise RAG chain, close connections) | Like `@app.on_event("startup")` in shared-proxy | Saddlebag check 🫏 |
| `prefix="/api"` | All routes get `/api` prefix → `/chat` becomes `/api/chat` | Same as any FastAPI app | Stable door 🚪 |
| `tags=["Chat"]` | Groups endpoints in Swagger UI | Same as any FastAPI app | Stable door 🚪 |

### The Lifespan — Where the AI Engine Gets Created

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    rag_chain = await RAGChain.create(settings)   # ← Creates the entire AI engine
    app.state.rag_chain = rag_chain                # ← Stores it on app.state

    yield   # ← App runs here, serves requests

    # SHUTDOWN
    logger.info("Shutting down...")
```

**Why this matters:** The `rag_chain` is created ONCE at startup, stored on
`app.state`, and every route accesses it from there. This is the same pattern as
storing a database connection pool on `app.state` — you just wouldn't create a new
PostgreSQL connection per request.

The difference: instead of a DB connection, you're storing an AI engine that knows
how to embed questions, search vectors, and call an LLM.

- 🫏 **Donkey:** The mechanics of the stable — understanding how each piece fits so you can maintain and extend the system.

---

## The Middleware Layer

File: `src/api/middleware/logging.py`

### What it does

Every HTTP request passes through this middleware **before** reaching any route.
It logs the request, measures timing, and adds tracing headers.

### Line-by-line explanation

```python
class RequestLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid4())          # Generate unique ID for this request
        start_time = time.time()           # Start the stopwatch

        request.state.request_id = request_id   # Attach to request (routes can read this)

        logger.info(f"[{request_id}] → {request.method} {request.url.path}")   # Log incoming

        response = await call_next(request)   # ← Call the actual route handler

        latency_ms = int((time.time() - start_time) * 1000)   # Stop the stopwatch

        logger.info(f"[{request_id}] ← {response.status_code} ({latency_ms}ms)")   # Log outgoing

        response.headers["X-Request-ID"] = request_id          # Add tracing header
        response.headers["X-Latency-Ms"] = str(latency_ms)     # Add latency header

        return response
```

### DE comparison

This is **identical** to `BnaEventMiddleware` in the shared-proxy. Same pattern:
log request → call next → log response → add headers. Nothing AI-specific here.

### Request lifecycle with middleware

```text
Browser sends POST /api/chat
    │
    ▼
CORSMiddleware (checks origin headers)
    │
    ▼
RequestLoggingMiddleware
    ├── Generates request_id: "abc-123"
    ├── Logs: "[abc-123] → POST /api/chat"
    ├── Calls: chat() route handler
    │       │
    │       ▼
    │   chat() runs (calls rag_chain, gets answer)
    │       │
    │       ▼
    │   Returns ChatResponse
    │
    ├── Logs: "[abc-123] ← 200 (450ms)"
    ├── Adds headers: X-Request-ID, X-Latency-Ms
    │
    ▼
Response sent to browser
```

- 🫏 **Donkey:** The modular gear room — each layer (LLM, vector store, storage) handles one job, so you can swap any piece out without touching the rest.

---

## The Route Files

This app has 6 route files, each with different AI complexity. Each has its own
detailed deep-dive document:

| Route file | Endpoint(s) | AI complexity | Deep dive | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| `health.py` | `GET /api/health` | ★☆☆☆☆ — nothing new | 📖 [Health Endpoint Deep Dive](api-routes/health-endpoint-explained.md) | Donkey check ✅ |
| `chat.py` | `POST /api/chat` | ★★★★★ — the RAG query pipeline | 📖 [Chat Endpoint Deep Dive](api-routes/chat-endpoint-explained.md) | Saddlebag check 🫏 |
| `documents.py` | `POST /api/documents/upload`, `GET /api/documents`, `DELETE /api/documents/{id}` | ★★★★☆ — the ingestion pipeline | 📖 [Documents Endpoint Deep Dive](api-routes/documents-endpoint-explained.md) | Pre-sort 📮 |
| `evaluate.py` | `POST /api/evaluate`, `POST /api/evaluate/suite` | ★★★★★ — the AI quality pipeline | 📖 [Evaluate Endpoint Deep Dive](api-routes/evaluate-endpoint-explained.md) | Report card 📝 |
| `queries.py` | `GET /api/queries/stats`, `GET /api/queries/failures` | ★★★☆☆ — production debugging | 📖 [Queries Endpoint Deep Dive](api-routes/queries-endpoint-explained.md) | Stable door 🚪 |
| `metrics.py` | `GET /api/metrics` | ★★☆☆☆ — Prometheus metrics | 📖 [Metrics Endpoint Deep Dive](api-routes/metrics-endpoint-explained.md) | Tachograph 📊 |

### Quick summary of each

**health.py** — Checks if the RAG chain is initialised. No AI calls. Pure
infrastructure. If you've ever written a health check, you already know this.

**chat.py** — The most important endpoint. User sends a question, the app runs a
5-step AI pipeline: embed question → search vector store → build prompt → call LLM →
return answer with sources and token usage. The route itself is thin FastAPI code —
the intelligence lives in `rag_chain.query()`.

**documents.py** — User uploads a document, the app runs a 4-step AI pipeline: read
file → chunk text → embed each chunk → store vectors. This is an ETL pipeline where
Transform = chunk + embed instead of clean + aggregate. List and Delete are pure CRUD.

**evaluate.py** — The AI Engineer's quality assurance endpoint. Runs a question
through the full RAG pipeline AND evaluates the answer quality. The suite endpoint
runs the entire golden dataset — like running `dbt test` for your AI system.

**queries.py** (I30) — Production debugging endpoints. `GET /queries/failures` lists
recent failed queries with failure categories (bad_retrieval, hallucination, etc.).
`GET /queries/stats` returns aggregate pass rate and failure breakdown. Reads from
the JSONL query logs written by I30's QueryLogger. DE parallel: a `/pipeline/failures`
endpoint that shows which DAG runs failed and why.

**metrics.py** (I31) — Prometheus-compatible metrics. `GET /metrics` returns counters
(requests, errors, tokens) and gauges (latency percentiles, pass rate, failure counts)
in Prometheus text format. Any monitoring tool (Grafana, Datadog, CloudWatch) can
scrape this endpoint. DE parallel: exposing Airflow/ECS metrics for Prometheus.

### Recommended reading order

1. **Health** (5 min) — build confidence that you can read routes in this repo
2. **Chat** (20 min) — understand the RAG query pipeline end-to-end
3. **Documents** (15 min) — understand the ingestion pipeline end-to-end
4. **Evaluate** (15 min) — understand how to measure AI quality
5. **Queries** (10 min) — understand production debugging via structured logs
6. **Metrics** (10 min) — understand Prometheus metrics for dashboards & alerting

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

---

## The app.state Pattern

You'll notice every route does this:

```python
rag_chain = getattr(request.app.state, "rag_chain", None)
```

### Why not just import rag_chain?

```python
# ❌ You might expect this:
from src.rag.chain import rag_chain

# ✅ But the code does this instead:
rag_chain = getattr(request.app.state, "rag_chain", None)
```

**Reason:** The RAG chain is created asynchronously at startup (it needs to connect
to AWS/Azure services, or initialise local Ollama/ChromaDB). You can't import something that doesn't exist yet at import
time.

### How it works

```text
App startup (lifespan):
    rag_chain = await RAGChain.create(settings)    # Create async
    app.state.rag_chain = rag_chain                # Store on app

Request comes in:
    async def chat(request: Request, ...):
        rag_chain = getattr(request.app.state, "rag_chain", None)   # Read from app
        result = await rag_chain.query(...)
```

### DE parallel

Same as storing a database connection pool:

```python
# Standard FastAPI pattern:
app.state.db_pool = create_db_pool()

# Then in routes:
pool = request.app.state.db_pool
result = await pool.execute(query)
```

The pattern is identical. The only difference is what you're storing: a DB pool vs
an AI engine.

### Why getattr() with a default?

```python
rag_chain = getattr(request.app.state, "rag_chain", None)   # Returns None if missing
```

If the RAG chain failed to initialise at startup (bad credentials, cloud service
down), `app.state.rag_chain` is set to `None`. Using `getattr(..., None)` prevents
an `AttributeError` crash and lets the route return a clean 500 error instead.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Comparing: Shared-Proxy Routes vs RAG Routes

You work on the shared-proxy daily. Here's a side-by-side comparison to show what's
the same and what's different:

| Aspect | A Typical FastAPI API | RAG Chatbot | 🫏 Donkey |
| --- | --- | --- | --- |
| **Framework** | FastAPI | FastAPI | Stable door 🚪 |
| **Router pattern** | `APIRouter()` + `include_router()` | `APIRouter()` + `include_router()` | Stable door 🚪 |
| **Middleware** | `BnaEventMiddleware` | `RequestLoggingMiddleware` | Gate guard 🔐 |
| **Request validation** | Pydantic models | Pydantic models | Manifest template 📋 |
| **Dependency injection** | `app.state` or FastAPI `Depends()` | `app.state` (for rag_chain) | Saddlebag check 🫏 |
| **Error handling** | `HTTPException` | `HTTPException` | Stable door 🚪 |
| **Logging** | Loguru | Loguru | Gate guard 🔐 |
| **What routes call** | Service classes → DynamoDB/S3 | `rag_chain` → LLM + Vector Store + Storage | The donkey 🐴 |
| **Response contains** | Data records | Answer + sources + token usage | Cargo unit ⚖️ |
| **New concepts** | None | Embeddings, semantic search, token costs | Cargo unit ⚖️ |

**Bottom line:** The routes layer is 90% identical. The 10% difference is *what they
call* and *what comes back*. The AI lives in `rag_chain`, not in the routes.

- 🫏 **Donkey:** The donkey checks its saddlebag full of retrieved document chunks before answering — no guessing from memory.

---

## What You Should Understand After Reading This

Use this as your self-check. Can you answer each question?

### Tier 1 — Must understand (if you can't answer these, re-read the section)

- [ ] How does `main.py` register routes with `include_router()`?
- [ ] What does the `lifespan` function do at startup?
- [ ] Why is `rag_chain` stored on `app.state` instead of imported?
- [ ] What does `getattr(request.app.state, "rag_chain", None)` do and why?
- [ ] What are the 6 route files and what does each one do?

### Tier 2 — Should understand (makes you a stronger engineer)

- [ ] What happens inside `rag_chain.query()` at a high level? (embed → search → generate)
- [ ] What happens inside `rag_chain.ingest_document()` at a high level? (read → chunk → embed → store)
- [ ] Why does the chat endpoint return `sources`? (transparency, anti-hallucination)
- [ ] Why track `token_usage`? (LLMs charge per token)

### Tier 3 — Go deeper (read the per-route deep dives)

- [ ] 📖 [Health Endpoint](api-routes/health-endpoint-explained.md) — line-by-line code walkthrough
- [ ] 📖 [Chat Endpoint](api-routes/chat-endpoint-explained.md) — full 5-step RAG query pipeline with DE parallels
- [ ] 📖 [Documents Endpoint](api-routes/documents-endpoint-explained.md) — full 4-step ingestion pipeline as ETL

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## What to Study Next

Now that you understand the routes layer, here's the recommended path:

- **Next in Phase 1:** `src/storage/` — pure DE territory (S3/Blob storage)
- **The bridge:** Phase 2 files (`src/llm/`, `src/vectorstore/`, `src/rag/`) — where the AI concepts you just learned (embeddings, chunks, tokens) are implemented in actual code
- **Deep reference:** [How Services Work](how-services-work.md) — what happens on the cloud side when `rag_chain.query()` calls Bedrock/OpenSearch

- 🫏 **Donkey:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
