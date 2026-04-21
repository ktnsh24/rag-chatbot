"""
Evaluation Route Test Suite

Tests for the /api/evaluate and /api/evaluate/suite endpoints.

These tests verify the evaluation route logic using mocked RAG chains,
similar to how test_chat.py tests the chat endpoint.

Run with:
    pytest tests/test_evaluate_route.py -v
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from src.api.models import CloudProvider
from src.main import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """Create a test app with a mocked RAG chain."""
    test_app = create_app()

    # Mock the RAG chain on app.state
    mock_rag_chain = AsyncMock()
    mock_rag_chain.query.return_value = {
        "answer": "Refunds are processed within 14 business days.",
        "sources": [
            {
                "document_name": "refund-policy.pdf",
                "text": "Refunds are processed within 14 business days of receiving the returned item.",
                "score": 0.92,
                "page_number": 3,
            },
            {
                "document_name": "refund-policy.pdf",
                "text": "To request a refund, email support@example.com with your order number.",
                "score": 0.85,
                "page_number": 4,
            },
        ],
        "token_usage": {
            "input_tokens": 500,
            "output_tokens": 50,
            "total_tokens": 550,
            "estimated_cost_usd": 0.002,
        },
    }

    test_app.state.rag_chain = mock_rag_chain
    return test_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def app_no_rag():
    """Create a test app WITHOUT a RAG chain (simulates init failure)."""
    test_app = create_app()
    test_app.state.rag_chain = None
    return test_app


@pytest.fixture
def client_no_rag(app_no_rag):
    """Test client without RAG chain."""
    return TestClient(app_no_rag)


# ---------------------------------------------------------------------------
# POST /api/evaluate — Single Question Evaluation
# ---------------------------------------------------------------------------

class TestEvaluateSingle:
    """Tests for the single question evaluation endpoint."""

    def test_evaluate_returns_scores(self, client):
        """Evaluate a question and get scores back."""
        response = client.post(
            "/api/evaluate",
            json={"question": "What is the refund policy?"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["question"] == "What is the refund policy?"
        assert "answer" in data
        assert "scores" in data

        scores = data["scores"]
        assert "retrieval" in scores
        assert "faithfulness" in scores
        assert "answer_relevance" in scores
        assert "overall" in scores
        assert "passed" in scores
        assert isinstance(scores["passed"], bool)

    def test_evaluate_scores_are_in_range(self, client):
        """All scores should be between 0.0 and 1.0."""
        response = client.post(
            "/api/evaluate",
            json={"question": "What is the refund policy?"},
        )
        data = response.json()
        scores = data["scores"]

        assert 0.0 <= scores["retrieval"] <= 1.0
        assert 0.0 <= scores["faithfulness"] <= 1.0
        assert 0.0 <= scores["answer_relevance"] <= 1.0
        assert 0.0 <= scores["overall"] <= 1.0

    def test_evaluate_includes_metadata(self, client):
        """Response should include cloud_provider, latency, request_id."""
        response = client.post(
            "/api/evaluate",
            json={"question": "What is the refund policy?"},
        )
        data = response.json()

        assert "cloud_provider" in data
        assert "latency_ms" in data
        assert "request_id" in data
        assert "sources_used" in data
        assert data["sources_used"] == 2

    def test_evaluate_with_expected_answer(self, client):
        """Providing an expected answer should still return valid scores."""
        response = client.post(
            "/api/evaluate",
            json={
                "question": "What is the refund policy?",
                "expected_answer": "Refunds take 14 business days.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["scores"]["overall"] > 0

    def test_evaluate_with_custom_top_k(self, client, app):
        """Custom top_k should be passed to the RAG chain."""
        response = client.post(
            "/api/evaluate",
            json={"question": "What is the refund policy?", "top_k": 3},
        )
        assert response.status_code == 200

    def test_evaluate_empty_question_rejected(self, client):
        """Empty questions should be rejected with 422."""
        response = client.post(
            "/api/evaluate",
            json={"question": ""},
        )
        assert response.status_code == 422

    def test_evaluate_without_rag_chain(self, client_no_rag):
        """Should return 500 when RAG chain is not initialized."""
        response = client_no_rag.post(
            "/api/evaluate",
            json={"question": "What is the refund policy?"},
        )
        assert response.status_code == 500
        assert "RAG chain not initialized" in response.json()["detail"]

    def test_evaluate_includes_notes(self, client):
        """Response should include evaluation_notes list."""
        response = client.post(
            "/api/evaluate",
            json={"question": "What is the refund policy?"},
        )
        data = response.json()
        assert "evaluation_notes" in data
        assert isinstance(data["evaluation_notes"], list)


# ---------------------------------------------------------------------------
# POST /api/evaluate/suite — Golden Dataset Suite
# ---------------------------------------------------------------------------

class TestEvaluateSuite:
    """Tests for the golden dataset evaluation suite endpoint."""

    def test_suite_runs_all_cases(self, client):
        """Suite should run all golden dataset cases."""
        response = client.post("/api/evaluate/suite", json={})
        assert response.status_code == 200

        data = response.json()
        assert "total_cases" in data
        assert "passed" in data
        assert "failed" in data
        assert "pass_rate" in data
        assert "average_overall_score" in data
        assert "cases" in data
        assert data["total_cases"] == len(data["cases"])
        assert data["total_cases"] > 0

    def test_suite_case_results_have_required_fields(self, client):
        """Each case result should have all required fields."""
        response = client.post("/api/evaluate/suite", json={})
        data = response.json()

        for case in data["cases"]:
            assert "case_id" in case
            assert "category" in case
            assert "question" in case
            assert "answer_preview" in case
            assert "scores" in case
            assert "passed" in case
            assert "latency_ms" in case

    def test_suite_filter_by_category(self, client):
        """Suite should respect category filter."""
        response = client.post(
            "/api/evaluate/suite",
            json={"categories": ["policy"]},
        )
        assert response.status_code == 200
        data = response.json()

        # All returned cases should be in the "policy" category
        for case in data["cases"]:
            assert case["category"] == "policy"

    def test_suite_pass_rate_calculation(self, client):
        """Pass rate should be calculated correctly."""
        response = client.post("/api/evaluate/suite", json={})
        data = response.json()

        total = data["total_cases"]
        if total > 0:
            expected_rate = round(data["passed"] / total * 100, 1)
            assert data["pass_rate"] == expected_rate

    def test_suite_includes_metadata(self, client):
        """Suite response should include cloud_provider and latency."""
        response = client.post("/api/evaluate/suite", json={})
        data = response.json()

        assert "cloud_provider" in data
        assert "latency_ms" in data
        assert "request_id" in data

    def test_suite_without_rag_chain(self, client_no_rag):
        """Should return 500 when RAG chain is not initialized."""
        response = client_no_rag.post("/api/evaluate/suite", json={})
        assert response.status_code == 500

    def test_suite_with_custom_top_k(self, client):
        """Custom top_k should apply to all cases in the suite."""
        response = client.post(
            "/api/evaluate/suite",
            json={"top_k": 3},
        )
        assert response.status_code == 200

    def test_suite_passed_plus_failed_equals_total(self, client):
        """passed + failed should always equal total_cases."""
        response = client.post("/api/evaluate/suite", json={})
        data = response.json()
        assert data["passed"] + data["failed"] == data["total_cases"]
