# API Reference

Complete reference for every endpoint in the RAG Chatbot API.

**Base URL:** `http://localhost:8000` (local) or your deployed URL.

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

---

## Chat

### `POST /api/chat`

Send a question and get an answer grounded in your uploaded documents.

**Request Body:**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `message` | string | ✅ | — | The user's question |
| `session_id` | string | ❌ | auto-generated UUID | Conversation session ID for history |
| `max_sources` | integer | ❌ | `5` | Max source chunks to retrieve |

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

---

## Documents

### `POST /api/documents/upload`

Upload a document for RAG ingestion. The document is stored, split into chunks,
embedded, and indexed in the vector store.

**Content-Type:** `multipart/form-data`

**Form Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | ✅ | The document file (PDF, TXT, MD, CSV, DOCX) |

**Supported file types:**
- `.pdf` — Portable Document Format
- `.txt` — Plain text
- `.md` — Markdown
- `.csv` — Comma-separated values
- `.docx` — Microsoft Word

**Example (cURL):**

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@./my-document.pdf"
```

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

| Parameter | Type | Description |
|---|---|---|
| `document_id` | string | The document's unique ID |

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

## Chat UI

### `GET /`

Serves the built-in chat web interface. Open this URL in your browser
to interact with the chatbot through a graphical interface.

---

## Error Responses

All error responses follow a consistent format:

```json
{
  "detail": "Human-readable error message"
}
```

**Common HTTP Status Codes:**

| Code | Meaning |
|---|---|
| `200` | Success |
| `400` | Bad request — check your input |
| `404` | Resource not found |
| `413` | Payload too large |
| `500` | Internal server error |
| `503` | Service unavailable — a dependency is down |

---

## Authentication (Future)

> **Note:** Authentication is not implemented in v0.1.0.
> Planned for v0.2.0: API key authentication via `X-API-Key` header.

---

## Rate Limiting (Future)

> **Note:** Rate limiting is not implemented in v0.1.0.
> Planned for v0.2.0: 60 requests/minute per API key.

---

## Interactive Docs

FastAPI provides auto-generated interactive API documentation:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

These are available in development and can be disabled in production via the
`DOCS_ENABLED` environment variable.
