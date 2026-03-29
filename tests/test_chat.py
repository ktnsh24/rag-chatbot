"""
Tests for the chat API endpoint.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.fixture
def app():
    """Create a test app instance."""
    return create_app()


@pytest.fixture
async def client(app):
    """Create an async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    """Tests for GET /api/health."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        """Health endpoint should always return 200."""
        response = await client.get("/api/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_has_status(self, client):
        """Health response should include status field."""
        response = await client.get("/api/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    @pytest.mark.asyncio
    async def test_health_has_cloud_provider(self, client):
        """Health response should include cloud_provider field."""
        response = await client.get("/api/health")
        data = response.json()
        assert "cloud_provider" in data


class TestChatEndpoint:
    """Tests for POST /api/chat."""

    @pytest.mark.asyncio
    async def test_chat_requires_question(self, client):
        """Chat should return 422 if question is missing."""
        response = await client.post("/api/chat", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_empty_question_rejected(self, client):
        """Chat should reject empty questions."""
        response = await client.post("/api/chat", json={"question": ""})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_without_rag_chain_returns_500(self, client):
        """Chat should return 500 if RAG chain is not initialized."""
        response = await client.post("/api/chat", json={"question": "What is this?"})
        assert response.status_code == 500


class TestDocumentEndpoints:
    """Tests for document CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, client):
        """Listing documents when none uploaded should return empty list."""
        response = await client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["documents"] == []

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, client):
        """Deleting a non-existent document should return 404."""
        response = await client.delete("/api/documents/fake-id")
        assert response.status_code == 404
