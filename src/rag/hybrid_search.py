"""
Hybrid Search — Combines BM25 keyword search with vector semantic search.

Why hybrid?
    - Vector search is great for semantic queries ("how do I return an item?")
    - BM25 is great for keyword queries ("error code 5412", "product SKU-ABC")
    - Hybrid combines both using Reciprocal Rank Fusion (RRF) for best of both worlds

How it works:
    1. Run vector search → get top N results with semantic scores
    2. Run BM25 search → get top N results with keyword scores
    3. Merge using RRF: score = Σ 1/(k + rank_i) for each retrieval system
    4. Sort by fused score, return top_k

Implementations:
    - aws:   OpenSearch hybrid (k-NN + BM25 natively)
    - azure: Azure AI Search hybrid mode (built-in)
    - local: rank-bm25 library + ChromaDB vector search
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from loguru import logger

from src.vectorstore.base import BaseVectorStore, VectorSearchResult


class BaseHybridSearch(ABC):
    """
    Abstract base class for hybrid search.

    Combines vector (semantic) and keyword (BM25) retrieval.
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        query_embedding: list[float],
        top_k: int = 5,
        alpha: float = 0.7,
    ) -> list[VectorSearchResult]:
        """
        Run hybrid search combining vector and keyword results.

        Args:
            query: The user's question (text, for BM25).
            query_embedding: The question's embedding (vector, for semantic search).
            top_k: Number of final results to return.
            alpha: Weight for vector search (0.0 = BM25 only, 1.0 = vector only).

        Returns:
            Fused and sorted search results.
        """
        ...


class LocalHybridSearch(BaseHybridSearch):
    """
    Local hybrid search using rank-bm25 + vector store.

    BM25 is run in-memory over the document chunks.
    Vector search uses the existing vector store (ChromaDB/DynamoDB).

    This demonstrates the hybrid pattern without cloud services.
    """

    def __init__(self, vector_store: BaseVectorStore, corpus: list[dict] | None = None) -> None:
        self._vector_store = vector_store
        self._corpus: list[dict] = corpus or []
        self._bm25 = None
        self._tokenized_corpus: list[list[str]] = []

    def index_corpus(self, chunks: list[dict]) -> None:
        """
        Build the BM25 index from document chunks.

        Args:
            chunks: List of dicts with at least {"text": str, "document_name": str}
        """
        from rank_bm25 import BM25Okapi

        self._corpus = chunks
        self._tokenized_corpus = [
            chunk["text"].lower().split() for chunk in chunks
        ]
        self._bm25 = BM25Okapi(self._tokenized_corpus)
        logger.info(f"BM25 index built with {len(chunks)} chunks")

    async def search(
        self,
        query: str,
        query_embedding: list[float],
        top_k: int = 5,
        alpha: float = 0.7,
    ) -> list[VectorSearchResult]:
        """Hybrid search: vector (alpha) + BM25 (1-alpha), fused with RRF."""

        # Retrieve more candidates than needed (for fusion)
        retrieve_k = top_k * 4  # Get 4x candidates from each system

        # Stage 1: Vector search
        vector_results = await self._vector_store.search(
            query_embedding=query_embedding,
            top_k=retrieve_k,
        )

        # Stage 2: BM25 search
        bm25_results = self._bm25_search(query, top_k=retrieve_k)

        # Stage 3: Reciprocal Rank Fusion
        fused = reciprocal_rank_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            alpha=alpha,
            k=60,  # Standard RRF constant
        )

        # Return top_k
        result = fused[:top_k]
        logger.debug(
            "Hybrid search: {} vector + {} BM25 → {} fused (alpha={:.1f})",
            len(vector_results),
            len(bm25_results),
            len(result),
            alpha,
        )
        return result

    def _bm25_search(self, query: str, top_k: int = 20) -> list[VectorSearchResult]:
        """Run BM25 keyword search over the in-memory corpus."""
        if not self._bm25 or not self._corpus:
            return []

        tokenized_query = query.lower().split()
        scores = self._bm25.get_scores(tokenized_query)

        # Pair scores with corpus items and sort
        scored = list(zip(scores, self._corpus))
        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[VectorSearchResult] = []
        for score, chunk in scored[:top_k]:
            if score <= 0:
                break
            results.append(
                VectorSearchResult(
                    text=chunk["text"],
                    document_name=chunk.get("document_name", "unknown"),
                    score=float(score),
                    page_number=chunk.get("page_number"),
                    metadata={"search_type": "bm25"},
                )
            )

        return results


def reciprocal_rank_fusion(
    vector_results: list[VectorSearchResult],
    bm25_results: list[VectorSearchResult],
    alpha: float = 0.7,
    k: int = 60,
) -> list[VectorSearchResult]:
    """
    Merge results from two retrieval systems using Reciprocal Rank Fusion (RRF).

    RRF score = alpha * 1/(k + vector_rank) + (1-alpha) * 1/(k + bm25_rank)

    The constant k (default 60) controls how much rank position matters:
        - Lower k → top ranks matter much more
        - Higher k → ranks are more equally weighted

    Args:
        vector_results: Results from vector/semantic search (ordered by relevance).
        bm25_results: Results from BM25 keyword search (ordered by relevance).
        alpha: Weight for vector results (0.7 = 70% vector, 30% BM25).
        k: RRF constant (standard = 60).

    Returns:
        Fused results sorted by RRF score (highest first).
    """
    # Build lookup: text → (best result object, rrf_score)
    scores: dict[str, tuple[VectorSearchResult, float]] = {}

    # Score vector results
    for rank, result in enumerate(vector_results):
        key = result.text[:200]  # Use first 200 chars as key (dedup)
        rrf_score = alpha * (1.0 / (k + rank + 1))
        if key in scores:
            existing_result, existing_score = scores[key]
            scores[key] = (existing_result, existing_score + rrf_score)
        else:
            scores[key] = (result, rrf_score)

    # Score BM25 results
    for rank, result in enumerate(bm25_results):
        key = result.text[:200]
        rrf_score = (1 - alpha) * (1.0 / (k + rank + 1))
        if key in scores:
            existing_result, existing_score = scores[key]
            scores[key] = (existing_result, existing_score + rrf_score)
        else:
            scores[key] = (result, rrf_score)

    # Sort by fused score
    fused = sorted(scores.values(), key=lambda x: x[1], reverse=True)

    # Build final results with fused scores
    results: list[VectorSearchResult] = []
    for result, fused_score in fused:
        results.append(
            VectorSearchResult(
                text=result.text,
                document_name=result.document_name,
                score=round(fused_score, 6),
                page_number=result.page_number,
                metadata={**result.metadata, "search_type": "hybrid_rrf"},
            )
        )

    return results
