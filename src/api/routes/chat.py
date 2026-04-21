"""
Chat Route — The main RAG endpoint.

Provides:
    POST /api/chat — Ask a question, get an AI answer with sources
"""

import time
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from src.api.middleware.guardrails import apply_input_guardrail, apply_output_guardrail
from src.api.models import ChatRequest, ChatResponse, CloudProvider, ErrorResponse, SourceChunk, TokenUsage
from src.config import get_settings
from src.evaluation.evaluator import RAGEvaluator
from src.guardrails.base import GuardrailAction
from src.monitoring.query_logger import (
    EvaluationScores,
    LoggedChunk,
    QueryLogRecord,
    QueryLogger,
)

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

        # --- Input Guardrails ---
        guardrails = getattr(request.app.state, "guardrails", None)
        question = body.question
        question, input_result = await apply_input_guardrail(guardrails, question)

        if input_result and input_result.action == GuardrailAction.BLOCK:
            raise HTTPException(
                status_code=400,
                detail={
                    "blocked": True,
                    "category": input_result.category.value,
                    "details": input_result.details,
                },
            )

        # Execute RAG pipeline
        result = await rag_chain.query(
            question=question,
            session_id=session_id,
            top_k=top_k,
        )

        # --- Output Guardrails ---
        answer = result.get("answer", "I could not generate an answer.")
        answer, output_result = await apply_output_guardrail(guardrails, answer)

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
            answer=answer,
            sources=sources,
            session_id=session_id,
            request_id=request_id,
            cloud_provider=CloudProvider(settings.cloud_provider.value),
            latency_ms=latency_ms,
            token_usage=token_usage,
        )

        logger.info(f"[{request_id}] Response generated in {latency_ms}ms — {len(sources)} sources used")

        # --- Query Logging (I30) ---
        query_logger: QueryLogger | None = getattr(request.app.state, "query_logger", None)
        if query_logger:
            try:
                # Run lightweight heuristic evaluation on the response
                evaluator = RAGEvaluator()
                retrieved_chunks = [(s.chunk_text, s.relevance_score) for s in sources]
                eval_result = evaluator.evaluate(
                    question=body.question,
                    answer=answer,
                    retrieved_chunks=retrieved_chunks,
                )

                scores = EvaluationScores(
                    retrieval=round(eval_result.retrieval.avg_relevance_score, 3),
                    faithfulness=round(eval_result.faithfulness.score, 3),
                    answer_relevance=round(eval_result.answer_relevance.score, 3),
                    overall=round(eval_result.overall_score, 3),
                    passed=eval_result.passed,
                )

                logged_chunks = [
                    LoggedChunk(
                        document_name=s.document_name,
                        chunk_text=s.chunk_text[:500],
                        relevance_score=s.relevance_score,
                    )
                    for s in sources
                ]

                record = QueryLogRecord(
                    request_id=str(request_id),
                    session_id=session_id,
                    question=body.question,
                    cloud_provider=settings.cloud_provider.value,
                    chunks=logged_chunks,
                    top_k=top_k,
                    answer=answer,
                    scores=scores,
                    latency_ms=latency_ms,
                    input_tokens=token_usage.input_tokens if token_usage else 0,
                    output_tokens=token_usage.output_tokens if token_usage else 0,
                    estimated_cost_usd=token_usage.estimated_cost_usd if token_usage else 0.0,
                    failure_category=QueryLogger.classify_failure(scores),
                )
                await query_logger.log_query(record)
            except Exception as log_err:
                logger.warning(f"[{request_id}] Query logging failed (non-fatal): {log_err}")

        return response

    except HTTPException:
        raise  # Re-raise 400s (e.g. guardrail blocks) without wrapping

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[{request_id}] Chat error after {latency_ms}ms: {e}")
        raise HTTPException(status_code=500, detail=str(e))
