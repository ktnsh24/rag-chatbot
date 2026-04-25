# API Reference

Complete reference for every endpoint in the RAG Chatbot API.

**Base URL:** `http://localhost:8000` (local) or your deployed URL.

> 📖 **New to this codebase?** Start with the [API Routes — Overview](../architecture-and-design/api-routes-explained.md)
> to see how `main.py` wires everything together, then dive into each route:
> [Health](../architecture-and-design/api-routes/health-endpoint-explained.md) ·
> [Chat](../architecture-and-design/api-routes/chat-endpoint-explained.md) ·
> [Documents](../architecture-and-design/api-routes/documents-endpoint-explained.md) ·
> [Evaluate](../architecture-and-design/api-routes/evaluate-endpoint-explained.md) ·
> Queries (I30) · Metrics (I31).
> This reference doc covers the *what* (specs and examples). The deep dives cover
> the *why* and *how* — including embeddings, tokens, cosine similarity, and chunking.

---

## Health Check

### `GET /api/health`

Returns the health status of the application and its connected services.

**Response `200 OK`:**

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "cloud_provider": "aws",
  "services": {
    "llm": {
      "status": "healthy",
      "latency_ms": 120.5
    },
    "vector_store": {
      "status": "healthy",
      "latency_ms": 45.2
    },
    "storage": {
      "status": "healthy",
      "latency_ms": 30.1
    }
  }
}
```

**Response `503 Service Unavailable`** (when a critical service is down):

```json
{
  "status": "unhealthy",
  "version": "0.1.0",
  "cloud_provider": "aws",
  "services": {
    "llm": {
      "status": "unhealthy",
      "latency_ms": null,
      "error": "Connection refused"
    }
  }
}
```

- 🫏 **Donkey:** Checking whether the donkey is awake, saddled, and ready to run before dispatching it.

---

## Chat

### `POST /api/chat`

Send a question and get an answer grounded in your uploaded documents.

**Request Body:**

| Field | Type | Required | Default | Description | 🫏 Donkey |
|---|---|---|---|---| --- |
| `message` | string | ✅ | — | The user's question | 🫏 On the route |
| `session_id` | string | ❌ | auto-generated UUID | Conversation session ID for history | Trip log 📒 |
| `max_sources` | integer | ❌ | `5` | Max source chunks to retrieve | Saddlebag piece 📦 |

**Example Request:**

```json
{
  "message": "What is the refund policy?",
  "session_id": "abc-123-def",
  "max_sources": 3
}
```

**Response `200 OK`:**

```json
{
  "answer": "According to the policy document, refunds are processed within 14 business days...",
  "session_id": "abc-123-def",
  "sources": [
    {
      "content": "Refunds are processed within 14 business days of the return being received...",
      "document_id": "doc-456",
      "document_name": "refund-policy.pdf",
      "relevance_score": 0.92,
      "page_number": 3
    }
  ],
  "token_usage": {
    "prompt_tokens": 1250,
    "completion_tokens": 180,
    "total_tokens": 1430,
    "estimated_cost_usd": 0.0043
  }
}
```

**Response `400 Bad Request`:**

```json
{
  "detail": "Message cannot be empty"
}
```

**Response `503 Service Unavailable`:**

```json
{
  "detail": "LLM service is currently unavailable"
}
```

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Documents

### `POST /api/documents/upload`

Upload a document for RAG ingestion. The document is stored, split into chunks,
embedded, and indexed in the vector store.

**Content-Type:** `multipart/form-data`

**Form Fields:**

| Field | Type | Required | Description | 🫏 Donkey |
|---|---|---|---| --- |
| `file` | file | ✅ | The document file (PDF, TXT, MD, CSV, DOCX) | 🫏 On the route |

**Supported file types:**
- `.pdf` — Portable Document Format
- `.txt` — Plain text
- `.md` — Markdown
- `.csv` — Comma-separated values
- `.docx` — Microsoft Word

**Example (Swagger UI):**

1. Open `http://localhost:8000/docs`
2. Find `POST /api/documents/upload` → click **"Try it out"**
3. Click **"Choose File"** and select your document
4. Click **"Execute"**

**Example (Python):**

```python
import httpx

async with httpx.AsyncClient() as client:
    with open("my-document.pdf", "rb") as f:
        response = await client.post(
            "http://localhost:8000/api/documents/upload",
            files={"file": ("my-document.pdf", f, "application/pdf")},
        )
    print(response.json())
```

**Response `200 OK`:**

```json
{
  "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "filename": "my-document.pdf",
  "chunks_created": 42,
  "status": "indexed"
}
```

**Response `400 Bad Request`:**

```json
{
  "detail": "Unsupported file type: .exe"
}
```

**Response `413 Request Entity Too Large`:**

```json
{
  "detail": "File size exceeds the 50 MB limit"
}
```

- 🫏 **Donkey:** The parcels being ingested — split into saddlebag-sized chunks, GPS-stamped, and shelved in the warehouse for the donkey to retrieve later.

---

### `GET /api/documents`

List all uploaded documents.

**Response `200 OK`:**

```json
{
  "documents": [
    {
      "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "filename": "my-document.pdf",
      "size_bytes": 1048576,
      "uploaded_at": "2025-03-29T10:30:00Z",
      "chunks_count": 42
    },
    {
      "document_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "filename": "faq.md",
      "size_bytes": 4096,
      "uploaded_at": "2025-03-29T11:00:00Z",
      "chunks_count": 5
    }
  ],
  "total": 2
}
```

---

### `DELETE /api/documents/{document_id}`

Delete a document and all its associated vector embeddings.

**Path Parameters:**

| Parameter | Type | Description | 🫏 Donkey |
|---|---|---| --- |
| `document_id` | string | The document's unique ID | 🫏 On the route |

**Response `200 OK`:**

```json
{
  "status": "deleted",
  "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Response `404 Not Found`:**

```json
{
  "detail": "Document not found: a1b2c3d4-..."
}
```

---

## Evaluation

### `POST /api/evaluate`

Evaluate a single question through the live RAG pipeline. Returns the answer
AND quality scores (retrieval, faithfulness, answer relevance, overall).

**Request Body:**

| Field | Type | Required | Default | Description | 🫏 Donkey |
|---|---|---|---|---| --- |
| `question` | string | ✅ | — | The question to evaluate | Report card 📝 |
| `expected_answer` | string | ❌ | `null` | Optional ground truth for comparison | 🫏 On the route |
| `top_k` | integer | ❌ | `5` | Number of chunks to retrieve | Saddlebag piece 📦 |

**Example Request:**

```json
{
  "question": "What is the refund policy?",
  "expected_answer": "Refunds take 14 business days."
}
```

**Response `200 OK`:**

```json
{
  "question": "What is the refund policy?",
  "answer": "Refunds are processed within 14 business days...",
  "scores": {
    "retrieval": 0.885,
    "retrieval_quality": "excellent",
    "faithfulness": 0.95,
    "has_hallucination": false,
    "answer_relevance": 0.75,
    "answer_relevance_quality": "partially relevant",
    "overall": 0.862,
    "passed": true
  },
  "sources_used": 3,
  "evaluation_notes": [],
  "cloud_provider": "local",
  "latency_ms": 2450,
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

- 🫏 **Donkey:** The donkey's report card — did it grab the right saddlebags and write an accurate answer?

---

### `POST /api/evaluate/suite`

Run the full golden dataset evaluation suite. Returns a scorecard with
per-case results and aggregated metrics.

**Request Body:**

| Field | Type | Required | Default | Description | 🫏 Donkey |
|---|---|---|---|---| --- |
| `categories` | string[] | ❌ | all | Filter by test categories (e.g. `["policy", "edge_case"]`) | Test delivery 🧪 |
| `top_k` | integer | ❌ | `5` | Override top_k for all cases | 🫏 On the route |

**Example Request:**

```json
{
  "categories": ["policy"]
}
```

**Response `200 OK`:**

```json
{
  "total_cases": 5,
  "passed": 4,
  "failed": 1,
  "pass_rate": 80.0,
  "average_overall_score": 0.782,
  "cases": [
    {
      "case_id": "refund_basic",
      "category": "policy",
      "question": "What is the refund policy?",
      "answer_preview": "Refunds are processed within 14 business days...",
      "scores": {
        "retrieval": 0.885,
        "retrieval_quality": "excellent",
        "faithfulness": 0.95,
        "has_hallucination": false,
        "answer_relevance": 0.75,
        "answer_relevance_quality": "partially relevant",
        "overall": 0.862,
        "passed": true
      },
      "passed": true,
      "notes": [],
      "latency_ms": 2100
    }
  ],
  "cloud_provider": "local",
  "latency_ms": 12500,
  "request_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"
}
```

---

## Query Debugging (I30)

### `GET /api/queries/failures`

List recent queries that failed evaluation. Use this to diagnose production issues.

**Query Parameters:**

| Param | Type | Default | Description | 🫏 Donkey |
|---|---|---|---| --- |
| `limit` | integer | `20` | Max results (1–100) | 🫏 On the route |
| `days` | integer | `7` | How many days back (1–30) | 🫏 On the route |
| `category` | string | all | Filter: `bad_retrieval`, `hallucination`, `both_bad`, `off_topic`, `marginal` | Memory drift ⚠️ |

**Example:**

```
GET /api/queries/failures?category=hallucination&limit=5&days=3
```

**Response `200 OK`:**

```json
[
  {
    "request_id": "a1b2c3d4-...",
    "timestamp": "2026-04-17T14:32:05Z",
    "question": "What is the cancellation policy?",
    "answer": "You can cancel within 24 hours...",
    "chunks": [
      {"text": "Refunds are processed within 14 business days.", "score": 0.35}
    ],
    "retrieval_score": 0.35,
    "faithfulness_score": 0.20,
    "answer_relevance_score": 0.40,
    "overall_score": 0.32,
    "failure_category": "hallucination",
    "latency_ms": 3200
  }
]
```

**Response `503`** — Query logger not initialised (check `QUERY_LOG_ENABLED`).

- 🫏 **Donkey:** Checking the donkey's hooves, saddle straps, and GPS signal before concluding it's lost — most delivery failures have a simple root cause.

---

### `GET /api/queries/stats`

Aggregate query quality statistics for dashboards and monitoring.

**Query Parameters:**

| Param | Type | Default | Description | 🫏 Donkey |
|---|---|---|---| --- |
| `days` | integer | `1` | How many days to aggregate (1–30) | 🫏 On the route |

**Example:**

```
GET /api/queries/stats?days=7
```

**Response `200 OK`:**

```json
{
  "total_queries": 142,
  "passed": 118,
  "failed": 24,
  "pass_rate": 83.1,
  "avg_retrieval": 0.74,
  "avg_faithfulness": 0.81,
  "avg_relevance": 0.69,
  "failure_breakdown": {
    "none": 118,
    "bad_retrieval": 12,
    "hallucination": 5,
    "off_topic": 4,
    "marginal": 3
  }
}
```

---

## Prometheus Metrics (I31)

### `GET /api/metrics`

Returns application metrics in Prometheus text exposition format. Configure your Prometheus scraper to hit this endpoint.

**Response `200 OK` (`text/plain`):**

```
# HELP rag_chat_requests_total Total chat requests processed.
# TYPE rag_chat_requests_total counter
rag_chat_requests_total 847

# HELP rag_chat_errors_total Total chat request errors.
# TYPE rag_chat_errors_total counter
rag_chat_errors_total 12

# HELP rag_chat_latency_p50_ms Chat latency 50th percentile in ms.
# TYPE rag_chat_latency_p50_ms gauge
rag_chat_latency_p50_ms 2340.0

# HELP rag_chat_latency_p95_ms Chat latency 95th percentile in ms.
# TYPE rag_chat_latency_p95_ms gauge
rag_chat_latency_p95_ms 4120.0

# HELP rag_tokens_input_total Total input tokens consumed.
# TYPE rag_tokens_input_total counter
rag_tokens_input_total 52340

# HELP rag_queries_pass_rate_percent Evaluation pass rate today.
# TYPE rag_queries_pass_rate_percent gauge
rag_queries_pass_rate_percent 83.1

# HELP rag_queries_failure_hallucination Queries failing with hallucination today.
# TYPE rag_queries_failure_hallucination gauge
rag_queries_failure_hallucination 5
```

**Metrics exposed:**

| Metric | Type | Description | 🫏 Donkey |
|---|---|---| --- |
| `rag_chat_requests_total` | counter | Total chat requests | Saddlebag check 🫏 |
| `rag_chat_errors_total` | counter | Total chat errors | Saddlebag check 🫏 |
| `rag_chat_error_rate_percent` | gauge | Current error rate % | Saddlebag check 🫏 |
| `rag_chat_latency_p50/p95/p99_ms` | gauge | Latency percentiles | Saddlebag check 🫏 |
| `rag_tokens_input_total` | counter | Total input tokens | Cargo unit ⚖️ |
| `rag_tokens_output_total` | counter | Total output tokens | Cargo unit ⚖️ |
| `rag_tokens_cost_usd_total` | counter | Estimated cost in USD | Cargo unit ⚖️ |
| `rag_documents_ingested_total` | counter | Documents ingested | Saddlebag check 🫏 |
| `rag_chunks_created_total` | counter | Chunks created | Saddlebag piece 📦 |
| `rag_uptime_seconds` | gauge | App uptime | Saddlebag check 🫏 |
| `rag_queries_total` | gauge | Queries logged today | Saddlebag check 🫏 |
| `rag_queries_pass_rate_percent` | gauge | Pass rate today | Saddlebag check 🫏 |
| `rag_queries_avg_retrieval` | gauge | Avg retrieval score | Saddlebag fetch 🎒 |
| `rag_queries_avg_faithfulness` | gauge | Avg faithfulness score | Saddlebag check 🫏 |
| `rag_queries_failure_{category}` | gauge | Failures by category | Saddlebag check 🫏 |

- 🫏 **Donkey:** The tachograph reading — every delivery time, token cost, and quality score recorded for review.

---

## Chat UI

### `GET /`

Serves the built-in chat web interface. Open this URL in your browser
to interact with the chatbot through a graphical interface.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Error Responses

All error responses follow a consistent format:

```json
{
  "detail": "Human-readable error message"
}
```

**Common HTTP Status Codes:**

| Code | Meaning | 🫏 Donkey |
|---|---| --- |
| `200` | Success | 🫏 On the route |
| `400` | Bad request — check your input | 🫏 On the route |
| `404` | Resource not found | 🫏 On the route |
| `413` | Payload too large | 🫏 On the route |
| `500` | Internal server error | Hoof check 🔧 |
| `503` | Service unavailable — a dependency is down | 🫏 On the route |

- 🫏 **Donkey:** When the donkey returns empty-hooved — use the trip log and saddle inspection checklist to find what went wrong.

---

## Authentication (Future)

> **Note:** Authentication is not implemented in v0.1.0.
> Planned for v0.2.0: API key authentication via `X-API-Key` header.

- 🫏 **Donkey:** The stable's lock and key — only authorised riders can dispatch the donkey.

---

## Rate Limiting (Future)

> **Note:** Rate limiting is not implemented in v0.1.0.
> Planned for v0.2.0: 60 requests/minute per API key.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Interactive Docs

FastAPI provides auto-generated interactive API documentation:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

These are available in development and can be disabled in production via the
`DOCS_ENABLED` environment variable.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.
