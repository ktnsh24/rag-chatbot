# Health Endpoint — Deep Dive

> `GET /api/health` — Check if the app and all backend services are alive.

> **DE verdict: ★☆☆☆☆ — Nothing new here.** This route is 100% familiar territory.
> It exists so you can start reading this codebase with confidence: "I can read route
> code in this repo."

> **Related docs:**
> - [API Routes Overview](../api-routes-explained.md) — how all routes fit together
> - [Chat Endpoint Deep Dive](chat-endpoint-explained.md) — the RAG query route ★★★★★
> - [Documents Endpoint Deep Dive](documents-endpoint-explained.md) — the ingestion route ★★★★☆
> - [API Reference → Health](../reference/api-reference.md) — request/response examples
> - [Pydantic Models → HealthResponse](../reference/pydantic-models.md) — model fields

---

## Table of Contents

1. [What This Endpoint Does](#what-this-endpoint-does)
2. [The Complete Request Flow](#the-complete-request-flow)
3. [Line-by-Line Code Walkthrough](#line-by-line-code-walkthrough)
4. [The Pydantic Response Models](#the-pydantic-response-models)
5. [DE Comparison — Shared-Proxy Health Check vs RAG Health Check](#de-comparison)
6. [What's the Only New Thing Here?](#whats-the-only-new-thing)
7. [Self-Check Questions](#self-check-questions)

---

## Plain-English Walkthrough (Start Here)

> **Read this first if you're new to the chatbot.** Same courier analogy as the [Chat Walkthrough](./chat-endpoint-explained.md#plain-english-walkthrough-start-here). This explains what's specific about the health endpoint.

### What this endpoint is for

`GET /api/health` is the **"is the depot open?"** check. Load balancers, Kubernetes liveness probes, and Docker healthchecks hit this endpoint to decide whether the chatbot is alive and able to serve requests.

> **Courier version.** It's the porch lamp at the depot, plus a quick wave through the door: "Are you still in business? Yes/no." The reply is one status card.

### What really happens

This is the simplest endpoint in the chatbot. There's no RAG pipeline, no LLM call, no database write. It does **one check**: was the RAG chain initialised at app startup? If yes, return `healthy`. If no, return `unhealthy`.

```
1. Read app.state.rag_chain
2. If None  → service is unhealthy
   If set  → service is healthy
3. Compute uptime in seconds
4. Return the response
```

The aggregation logic is genuinely correct here — unlike on the gateway side, the top-level `status` field **does** reflect whether the underlying services are unhealthy. If any service reports `UNHEALTHY`, the overall is `UNHEALTHY`. If any reports `DEGRADED`, the overall is `DEGRADED`. Otherwise it's `HEALTHY`.

### What it does *not* check

The check today is shallow. It only verifies the chain was constructed successfully — it does **not** ping any of the actual backends. So:

- The vector store could be unreachable right now and `/health` will still say healthy.
- The LLM provider could be down and `/health` will still say healthy.
- The cloud storage (S3 / Blob) could be denying writes and `/health` will still say healthy.

The chain-init check is essentially a "did the cloud creds work at startup?" check. It does not catch outages that happen after startup. A more thorough version would also try a tiny vector-store list call and a tiny LLM ping, but doing so on every probe call is expensive — that's a deliberate trade-off.

### Worked example

Your AWS creds are valid at startup but DynamoDB has an outage two hours later. You hit `/health`:

```jsonc
{
  "status": "healthy",        // ← still healthy because chain was built
  "cloud_provider": "aws",
  "services": [
    { "name": "rag_chain", "status": "healthy", "message": "RAG chain initialized and ready" }
  ],
  "uptime_seconds": 7234
}
```

But hit `/api/chat` and it'll fail with a 500 because the vector store search throws. So `/health` here is **liveness** (the app process is up) more than **readiness** (the app can actually serve traffic).

### Quirks worth knowing

1. **Shallow check.** No live backend probes. A green `/health` does not guarantee `/api/chat` works.
2. **Always returns 200.** Even when the chain is missing and `status: "unhealthy"`, the HTTP code is still 200. Orchestrators that interpret 5xx as unhealthy will never see one from this endpoint.
3. **`uptime_seconds` is per-process.** Restarts reset it; multi-pod deployments report different uptimes per pod.
4. **No auth.** Anyone hitting your URL can read the cloud provider and uptime. Standard for liveness probes.
5. **Single service in the list today.** The structure is set up to track many services (`services: list[ServiceHealth]`) but only `rag_chain` is added. Future: add per-backend probes.

### TL;DR

- Single check: was the RAG chain successfully initialised at startup?
- **Liveness, not readiness.** Doesn't actually probe the backends.
- Always returns HTTP 200; check the `status` field, not the response code.
- Aggregation logic across services *is* correct — just only one service is reported today.

---

## What This Endpoint Does

A health check endpoint answers one question: **"Is this app working?"**

In a traditional app, "working" means "can I reach the database?". In this RAG app,
"working" means "is the AI engine (RAG chain) initialised?" — which itself means
"can I reach the LLM, the vector store, and the cloud storage?"

```
Client (load balancer, monitoring tool, or developer) sends:
    GET /api/health

Server checks:
    ✅ Is the RAG chain initialised? (LLM + vector store + storage all connected)

Server responds:
    { "status": "healthy", "services": [...], "uptime_seconds": 3600 }
```

**DE parallel:** This is exactly the same pattern as a health check in the shared-proxy
or any microservice. Kubernetes/ECS uses this endpoint to decide whether to send
traffic to this container or restart it.

- 🚚 **Courier:** The specific delivery address the courier is dispatched to — each route handles a different type of parcels drop-off.

---

## The Complete Request Flow

```
GET /api/health hits the server
    │
    ▼
CORSMiddleware (allows browser access — passes through)
    │
    ▼
RequestLoggingMiddleware
    ├── Generates request_id: "abc-123"
    ├── Logs: "[abc-123] → GET /api/health"
    │
    ▼
health_check() route handler
    │
    ├── Step 1: Get rag_chain from app.state
    │   ├── If rag_chain exists → ServiceHealth(status=HEALTHY)
    │   └── If rag_chain is None → ServiceHealth(status=UNHEALTHY)
    │
    ├── Step 2: Determine overall status
    │   └── "Worst status wins" — if any service is UNHEALTHY, overall is UNHEALTHY
    │
    ├── Step 3: Calculate uptime (now - app start time)
    │
    └── Step 4: Build HealthResponse and return
    │
    ▼
RequestLoggingMiddleware
    ├── Logs: "[abc-123] ← 200 (5ms)"
    ├── Adds headers: X-Request-ID, X-Latency-Ms
    │
    ▼
JSON response sent to client
```

**Notice:** There are NO AI calls here. No embeddings, no LLM, no vector search.
This route just checks if the RAG chain object exists — it doesn't call it.

- 🚚 **Courier:** The step-by-step route map showing every checkpoint the courier passes from question intake to answer delivery.

---

## Line-by-Line Code Walkthrough

### File: `src/api/routes/health.py`

#### Imports and module-level setup

```python
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from src.api.models import HealthResponse, HealthStatus, ServiceHealth
from src.config import get_settings

router = APIRouter()

# Track app start time for uptime calculation
_start_time = datetime.now(timezone.utc)
```

**What each line does:**

| Line | Purpose | DE parallel | 🚚 Courier |
| --- | --- | --- | --- |
| `from fastapi import APIRouter, Request` | Create a router, access the request object | Same as shared-proxy | Entry gate to the depot — from fastapi import APIRouter, Request: Create a router, access the request object · Same as shared-proxy |
| `from src.api.models import ...` | Import Pydantic response models | Same as any FastAPI app | Entry gate to the depot — from src.api.models import ...: Import Pydantic response models · Same as any FastAPI app |
| `router = APIRouter()` | Create the router that `main.py` will register | Same pattern everywhere | Depot's front door — router = APIRouter(): Create the router that main.py will register · Same pattern everywhere |
| `_start_time = datetime.now(timezone.utc)` | Record when the module was loaded (= app startup) | Common pattern for uptime tracking | Timestamp stamped on the trip log entry — when the courier set off or returned |

**Why `_start_time` is module-level:** This line runs once when Python imports the
module (at app startup). Every subsequent call to the health check uses this same
value to calculate uptime. The underscore prefix `_` means "private to this module".

#### The route decorator

```python
@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the health status of the application and all backend services.",
)
async def health_check(request: Request) -> HealthResponse:
```

**What each part does:**

| Part | Purpose | 🚚 Courier |
| --- | --- | --- |
| `@router.get("/health")` | Registers as GET, combined with `prefix="/api"` in main.py → becomes `GET /api/health` | Marks `/api/health` as the doorway villagers knock on to check whether the courier and warehouse are awake. |
| `response_model=HealthResponse` | Tells FastAPI to serialise the return value as this model, and to show it in Swagger | Tells the depot manager which shape to pour the health reply into so Swagger and callers see consistent fields. |
| `summary` and `description` | Shown in Swagger UI (`/docs`) — human-readable documentation | Courier-side view of summary` and `description — affects how the courier loads, reads, or delivers the parcels |
| `request: Request` | Gives access to `request.app.state` where the RAG chain lives | Courier-side view of request: Request — affects how the courier loads, reads, or delivers the parcels |
| `-> HealthResponse` | Type hint for your IDE — autocompletion on the response object | Tells the IDE the exact shape of the courier's health reply — no runtime effect, just autocomplete on the response object. |

#### Step 1 — Check if the RAG chain is initialised

```python
    settings = get_settings()
    services: list[ServiceHealth] = []

    # Check if RAG chain is initialized
    rag_chain = getattr(request.app.state, "rag_chain", None)
    if rag_chain is None:
        services.append(
            ServiceHealth(
                name="rag_chain",
                status=HealthStatus.UNHEALTHY,
                message="RAG chain not initialized — check cloud credentials",
            )
        )
    else:
        services.append(
            ServiceHealth(
                name="rag_chain",
                status=HealthStatus.HEALTHY,
                message="RAG chain initialized and ready",
            )
        )
```

**What's happening step by step:**

1. `get_settings()` — loads the app configuration (which cloud provider, etc.)
2. `services: list[ServiceHealth] = []` — starts an empty list of service health checks
3. `getattr(request.app.state, "rag_chain", None)` — safely reads `rag_chain` from
   `app.state`. Returns `None` if it doesn't exist (instead of crashing with `AttributeError`)
4. If `rag_chain is None` → the AI engine failed to initialise at startup (probably
   bad AWS/Azure credentials, or the cloud service is unreachable)
5. Appends a `ServiceHealth` object with the result

**DE parallel:** In shared-proxy, you'd check `can I reach DynamoDB?` or `can I reach
an upstream API?`. Same pattern — different dependency. Here the "dependency" is the
RAG chain, which wraps the LLM + vector store + storage.

**Why `getattr()` instead of `request.app.state.rag_chain`?**

```python
# ❌ This crashes if rag_chain doesn't exist on app.state:
rag_chain = request.app.state.rag_chain   # → AttributeError

# ✅ This returns None safely:
rag_chain = getattr(request.app.state, "rag_chain", None)
```

The RAG chain is set to `None` in `main.py` if initialisation fails. Using `getattr`
with a default is a defensive pattern — the health check should never crash itself.

#### Step 2 — Determine overall status ("worst status wins")

```python
    statuses = [s.status for s in services]
    if HealthStatus.UNHEALTHY in statuses:
        overall = HealthStatus.UNHEALTHY
    elif HealthStatus.DEGRADED in statuses:
        overall = HealthStatus.DEGRADED
    else:
        overall = HealthStatus.HEALTHY
```

**The logic:**

```
If ANY service is UNHEALTHY → overall = UNHEALTHY
    (critical failure — the app can't do its job)

Else if ANY service is DEGRADED → overall = DEGRADED
    (partial failure — some features work, others don't)

Else → overall = HEALTHY
    (everything is fine)
```

**DE parallel:** This is the exact same pattern in every health check everywhere.
Kubernetes uses this to decide:
- `HEALTHY` → send traffic to this pod
- `UNHEALTHY` → stop sending traffic, maybe restart the pod
- `DEGRADED` → send traffic but alert the team

**Currently there's only one service check** (the RAG chain), but the list pattern
makes it easy to add more later (e.g., check cloud storage, check database, check
external APIs).

#### Step 3 — Calculate uptime and return

```python
    uptime = int((datetime.now(timezone.utc) - _start_time).total_seconds())

    return HealthResponse(
        status=overall,
        cloud_provider=settings.cloud_provider.value,
        services=services,
        uptime_seconds=uptime,
    )
```

**What's happening:**

1. `datetime.now(timezone.utc) - _start_time` → timedelta since app started
2. `.total_seconds()` → convert to seconds (e.g., 3661.5)
3. `int(...)` → round down to whole seconds (e.g., 3661)
4. Build `HealthResponse` with all the collected data
5. FastAPI automatically serialises it to JSON and sends it

**Example response:**

```json
{
    "status": "healthy",
    "cloud_provider": "aws",       // or "azure" or "local"
    "services": [
        {
            "name": "rag_chain",
            "status": "healthy",
            "message": "RAG chain initialized and ready"
        }
    ],
    "uptime_seconds": 3661
}
```

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## The Pydantic Response Models

Three models are used in this route:

### `HealthStatus` (Enum)

```python
class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
```

An enum with 3 possible values. Using an enum (instead of raw strings) means:
- You can't accidentally write `"healhty"` (typo) — the IDE catches it
- All possible values are documented in one place
- Swagger UI shows a dropdown with the allowed values

### `ServiceHealth` (individual service check)

```python
class ServiceHealth(BaseModel):
    name: str           # "rag_chain", "s3", "dynamodb", etc.
    status: HealthStatus  # healthy / degraded / unhealthy
    latency_ms: int | None  # How long the check took (optional)
    message: str        # Human-readable details
```

### `HealthResponse` (the full response)

```python
class HealthResponse(BaseModel):
    status: HealthStatus          # Overall status (worst of all services)
    cloud_provider: str           # "aws", "azure", or "local"
    services: list[ServiceHealth] # Individual checks
    uptime_seconds: int           # How long the app has been running
```

See [Pydantic Models Guide](../reference/pydantic-models.md) for full field details.

- 🚚 **Courier:** The shipping manifest template — every field is typed and validated before the courier is loaded, preventing mispackaged deliveries.

---

## DE Comparison

| Aspect | Shared-Proxy Health Check | RAG Chatbot Health Check | 🚚 Courier |
| --- | --- | --- | --- |
| **Endpoint** | `GET /health` or `GET /api/health` | `GET /api/health` | The exact doorway customers knock on to check the courier is awake — `GET /api/health` rather than the bare `/health`. |
| **What it checks** | Database connectivity, upstream APIs | RAG chain (LLM + vector store) | Is the courier awake and the warehouse reachable? Confirms LLM and vector store are wired up |
| **Status values** | Usually `"ok"` / `"error"` | `healthy` / `degraded` / `unhealthy` | Three-state courier verdict — healthy, degraded, or unhealthy — instead of binary ok/error so partial outages stay visible. |
| **Pattern** | Check deps → worst status wins → return | Check deps → worst status wins → return | Courier-side view of Pattern — affects how the courier loads, reads, or delivers the parcels |
| **Used by** | Kubernetes liveness/readiness probes | Same | The same Kubernetes liveness and readiness probes that poll any other depot also poll this one to decide if the courier gets restarted. |
| **AI concepts** | None | None — it only checks if rag_chain is not None | Courier-side view of AI concepts — affects how the courier loads, reads, or delivers the parcels |

**Bottom line:** If you can write a health check in shared-proxy, you can write this
one. There's nothing new to learn here.

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## What's the Only New Thing?

The only AI-adjacent thing in this entire route is **what** it's checking:

```python
rag_chain = getattr(request.app.state, "rag_chain", None)
```

In shared-proxy, you'd check a database pool. Here you check the RAG chain. But you
don't need to understand what the RAG chain does to understand this health check —
you only need to know that if it's `None`, the app can't answer questions.

To understand what the RAG chain actually is and how it works, read:
- [Chat Endpoint Deep Dive](chat-endpoint-explained.md) — how `rag_chain.query()` works
- [Documents Endpoint Deep Dive](documents-endpoint-explained.md) — how `rag_chain.ingest_document()` works

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Self-Check Questions

After reading this, can you answer:

- [ ] What does `_start_time` track and why is it module-level?
- [ ] Why `getattr(request.app.state, "rag_chain", None)` instead of accessing it directly?
- [ ] What does the "worst status wins" pattern do?
- [ ] Who calls this endpoint in production? (Kubernetes/ECS health probes)
- [ ] Is there any AI-specific code in this route? (No — just checking if rag_chain exists)

- 🚚 **Courier:** A quick quiz for the trainee dispatch clerk — answer these to confirm the key courier delivery concepts have landed.
