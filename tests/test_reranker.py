"""
Tests for the Re-ranker module (I24).

Tests cover:
    - BaseReranker contract
    - LocalReranker: re-ordering, top_k, empty input, score replacement
    - RerankResult dataclass

Only tests the local (sentence-transformers) provider.
AWS/Azure re-rankers require cloud credentials → integration tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.rag.reranker import BaseReranker, LocalReranker
from src.vectorstore.base import VectorSearchResult


def _make_results(count: int) -> list[VectorSearchResult]:
    """Helper: create dummy search results."""
    return [
        VectorSearchResult(
            text=f"Document chunk {i} about topic {chr(65 + i)}",
            document_name=f"doc-{i}.txt",
            score=1.0 - (i * 0.1),  # Descending scores
            page_number=i + 1,
            metadata={"chunk_index": i},
        )
        for i in range(count)
    ]


class TestBaseRerankerInterface:
    """Test that BaseReranker cannot be instantiated directly."""

    def test_cannot_instantiate_abstract(self):
        """BaseReranker is abstract — must use a concrete implementation."""
        with pytest.raises(TypeError):
            BaseReranker()  # type: ignore


class TestLocalReranker:
    """Test the local cross-encoder re-ranker."""

    @pytest.fixture
    def mock_reranker(self) -> LocalReranker:
        """Create a LocalReranker with a mocked CrossEncoder model."""
        with patch("src.rag.reranker.LocalReranker.__init__", return_value=None):
            reranker = LocalReranker.__new__(LocalReranker)
            reranker._model = MagicMock()
            reranker._model_name = "mock-model"
            return reranker

    @pytest.mark.asyncio
    async def test_rerank_reorders_by_score(self, mock_reranker: LocalReranker):
        """Results should be re-ordered by cross-encoder scores."""
        results = _make_results(4)

        # Mock cross-encoder: last document gets highest score (reverse order)
        mock_reranker._model.predict.return_value = [0.1, 0.3, 0.9, 0.5]

        reranked = await mock_reranker.rerank(query="test query", results=results, top_k=4)

        assert len(reranked) == 4
        # Chunk 2 had score 0.9 → should be first
        assert reranked[0].text == "Document chunk 2 about topic C"
        assert reranked[0].score == 0.9

    @pytest.mark.asyncio
    async def test_rerank_respects_top_k(self, mock_reranker: LocalReranker):
        """Only top_k results should be returned."""
        results = _make_results(10)
        mock_reranker._model.predict.return_value = [0.1, 0.9, 0.3, 0.7, 0.5, 0.2, 0.4, 0.6, 0.8, 0.0]

        reranked = await mock_reranker.rerank(query="test", results=results, top_k=3)

        assert len(reranked) == 3
        # Top 3 by score: 0.9 (idx 1), 0.8 (idx 8), 0.7 (idx 3)
        assert reranked[0].score == 0.9
        assert reranked[1].score == 0.8
        assert reranked[2].score == 0.7

    @pytest.mark.asyncio
    async def test_rerank_empty_input(self, mock_reranker: LocalReranker):
        """Empty results list should return empty list."""
        reranked = await mock_reranker.rerank(query="test", results=[], top_k=5)
        assert reranked == []
        mock_reranker._model.predict.assert_not_called()

    @pytest.mark.asyncio
    async def test_rerank_preserves_metadata(self, mock_reranker: LocalReranker):
        """Re-ranked results should preserve document_name, page_number, and add original_score."""
        results = _make_results(2)
        mock_reranker._model.predict.return_value = [0.8, 0.6]

        reranked = await mock_reranker.rerank(query="test", results=results, top_k=2)

        assert reranked[0].document_name == "doc-0.txt"
        assert reranked[0].page_number == 1
        assert reranked[0].metadata["original_score"] == 1.0  # Original score preserved
        assert reranked[0].metadata["chunk_index"] == 0  # Original metadata preserved

    @pytest.mark.asyncio
    async def test_rerank_passes_correct_pairs(self, mock_reranker: LocalReranker):
        """CrossEncoder should receive (query, text) pairs."""
        results = _make_results(2)
        mock_reranker._model.predict.return_value = [0.5, 0.5]

        await mock_reranker.rerank(query="my question", results=results, top_k=2)

        call_args = mock_reranker._model.predict.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0][0] == "my question"
        assert call_args[0][1] == results[0].text
        assert call_args[1][0] == "my question"
        assert call_args[1][1] == results[1].text

    @pytest.mark.asyncio
    async def test_rerank_single_result(self, mock_reranker: LocalReranker):
        """Should work with a single result."""
        results = _make_results(1)
        mock_reranker._model.predict.return_value = [0.95]

        reranked = await mock_reranker.rerank(query="test", results=results, top_k=5)

        assert len(reranked) == 1
        assert reranked[0].score == 0.95
