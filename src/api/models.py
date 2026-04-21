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
    LOCAL = "local"


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


class BatchDocumentResult(BaseModel):
    """
    Result of ingesting a single document within a batch upload.

    Fields:
        document_id: Unique identifier for this document.
        filename: Original filename.
        status: Processing status (ready or failed).
        chunk_count: Number of chunks created.
        error: Error message if ingestion failed.
    """

    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    status: DocumentStatus = Field(..., description="Processing status")
    chunk_count: int = Field(default=0, ge=0, description="Number of chunks created")
    error: str | None = Field(default=None, description="Error message if failed")


class BatchUploadResponse(BaseModel):
    """
    Response after uploading multiple documents in a single batch.

    Fields:
        total_files: Number of files submitted.
        succeeded: Number of files successfully ingested.
        failed: Number of files that failed.
        total_chunks: Total chunks created across all documents.
        results: Per-file results.
        message: Human-readable summary.
    """

    total_files: int = Field(..., ge=0, description="Total files in batch")
    succeeded: int = Field(..., ge=0, description="Files successfully ingested")
    failed: int = Field(..., ge=0, description="Files that failed")
    total_chunks: int = Field(default=0, ge=0, description="Total chunks across all files")
    results: list[BatchDocumentResult] = Field(default_factory=list, description="Per-file results")
    message: str = Field(..., description="Summary message")


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


# =============================================================================
# Evaluation Models
# =============================================================================


class EvaluateSingleRequest(BaseModel):
    """
    Request to evaluate a single question through the live RAG pipeline.

    Fields:
        question: The question to ask and evaluate.
        expected_answer: Optional ground truth for comparison.
        top_k: Override the default number of retrieved chunks.
    """

    question: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The question to evaluate.",
        examples=["What is the refund policy?"],
    )
    expected_answer: str | None = Field(
        default=None,
        description="Optional expected answer (ground truth) for comparison.",
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of chunks to retrieve. Overrides settings default.",
    )


class EvaluateSuiteRequest(BaseModel):
    """
    Request to run the golden dataset evaluation suite.

    Fields:
        categories: Optional list of categories to filter (e.g. ["policy", "edge_case"]).
                    If omitted, runs all categories.
        top_k: Override the default number of retrieved chunks for all cases.
    """

    categories: list[str] | None = Field(
        default=None,
        description="Filter by test case categories. Omit to run all.",
        examples=[["policy", "edge_case"]],
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Override top_k for all evaluation cases.",
    )


class EvaluationScoreDetail(BaseModel):
    """
    Detailed scores from the RAG evaluation.

    These are the 3 dimensions that define RAG quality:
        - Retrieval: Did vector search find relevant chunks?
        - Faithfulness: Did the LLM stick to the context (no hallucination)?
        - Answer Relevance: Did the LLM actually answer the question?
    """

    retrieval: float = Field(..., ge=0.0, le=1.0, description="Retrieval quality score")
    retrieval_quality: str = Field(..., description="Quality label: excellent/good/fair/poor")
    faithfulness: float = Field(..., ge=0.0, le=1.0, description="Faithfulness score (1.0 = no hallucination)")
    has_hallucination: bool = Field(..., description="True if the answer contains claims not in the context")
    answer_relevance: float = Field(..., ge=0.0, le=1.0, description="Answer relevance score")
    answer_relevance_quality: str = Field(..., description="Quality label: highly relevant/partially relevant/off-topic")
    overall: float = Field(..., ge=0.0, le=1.0, description="Weighted overall score (retrieval 30% + faithfulness 40% + relevance 30%)")
    passed: bool = Field(..., description="True if overall score >= 0.7")


class EvaluateSingleResponse(BaseModel):
    """
    Response from evaluating a single question.

    Contains the answer (same as /api/chat) PLUS evaluation scores.
    This is the key difference: /api/chat returns answers, /api/evaluate
    returns answers WITH quality measurements.
    """

    question: str = Field(..., description="The evaluated question")
    answer: str = Field(..., description="The LLM-generated answer")
    scores: EvaluationScoreDetail = Field(..., description="Evaluation scores")
    sources_used: int = Field(..., ge=0, description="Number of source chunks retrieved")
    evaluation_notes: list[str] = Field(default_factory=list, description="Diagnostic notes from the evaluator")
    cloud_provider: CloudProvider = Field(..., description="Which cloud processed this")
    latency_ms: int = Field(..., description="Total processing time in milliseconds")
    request_id: UUID = Field(default_factory=uuid4, description="Unique request ID")


class EvaluationCaseResult(BaseModel):
    """
    Result of evaluating a single golden dataset test case.
    Used as an item within the suite response.
    """

    case_id: str = Field(..., description="Golden dataset case ID (e.g. refund_basic)")
    category: str = Field(..., description="Test case category")
    question: str = Field(..., description="The test question")
    answer_preview: str = Field(..., description="First 200 chars of the answer")
    scores: EvaluationScoreDetail = Field(..., description="Evaluation scores")
    passed: bool = Field(..., description="Whether this case passed")
    notes: list[str] = Field(default_factory=list, description="Diagnostic notes")
    latency_ms: int = Field(..., description="Processing time for this case")


class EvaluateSuiteResponse(BaseModel):
    """
    Response from running the full golden dataset evaluation suite.

    This is the AI Engineer's equivalent of a dbt test summary:
    - How many passed/failed
    - Overall quality score
    - Per-case breakdown for debugging failures

    DE parallel: Like `dbt test` output — total tests, passed, failed, warnings.
    """

    total_cases: int = Field(..., ge=0, description="Total test cases evaluated")
    passed: int = Field(..., ge=0, description="Number of cases that passed")
    failed: int = Field(..., ge=0, description="Number of cases that failed")
    pass_rate: float = Field(..., ge=0.0, le=100.0, description="Pass rate percentage")
    average_overall_score: float = Field(..., ge=0.0, le=1.0, description="Average overall score across all cases")
    cases: list[EvaluationCaseResult] = Field(default_factory=list, description="Per-case results")
    cloud_provider: CloudProvider = Field(..., description="Which cloud processed this")
    latency_ms: int = Field(..., description="Total suite processing time")
    request_id: UUID = Field(default_factory=uuid4, description="Unique request ID")
