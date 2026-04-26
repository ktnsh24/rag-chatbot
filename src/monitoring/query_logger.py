"""
Query Logger — Structured per-query logging for production debugging.

Story I30: Every RAG query is logged as a structured JSON record containing:
    - Question, answer, session ID, request ID
    - Retrieved chunks with text and relevance scores
    - Evaluation scores (retrieval, faithfulness, relevance, overall)
    - Token usage and latency
    - Pass/fail status

This enables the production debugging workflow:
    1. Dashboard shows pass rate dropping
    2. AI engineer filters for failed queries
    3. Engineer reads the chunks + scores → diagnoses root cause
    4. Fixes the issue → re-runs golden dataset to verify

DE parallel: This is the "Airflow task logs" for your RAG pipeline. Without
structured query logs, you can't debug anything after the fact.

Usage:
    logger = QueryLogger(log_dir="logs/queries")
    await logger.log_query(query_record)
    failures = await logger.get_failures(limit=20)
"""

from datetime import UTC, datetime
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field

# =============================================================================
# Query Log Models
# =============================================================================


class LoggedChunk(BaseModel):
    """A retrieved chunk as stored in the query log."""

    document_name: str = Field(..., description="Source document filename")
    chunk_text: str = Field(..., description="The chunk text (first 500 chars)")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score")


class EvaluationScores(BaseModel):
    """Evaluation scores for a logged query."""

    retrieval: float = Field(default=0.0, ge=0.0, le=1.0, description="Retrieval quality score")
    faithfulness: float = Field(default=0.0, ge=0.0, le=1.0, description="Faithfulness score")
    answer_relevance: float = Field(default=0.0, ge=0.0, le=1.0, description="Answer relevance score")
    overall: float = Field(default=0.0, ge=0.0, le=1.0, description="Weighted overall score")
    passed: bool = Field(default=False, description="True if overall >= 0.70")


class QueryLogRecord(BaseModel):
    """
    A single structured query log record.

    This is the core data structure for production debugging — every field
    is something an AI engineer needs when triaging a failed query.
    """

    # Identity
    request_id: str = Field(..., description="Unique request ID")
    session_id: str = Field(..., description="Conversation session ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="UTC timestamp")

    # Input
    question: str = Field(..., description="The user's question")
    cloud_provider: str = Field(..., description="Which backend processed this (aws/azure/local)")

    # Retrieval
    chunks: list[LoggedChunk] = Field(default_factory=list, description="Retrieved chunks with scores")
    top_k: int = Field(default=5, description="Number of chunks requested")

    # Output
    answer: str = Field(..., description="The LLM-generated answer")

    # Evaluation scores (computed inline using the heuristic evaluator)
    scores: EvaluationScores = Field(default_factory=EvaluationScores, description="Evaluation scores")

    # Performance
    latency_ms: int = Field(default=0, description="Total request latency in milliseconds")
    input_tokens: int = Field(default=0, description="Input token count")
    output_tokens: int = Field(default=0, description="Output token count")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated cost for this query")

    # Diagnosis
    failure_category: str = Field(
        default="none",
        description=(
            "Failure triage category: "
            "'none' (passed), "
            "'bad_retrieval' (low retrieval, high faithfulness), "
            "'hallucination' (high retrieval, low faithfulness), "
            "'both_bad' (low retrieval + low faithfulness), "
            "'off_topic' (good retrieval + faithfulness, low relevance)"
        ),
    )


# =============================================================================
# Query Logger
# =============================================================================


class QueryLogger:
    """
    Persistent structured query logger.

    Writes one JSON record per line (JSONL format) to daily log files.
    Supports reading back failures for the /api/queries/failures endpoint.

    File layout:
        logs/queries/2026-04-17.jsonl
        logs/queries/2026-04-18.jsonl
        ...
    """

    def __init__(self, log_dir: str = "logs/queries") -> None:
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"QueryLogger initialized — writing to {self._log_dir.resolve()}")

    def _today_file(self) -> Path:
        """Get today's log file path."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return self._log_dir / f"{today}.jsonl"

    @staticmethod
    def classify_failure(scores: EvaluationScores) -> str:
        """
        Classify the failure pattern for triage.

        This implements the triage table from the production debugging workflow:
            - bad_retrieval: librarian grabbed wrong chunks, LLM said "I don't know"
            - hallucination: right chunks, but LLM made stuff up
            - both_bad: wrong chunks AND LLM improvised
            - off_topic: right chunks, faithful, but didn't answer the question
            - none: everything passed
        """
        if scores.passed:
            return "none"

        low_retrieval = scores.retrieval < 0.50
        low_faithfulness = scores.faithfulness < 0.70
        low_relevance = scores.answer_relevance < 0.50

        if low_retrieval and low_faithfulness:
            return "both_bad"
        if low_retrieval:
            return "bad_retrieval"
        if low_faithfulness:
            return "hallucination"
        if low_relevance:
            return "off_topic"
        return "marginal"  # failed overall but no single dimension is terrible

    async def log_query(self, record: QueryLogRecord) -> None:
        """
        Append a query log record to today's JSONL file.

        Each line is a complete JSON object — easy to parse with jq, pandas, or any tool.
        """
        try:
            file_path = self._today_file()
            line = record.model_dump_json() + "\n"
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            # Never let logging failures break the chat endpoint
            logger.error(f"Failed to write query log: {e}")

    async def get_failures(
        self,
        limit: int = 20,
        days: int = 7,
        category: str | None = None,
    ) -> list[QueryLogRecord]:
        """
        Read back failed queries from recent log files.

        Args:
            limit: Max number of failures to return.
            days: How many days back to search.
            category: Optional filter by failure_category.

        Returns:
            List of QueryLogRecord sorted by timestamp (newest first).
        """
        failures: list[QueryLogRecord] = []

        # Iterate over recent days
        for day_offset in range(days):
            date = datetime.now(UTC)
            date = (
                date.replace(day=date.day - day_offset)
                if day_offset == 0
                else datetime(date.year, date.month, date.day - day_offset, tzinfo=UTC)
            )
            file_path = self._log_dir / f"{date.strftime('%Y-%m-%d')}.jsonl"

            if not file_path.exists():
                continue

            try:
                with open(file_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        record = QueryLogRecord.model_validate_json(line)
                        if record.failure_category == "none":
                            continue
                        if category and record.failure_category != category:
                            continue
                        failures.append(record)
            except Exception as e:
                logger.warning(f"Failed to read query log {file_path}: {e}")

        # Sort newest first, apply limit
        failures.sort(key=lambda r: r.timestamp, reverse=True)
        return failures[:limit]

    async def get_stats(self, days: int = 1) -> dict:
        """
        Get aggregate stats from recent query logs.

        Returns pass rate, failure breakdown, and average scores.
        """
        total = 0
        passed = 0
        category_counts: dict[str, int] = {}
        total_retrieval = 0.0
        total_faithfulness = 0.0
        total_relevance = 0.0

        for _day_offset in range(days):
            date = datetime.now(UTC)
            file_path = self._log_dir / f"{date.strftime('%Y-%m-%d')}.jsonl"

            if not file_path.exists():
                continue

            try:
                with open(file_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        record = QueryLogRecord.model_validate_json(line)
                        total += 1
                        if record.scores.passed:
                            passed += 1
                        cat = record.failure_category
                        category_counts[cat] = category_counts.get(cat, 0) + 1
                        total_retrieval += record.scores.retrieval
                        total_faithfulness += record.scores.faithfulness
                        total_relevance += record.scores.answer_relevance
            except Exception as e:
                logger.warning(f"Failed to read query log: {e}")

        return {
            "total_queries": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / max(total, 1) * 100, 1),
            "avg_retrieval": round(total_retrieval / max(total, 1), 3),
            "avg_faithfulness": round(total_faithfulness / max(total, 1), 3),
            "avg_relevance": round(total_relevance / max(total, 1), 3),
            "failure_breakdown": category_counts,
        }
