"""
RAG Chatbot — Application Configuration

Uses Pydantic Settings to load configuration from environment variables.
See docs/pydantic-models.md for detailed explanation of every field.
"""

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CloudProvider(str, Enum):
    """Which cloud backend to use. Controls LLM, vector store, storage, and history."""

    AWS = "aws"
    AZURE = "azure"
    LOCAL = "local"


class VectorStoreType(str, Enum):
    """Which vector store backend to use within a cloud provider.

    This allows choosing a cheaper vector store (DynamoDB) on AWS
    instead of the default OpenSearch Serverless ($350/month).
    """

    AUTO = "auto"  # Use the default for the cloud provider
    DYNAMODB = "dynamodb"  # DynamoDB + brute-force cosine (~$0/month)


class AppEnvironment(str, Enum):
    """Deployment environment. Affects log verbosity and feature flags."""

    DEV = "dev"
    STG = "stg"
    PRD = "prd"


class Settings(BaseSettings):
    """
    Central configuration for the RAG Chatbot.

    Every setting comes from an environment variable (or .env file).
    Pydantic Settings automatically reads them — you never need to call os.getenv().

    Example:
        CLOUD_PROVIDER=aws  →  settings.cloud_provider == CloudProvider.AWS
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = Field(default="rag-chatbot", description="Service name used in logs and monitoring")
    app_env: AppEnvironment = Field(default=AppEnvironment.DEV, description="Current deployment environment")
    app_port: int = Field(default=8000, description="Port the FastAPI server listens on")
    log_level: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR")

    # --- Cloud Provider ---
    cloud_provider: CloudProvider = Field(
        default=CloudProvider.AWS,
        description="Which cloud to use: 'aws', 'azure', or 'local'. Controls all backend services.",
    )

    # --- RAG Settings ---
    rag_top_k: int = Field(default=5, description="Number of document chunks to retrieve per query")
    rag_chunk_size: int = Field(default=1000, description="Maximum characters per document chunk")
    rag_chunk_overlap: int = Field(default=200, description="Character overlap between consecutive chunks")

    # --- HNSW Tuning (applies to all vector stores: OpenSearch, Azure AI Search, ChromaDB) ---
    hnsw_m: int = Field(
        default=16,
        description=(
            "HNSW max bi-directional connections per node (graph degree). "
            "Higher = better recall but more memory. Typical: 8-32. Default 16."
        ),
    )
    hnsw_ef_construction: int = Field(
        default=512,
        description=(
            "HNSW exploration factor at build time. How many candidates to consider "
            "when connecting a new node. Must be >= m. Higher = better graph, slower build. "
            "Typical: 100-512. Default 512."
        ),
    )
    hnsw_ef_search: int = Field(
        default=512,
        description=(
            "HNSW exploration factor at query time. How many candidates to keep in the "
            "running list during search. Higher = better recall, slower search. "
            "Typical: 50-512. Can be changed per query. Default 512."
        ),
    )
    opensearch_number_of_shards: int = Field(
        default=1,
        description=(
            "Number of shards for the OpenSearch index. Each shard is searched in parallel. "
            "Rule of thumb: 1 shard per 5M vectors. For < 1M vectors, 1 shard is fine. "
            "Cannot be changed after index creation — must reindex."
        ),
    )
    opensearch_number_of_replicas: int = Field(
        default=0,
        description=(
            "Number of replica shards. 0 = no replicas (fine for dev). "
            "1 = one copy per shard (production — survives node failure)."
        ),
    )

    # --- AWS ---
    aws_region: str = Field(default="eu-central-1", description="AWS region for all services")
    aws_bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        description="Bedrock model ID for LLM inference",
    )
    aws_bedrock_region: str = Field(default="eu-central-1", description="Region where Bedrock model is available")
    aws_opensearch_endpoint: str = Field(default="", description="OpenSearch Serverless collection endpoint URL")
    aws_opensearch_index_name: str = Field(default="rag-chatbot-vectors", description="OpenSearch index for vectors")
    aws_s3_bucket_name: str = Field(default="rag-chatbot-documents", description="S3 bucket for uploaded documents")
    aws_dynamodb_table_name: str = Field(
        default="rag-chatbot-conversations", description="DynamoDB table for conversation history"
    )
    aws_dynamodb_vector_table_name: str = Field(
        default="rag-chatbot-vectors", description="DynamoDB table for vector storage (cheap alternative to OpenSearch)"
    )

    # --- Vector Store Override ---
    vector_store_type: VectorStoreType = Field(
        default=VectorStoreType.AUTO,
        description=(
            "Override the vector store backend. "
            "'auto' = use default for cloud_provider (OpenSearch for AWS, AI Search for Azure, ChromaDB for local). "
            "'dynamodb' = use DynamoDB + brute-force cosine similarity (~$0/month on AWS)."
        ),
    )

    # --- Azure ---
    azure_openai_endpoint: str = Field(default="", description="Azure OpenAI resource endpoint URL")
    azure_openai_api_key: str = Field(default="", description="Azure OpenAI API key")
    azure_openai_deployment_name: str = Field(default="gpt-4o", description="Azure OpenAI model deployment name")
    azure_openai_api_version: str = Field(default="2024-08-01-preview", description="Azure OpenAI API version")
    azure_openai_embedding_deployment: str = Field(
        default="text-embedding-3-small", description="Azure OpenAI embedding model deployment"
    )
    azure_search_endpoint: str = Field(default="", description="Azure AI Search endpoint URL")
    azure_search_api_key: str = Field(default="", description="Azure AI Search admin API key")
    azure_search_index_name: str = Field(default="rag-chatbot-vectors", description="Azure AI Search index name")
    azure_storage_connection_string: str = Field(default="", description="Azure Blob Storage connection string")
    azure_storage_container_name: str = Field(default="rag-chatbot-documents", description="Azure Blob container name")
    azure_cosmos_endpoint: str = Field(default="", description="Azure Cosmos DB endpoint URL")
    azure_cosmos_key: str = Field(default="", description="Azure Cosmos DB primary key")
    azure_cosmos_database_name: str = Field(default="rag-chatbot", description="Cosmos DB database name")
    azure_cosmos_container_name: str = Field(default="conversations", description="Cosmos DB container name")

    # --- Local (Ollama + ChromaDB) ---
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    ollama_model: str = Field(default="llama3.2", description="Ollama model for generation")
    ollama_embedding_model: str = Field(default="nomic-embed-text", description="Ollama model for embeddings")
    chroma_collection_name: str = Field(default="rag-chatbot-vectors", description="ChromaDB collection name")
    chroma_persist_directory: str = Field(default="", description="ChromaDB persistence path (empty = in-memory)")

    # --- Guardrails (I23) ---
    guardrails_enabled: bool = Field(default=False, description="Enable input/output guardrails on /api/chat")
    aws_bedrock_guardrail_id: str = Field(default="", description="Bedrock Guardrails resource ID (AWS only)")
    aws_bedrock_guardrail_version: str = Field(default="DRAFT", description="Bedrock Guardrails version (AWS only)")
    azure_content_safety_endpoint: str = Field(default="", description="Azure AI Content Safety endpoint (Azure only)")
    azure_content_safety_key: str = Field(default="", description="Azure AI Content Safety API key (Azure only)")
    azure_language_endpoint: str = Field(
        default="", description="Azure AI Language endpoint for PII detection (Azure only)"
    )
    azure_language_key: str = Field(default="", description="Azure AI Language API key (Azure only)")

    # --- Re-ranker (I24) ---
    reranker_enabled: bool = Field(default=False, description="Enable two-stage retrieval with re-ranking")
    reranker_candidate_count: int = Field(
        default=20, description="Number of candidates to fetch before re-ranking (stage 1)"
    )

    # --- Hybrid Search (I25) ---
    hybrid_search_enabled: bool = Field(default=False, description="Enable hybrid search (BM25 + vector)")
    hybrid_search_alpha: float = Field(
        default=0.7,
        description="Weight for vector results in hybrid search (0.0=BM25 only, 1.0=vector only)",
    )

    # --- Monitoring ---
    otel_exporter_otlp_endpoint: str = Field(default="", description="OpenTelemetry collector endpoint")
    otel_service_name: str = Field(default="rag-chatbot", description="Service name in traces")
    enable_tracing: bool = Field(default=False, description="Enable OpenTelemetry distributed tracing")

    # --- Query Logging (I30) ---
    query_log_enabled: bool = Field(
        default=True,
        description="Enable structured per-query logging for production debugging. Logs to JSONL files.",
    )
    query_log_dir: str = Field(
        default="logs/queries",
        description="Directory for structured query log files (JSONL). One file per day.",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns the singleton Settings instance.

    Uses @lru_cache so the .env file is only read once.
    Every subsequent call returns the same object from memory.
    """
    return Settings()
