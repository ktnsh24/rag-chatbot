"""
Tests for the Hybrid Search module (I25).

Tests cover:
    - Reciprocal Rank Fusion (RRF) algorithm correctness
    - LocalHybridSearch: BM25 indexing, search, fusion
    - Edge cases: empty results, alpha weighting, deduplication

Uses mocked vector store — no cloud credentials needed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.rag.hybrid_search import LocalHybridSearch, reciprocal_rank_fusion
from src.vectorstore.base import BaseVectorStore, VectorSearchResult


def _make_result(text: str, score: float, doc: str = "test.txt") -> VectorSearchResult:
    """Helper: create a single VectorSearchResult."""
    return VectorSearchResult(
        text=text,
        document_name=doc,
        score=score,
        metadata={},
    )


class TestReciprocalRankFusion:
    """Test the RRF algorithm directly."""

    def test_vector_only_alpha_1(self):
        """With alpha=1.0, only vector results should contribute."""
        vector = [_make_result("A", 0.9), _make_result("B", 0.8)]
        bm25 = [_make_result("C", 5.0), _make_result("D", 4.0)]

        fused = reciprocal_rank_fusion(vector, bm25, alpha=1.0, k=60)

        # A and B should be first (only vector contributes)
        texts = [r.text for r in fused]
        assert texts[0] == "A"
        assert texts[1] == "B"
        # C and D should have score 0 (alpha=1.0 → bm25 weight = 0)
        cd_scores = [r.score for r in fused if r.text in ("C", "D")]
        assert all(s == 0.0 for s in cd_scores)

    def test_bm25_only_alpha_0(self):
        """With alpha=0.0, only BM25 results should contribute."""
        vector = [_make_result("A", 0.9), _make_result("B", 0.8)]
        bm25 = [_make_result("C", 5.0), _make_result("D", 4.0)]

        fused = reciprocal_rank_fusion(vector, bm25, alpha=0.0, k=60)

        texts = [r.text for r in fused]
        assert texts[0] == "C"
        assert texts[1] == "D"

    def test_balanced_fusion(self):
        """With alpha=0.5, results from both systems should contribute equally."""
        vector = [_make_result("A", 0.9), _make_result("B", 0.8)]
        bm25 = [_make_result("B", 5.0), _make_result("C", 4.0)]

        fused = reciprocal_rank_fusion(vector, bm25, alpha=0.5, k=60)

        # B appears in both → should have highest fused score
        assert fused[0].text == "B"

    def test_deduplication(self):
        """Same text appearing in both systems should be merged, not duplicated."""
        vector = [_make_result("Same chunk", 0.9)]
        bm25 = [_make_result("Same chunk", 5.0)]

        fused = reciprocal_rank_fusion(vector, bm25, alpha=0.5, k=60)

        # Should be merged into one result
        assert len(fused) == 1
        # Score should be from both systems
        assert fused[0].score > 0

    def test_empty_vector_results(self):
        """If vector returns nothing, only BM25 results appear."""
        bm25 = [_make_result("A", 5.0), _make_result("B", 4.0)]

        fused = reciprocal_rank_fusion([], bm25, alpha=0.7, k=60)

        assert len(fused) == 2
        assert fused[0].text == "A"

    def test_empty_bm25_results(self):
        """If BM25 returns nothing, only vector results appear."""
        vector = [_make_result("A", 0.9), _make_result("B", 0.8)]

        fused = reciprocal_rank_fusion(vector, [], alpha=0.7, k=60)

        assert len(fused) == 2
        assert fused[0].text == "A"

    def test_both_empty(self):
        """If both systems return nothing, result is empty."""
        fused = reciprocal_rank_fusion([], [], alpha=0.7, k=60)
        assert fused == []

    def test_rrf_scores_are_positive(self):
        """All fused scores should be positive."""
        vector = [_make_result(f"V{i}", 0.9 - i * 0.1) for i in range(5)]
        bm25 = [_make_result(f"B{i}", 5.0 - i) for i in range(5)]

        fused = reciprocal_rank_fusion(vector, bm25, alpha=0.7, k=60)

        for result in fused:
            assert result.score > 0

    def test_rrf_metadata_has_search_type(self):
        """Fused results should have search_type='hybrid_rrf' in metadata."""
        vector = [_make_result("A", 0.9)]
        bm25 = [_make_result("B", 5.0)]

        fused = reciprocal_rank_fusion(vector, bm25, alpha=0.7, k=60)

        for result in fused:
            assert result.metadata["search_type"] == "hybrid_rrf"

    def test_rank_ordering_matters(self):
        """First-ranked results should get higher RRF scores than later ones."""
        vector = [_make_result("First", 0.9), _make_result("Second", 0.8)]

        fused = reciprocal_rank_fusion(vector, [], alpha=1.0, k=60)

        assert fused[0].text == "First"
        assert fused[0].score > fused[1].score


class TestLocalHybridSearchBM25:
    """Test BM25 indexing and keyword search."""

    @pytest.fixture
    def mock_vector_store(self) -> BaseVectorStore:
        """Create a mock vector store."""
        store = AsyncMock(spec=BaseVectorStore)
        store.search = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def hybrid_search(self, mock_vector_store: BaseVectorStore) -> LocalHybridSearch:
        """Create a LocalHybridSearch with BM25 indexed."""
        hs = LocalHybridSearch(vector_store=mock_vector_store)
        hs.index_corpus([
            {"text": "The refund policy allows returns within 30 days", "document_name": "policy.txt"},
            {"text": "Shipping takes 3-5 business days to arrive", "document_name": "shipping.txt"},
            {"text": "Contact customer support at the help desk", "document_name": "support.txt"},
            {"text": "The return process requires a receipt and original packaging", "document_name": "returns.txt"},
        ])
        return hs

    def test_bm25_search_keyword_match(self, hybrid_search: LocalHybridSearch):
        """BM25 should rank keyword matches highest."""
        results = hybrid_search._bm25_search("refund policy", top_k=4)

        assert len(results) > 0
        # "refund policy" should match the first document best
        assert results[0].document_name == "policy.txt"

    def test_bm25_search_returns_correct_type(self, hybrid_search: LocalHybridSearch):
        """BM25 results should be VectorSearchResult instances."""
        results = hybrid_search._bm25_search("shipping", top_k=2)

        assert len(results) > 0
        for result in results:
            assert isinstance(result, VectorSearchResult)
            assert result.metadata["search_type"] == "bm25"

    def test_bm25_search_respects_top_k(self, hybrid_search: LocalHybridSearch):
        """Should return at most top_k results."""
        results = hybrid_search._bm25_search("the", top_k=2)
        assert len(results) <= 2

    def test_bm25_search_no_match(self, hybrid_search: LocalHybridSearch):
        """Query with no matching terms should return empty or low-score results."""
        results = hybrid_search._bm25_search("xyznonexistent", top_k=4)
        # BM25 returns 0 score for non-matching terms
        assert all(r.score == 0 for r in results) or len(results) == 0

    def test_bm25_empty_corpus(self, mock_vector_store: BaseVectorStore):
        """BM25 search on empty corpus should return empty list."""
        hs = LocalHybridSearch(vector_store=mock_vector_store)
        results = hs._bm25_search("anything", top_k=5)
        assert results == []


class TestLocalHybridSearchFull:
    """Test the full hybrid search pipeline (BM25 + vector + fusion)."""

    @pytest.fixture
    def mock_vector_store(self) -> BaseVectorStore:
        """Create a mock vector store that returns predictable results."""
        store = AsyncMock(spec=BaseVectorStore)
        store.search = AsyncMock(return_value=[
            _make_result("Vector result about refunds and returns", 0.92),
            _make_result("Vector result about shipping speed", 0.85),
        ])
        return store

    @pytest.fixture
    def hybrid_search(self, mock_vector_store: BaseVectorStore) -> LocalHybridSearch:
        """Create a fully configured LocalHybridSearch."""
        hs = LocalHybridSearch(vector_store=mock_vector_store)
        hs.index_corpus([
            {"text": "BM25 result about the refund policy details", "document_name": "policy.txt"},
            {"text": "BM25 result about fast shipping options", "document_name": "shipping.txt"},
            {"text": "Vector result about refunds and returns", "document_name": "returns.txt"},
        ])
        return hs

    @pytest.mark.asyncio
    async def test_hybrid_search_returns_results(self, hybrid_search: LocalHybridSearch):
        """Hybrid search should return fused results."""
        results = await hybrid_search.search(
            query="refund policy",
            query_embedding=[0.1, 0.2, 0.3],
            top_k=5,
            alpha=0.7,
        )
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_hybrid_search_respects_top_k(self, hybrid_search: LocalHybridSearch):
        """Should return at most top_k results."""
        results = await hybrid_search.search(
            query="refund",
            query_embedding=[0.1, 0.2, 0.3],
            top_k=2,
            alpha=0.7,
        )
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_hybrid_search_calls_vector_store(
        self, hybrid_search: LocalHybridSearch, mock_vector_store: BaseVectorStore
    ):
        """Hybrid search should call the vector store's search method."""
        await hybrid_search.search(
            query="test",
            query_embedding=[0.1, 0.2, 0.3],
            top_k=3,
            alpha=0.7,
        )
        mock_vector_store.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_alpha_1_favors_vector(self, hybrid_search: LocalHybridSearch):
        """alpha=1.0 should only use vector results."""
        results = await hybrid_search.search(
            query="shipping",
            query_embedding=[0.1, 0.2, 0.3],
            top_k=5,
            alpha=1.0,
        )
        # With alpha=1.0, BM25 results should have 0 contribution
        # Vector results should dominate
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_all_results_have_hybrid_metadata(self, hybrid_search: LocalHybridSearch):
        """All results should have search_type='hybrid_rrf' in metadata."""
        results = await hybrid_search.search(
            query="refund",
            query_embedding=[0.1, 0.2, 0.3],
            top_k=5,
            alpha=0.7,
        )
        for result in results:
            assert result.metadata.get("search_type") == "hybrid_rrf"
