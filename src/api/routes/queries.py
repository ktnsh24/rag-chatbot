"""
Queries Route — Production debugging endpoints for RAG query analysis.

Story I30: Provides endpoints for AI engineers to inspect query quality:
    GET  /api/queries/failures   — List recent failed queries with triage categories
    GET  /api/queries/stats      — Aggregate pass rate, avg scores, failure breakdown

These endpoints power the production debugging workflow:
    1. Check /api/queries/stats → see pass rate dropping
    2. Hit /api/queries/failures → see which queries failed
    3. Read the chunks + scores → diagnose root cause
    4. Fix the issue → re-run golden dataset to verify

DE parallel: This is like having a /api/pipeline/failures endpoint that shows
which DAG runs failed and why — instead of digging through Airflow logs manually.
"""

from fastapi import APIRouter, HTTPException, Query, Request

from src.monitoring.query_logger import QueryLogRecord

router = APIRouter()


@router.get(
    "/queries/failures",
    response_model=list[QueryLogRecord],
    summary="List Failed Queries",
    description=(
        "Returns recent queries that failed evaluation (overall score < 0.70). "
        "Each record includes the question, retrieved chunks with scores, "
        "the LLM answer, evaluation scores, and a failure category for triage. "
        "Use the 'category' param to filter: bad_retrieval, hallucination, both_bad, off_topic."
    ),
)
async def list_failures(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100, description="Max results to return"),
    days: int = Query(default=7, ge=1, le=30, description="How many days back to search"),
    category: str | None = Query(
        default=None,
        description="Filter by failure category: bad_retrieval, hallucination, both_bad, off_topic, marginal",
    ),
) -> list[QueryLogRecord]:
    """
    List recent failed queries for debugging.

    Failure categories (from the triage table):
        - bad_retrieval: chunks were irrelevant, LLM couldn't answer properly
        - hallucination: chunks were good, but LLM made things up
        - both_bad: wrong chunks AND LLM improvised
        - off_topic: good chunks, faithful, but didn't address the question
        - marginal: failed overall but no single dimension is terrible
    """
    query_logger = getattr(request.app.state, "query_logger", None)
    if query_logger is None:
        raise HTTPException(status_code=503, detail="Query logger not initialized")

    return await query_logger.get_failures(limit=limit, days=days, category=category)


@router.get(
    "/queries/stats",
    summary="Query Quality Stats",
    description=(
        "Returns aggregate stats from recent query logs: total queries, "
        "pass rate, average scores, and failure category breakdown."
    ),
)
async def query_stats(
    request: Request,
    days: int = Query(default=1, ge=1, le=30, description="How many days to aggregate"),
) -> dict:
    """
    Get aggregate query quality statistics.

    Returns:
        total_queries: How many queries were logged
        passed: Number that scored >= 0.70 overall
        failed: Number that scored < 0.70
        pass_rate: Percentage passed
        avg_retrieval: Average retrieval score
        avg_faithfulness: Average faithfulness score
        avg_relevance: Average relevance score
        failure_breakdown: Count per failure category
    """
    query_logger = getattr(request.app.state, "query_logger", None)
    if query_logger is None:
        raise HTTPException(status_code=503, detail="Query logger not initialized")

    return await query_logger.get_stats(days=days)
