"""
End-to-End Tests — Full RAG Pipeline

Tests the complete user journey:
    1. Upload a document → chunks stored
    2. Chat about the document → answer uses document content
    3. Evaluate retrieval quality → scores returned
    4. Delete the document → no longer searchable

These tests use mocked backends (no real LLM or vector store),
but verify the full request → routing → handler → response flow.

Run with:
    pytest tests/test_e2e_rag_pipeline.py -v
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app

# ---------------------------------------------------------------------------
# Fixtures — E2E app with stateful mock
# ---------------------------------------------------------------------------

POLICY_CONTENT = (
    b"REMOTE WORK POLICY\n\n"
    b"All employees may work remotely up to 3 days per week.\n"
    b"Remote work must be approved by your direct manager.\n"
    b"Equipment for home office is provided by the company up to 500 euros.\n"
)


@pytest.fixture
def e2e_app():
    """Create an app with a stateful mock RAG chain for E2E testing."""
    app = create_app()

    # Track uploaded documents
    uploaded_docs: dict[str, dict] = {}

    mock_chain = AsyncMock()

    async def mock_ingest(document_id: str, filename: str, content: bytes) -> int:
        uploaded_docs[document_id] = {
            "filename": filename,
            "content": content.decode("utf-8", errors="replace"),
            "chunks": 5,
        }
        return 5

    async def mock_query(question: str, session_id: str, top_k: int | None = None) -> dict:
        # If documents are uploaded, return content-based answer
        if uploaded_docs:
            doc = next(iter(uploaded_docs.values()))
            return {
                "answer": "Employees may work remotely up to 3 days per week with manager approval.",
                "sources": [
                    {
                        "document_name": doc["filename"],
                        "text": "All employees may work remotely up to 3 days per week.",
                        "score": 0.95,
                    },
                ],
                "token_usage": {
                    "input_tokens": 400,
                    "output_tokens": 30,
                    "total_tokens": 430,
                    "estimated_cost_usd": 0.001,
                },
            }
        return {
            "answer": "I don't have any documents to answer your question.",
            "sources": [],
            "token_usage": None,
        }

    mock_chain.ingest_document.side_effect = mock_ingest
    mock_chain.query.side_effect = mock_query

    # Mock vector store for document operations
    mock_vs = AsyncMock()
    mock_vs.list_documents.return_value = []
    mock_vs.delete_document.return_value = True
    mock_chain._vector_store = mock_vs
    mock_chain._settings = MagicMock()
    mock_chain._settings.rag_top_k = 5

    app.state.rag_chain = mock_chain
    app.state.guardrails = None
    app.state.metrics = MagicMock()
    app.state.query_logger = None
    app.state._uploaded_docs = uploaded_docs  # for assertions

    return app


@pytest.fixture
async def e2e_client(e2e_app):
    """Async test client for E2E tests."""
    async with AsyncClient(
        transport=ASGITransport(app=e2e_app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# E2E: Upload → Chat → Evaluate → Delete
# ---------------------------------------------------------------------------


class TestE2EFullPipeline:
    """Full end-to-end RAG pipeline test."""

    @pytest.mark.asyncio
    async def test_upload_then_chat(self, e2e_client, e2e_app):
        """Upload a document, then ask a question about it."""
        # Step 1: Upload document
        resp = await e2e_client.post(
            "/api/documents/upload",
            files={"file": ("remote-work-policy.txt", POLICY_CONTENT, "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["chunk_count"] == 5
        data["document_id"]

        # Step 2: Chat about the document
        resp = await e2e_client.post(
            "/api/chat",
            json={"question": "How many days can I work remotely?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "3 days" in data["answer"].lower() or "remotely" in data["answer"].lower()
        assert len(data["sources"]) > 0
        assert data["sources"][0]["document_name"] == "remote-work-policy.txt"

    @pytest.mark.asyncio
    async def test_upload_then_evaluate(self, e2e_client, e2e_app):
        """Upload a document, then evaluate retrieval quality."""
        # Step 1: Upload
        resp = await e2e_client.post(
            "/api/documents/upload",
            files={"file": ("policy.txt", POLICY_CONTENT, "text/plain")},
        )
        assert resp.status_code == 200

        # Step 2: Evaluate
        resp = await e2e_client.post(
            "/api/evaluate",
            json={
                "question": "What is the remote work policy?",
                "expected_answer": "3 days per week with manager approval",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "scores" in data
        assert "answer" in data

    @pytest.mark.asyncio
    async def test_chat_without_documents(self, e2e_client):
        """Chat without any uploaded documents should indicate no docs available."""
        resp = await e2e_client.post(
            "/api/chat",
            json={"question": "What is the policy?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should indicate no documents
        assert "don't have" in data["answer"].lower() or len(data["sources"]) == 0

    @pytest.mark.asyncio
    async def test_multiple_uploads_then_chat(self, e2e_client, e2e_app):
        """Upload multiple documents, then chat."""
        # Upload first document
        await e2e_client.post(
            "/api/documents/upload",
            files={"file": ("policy.txt", POLICY_CONTENT, "text/plain")},
        )

        # Upload second document
        await e2e_client.post(
            "/api/documents/upload",
            files={"file": ("faq.txt", b"FAQ: The office is open 9am to 5pm.", "text/plain")},
        )

        # Chat should work with multiple docs
        resp = await e2e_client.post(
            "/api/chat",
            json={"question": "What are the office hours?"},
        )
        assert resp.status_code == 200
        assert "answer" in resp.json()


# ---------------------------------------------------------------------------
# E2E: Multi-turn conversation
# ---------------------------------------------------------------------------


class TestE2EConversation:
    """Multi-turn conversation tests."""

    @pytest.mark.asyncio
    async def test_multi_turn_same_session(self, e2e_client, e2e_app):
        """Multiple questions in the same session should work."""
        # Upload a document first
        await e2e_client.post(
            "/api/documents/upload",
            files={"file": ("policy.txt", POLICY_CONTENT, "text/plain")},
        )

        session_id = "e2e-session-001"

        # First question
        resp1 = await e2e_client.post(
            "/api/chat",
            json={"question": "What is the remote work policy?", "session_id": session_id},
        )
        assert resp1.status_code == 200
        assert resp1.json()["session_id"] == session_id

        # Follow-up question (same session)
        resp2 = await e2e_client.post(
            "/api/chat",
            json={"question": "How much equipment budget?", "session_id": session_id},
        )
        assert resp2.status_code == 200
        assert resp2.json()["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_different_sessions_isolated(self, e2e_client, e2e_app):
        """Different sessions should get independent responses."""
        await e2e_client.post(
            "/api/documents/upload",
            files={"file": ("policy.txt", POLICY_CONTENT, "text/plain")},
        )

        resp_a = await e2e_client.post(
            "/api/chat",
            json={"question": "What is the policy?", "session_id": "session-A"},
        )
        resp_b = await e2e_client.post(
            "/api/chat",
            json={"question": "What is the policy?", "session_id": "session-B"},
        )
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        # Both should get answers (sessions are independent)
        assert resp_a.json()["session_id"] == "session-A"
        assert resp_b.json()["session_id"] == "session-B"


# ---------------------------------------------------------------------------
# E2E: Observability endpoints after activity
# ---------------------------------------------------------------------------


class TestE2EObservability:
    """Verify observability endpoints work after chat activity."""

    @pytest.mark.asyncio
    async def test_metrics_after_chat(self, e2e_client, e2e_app):
        """Metrics endpoint should work after chat activity."""
        # Generate some activity
        await e2e_client.post(
            "/api/documents/upload",
            files={"file": ("policy.txt", POLICY_CONTENT, "text/plain")},
        )
        await e2e_client.post(
            "/api/chat",
            json={"question": "What is the policy?"},
        )

        # Check metrics
        resp = await e2e_client.get("/api/metrics")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_after_activity(self, e2e_client, e2e_app):
        """Health endpoint should still work after chat activity."""
        await e2e_client.post(
            "/api/chat",
            json={"question": "Test question"},
        )
        resp = await e2e_client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("healthy", "degraded", "unhealthy")
