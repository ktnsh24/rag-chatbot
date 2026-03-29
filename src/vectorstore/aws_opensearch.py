"""
Amazon OpenSearch Serverless — Vector Store Implementation

Uses OpenSearch Serverless with vector search (k-NN plugin) to store
and retrieve document chunk embeddings.

Why OpenSearch Serverless (not regular OpenSearch)?
    - No cluster management — AWS handles scaling
    - Pay per OCU (OpenSearch Compute Unit) — scales to zero when idle
    - Built-in k-NN vector search
    - Encryption at rest and in transit by default

Cost:
    - Indexing OCU: $0.24/hr (minimum 2 OCUs = $0.48/hr when active)
    - Search OCU:  $0.24/hr (minimum 2 OCUs = $0.48/hr when active)
    - Storage:     $0.024/GB/month
    - ⚠️ WARNING: Minimum ~$350/month even when idle (OCUs don't scale to zero yet)
    - See docs/cost-analysis.md for cheaper alternatives

See docs/aws-services.md for deep dive on OpenSearch Serverless.
"""

import json
from uuid import uuid4

from loguru import logger
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection

from src.vectorstore.base import BaseVectorStore, VectorSearchResult


class OpenSearchVectorStore(BaseVectorStore):
    """
    Amazon OpenSearch Serverless vector store.

    Initialization:
        store = OpenSearchVectorStore(
            endpoint="https://abc123.eu-central-1.aoss.amazonaws.com",
            index_name="rag-chatbot-vectors",
            region="eu-central-1",
        )
    """

    def __init__(self, endpoint: str, index_name: str, region: str):
        self.index_name = index_name
        self.endpoint = endpoint

        # Create OpenSearch client with AWS SigV4 auth
        import boto3

        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, region, "aoss")

        self._client = OpenSearch(
            hosts=[{"host": endpoint.replace("https://", ""), "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30,
        )

        # Create index if it doesn't exist
        self._ensure_index()
        logger.info(f"OpenSearch vector store initialized: {endpoint}/{index_name}")

    def _ensure_index(self):
        """Create the vector index with k-NN settings if it doesn't exist."""
        if not self._client.indices.exists(self.index_name):
            body = {
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 512,
                    }
                },
                "mappings": {
                    "properties": {
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 1024,  # Titan Embeddings v2 dimension
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib",
                            },
                        },
                        "text": {"type": "text"},
                        "document_id": {"type": "keyword"},
                        "document_name": {"type": "keyword"},
                        "page_number": {"type": "integer"},
                        "chunk_index": {"type": "integer"},
                    }
                },
            }
            self._client.indices.create(self.index_name, body=body)
            logger.info(f"Created OpenSearch index: {self.index_name}")

    async def store_vectors(
        self,
        document_id: str,
        document_name: str,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> int:
        """Store document chunk embeddings in OpenSearch."""
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            metadata = metadatas[i] if metadatas else {}
            doc = {
                "embedding": embedding,
                "text": text,
                "document_id": document_id,
                "document_name": document_name,
                "chunk_index": i,
                "page_number": metadata.get("page_number"),
            }
            self._client.index(
                index=self.index_name,
                body=doc,
                id=f"{document_id}_{i}",
            )

        # Refresh index to make documents searchable immediately
        self._client.indices.refresh(self.index_name)
        logger.info(f"Stored {len(texts)} vectors for document {document_id}")
        return len(texts)

    async def search(self, query_embedding: list[float], top_k: int = 5) -> list[VectorSearchResult]:
        """Search for the most similar vectors using k-NN."""
        body = {
            "size": top_k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": top_k,
                    }
                }
            },
        }

        response = self._client.search(index=self.index_name, body=body)
        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            results.append(
                VectorSearchResult(
                    text=source["text"],
                    document_name=source["document_name"],
                    score=hit["_score"],
                    page_number=source.get("page_number"),
                    metadata={"document_id": source["document_id"], "chunk_index": source.get("chunk_index", 0)},
                )
            )
        return results

    async def delete_document(self, document_id: str) -> int:
        """Delete all vectors for a document."""
        body = {"query": {"term": {"document_id": document_id}}}
        response = self._client.delete_by_query(index=self.index_name, body=body)
        deleted = response.get("deleted", 0)
        logger.info(f"Deleted {deleted} vectors for document {document_id}")
        return deleted
