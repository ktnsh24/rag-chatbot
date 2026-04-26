"""
Re-ranker — Two-stage retrieval for improved RAG quality.

First stage:  Vector search returns top_k=20 candidates (fast, approximate)
Second stage: Re-ranker scores each candidate against the query (slow, precise)
              and returns only the best top_k=5

Implementations:
    - aws:   Bedrock Reranker (Amazon Rerank 1.0)
    - azure: Azure AI Search Semantic Ranker
    - local: Cross-encoder model via sentence-transformers

Why re-ranking improves RAG:
    - Bi-encoders (embeddings) encode query and document separately — they can't
      see how they relate to each other
    - Cross-encoders see query + document together — they understand relevance
      in context, catching subtle relationships the embedding missed
    - Studies show 10-25% improvement in retrieval relevance with re-ranking
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from loguru import logger

from src.vectorstore.base import VectorSearchResult


@dataclass
class RerankResult:
    """A search result after re-ranking, with the new relevance score."""

    original_result: VectorSearchResult
    rerank_score: float  # New score from the re-ranker (0.0 to 1.0)


class BaseReranker(ABC):
    """
    Abstract base class for re-rankers.

    Every re-ranker takes a query + list of search results and returns
    the results re-ordered by a more accurate relevance model.
    """

    @abstractmethod
    async def rerank(self, query: str, results: list[VectorSearchResult], top_k: int = 5) -> list[VectorSearchResult]:
        """
        Re-rank search results using a cross-encoder model.

        Args:
            query: The user's question.
            results: Initial search results from the vector store (e.g. top 20).
            top_k: How many results to return after re-ranking.

        Returns:
            The top_k most relevant results, re-ordered by the cross-encoder.
        """
        ...


class LocalReranker(BaseReranker):
    """
    Local re-ranker using sentence-transformers CrossEncoder.

    Model: ms-marco-MiniLM-L-6-v2 (22M params, fast, good quality)
    Latency: ~50ms for 20 candidates on CPU

    No cloud needed — runs locally with CLOUD_PROVIDER=local.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(model_name)
        self._model_name = model_name
        logger.info(f"Local re-ranker initialized: {model_name}")

    async def rerank(self, query: str, results: list[VectorSearchResult], top_k: int = 5) -> list[VectorSearchResult]:
        """Re-rank using cross-encoder scores."""
        if not results:
            return []

        import math

        # Build query-document pairs for the cross-encoder
        pairs = [(query, result.text) for result in results]

        # Score all pairs at once (batch inference)
        raw_scores = self._model.predict(pairs)

        # Normalize scores to [0, 1] using sigmoid (cross-encoder scores are logits)
        def sigmoid(x: float) -> float:
            return 1.0 / (1.0 + math.exp(-x))

        scores = [sigmoid(float(s)) for s in raw_scores]

        # Combine scores with original results
        scored = list(zip(scores, results, strict=False))
        scored.sort(key=lambda x: x[0], reverse=True)

        # Return top_k, updating the score to the normalized re-ranker score
        reranked: list[VectorSearchResult] = []
        for score, result in scored[:top_k]:
            reranked.append(
                VectorSearchResult(
                    text=result.text,
                    document_name=result.document_name,
                    score=round(score, 4),  # Normalized sigmoid score [0, 1]
                    page_number=result.page_number,
                    metadata={**result.metadata, "original_score": result.score},
                )
            )

        logger.debug(
            "Re-ranked {} → {} results (best={:.3f})",
            len(results),
            len(reranked),
            reranked[0].score if reranked else 0.0,
        )
        return reranked


class AWSReranker(BaseReranker):
    """
    AWS re-ranker using Amazon Bedrock Reranker.

    Model: amazon.rerank-v1:0
    Cost: $0.10 per 1K text units (1 unit = 1,000 characters)
    """

    def __init__(self, region: str, model_id: str = "amazon.rerank-v1:0") -> None:
        import boto3

        self._region = region
        self._model_id = model_id
        session = boto3.Session(region_name=region)
        self._client = session.client("bedrock-agent-runtime")
        logger.info(f"AWS re-ranker initialized: {model_id} in {region}")

    async def rerank(self, query: str, results: list[VectorSearchResult], top_k: int = 5) -> list[VectorSearchResult]:
        """Re-rank using Bedrock Reranker."""
        if not results:
            return []

        try:
            # Build the sources list for Bedrock
            sources = [
                {
                    "type": "INLINE",
                    "inlineDocumentSource": {
                        "type": "TEXT",
                        "textDocument": {"text": result.text},
                    },
                }
                for result in results
            ]

            # Guard: numberOfResults must not exceed len(sources)
            safe_top_k = min(top_k, len(sources))

            response = self._client.rerank(
                rerankingConfiguration={
                    "type": "BEDROCK_RERANKING_MODEL",
                    "bedrockRerankingConfiguration": {
                        "modelConfiguration": {
                            "modelArn": f"arn:aws:bedrock:{self._region}::foundation-model/{self._model_id}"
                        },
                        "numberOfResults": safe_top_k,
                    },
                },
                sources=sources,
                queries=[{"type": "TEXT", "textQuery": {"text": query}}],
            )

            # Map Bedrock results back to VectorSearchResult
            reranked: list[VectorSearchResult] = []
            for item in response.get("results", []):
                idx = item["index"]
                original = results[idx]
                reranked.append(
                    VectorSearchResult(
                        text=original.text,
                        document_name=original.document_name,
                        score=item["relevanceScore"],
                        page_number=original.page_number,
                        metadata={**original.metadata, "original_score": original.score},
                    )
                )

            logger.debug(f"Bedrock re-ranked {len(results)} → {len(reranked)} results")
            return reranked

        except Exception as e:
            logger.error(f"Bedrock re-ranking failed: {e}, returning original results")
            return results[:top_k]


class AzureReranker(BaseReranker):
    """
    Azure re-ranker using Azure AI Search Semantic Ranker.

    Azure AI Search has built-in semantic ranking that can be enabled
    at query time. This wrapper calls the semantic search API.

    Cost: Included in Azure AI Search Standard tier ($249/month)
    """

    def __init__(self, endpoint: str, api_key: str, index_name: str) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._index_name = index_name
        logger.info(f"Azure re-ranker initialized: {endpoint}/{index_name}")

    async def rerank(self, query: str, results: list[VectorSearchResult], top_k: int = 5) -> list[VectorSearchResult]:
        """
        Re-rank using Azure Semantic Ranker.

        Note: Azure Semantic Ranker works at the search level, not as a
        post-processing step. For consistency with the interface, we
        re-score the existing results using a secondary semantic search.
        In production, you'd enable semantic ranking directly in the
        search query (query_type="semantic").
        """
        if not results:
            return []

        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient

            client = SearchClient(
                endpoint=self._endpoint,
                index_name=self._index_name,
                credential=AzureKeyCredential(self._api_key),
            )

            # Use semantic search to re-rank
            search_results = client.search(
                search_text=query,
                query_type="semantic",
                semantic_configuration_name="default",
                top=top_k,
                select=["text", "document_name", "page_number"],
            )

            reranked: list[VectorSearchResult] = []
            for item in search_results:
                reranked.append(
                    VectorSearchResult(
                        text=item["text"],
                        document_name=item["document_name"],
                        score=item.get("@search.reranker_score", 0.0),
                        page_number=item.get("page_number"),
                        metadata={"source": "azure_semantic_ranker"},
                    )
                )

            if reranked:
                logger.debug(f"Azure re-ranked → {len(reranked)} results")
                return reranked

            # Fallback to original results if semantic search returns nothing
            return results[:top_k]

        except Exception as e:
            logger.error(f"Azure semantic re-ranking failed: {e}, returning original results")
            return results[:top_k]
