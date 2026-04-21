"""
Tests for the DynamoDB Vector Store implementation.

Uses moto to mock DynamoDB — no real AWS credentials needed.
Tests cover: store, search (cosine similarity), delete, edge cases.
"""

from __future__ import annotations

import json

import numpy as np
import pytest
from moto import mock_aws

from src.vectorstore.aws_dynamodb import DynamoDBVectorStore
from src.vectorstore.base import VectorSearchResult

TABLE_NAME = "test-vectors"
COLLECTION = "test-collection"
REGION = "eu-central-1"


@pytest.fixture
def dynamodb_store():
    """Create a DynamoDBVectorStore with mocked DynamoDB."""
    with mock_aws():
        store = DynamoDBVectorStore(
            table_name=TABLE_NAME,
            collection_name=COLLECTION,
            region=REGION,
        )
        yield store


def _make_embedding(values: list[float]) -> list[float]:
    """Helper: create a simple embedding vector."""
    return values


class TestDynamoDBVectorStoreInit:
    """Test initialization and table creation."""

    def test_creates_table_if_not_exists(self):
        """Table should be auto-created on first init."""
        with mock_aws():
            store = DynamoDBVectorStore(
                table_name=TABLE_NAME,
                collection_name=COLLECTION,
                region=REGION,
            )
            # The table should exist (store init creates it)
            import boto3

            client = boto3.client("dynamodb", region_name=REGION)
            tables = client.list_tables()["TableNames"]
            assert TABLE_NAME in tables

    def test_idempotent_table_creation(self):
        """Creating a store twice should not raise (table already exists)."""
        with mock_aws():
            DynamoDBVectorStore(
                table_name=TABLE_NAME,
                collection_name=COLLECTION,
                region=REGION,
            )
            # Second init should not crash
            DynamoDBVectorStore(
                table_name=TABLE_NAME,
                collection_name=COLLECTION,
                region=REGION,
            )


class TestStoreVectors:
    """Test storing document chunks."""

    @pytest.mark.asyncio
    async def test_store_single_chunk(self, dynamodb_store: DynamoDBVectorStore):
        """Storing one chunk should return count=1."""
        count = await dynamodb_store.store_vectors(
            document_id="doc-1",
            document_name="test.txt",
            texts=["Hello world"],
            embeddings=[[0.1, 0.2, 0.3]],
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_store_multiple_chunks(self, dynamodb_store: DynamoDBVectorStore):
        """Storing N chunks should return count=N."""
        texts = ["Chunk A", "Chunk B", "Chunk C"]
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]

        count = await dynamodb_store.store_vectors(
            document_id="doc-1",
            document_name="test.txt",
            texts=texts,
            embeddings=embeddings,
        )
        assert count == 3

    @pytest.mark.asyncio
    async def test_store_with_metadata(self, dynamodb_store: DynamoDBVectorStore):
        """Metadata (including page_number) should be stored correctly."""
        count = await dynamodb_store.store_vectors(
            document_id="doc-1",
            document_name="test.pdf",
            texts=["Page 1 content"],
            embeddings=[[0.1, 0.2, 0.3]],
            metadatas=[{"page_number": 1, "source": "manual"}],
        )
        assert count == 1

        # Verify metadata was stored by searching
        results = await dynamodb_store.search(
            query_embedding=[0.1, 0.2, 0.3], top_k=1
        )
        assert len(results) == 1
        assert results[0].page_number == 1


class TestSearch:
    """Test vector similarity search."""

    @pytest.mark.asyncio
    async def test_search_returns_most_similar(self, dynamodb_store: DynamoDBVectorStore):
        """Search should return the chunk closest to the query vector."""
        # Store two chunks with different embeddings
        await dynamodb_store.store_vectors(
            document_id="doc-1",
            document_name="test.txt",
            texts=["About refunds", "About shipping"],
            embeddings=[
                [1.0, 0.0, 0.0],  # Points in x-direction
                [0.0, 1.0, 0.0],  # Points in y-direction
            ],
        )

        # Query for something similar to "About refunds" (x-direction)
        results = await dynamodb_store.search(
            query_embedding=[0.9, 0.1, 0.0], top_k=2
        )

        assert len(results) == 2
        assert results[0].text == "About refunds"  # Most similar
        assert results[1].text == "About shipping"  # Less similar
        assert results[0].score > results[1].score

    @pytest.mark.asyncio
    async def test_search_respects_top_k(self, dynamodb_store: DynamoDBVectorStore):
        """Search should return at most top_k results."""
        texts = [f"Chunk {i}" for i in range(10)]
        embeddings = [
            [float(i) / 10, float(10 - i) / 10, 0.5] for i in range(10)
        ]

        await dynamodb_store.store_vectors(
            document_id="doc-1",
            document_name="test.txt",
            texts=texts,
            embeddings=embeddings,
        )

        results = await dynamodb_store.search(
            query_embedding=[0.5, 0.5, 0.5], top_k=3
        )
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_empty_collection(self, dynamodb_store: DynamoDBVectorStore):
        """Searching an empty collection should return an empty list."""
        results = await dynamodb_store.search(
            query_embedding=[0.1, 0.2, 0.3], top_k=5
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_search_returns_correct_type(self, dynamodb_store: DynamoDBVectorStore):
        """Results should be VectorSearchResult instances."""
        await dynamodb_store.store_vectors(
            document_id="doc-1",
            document_name="test.txt",
            texts=["Test chunk"],
            embeddings=[[0.1, 0.2, 0.3]],
        )

        results = await dynamodb_store.search(
            query_embedding=[0.1, 0.2, 0.3], top_k=1
        )

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, VectorSearchResult)
        assert result.text == "Test chunk"
        assert result.document_name == "test.txt"
        assert result.score > 0.99  # Same vector → cosine similarity ≈ 1.0
        assert result.metadata["document_id"] == "doc-1"
        assert result.metadata["chunk_index"] == 0

    @pytest.mark.asyncio
    async def test_cosine_similarity_correctness(self, dynamodb_store: DynamoDBVectorStore):
        """Verify the cosine similarity calculation is correct."""
        # Orthogonal vectors → cosine similarity = 0
        # Identical vectors → cosine similarity = 1
        # Opposite vectors → cosine similarity = -1
        await dynamodb_store.store_vectors(
            document_id="doc-1",
            document_name="test.txt",
            texts=["Same direction", "Orthogonal", "Opposite"],
            embeddings=[
                [1.0, 0.0, 0.0],   # Same as query
                [0.0, 1.0, 0.0],   # Orthogonal to query
                [-1.0, 0.0, 0.0],  # Opposite to query
            ],
        )

        results = await dynamodb_store.search(
            query_embedding=[1.0, 0.0, 0.0], top_k=3
        )

        assert results[0].text == "Same direction"
        assert abs(results[0].score - 1.0) < 0.001  # Should be ~1.0

        # Find the orthogonal result
        ortho = [r for r in results if r.text == "Orthogonal"][0]
        assert abs(ortho.score - 0.0) < 0.001  # Should be ~0.0


class TestDeleteDocument:
    """Test deleting document vectors."""

    @pytest.mark.asyncio
    async def test_delete_existing_document(self, dynamodb_store: DynamoDBVectorStore):
        """Deleting a document should remove all its chunks."""
        await dynamodb_store.store_vectors(
            document_id="doc-1",
            document_name="test.txt",
            texts=["Chunk A", "Chunk B"],
            embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        )

        deleted = await dynamodb_store.delete_document("doc-1")
        assert deleted == 2

        # Verify chunks are gone
        results = await dynamodb_store.search(
            query_embedding=[0.1, 0.2, 0.3], top_k=5
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, dynamodb_store: DynamoDBVectorStore):
        """Deleting a document that doesn't exist should return 0."""
        deleted = await dynamodb_store.delete_document("nonexistent")
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_delete_only_target_document(self, dynamodb_store: DynamoDBVectorStore):
        """Deleting one document should not affect other documents."""
        await dynamodb_store.store_vectors(
            document_id="doc-1",
            document_name="test1.txt",
            texts=["Doc 1 content"],
            embeddings=[[0.1, 0.2, 0.3]],
        )
        await dynamodb_store.store_vectors(
            document_id="doc-2",
            document_name="test2.txt",
            texts=["Doc 2 content"],
            embeddings=[[0.4, 0.5, 0.6]],
        )

        await dynamodb_store.delete_document("doc-1")

        # Doc 2 should still be searchable
        results = await dynamodb_store.search(
            query_embedding=[0.4, 0.5, 0.6], top_k=5
        )
        assert len(results) == 1
        assert results[0].text == "Doc 2 content"
