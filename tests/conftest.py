"""
Shared test fixtures for all test modules.

Provides:
    - mock_rag_chain: A fully-mocked RAGChain with configurable responses
    - app_with_rag: A FastAPI app with mocked RAG chain on app.state
    - client_with_rag: An async test client with working RAG chain
    - mock_guardrails: A mocked LocalGuardrails instance
    - app_with_guardrails: App with both RAG chain and guardrails enabled

Usage:
    pytest tests/ -v
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app

# ---------------------------------------------------------------------------
# Mock RAG chain
# ---------------------------------------------------------------------------

MOCK_QUERY_RESPONSE = {
    "answer": "Employees may work remotely up to 3 days per week with manager approval.",
    "sources": [
        {
            "document_name": "remote-work-policy.txt",
            "text": "All employees may work remotely up to 3 days per week.",
            "score": 0.92,
        },
        {
            "document_name": "remote-work-policy.txt",
            "text": "Remote work must be approved by your direct manager.",
            "score": 0.87,
        },
    ],
    "token_usage": {
        "input_tokens": 450,
        "output_tokens": 40,
        "total_tokens": 490,
        "estimated_cost_usd": 0.002,
    },
}


@pytest.fixture
def mock_rag_chain() -> AsyncMock:
    """Create a mock RAG chain with default responses."""
    chain = AsyncMock()
    chain.query.return_value = MOCK_QUERY_RESPONSE.copy()
    chain.ingest_document.return_value = 5  # 5 chunks created
    chain.ingest_documents.return_value = [
        ("doc-1", "file1.txt", 3, None),
        ("doc-2", "file2.txt", 4, None),
    ]
    chain._vector_store = AsyncMock()
    chain._vector_store.delete_document.return_value = True
    chain._vector_store.list_documents.return_value = []
    chain._llm = AsyncMock()
    chain._settings = MagicMock()
    chain._settings.rag_top_k = 5
    return chain


# ---------------------------------------------------------------------------
# App fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_with_rag(mock_rag_chain: AsyncMock):
    """Create a FastAPI app with a mocked RAG chain."""
    app = create_app()
    app.state.rag_chain = mock_rag_chain
    app.state.guardrails = None
    app.state.metrics = MagicMock()
    app.state.query_logger = None
    return app


@pytest.fixture
async def client_with_rag(app_with_rag):
    """Async test client with working (mocked) RAG chain."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_rag),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def app_no_rag():
    """Create a FastAPI app WITHOUT a RAG chain (simulates init failure)."""
    app = create_app()
    app.state.rag_chain = None
    app.state.guardrails = None
    app.state.metrics = MagicMock()
    app.state.query_logger = None
    return app


@pytest.fixture
async def client_no_rag(app_no_rag):
    """Async test client without RAG chain."""
    async with AsyncClient(
        transport=ASGITransport(app=app_no_rag),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Guardrails fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_guardrails():
    """Create a mock guardrails instance that blocks injection and redacts PII."""
    from src.guardrails.local_guardrails import LocalGuardrails

    return LocalGuardrails()


@pytest.fixture
def app_with_guardrails(mock_rag_chain: AsyncMock, mock_guardrails):
    """App with both RAG chain and guardrails enabled."""
    app = create_app()
    app.state.rag_chain = mock_rag_chain
    app.state.guardrails = mock_guardrails
    app.state.metrics = MagicMock()
    app.state.query_logger = None
    return app


@pytest.fixture
async def client_with_guardrails(app_with_guardrails):
    """Async test client with guardrails enabled."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_guardrails),
        base_url="http://test",
    ) as ac:
        yield ac
