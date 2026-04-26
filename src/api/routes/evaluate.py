"""
Evaluate Route — Run the RAG Evaluation Pipeline.

Provides:
    POST /api/evaluate          — Evaluate a single question against the live RAG pipeline
    POST /api/evaluate/suite    — Run the full golden dataset evaluation suite

This is what makes you an AI Engineer, not just a pipeline builder.
Instead of only checking "did the API return 200?", this endpoint checks
"is the AI giving GOOD answers?"

DE parallel: This is like running Great Expectations on your data pipeline —
automated quality checks that produce scores, not just pass/fail.

See docs/architecture-and-design/api-routes/evaluate-endpoint-explained.md
for a full walkthrough.
"""

import time
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from src.api.models import (
    CloudProvider,
    ErrorResponse,
    EvaluateSingleRequest,
    EvaluateSingleResponse,
    EvaluateSuiteRequest,
    EvaluateSuiteResponse,
    EvaluationCaseResult,
    EvaluationScoreDetail,
)
from src.config import get_settings
from src.evaluation.evaluator import RAGEvaluator
from src.evaluation.golden_dataset import GOLDEN_DATASET

router = APIRouter()


@router.post(
    "/evaluate",
    response_model=EvaluateSingleResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Evaluate a Single Question",
    description=(
        "Run a question through the full RAG pipeline (retrieve → generate → evaluate). "
        "Returns the answer, sources, AND quality scores. "
        "Use this to test individual questions and tune your RAG settings."
    ),
)
async def evaluate_single(request: Request, body: EvaluateSingleRequest) -> EvaluateSingleResponse:
    """
    Single Question Evaluation — the core AI engineering workflow.

    Flow:
        1. Run the question through rag_chain.query() (same as /api/chat)
        2. Pass the answer + retrieved chunks to RAGEvaluator
        3. Return the answer AND quality scores

    This lets you:
        - Test a specific question and see exactly how the AI performed
        - Compare scores before and after changing settings (chunk_size, top_k, model)
        - Debug low-quality answers by inspecting individual scores

    DE parallel: Like running `dbt test` on a single model — targeted validation.
    """
    start_time = time.time()
    settings = get_settings()
    request_id = uuid4()

    logger.info(f"[{request_id}] Evaluate request: {body.question[:100]}...")

    # Check RAG chain availability
    rag_chain = getattr(request.app.state, "rag_chain", None)
    if rag_chain is None:
        raise HTTPException(
            status_code=500,
            detail="RAG chain not initialized. Check your cloud credentials and restart the app.",
        )

    try:
        top_k = body.top_k or settings.rag_top_k

        # Step 1: Run the RAG pipeline (same as /api/chat)
        result = await rag_chain.query(
            question=body.question,
            session_id=str(request_id),
            top_k=top_k,
        )

        answer = result.get("answer", "")
        sources = result.get("sources", [])

        # Build chunks for evaluator: list of (text, score) tuples
        retrieved_chunks = [(chunk.get("text", ""), chunk.get("score", 0.0)) for chunk in sources]

        # Step 2: Evaluate the result
        evaluator = RAGEvaluator()
        eval_result = evaluator.evaluate(
            question=body.question,
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            expected_answer=body.expected_answer,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # Build response
        response = EvaluateSingleResponse(
            question=body.question,
            answer=answer,
            scores=EvaluationScoreDetail(
                retrieval=round(eval_result.retrieval.avg_relevance_score, 3),
                retrieval_quality=eval_result.retrieval.quality,
                faithfulness=round(eval_result.faithfulness.score, 3),
                has_hallucination=eval_result.faithfulness.has_hallucination,
                answer_relevance=round(eval_result.answer_relevance.score, 3),
                answer_relevance_quality=eval_result.answer_relevance.quality,
                overall=eval_result.overall_score,
                passed=eval_result.passed,
            ),
            sources_used=len(sources),
            evaluation_notes=eval_result.evaluation_notes,
            cloud_provider=CloudProvider(settings.cloud_provider.value),
            latency_ms=latency_ms,
            request_id=request_id,
        )

        logger.info(
            f"[{request_id}] Evaluation complete: overall={eval_result.overall_score} "
            f"passed={eval_result.passed} latency={latency_ms}ms"
        )
        return response

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[{request_id}] Evaluation error after {latency_ms}ms: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/evaluate/suite",
    response_model=EvaluateSuiteResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Run Golden Dataset Evaluation Suite",
    description=(
        "Run the entire golden dataset through the RAG pipeline and return a scorecard. "
        "Each test case is evaluated individually and the results are aggregated. "
        "Use this after changing any setting (model, chunk_size, top_k, prompt) "
        "to check for regressions."
    ),
)
async def evaluate_suite(request: Request, body: EvaluateSuiteRequest | None = None) -> EvaluateSuiteResponse:
    """
    Golden Dataset Evaluation Suite — regression testing for AI.

    Flow:
        1. For each case in the golden dataset:
           a. Run rag_chain.query() with the test question
           b. Evaluate the answer with RAGEvaluator
           c. Record pass/fail and scores
        2. Aggregate results into a scorecard

    When to run this:
        - After changing chunk_size or overlap
        - After switching the LLM model
        - After modifying prompt templates
        - After changing top_k
        - Before deploying to production
        - In CI/CD as a quality gate

    DE parallel: Like running your full dbt test suite — checks ALL models,
    reports which passed, which failed, and overall health.
    """
    start_time = time.time()
    settings = get_settings()
    request_id = uuid4()

    logger.info(f"[{request_id}] Starting golden dataset evaluation suite...")

    # Check RAG chain availability
    rag_chain = getattr(request.app.state, "rag_chain", None)
    if rag_chain is None:
        raise HTTPException(
            status_code=500,
            detail="RAG chain not initialized. Check your cloud credentials and restart the app.",
        )

    # Determine which categories to run (default: all)
    categories_filter = None
    if body and body.categories:
        categories_filter = set(body.categories)

    evaluator = RAGEvaluator()
    case_results: list[EvaluationCaseResult] = []
    passed_count = 0
    failed_count = 0

    try:
        for case in GOLDEN_DATASET:
            # Filter by category if specified
            if categories_filter and case["category"] not in categories_filter:
                continue

            case_start = time.time()
            case_id = case["id"]

            logger.info(f"[{request_id}] Evaluating case: {case_id}")

            try:
                # Run RAG pipeline
                top_k = (body.top_k if body and body.top_k else None) or settings.rag_top_k
                result = await rag_chain.query(
                    question=case["question"],
                    session_id=f"eval-{request_id}-{case_id}",
                    top_k=top_k,
                )

                answer = result.get("answer", "")
                sources = result.get("sources", [])

                retrieved_chunks = [(chunk.get("text", ""), chunk.get("score", 0.0)) for chunk in sources]

                # Evaluate
                eval_result = evaluator.evaluate(
                    question=case["question"],
                    answer=answer,
                    retrieved_chunks=retrieved_chunks,
                )

                case_latency = int((time.time() - case_start) * 1000)
                case_passed = eval_result.passed

                if case_passed:
                    passed_count += 1
                else:
                    failed_count += 1

                case_results.append(
                    EvaluationCaseResult(
                        case_id=case_id,
                        category=case["category"],
                        question=case["question"],
                        answer_preview=answer[:200] + "..." if len(answer) > 200 else answer,
                        scores=EvaluationScoreDetail(
                            retrieval=round(eval_result.retrieval.avg_relevance_score, 3),
                            retrieval_quality=eval_result.retrieval.quality,
                            faithfulness=round(eval_result.faithfulness.score, 3),
                            has_hallucination=eval_result.faithfulness.has_hallucination,
                            answer_relevance=round(eval_result.answer_relevance.score, 3),
                            answer_relevance_quality=eval_result.answer_relevance.quality,
                            overall=eval_result.overall_score,
                            passed=eval_result.passed,
                        ),
                        passed=case_passed,
                        notes=eval_result.evaluation_notes,
                        latency_ms=case_latency,
                    )
                )

            except Exception as case_error:
                failed_count += 1
                case_results.append(
                    EvaluationCaseResult(
                        case_id=case_id,
                        category=case["category"],
                        question=case["question"],
                        answer_preview=f"ERROR: {case_error}",
                        scores=EvaluationScoreDetail(
                            retrieval=0.0,
                            retrieval_quality="error",
                            faithfulness=0.0,
                            has_hallucination=False,
                            answer_relevance=0.0,
                            answer_relevance_quality="error",
                            overall=0.0,
                            passed=False,
                        ),
                        passed=False,
                        notes=[f"Error during evaluation: {case_error}"],
                        latency_ms=int((time.time() - case_start) * 1000),
                    )
                )

        total_latency_ms = int((time.time() - start_time) * 1000)
        total_cases = passed_count + failed_count

        # Calculate average overall score
        avg_score = 0.0
        if case_results:
            avg_score = round(sum(r.scores.overall for r in case_results) / len(case_results), 3)

        response = EvaluateSuiteResponse(
            total_cases=total_cases,
            passed=passed_count,
            failed=failed_count,
            pass_rate=round(passed_count / total_cases * 100, 1) if total_cases > 0 else 0.0,
            average_overall_score=avg_score,
            cases=case_results,
            cloud_provider=CloudProvider(settings.cloud_provider.value),
            latency_ms=total_latency_ms,
            request_id=request_id,
        )

        logger.info(
            f"[{request_id}] Suite complete: {passed_count}/{total_cases} passed "
            f"(avg={avg_score}) latency={total_latency_ms}ms"
        )
        return response

    except Exception as e:
        logger.error(f"[{request_id}] Suite error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
