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
        description="Which cloud to use: 'aws' or 'azure'. Controls all backend services.",
    )

    # --- RAG Settings ---
    rag_top_k: int = Field(default=5, description="Number of document chunks to retrieve per query")
    rag_chunk_size: int = Field(default=1000, description="Maximum characters per document chunk")
    rag_chunk_overlap: int = Field(default=200, description="Character overlap between consecutive chunks")

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
    azure_storage_container_name: str = Field(
        default="rag-chatbot-documents", description="Azure Blob container name"
    )
    azure_cosmos_endpoint: str = Field(default="", description="Azure Cosmos DB endpoint URL")
    azure_cosmos_key: str = Field(default="", description="Azure Cosmos DB primary key")
    azure_cosmos_database_name: str = Field(default="rag-chatbot", description="Cosmos DB database name")
    azure_cosmos_container_name: str = Field(default="conversations", description="Cosmos DB container name")

    # --- Monitoring ---
    otel_exporter_otlp_endpoint: str = Field(default="", description="OpenTelemetry collector endpoint")
    otel_service_name: str = Field(default="rag-chatbot", description="Service name in traces")
    enable_tracing: bool = Field(default=False, description="Enable OpenTelemetry distributed tracing")


@lru_cache
def get_settings() -> Settings:
    """
    Returns the singleton Settings instance.

    Uses @lru_cache so the .env file is only read once.
    Every subsequent call returns the same object from memory.
    """
    return Settings()
