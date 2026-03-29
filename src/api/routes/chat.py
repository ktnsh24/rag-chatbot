"""
Chat Route — The main RAG endpoint.

Provides:
    POST /api/chat — Ask a question, get an AI answer with sources
"""

import time
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from src.api.models import ChatRequest, ChatResponse, CloudProvider, ErrorResponse, SourceChunk, TokenUsage
from src.config import get_settings

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Ask a Question",
    description="Send a question and get an AI-generated answer grounded in your uploaded documents.",
)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """
    RAG Chat Endpoint — the core of this application.

    Flow:
        1. Receive the user's question
        2. Retrieve the top-k most relevant document chunks from the vector store
        3. Send the question + chunks to the LLM
        4. Return the answer with source citations

    If no RAG chain is initialized (e.g. missing credentials), returns a 500 error.
    """
    start_time = time.time()
    settings = get_settings()
    request_id = uuid4()

    logger.info(f"[{request_id}] Chat request: {body.question[:100]}...")

    # Check RAG chain availability
    rag_chain = getattr(request.app.state, "rag_chain", None)
    if rag_chain is None:
        raise HTTPException(
            status_code=500,
            detail="RAG chain not initialized. Check your cloud credentials and restart the app.",
        )

    try:
        # Determine session ID
        session_id = body.session_id or str(uuid4())
        top_k = body.top_k or settings.rag_top_k

        # Execute RAG pipeline
        result = await rag_chain.query(
            question=body.question,
            session_id=session_id,
            top_k=top_k,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # Build source chunks
        sources = [
            SourceChunk(
                document_name=chunk.get("document_name", "unknown"),
                chunk_text=chunk.get("text", ""),
                relevance_score=chunk.get("score", 0.0),
                page_number=chunk.get("page_number"),
            )
            for chunk in result.get("sources", [])
        ]

        # Build token usage
        token_usage = None
        if usage := result.get("token_usage"):
            token_usage = TokenUsage(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                estimated_cost_usd=usage.get("estimated_cost_usd", 0.0),
            )

        # Track metrics
        metrics = getattr(request.app.state, "metrics", None)
        if metrics:
            metrics.record_chat_request(latency_ms=latency_ms, token_usage=token_usage)

        response = ChatResponse(
            answer=result.get("answer", "I could not generate an answer."),
            sources=sources,
            session_id=session_id,
            request_id=request_id,
            cloud_provider=CloudProvider(settings.cloud_provider.value),
            latency_ms=latency_ms,
            token_usage=token_usage,
        )

        logger.info(f"[{request_id}] Response generated in {latency_ms}ms — {len(sources)} sources used")
        return response

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[{request_id}] Chat error after {latency_ms}ms: {e}")
        raise HTTPException(status_code=500, detail=str(e))
