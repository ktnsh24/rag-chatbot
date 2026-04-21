"""
ChromaDB — Local Vector Store Implementation

Uses ChromaDB for local development vector storage and retrieval.
No cloud account, no API keys, no internet required.

Why ChromaDB?
    - Zero setup — runs in-memory or with SQLite persistence
    - Free and open source
    - Automatic dimension detection — works with any embedding model
    - Built-in HNSW indexing and cosine similarity
    - Python-native — no external service to manage

Storage modes:
    - In-memory (default): Fast, lost on restart. Good for quick testing.
    - Persistent (set CHROMA_PERSIST_DIR): Saved to disk. Survives restarts.

Cost:
    - $0.00 — runs locally on your machine
    - Storage: whatever your disk can hold

Setup:
    1. pip install chromadb (already in pyproject.toml dev dependencies)
    2. Set CLOUD_PROVIDER=local in .env
    3. Optionally set CHROMA_PERSIST_DIR=./chroma_data for persistence
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from loguru import logger

from src.vectorstore.base import BaseVectorStore, VectorSearchResult


class ChromaDBVectorStore(BaseVectorStore):
    """
    ChromaDB local vector store.

    Initialization:
        store = ChromaDBVectorStore(
            collection_name="rag-chatbot-vectors",
            persist_directory=None,  # None = in-memory, set path for persistence
        )

    ChromaDB handles:
        - Dimension auto-detection (works with 768, 1024, 1536, any size)
        - HNSW indexing (same algorithm as OpenSearch and Azure AI Search)
        - Cosine similarity scoring
        - SQLite-based persistence (optional)
    """

    def __init__(
        self,
        collection_name: str = "rag-chatbot-vectors",
        persist_directory: str | None = None,
        hnsw_m: int = 16,
        hnsw_ef_construction: int = 512,
        hnsw_ef_search: int = 512,
    ):
        self.collection_name = collection_name
        self._hnsw_m = hnsw_m
        self._hnsw_ef_construction = hnsw_ef_construction
        self._hnsw_ef_search = hnsw_ef_search

        if persist_directory:
            self._client = chromadb.PersistentClient(
                path=persist_directory,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            logger.info(f"ChromaDB initialized with persistence: {persist_directory}")
        else:
            self._client = chromadb.Client(
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            logger.info("ChromaDB initialized in-memory (data lost on restart)")

        # Get or create the collection with explicit HNSW parameters
        # ChromaDB auto-detects dimensions from the first embedding
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",  # Use cosine similarity (same as OpenSearch/AI Search)
                "hnsw:M": self._hnsw_m,  # Max connections per node
                "hnsw:construction_ef": self._hnsw_ef_construction,  # Build-time exploration factor
                "hnsw:search_ef": self._hnsw_ef_search,  # Query-time exploration factor
            },
        )
        logger.info(f"ChromaDB collection ready: {collection_name}")

    async def store_vectors(
        self,
        document_id: str,
        document_name: str,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> int:
        """Store document chunk embeddings in ChromaDB."""
        ids = [f"{document_id}_{i}" for i in range(len(texts))]

        # Build metadata for each chunk
        chunk_metadatas = []
        for i in range(len(texts)):
            metadata = metadatas[i] if metadatas else {}
            chunk_metadatas.append(
                {
                    "document_id": document_id,
                    "document_name": document_name,
                    "chunk_index": i,
                    "page_number": metadata.get("page_number", 0),
                }
            )

        # ChromaDB upsert — adds or updates in one call
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=chunk_metadatas,
        )

        logger.info(f"Stored {len(texts)} vectors for document {document_id}")
        return len(texts)

    async def search(self, query_embedding: list[float], top_k: int = 5) -> list[VectorSearchResult]:
        """Search for the most similar vectors using ChromaDB's built-in HNSW."""
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                # ChromaDB returns distances (lower = more similar for cosine)
                # Convert to similarity score: 1 - distance
                distance = results["distances"][0][i] if results["distances"] else 0.0
                score = 1.0 - distance

                search_results.append(
                    VectorSearchResult(
                        text=doc,
                        document_name=metadata.get("document_name", "unknown"),
                        score=score,
                        page_number=metadata.get("page_number"),
                        metadata={
                            "document_id": metadata.get("document_id", ""),
                            "chunk_index": metadata.get("chunk_index", 0),
                        },
                    )
                )

        return search_results

    async def delete_document(self, document_id: str) -> int:
        """Delete all vectors for a document from ChromaDB."""
        # ChromaDB supports filtering by metadata
        try:
            # Get all IDs for this document
            results = self._collection.get(
                where={"document_id": document_id},
                include=[],
            )

            if results["ids"]:
                self._collection.delete(ids=results["ids"])
                deleted = len(results["ids"])
                logger.info(f"Deleted {deleted} vectors for document {document_id}")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"ChromaDB delete error: {e}")
            raise
