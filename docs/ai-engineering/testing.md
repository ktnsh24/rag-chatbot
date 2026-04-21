# Testing Strategy & Inventory

> How the RAG Chatbot is tested — unit, integration, E2E, and feature-flag tests.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Test Architecture](#test-architecture)
- [Test Pyramid](#test-pyramid)
- [Shared Fixtures (`conftest.py`)](#shared-fixtures-conftestpy)
- [Unit Tests](#unit-tests)
- [Integration Tests](#integration-tests)
- [End-to-End Tests](#end-to-end-tests)
- [Feature Flag Tests](#feature-flag-tests)
- [Full Test Inventory](#full-test-inventory)
- [Known Issues](#known-issues)
- [DE Parallel](#de-parallel)

---

## Quick Start

```bash
# Run all tests
poetry run pytest tests/ -v

# Run only the new integration + E2E + feature tests
poetry run pytest tests/test_integration_api.py tests/test_e2e_rag_pipeline.py tests/test_integration_features.py -v

# Run with coverage
poetry run pytest tests/ --cov=src --cov-report=term-missing

# Run a specific test class
poetry run pytest tests/test_integration_api.py::TestChatIntegration -v
```

---

## Test Architecture

```
tests/
├── conftest.py                    # Shared fixtures (mock RAG chain, clients, guardrails)
├── test_chat.py                   # Unit: /api/chat route logic
├── test_evaluate_route.py         # Unit: /api/evaluate route logic
├── test_ingestion.py              # Unit: document ingestion pipeline
├── test_evaluation.py             # Unit: evaluation framework
├── test_guardrails.py             # Unit: guardrail pattern matching
├── test_reranker.py               # Unit: cross-encoder re-ranking
├── test_hybrid_search.py          # Unit: BM25 + vector hybrid search
├── test_dynamodb_vectorstore.py   # Unit: DynamoDB vector store
├── test_integration_api.py        # Integration: all API endpoints
├── test_e2e_rag_pipeline.py       # E2E: upload → chat → evaluate flows
└── test_integration_features.py   # Feature flags: guardrails ON/OFF, PII
```

All tests run **without external services** — no Ollama, no cloud APIs, no databases. They use `AsyncMock` for the RAG chain and `LocalGuardrails` (real implementation, no network calls) for guardrail tests.

---

## Test Pyramid

```
        ╱╲
       ╱ E2E ╲          8 tests — full user journeys
      ╱────────╲
     ╱ Feature   ╲      12 tests — guardrails ON/OFF, PII
    ╱──────────────╲
   ╱  Integration    ╲   23 tests — all API endpoints
  ╱────────────────────╲
 ╱      Unit Tests       ╲  103 tests — components in isolation
╱──────────────────────────╲
         146 total
```

---

## Shared Fixtures (`conftest.py`)

All integration/E2E/feature tests share fixtures defined in `tests/conftest.py`:

| Fixture | What it provides |
|---|---|
| `mock_rag_chain` | `AsyncMock` with `.query()`, `.ingest_document()`, `.ingest_documents()`, `._vector_store` |
| `app_with_rag` | `create_app()` with mocked RAG chain on `app.state` |
| `client_with_rag` | `httpx.AsyncClient` using `ASGITransport` — full async HTTP testing |
| `app_no_rag` | App where `app.state.rag_chain = None` (simulates init failure) |
| `client_no_rag` | Client for testing error paths when RAG chain is unavailable |
| `mock_guardrails` | Real `LocalGuardrails()` instance (pattern-based, no network) |
| `app_with_guardrails` | App with both RAG chain and guardrails enabled |
| `client_with_guardrails` | Client for testing guardrail behavior end-to-end |

**Mock response constant:**

```python
MOCK_QUERY_RESPONSE = {
    "answer": "Employees may work remotely up to 3 days per week...",
    "sources": [{"document_name": "remote-work-policy.txt", "score": 0.92}, ...],
    "token_usage": {"input_tokens": 450, "output_tokens": 40, "total_tokens": 490},
}
```

---

## Unit Tests

Existing unit tests cover individual components in isolation:

| File | Tests | What it covers |
|---|---|---|
| `test_chat.py` | 7 | Chat route logic, request validation, error handling |
| `test_evaluate_route.py` | 16 | Evaluate route logic, response format, error handling |
| `test_ingestion.py` | 9 | Document chunking, ingestion pipeline, deduplication |
| `test_evaluation.py` | 14 | Evaluation framework, metrics computation, golden dataset |
| `test_guardrails.py` | 20 | Guardrail pattern matching, PII regex, injection detection |
| `test_reranker.py` | 7 | Cross-encoder scoring, re-ranking logic |
| `test_hybrid_search.py` | 17 | BM25 tokenization, hybrid score fusion |
| `test_dynamodb_vectorstore.py` | 13 | DynamoDB CRUD, vector storage, batch operations |
| **Total** | **103** | |

---

## Integration Tests

**File:** `tests/test_integration_api.py` — **23 tests**

Tests every API endpoint through the full FastAPI stack (middleware, routing, serialization) using `httpx.AsyncClient` with `ASGITransport`. The RAG chain is mocked but all FastAPI machinery runs for real.

| Class | Tests | What it validates |
|---|---|---|
| `TestHealthIntegration` | 2 | `GET /health` returns status + services; degrades when RAG chain is missing |
| `TestChatIntegration` | 6 | `POST /api/chat` — success, session IDs, custom `top_k`, validation (empty/missing question), 500 without RAG |
| `TestEvaluateIntegration` | 3 | `POST /api/evaluate` — single question, expected answer comparison, 500 without RAG |
| `TestDocumentsIntegration` | 4 | `GET /api/documents`, `POST /api/documents/upload`, `POST /api/documents/upload/batch`, `DELETE /api/documents/{id}` |
| `TestQueryAnalysisIntegration` | 4 | `GET /api/queries/stats`, `/api/queries/slow`, `/api/queries/patterns`, `/api/queries/recent` — returns 503 when query logger not configured |
| `TestMetricsIntegration` | 1 | `GET /metrics` returns Prometheus format |
| `TestErrorHandling` | 3 | Invalid JSON, wrong content type, non-existent endpoint |

---

## End-to-End Tests

**File:** `tests/test_e2e_rag_pipeline.py` — **8 tests**

Simulates complete user journeys through the system. Uses a **stateful mock** that tracks uploaded documents — when you upload a doc, subsequent chat queries return content-aware answers.

| Class | Tests | What it validates |
|---|---|---|
| `TestE2EFullPipeline` | 4 | Upload → chat (gets relevant answer), upload → evaluate (scores returned), chat without docs (empty answer), multiple uploads → chat |
| `TestE2EConversation` | 2 | Multi-turn conversation in same session, session isolation between users |
| `TestE2EObservability` | 2 | Metrics counter increments after chat, health endpoint remains up after activity |

**Stateful mock pattern:**

```python
uploaded_docs: dict[str, str] = {}  # tracks doc_id → content

async def mock_ingest(content, filename, **kwargs):
    doc_id = str(uuid.uuid4())
    uploaded_docs[doc_id] = content
    return 5  # chunks

async def mock_query(question, **kwargs):
    if uploaded_docs:
        return {"answer": f"Based on {len(uploaded_docs)} documents...", ...}
    return {"answer": "No documents available", ...}
```

---

## Feature Flag Tests

**File:** `tests/test_integration_features.py` — **12 tests**

Tests the guardrails feature flag (`GUARDRAILS_ENABLED`) by comparing behavior with guardrails ON vs OFF. Uses real `LocalGuardrails` (not mocked) — tests actual regex patterns.

| Class | Tests | What it validates |
|---|---|---|
| `TestGuardrailsInjection` | 4 | Prompt injection blocked (400), jailbreak blocked (400), safe questions pass, multiple safe questions pass |
| `TestGuardrailsPII` | 3 | Email/SSN/credit card detected and flagged in responses |
| `TestGuardrailsOff` | 2 | Same injection/PII queries pass through when guardrails disabled |
| `TestFeatureFlagBehavior` | 3 | Evaluate works regardless of features, chat includes `cloud_provider`, health always available |

---

## Full Test Inventory

| Test File | Tests | Type | Status |
|---|---|---|---|
| `test_chat.py` | 7 | Unit | ✅ Passing |
| `test_evaluate_route.py` | 16 | Unit | ✅ Passing |
| `test_ingestion.py` | 9 | Unit | ✅ Passing |
| `test_evaluation.py` | 14 | Unit | ✅ Passing |
| `test_guardrails.py` | 20 | Unit | ⚠️ 4 failures (redaction tag naming) |
| `test_reranker.py` | 7 | Unit | ⚠️ 3 failures (score mismatches) |
| `test_hybrid_search.py` | 17 | Unit | ⚠️ 9 errors (missing `rank_bm25` package) |
| `test_dynamodb_vectorstore.py` | 13 | Unit | ✅ Passing |
| `test_integration_api.py` | 23 | Integration | ✅ All 23 passing |
| `test_e2e_rag_pipeline.py` | 8 | E2E | ✅ All 8 passing |
| `test_integration_features.py` | 12 | Feature flags | ✅ All 12 passing |
| **Total** | **146** | | **130 passing, 7 failing, 9 errors** |

---

## Known Issues

| Test File | Issue | Root Cause |
|---|---|---|
| `test_guardrails.py` | 4 failures | Tests expect `[REDACTED_EMAIL]` but code produces `[EMAIL_REDACTED]` (naming convention mismatch) |
| `test_reranker.py` | 3 failures | Expected re-ranking scores don't match actual cross-encoder output |
| `test_hybrid_search.py` | 9 errors | Missing `rank_bm25` package — install with `poetry add rank_bm25` |

These are **pre-existing issues** unrelated to the integration/E2E tests.

---

## DE Parallel

| AI Engineering Test | Data Engineering Equivalent |
|---|---|
| Mock RAG chain with `AsyncMock` | Mock DynamoDB with `moto`, mock S3 with `moto` |
| `httpx.AsyncClient` + `ASGITransport` | `TestClient` for Flask/FastAPI in ETL APIs |
| Stateful E2E mock (upload → query) | Integration test: load → transform → query with real Spark/Pandas |
| Feature flag tests (guardrails ON/OFF) | Feature flag tests (data validation strict/lenient mode) |
| `conftest.py` shared fixtures | `conftest.py` shared fixtures (same pattern, same tool) |

---

## Related Docs

- [Architecture](../architecture-and-design/architecture.md) — system design and component map
- [Getting Started](../setup-and-tooling/getting-started.md) — setup instructions including test commands
- [Cost Analysis](cost-analysis.md) — what it costs to run tests with cloud providers

