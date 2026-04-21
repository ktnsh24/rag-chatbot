"""
Abstract Vector Store Interface

Defines the contract for vector stores:
    - Store embeddings (indexed by document_id)
    - Search for similar vectors (semantic search)
    - Delete vectors by document_id

Implementations:
    - aws_opensearch.py    → Amazon OpenSearch Serverless (~$350/month)
    - aws_dynamodb.py      → Amazon DynamoDB + brute-force cosine (~$0/month)
    - azure_ai_search.py   → Azure AI Search
    - local_chromadb.py    → ChromaDB (local development)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class VectorSearchResult:
    """
    A single result from a vector similarity search.

    Fields:
        text: The original text of the chunk.
        document_name: Which document this chunk came from.
        score: Cosine similarity (0.0 to 1.0, higher = more similar).
        page_number: Page in the original document (if applicable).
        metadata: Any additional metadata stored with this chunk.
    """

    text: str
    document_name: str
    score: float
    page_number: int | None = None
    metadata: dict = field(default_factory=dict)


class BaseVectorStore(ABC):
    """
    Abstract vector store.

    The vector store is the "memory" of the RAG system:
        - When you ingest a document, chunks are stored here as vectors
        - When you ask a question, we search here for similar vectors
        - The most similar vectors become the "context" for the LLM
    """

    @abstractmethod
    async def store_vectors(
        self,
        document_id: str,
        document_name: str,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> int:
        """
        Store document chunk embeddings in the vector store.

        Args:
            document_id: Unique document identifier.
            document_name: Original filename.
            texts: The text of each chunk.
            embeddings: The embedding vector for each chunk.
            metadatas: Optional metadata for each chunk.

        Returns:
            Number of vectors stored.
        """
        ...

    @abstractmethod
    async def search(self, query_embedding: list[float], top_k: int = 5) -> list[VectorSearchResult]:
        """
        Find the most similar vectors to the query.

        This is the core of RAG retrieval:
            1. Your question gets converted to a vector (by the LLM)
            2. This method finds the top_k closest vectors in the store
            3. Those vectors correspond to document chunks
            4. Those chunks become the context for the LLM

        Args:
            query_embedding: The query vector.
            top_k: How many results to return.

        Returns:
            List of VectorSearchResult, sorted by similarity (highest first).
        """
        ...

    @abstractmethod
    async def delete_document(self, document_id: str) -> int:
        """
        Delete all vectors belonging to a document.

        Args:
            document_id: The document to delete.

        Returns:
            Number of vectors deleted.
        """
        ...
