"""
Azure AI Search — Vector Store Implementation

Uses Azure AI Search (formerly Cognitive Search) with vector search
to store and retrieve document chunk embeddings.

Why Azure AI Search?
    - Fully managed vector search service
    - Hybrid search (vector + keyword) out of the box
    - Semantic ranking for better results
    - Integrates natively with Azure OpenAI

Cost (Basic tier, West Europe):
    - Basic: ~$75/month (15 GB storage, 3 replicas)
    - Free tier: Available (50 MB, 3 indexes) — good for development
    - See docs/cost-analysis.md for detailed comparison

See docs/azure-services.md for deep dive.
"""

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from loguru import logger

from src.vectorstore.base import BaseVectorStore, VectorSearchResult


class AzureAISearchVectorStore(BaseVectorStore):
    """
    Azure AI Search vector store.

    Initialization:
        store = AzureAISearchVectorStore(
            endpoint="https://my-search.search.windows.net",
            api_key="your-admin-key",
            index_name="rag-chatbot-vectors",
        )
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        index_name: str,
        hnsw_m: int = 4,
        hnsw_ef_construction: int = 400,
        hnsw_ef_search: int = 500,
    ):
        self.index_name = index_name
        self._hnsw_m = hnsw_m
        self._hnsw_ef_construction = hnsw_ef_construction
        self._hnsw_ef_search = hnsw_ef_search
        credential = AzureKeyCredential(api_key)

        self._search_client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=credential,
        )
        self._index_client = SearchIndexClient(
            endpoint=endpoint,
            credential=credential,
        )

        self._ensure_index()
        logger.info(f"Azure AI Search initialized: {endpoint}/{index_name}")

    def _ensure_index(self):
        """Create the search index with vector fields if it doesn't exist."""
        try:
            self._index_client.get_index(self.index_name)
            return  # Index exists
        except Exception:
            pass  # Index doesn't exist, create it

        # Define vector search configuration with explicit HNSW parameters
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw-config",
                    parameters={
                        "m": self._hnsw_m,
                        "efConstruction": self._hnsw_ef_construction,
                        "efSearch": self._hnsw_ef_search,
                    },
                ),
            ],
            profiles=[
                VectorSearchProfile(
                    name="vector-profile",
                    algorithm_configuration_name="hnsw-config",
                ),
            ],
        )

        # Define index fields
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="text", type=SearchFieldDataType.String),
            SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="document_name", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,  # text-embedding-3-small dimension
                vector_search_profile_name="vector-profile",
            ),
        ]

        index = SearchIndex(name=self.index_name, fields=fields, vector_search=vector_search)
        self._index_client.create_index(index)
        logger.info(f"Created Azure AI Search index: {self.index_name}")

    async def store_vectors(
        self,
        document_id: str,
        document_name: str,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> int:
        """Store document chunk embeddings in Azure AI Search."""
        documents = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings, strict=False)):
            metadata = metadatas[i] if metadatas else {}
            documents.append(
                {
                    "id": f"{document_id}_{i}",
                    "text": text,
                    "embedding": embedding,
                    "document_id": document_id,
                    "document_name": document_name,
                    "chunk_index": i,
                    "page_number": metadata.get("page_number", 0),
                }
            )

        # Upload in batches of 1000 (Azure limit)
        batch_size = 1000
        for start in range(0, len(documents), batch_size):
            batch = documents[start : start + batch_size]
            self._search_client.upload_documents(batch)

        logger.info(f"Stored {len(texts)} vectors for document {document_id}")
        return len(texts)

    async def search(self, query_embedding: list[float], top_k: int = 5) -> list[VectorSearchResult]:
        """Search for the most similar vectors using Azure AI Search vector query."""
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=top_k,
            fields="embedding",
        )

        results = self._search_client.search(
            search_text=None,
            vector_queries=[vector_query],
            top=top_k,
        )

        search_results = []
        for result in results:
            search_results.append(
                VectorSearchResult(
                    text=result["text"],
                    document_name=result["document_name"],
                    score=result["@search.score"],
                    page_number=result.get("page_number"),
                    metadata={"document_id": result["document_id"], "chunk_index": result.get("chunk_index", 0)},
                )
            )
        return search_results

    async def delete_document(self, document_id: str) -> int:
        """Delete all vectors for a document from Azure AI Search."""
        # Find all documents with this document_id
        results = self._search_client.search(
            search_text="*",
            filter=f"document_id eq '{document_id}'",
            select=["id"],
        )

        doc_ids = [{"id": r["id"]} for r in results]
        if doc_ids:
            self._search_client.delete_documents(doc_ids)

        logger.info(f"Deleted {len(doc_ids)} vectors for document {document_id}")
        return len(doc_ids)
