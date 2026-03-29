"""
Pydantic Models — Request and Response schemas for the RAG Chatbot API.

Every model here defines the exact shape of data flowing through the API.
See docs/pydantic-models.md for a detailed explanation of each model and field.

Pydantic enforces validation at runtime:
    - If a required field is missing → 422 Unprocessable Entity
    - If a field has the wrong type → 422 with a clear error message
    - If a field fails a custom validator → 422 with your custom message
"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class CloudProvider(str, Enum):
    """Identifies which cloud backend processed the request."""

    AWS = "aws"
    AZURE = "azure"


class DocumentStatus(str, Enum):
    """Tracks the lifecycle of an uploaded document."""

    PENDING = "pending"  # Uploaded but not yet ingested
    PROCESSING = "processing"  # Currently being chunked + embedded
    READY = "ready"  # Fully ingested and searchable
    FAILED = "failed"  # Ingestion failed


# =============================================================================
# Chat Models
# =============================================================================


class ChatRequest(BaseModel):
    """
    Incoming chat request from the user.

    Fields:
        question: The user's natural language question.
        session_id: Optional session ID to maintain conversation history.
                    If omitted, a new session is created.
        top_k: Override the default number of retrieved chunks (optional).
    """

    question: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The question to ask. Must be between 1 and 5000 characters.",
        examples=["What is the refund policy?", "How do I reset my password?"],
    )
    session_id: str | None = Field(
        default=None,
        description="Session ID for conversation history. Omit to start a new conversation.",
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of document chunks to retrieve. Overrides the default from settings.",
    )


class SourceChunk(BaseModel):
    """
    A single chunk of a document that was used to answer the question.

    This is what makes RAG transparent — you can see exactly which parts
    of which documents the LLM used to generate its answer.

    Fields:
        document_name: Original filename of the source document.
        chunk_text: The actual text content of this chunk.
        relevance_score: How similar this chunk is to the question (0.0 to 1.0).
        page_number: Which page this chunk came from (for PDFs).
    """

    document_name: str = Field(..., description="Filename of the source document")
    chunk_text: str = Field(..., description="The text content of this chunk")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Cosine similarity score (1.0 = perfect match)"
    )
    page_number: int | None = Field(default=None, description="Page number in original document (PDF only)")


class ChatResponse(BaseModel):
    """
    Response returned to the user after a chat query.

    Fields:
        answer: The LLM-generated answer grounded in the retrieved documents.
        sources: List of document chunks that were used to generate the answer.
        session_id: The session ID (new or existing) for follow-up questions.
        request_id: Unique identifier for this request (for debugging/tracing).
        cloud_provider: Which cloud backend processed this request.
        latency_ms: Total processing time in milliseconds.
        token_usage: Token counts for cost tracking.
    """

    answer: str = Field(..., description="The AI-generated answer")
    sources: list[SourceChunk] = Field(default_factory=list, description="Document chunks used as context")
    session_id: str = Field(..., description="Session ID for follow-up questions")
    request_id: UUID = Field(default_factory=uuid4, description="Unique request identifier")
    cloud_provider: CloudProvider = Field(..., description="Which cloud processed this request")
    latency_ms: int = Field(..., description="Processing time in milliseconds")
    token_usage: "TokenUsage | None" = Field(default=None, description="Token counts for the LLM call")


class TokenUsage(BaseModel):
    """
    Token usage for a single LLM call.

    Why track this?
        - LLM APIs charge per token
        - Input tokens = your prompt + context (you pay for the chunks you send)
        - Output tokens = the generated answer (usually more expensive per token)
        - Tracking this lets you estimate costs and set budgets

    Fields:
        input_tokens: Number of tokens in the prompt (question + context).
        output_tokens: Number of tokens in the generated answer.
        total_tokens: Sum of input + output.
        estimated_cost_usd: Estimated cost based on the model's pricing.
    """

    input_tokens: int = Field(..., ge=0, description="Tokens in the prompt")
    output_tokens: int = Field(..., ge=0, description="Tokens in the response")
    total_tokens: int = Field(..., ge=0, description="Total tokens (input + output)")
    estimated_cost_usd: float = Field(default=0.0, ge=0.0, description="Estimated cost in USD")


# Fix forward reference
ChatResponse.model_rebuild()


# =============================================================================
# Document Models
# =============================================================================


class DocumentUploadResponse(BaseModel):
    """
    Response after uploading a document.

    Fields:
        document_id: Unique identifier for the uploaded document.
        filename: Original filename.
        status: Current processing status.
        chunk_count: Number of chunks created (0 if still processing).
        message: Human-readable status message.
    """

    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    status: DocumentStatus = Field(..., description="Processing status")
    chunk_count: int = Field(default=0, ge=0, description="Number of chunks created")
    message: str = Field(..., description="Status message")


class DocumentInfo(BaseModel):
    """
    Information about an ingested document.

    Fields:
        document_id: Unique identifier.
        filename: Original filename.
        status: Current processing status.
        chunk_count: How many chunks this document was split into.
        uploaded_at: When the document was uploaded.
        file_size_bytes: Size of the original file.
    """

    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    status: DocumentStatus = Field(..., description="Processing status")
    chunk_count: int = Field(default=0, description="Number of chunks")
    uploaded_at: datetime = Field(..., description="Upload timestamp (UTC)")
    file_size_bytes: int = Field(..., ge=0, description="File size in bytes")


class DocumentListResponse(BaseModel):
    """
    Response for listing all documents.

    Fields:
        documents: List of document info objects.
        total_count: Total number of documents in the system.
    """

    documents: list[DocumentInfo] = Field(default_factory=list, description="List of documents")
    total_count: int = Field(default=0, ge=0, description="Total document count")


# =============================================================================
# Health Models
# =============================================================================


class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseModel):
    """
    Health of a single backend service.

    Fields:
        name: Service name (e.g. "opensearch", "bedrock", "s3").
        status: healthy / degraded / unhealthy.
        latency_ms: How long the health check took.
        message: Details about the status.
    """

    name: str = Field(..., description="Service name")
    status: HealthStatus = Field(..., description="Service health status")
    latency_ms: int | None = Field(default=None, description="Check latency in ms")
    message: str = Field(default="", description="Status details")


class HealthResponse(BaseModel):
    """
    Overall application health response.

    Fields:
        status: Overall status (worst of all services).
        cloud_provider: Which cloud backend is active.
        services: Individual service health checks.
        uptime_seconds: How long the app has been running.
    """

    status: HealthStatus = Field(..., description="Overall health status")
    cloud_provider: str = Field(..., description="Active cloud provider")
    services: list[ServiceHealth] = Field(default_factory=list, description="Individual service checks")
    uptime_seconds: int = Field(default=0, description="App uptime in seconds")


# =============================================================================
# Error Models
# =============================================================================


class ErrorResponse(BaseModel):
    """
    Standard error response.

    Fields:
        error: Error type (e.g. "validation_error", "not_found").
        message: Human-readable error description.
        request_id: Request ID for tracing.
    """

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error description")
    request_id: UUID = Field(default_factory=uuid4, description="Request ID for tracing")
