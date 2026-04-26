"""
RAG Chain — Orchestrator that ties everything together.

This is the central class that coordinates:
    1. Document ingestion (read → chunk → embed → store)
    2. Query processing (embed question → search → generate answer)

It uses the abstract interfaces (BaseLLM, BaseVectorStore) so it
doesn't care whether the backend is AWS or Azure.

Pattern: Factory Method
    RAGChain.create(settings) → reads CLOUD_PROVIDER → builds the right backends
"""

from loguru import logger

from src.config import CloudProvider, Settings, VectorStoreType
from src.llm.base import BaseLLM
from src.rag.ingestion import chunk_document, read_document
from src.rag.reranker import BaseReranker
from src.vectorstore.base import BaseVectorStore


class RAGChain:
    """
    The RAG pipeline orchestrator.

    Usage:
        chain = await RAGChain.create(settings)

        # Ingest a document
        chunks = await chain.ingest_document("doc-1", "manual.pdf", pdf_bytes)

        # Ask a question
        result = await chain.query("What is the refund policy?")
    """

    def __init__(
        self,
        llm: BaseLLM,
        vector_store: BaseVectorStore,
        settings: Settings,
        reranker: BaseReranker | None = None,
    ):
        self._llm = llm
        self._vector_store = vector_store
        self._settings = settings
        self._reranker = reranker

    @classmethod
    async def create(cls, settings: Settings) -> "RAGChain":
        """
        Factory method — creates a RAGChain with the right backends.

        Reads settings.cloud_provider and builds:
            AWS:   BedrockLLM + OpenSearchVectorStore
            Azure: AzureOpenAILLM + AzureAISearchVectorStore
            Local: OllamaLLM + ChromaDBVectorStore
        """
        if settings.cloud_provider == CloudProvider.AWS:
            llm, vector_store = await cls._create_aws_backends(settings)
        elif settings.cloud_provider == CloudProvider.AZURE:
            llm, vector_store = await cls._create_azure_backends(settings)
        elif settings.cloud_provider == CloudProvider.LOCAL:
            llm, vector_store = await cls._create_local_backends(settings)
        else:
            raise ValueError(f"Unknown cloud provider: {settings.cloud_provider}")

        # Override vector store if explicitly requested (skips default that may need unconfigured endpoints)
        if settings.vector_store_type == VectorStoreType.DYNAMODB and settings.cloud_provider != CloudProvider.AWS:
            vector_store = cls._create_dynamodb_vector_store(settings)
            logger.info("Vector store overridden to DynamoDB (cheap mode)")

        # Create re-ranker if enabled (I24)
        reranker = cls._create_reranker(settings) if settings.reranker_enabled else None

        logger.info(f"RAG chain created with {settings.cloud_provider.value} backends")
        return cls(llm=llm, vector_store=vector_store, settings=settings, reranker=reranker)

    @staticmethod
    async def _create_aws_backends(settings: Settings) -> tuple[BaseLLM, BaseVectorStore]:
        """Initialize AWS-specific backends."""
        from src.llm.aws_bedrock import BedrockLLM

        llm = BedrockLLM(
            model_id=settings.aws_bedrock_model_id,
            region=settings.aws_bedrock_region,
        )

        # Skip OpenSearch when DynamoDB is explicitly requested (avoids empty endpoint error)
        if settings.vector_store_type == VectorStoreType.DYNAMODB:
            vector_store = RAGChain._create_dynamodb_vector_store(settings)
        else:
            from src.vectorstore.aws_opensearch import OpenSearchVectorStore

            vector_store = OpenSearchVectorStore(
                endpoint=settings.aws_opensearch_endpoint,
                index_name=settings.aws_opensearch_index_name,
                region=settings.aws_region,
                hnsw_m=settings.hnsw_m,
                hnsw_ef_construction=settings.hnsw_ef_construction,
                hnsw_ef_search=settings.hnsw_ef_search,
                number_of_shards=settings.opensearch_number_of_shards,
                number_of_replicas=settings.opensearch_number_of_replicas,
            )
        return llm, vector_store

    @staticmethod
    async def _create_azure_backends(settings: Settings) -> tuple[BaseLLM, BaseVectorStore]:
        """Initialize Azure-specific backends."""
        from src.llm.azure_openai import AzureOpenAILLM
        from src.vectorstore.azure_ai_search import AzureAISearchVectorStore

        llm = AzureOpenAILLM(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment_name=settings.azure_openai_deployment_name,
            api_version=settings.azure_openai_api_version,
            embedding_deployment=settings.azure_openai_embedding_deployment,
        )
        vector_store = AzureAISearchVectorStore(
            endpoint=settings.azure_search_endpoint,
            api_key=settings.azure_search_api_key,
            index_name=settings.azure_search_index_name,
            hnsw_m=settings.hnsw_m,
            hnsw_ef_construction=settings.hnsw_ef_construction,
            hnsw_ef_search=settings.hnsw_ef_search,
        )
        return llm, vector_store

    @staticmethod
    async def _create_local_backends(settings: Settings) -> tuple[BaseLLM, BaseVectorStore]:
        """Initialize local backends (Ollama + ChromaDB) — no cloud credentials needed."""
        from src.llm.local_ollama import OllamaLLM
        from src.vectorstore.local_chromadb import ChromaDBVectorStore

        llm = OllamaLLM(
            base_url=settings.ollama_base_url,
            model_name=settings.ollama_model,
            embedding_model=settings.ollama_embedding_model,
        )
        vector_store = ChromaDBVectorStore(
            collection_name=settings.chroma_collection_name,
            persist_directory=settings.chroma_persist_directory or None,
            hnsw_m=settings.hnsw_m,
            hnsw_ef_construction=settings.hnsw_ef_construction,
            hnsw_ef_search=settings.hnsw_ef_search,
        )
        return llm, vector_store

    @staticmethod
    def _create_dynamodb_vector_store(settings: Settings) -> BaseVectorStore:
        """Create a DynamoDB vector store (cheap alternative to OpenSearch).

        Cost: ~$0/month (DynamoDB free tier) vs ~$350/month (OpenSearch Serverless).
        Trade-off: Brute-force cosine similarity — fine for < 10,000 chunks.
        """
        from src.vectorstore.aws_dynamodb import DynamoDBVectorStore

        return DynamoDBVectorStore(
            table_name=settings.aws_dynamodb_vector_table_name,
            collection_name=settings.chroma_collection_name,  # Reuse collection name
            region=settings.aws_region,
        )

    @staticmethod
    def _create_reranker(settings: Settings) -> BaseReranker:
        """Create a re-ranker based on cloud provider (I24).

        AWS:   Bedrock Reranker (amazon.rerank-v1:0)
        Azure: Azure AI Search Semantic Ranker
        Local: sentence-transformers CrossEncoder
        """
        if settings.cloud_provider == CloudProvider.AWS:
            from src.rag.reranker import AWSReranker

            return AWSReranker(region=settings.aws_region)
        elif settings.cloud_provider == CloudProvider.AZURE:
            from src.rag.reranker import AzureReranker

            return AzureReranker(
                endpoint=settings.azure_search_endpoint,
                api_key=settings.azure_search_api_key,
                index_name=settings.azure_search_index_name,
            )
        else:
            from src.rag.reranker import LocalReranker

            return LocalReranker()

    async def ingest_document(self, document_id: str, filename: str, content: bytes) -> int:
        """
        Ingest a document into the RAG system.

        Pipeline:
            1. Read the document (PDF, TXT, etc.) → raw text
            2. Split into chunks → list of text strings
            3. Generate embeddings → list of float vectors
            4. Store in vector database → searchable

        Args:
            document_id: Unique identifier for the document.
            filename: Original filename.
            content: Raw file bytes.

        Returns:
            Number of chunks created.
        """
        logger.info(f"[{document_id}] Ingesting: {filename}")

        # Step 1: Read document
        text = read_document(filename, content)
        logger.info(f"[{document_id}] Extracted {len(text)} characters")

        # Step 2: Chunk
        chunks = chunk_document(
            text,
            chunk_size=self._settings.rag_chunk_size,
            chunk_overlap=self._settings.rag_chunk_overlap,
        )
        logger.info(f"[{document_id}] Split into {len(chunks)} chunks")

        # Step 3: Embed
        embeddings = await self._llm.get_embeddings_batch(chunks)
        logger.info(f"[{document_id}] Generated {len(embeddings)} embeddings")

        # Step 4: Store
        stored = await self._vector_store.store_vectors(
            document_id=document_id,
            document_name=filename,
            texts=chunks,
            embeddings=embeddings,
        )
        logger.info(f"[{document_id}] Stored {stored} vectors")

        return stored

    async def ingest_documents(
        self,
        documents: list[tuple[str, str, bytes]],
    ) -> list[tuple[str, str, int, str | None]]:
        """
        Ingest multiple documents in a batch.

        This is more efficient than calling ingest_document() in a loop because:
            - Embeddings can be batched across documents
            - Vector store bulk APIs are used (OpenSearch _bulk, Azure upload_documents)
            - Reduces total HTTP round-trips

        Args:
            documents: List of (document_id, filename, content) tuples.

        Returns:
            List of (document_id, filename, chunk_count, error) tuples.
            error is None on success, or an error message string on failure.
        """
        results: list[tuple[str, str, int, str | None]] = []

        for document_id, filename, content in documents:
            try:
                chunk_count = await self.ingest_document(
                    document_id=document_id,
                    filename=filename,
                    content=content,
                )
                results.append((document_id, filename, chunk_count, None))
            except Exception as e:
                logger.error(f"[{document_id}] Batch ingestion failed for {filename}: {e}")
                results.append((document_id, filename, 0, str(e)))

        return results

    async def query(self, question: str, session_id: str, top_k: int | None = None) -> dict:
        """
        Execute a RAG query.

        Pipeline:
            1. Embed the question → vector
            2. Search vector store → top_k most similar chunks
            3. Build prompt with question + context chunks
            4. Send to LLM → generate answer
            5. Return answer + sources + token usage

        Args:
            question: The user's question.
            session_id: Session ID for conversation history.
            top_k: Number of chunks to retrieve (overrides default).

        Returns:
            Dict with keys: answer, sources, token_usage
        """
        k = top_k or self._settings.rag_top_k

        # Step 1: Embed the question
        query_embedding = await self._llm.get_embedding(question)

        # Step 2: Search for relevant chunks
        # If re-ranking is enabled, retrieve more candidates (stage 1) then re-rank (stage 2)
        retrieve_k = self._settings.reranker_candidate_count if self._reranker else k
        search_results = await self._vector_store.search(
            query_embedding=query_embedding,
            top_k=retrieve_k,
        )

        if not search_results:
            return {
                "answer": "I don't have any documents to answer your question. Please upload documents first.",
                "sources": [],
                "token_usage": None,
            }

        # Step 2b: Re-rank if enabled (I24 — two-stage retrieval)
        if self._reranker and search_results:
            search_results = await self._reranker.rerank(
                query=question,
                results=search_results,
                top_k=k,
            )
            logger.info(f"Re-ranked {retrieve_k} → {len(search_results)} results")

        # Step 3: Build context from search results
        context_texts = [result.text for result in search_results]

        # Step 4: Generate answer
        llm_response = await self._llm.generate(
            prompt=question,
            context=context_texts,
        )

        # Step 5: Build response
        sources = [
            {
                "document_name": result.document_name,
                "text": result.text[:500],  # Truncate for response
                "score": round(result.score, 4),
                "page_number": result.page_number,
            }
            for result in search_results
        ]

        token_usage = {
            "input_tokens": llm_response.input_tokens,
            "output_tokens": llm_response.output_tokens,
            "total_tokens": llm_response.input_tokens + llm_response.output_tokens,
            "estimated_cost_usd": self._estimate_cost(llm_response.input_tokens, llm_response.output_tokens),
        }

        return {
            "answer": llm_response.text,
            "sources": sources,
            "token_usage": token_usage,
        }

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost in USD based on the cloud provider's pricing.

        These are approximate prices — check the provider's pricing page for current rates.
        """
        if self._settings.cloud_provider == CloudProvider.LOCAL:
            return 0.0  # Local models are free
        elif self._settings.cloud_provider == CloudProvider.AWS:
            # Claude 3.5 Sonnet v2 pricing
            input_cost = (input_tokens / 1000) * 0.003
            output_cost = (output_tokens / 1000) * 0.015
        else:
            # GPT-4o pricing
            input_cost = (input_tokens / 1000) * 0.0025
            output_cost = (output_tokens / 1000) * 0.01

        return round(input_cost + output_cost, 6)
