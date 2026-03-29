"""
RAG Evaluation Framework

This is what makes you an AI Engineer — not just building the pipeline,
but MEASURING whether the AI is performing well.

A Data Engineer asks: "Did the pipeline run successfully?"
An AI Engineer asks:  "Is the AI giving GOOD answers?"

This module evaluates 4 dimensions of RAG quality:
    1. Retrieval Quality  → Did we find the right chunks?
    2. Faithfulness        → Does the answer only use facts from the context?
    3. Answer Relevance    → Does the answer actually address the question?
    4. Completeness        → Did the answer cover all important points?

How to use:
    evaluator = RAGEvaluator()

    # After a RAG query, evaluate the result
    score = evaluator.evaluate(
        question="What is the refund policy?",
        answer="Refunds are processed within 14 days...",
        retrieved_chunks=["Refunds are processed...", "Returns must be..."],
        expected_answer="Refunds take 14 business days"  # optional ground truth
    )
    print(score)
    # → EvaluationResult(
    #     retrieval_relevance=0.89,
    #     faithfulness=0.95,
    #     answer_relevance=0.91,
    #     overall=0.92
    #   )

Why this matters:
    Without evaluation, you're building blind. You might change the chunk size
    from 1000 to 500 and think "it seems better" — but evaluation gives you
    a NUMBER: retrieval quality went from 0.78 to 0.85. That's engineering,
    not guessing.

See docs/ai-engineer-guide.md for the full AI engineering mindset guide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from loguru import logger


# ---------------------------------------------------------------------------
# Data classes for evaluation results
# ---------------------------------------------------------------------------

@dataclass
class RetrievalScore:
    """How good was the retrieval step?

    Think of this as a Data Engineer checking: "Did my query return the right rows?"
    Except here it's: "Did the vector search return the right chunks?"
    """

    avg_relevance_score: float       # Average cosine similarity of retrieved chunks
    top_score: float                 # Best chunk's similarity score
    min_score: float                 # Worst chunk's similarity score
    chunks_above_threshold: int      # How many chunks scored above the threshold
    total_chunks: int                # Total chunks retrieved
    threshold: float = 0.7          # Minimum acceptable relevance

    @property
    def quality(self) -> str:
        """Human-readable quality label."""
        if self.avg_relevance_score >= 0.85:
            return "excellent"
        elif self.avg_relevance_score >= 0.7:
            return "good"
        elif self.avg_relevance_score >= 0.5:
            return "fair"
        else:
            return "poor"

    @property
    def pass_rate(self) -> float:
        """Percentage of chunks above the relevance threshold."""
        if self.total_chunks == 0:
            return 0.0
        return round(self.chunks_above_threshold / self.total_chunks * 100, 1)


@dataclass
class FaithfulnessScore:
    """Does the answer only use facts from the provided context?

    DE parallel: Referential integrity check — is every value in the output
    traceable back to the source?

    A score of 1.0 means every claim in the answer can be found in the chunks.
    A score of 0.5 means half the answer is made up (hallucination!).
    """

    score: float                    # 0.0 (all hallucinated) to 1.0 (fully faithful)
    claims_in_context: int          # Number of answer sentences found in context
    claims_not_in_context: int      # Number of answer sentences NOT in context
    flagged_sentences: list[str] = field(default_factory=list)  # Suspicious sentences

    @property
    def has_hallucination(self) -> bool:
        """Does the answer contain information not in the context?"""
        return self.claims_not_in_context > 0


@dataclass
class AnswerRelevanceScore:
    """Does the answer actually address the question?

    DE parallel: "Does the output table have the columns the business asked for?"
    """

    score: float                    # 0.0 (completely off-topic) to 1.0 (perfectly relevant)
    question_keywords_in_answer: int
    question_keywords_total: int

    @property
    def quality(self) -> str:
        if self.score >= 0.8:
            return "highly relevant"
        elif self.score >= 0.5:
            return "partially relevant"
        else:
            return "off-topic"


@dataclass
class EvaluationResult:
    """Complete evaluation of a single RAG query.

    This is the AI Engineer's equivalent of a Data Quality Report.
    """

    question: str
    answer: str
    retrieval: RetrievalScore
    faithfulness: FaithfulnessScore
    answer_relevance: AnswerRelevanceScore
    overall_score: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evaluation_notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Did this query meet the minimum quality bar?"""
        return self.overall_score >= 0.7

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization / logging."""
        return {
            "question": self.question,
            "answer_preview": self.answer[:200] + "..." if len(self.answer) > 200 else self.answer,
            "scores": {
                "retrieval": round(self.retrieval.avg_relevance_score, 3),
                "retrieval_quality": self.retrieval.quality,
                "faithfulness": round(self.faithfulness.score, 3),
                "has_hallucination": self.faithfulness.has_hallucination,
                "answer_relevance": round(self.answer_relevance.score, 3),
                "overall": round(self.overall_score, 3),
            },
            "passed": self.passed,
            "notes": self.evaluation_notes,
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# The Evaluator
# ---------------------------------------------------------------------------

class RAGEvaluator:
    """
    Evaluate RAG pipeline quality.

    This is a rule-based evaluator (no LLM needed for evaluation itself).
    For production, you'd upgrade to LLM-as-judge (use a second LLM to
    evaluate the first one's output).

    AI Engineering principle:
        Always measure before and after every change. Changed chunk_size?
        Run the evaluation suite. Changed the prompt? Run the evaluation suite.
        Changed the model? Run the evaluation suite.

    Usage:
        evaluator = RAGEvaluator()

        result = evaluator.evaluate(
            question="What is the refund policy?",
            answer="Refunds are processed within 14 days...",
            retrieved_chunks=[("Refunds are processed...", 0.92), ...],
        )

        if not result.passed:
            logger.warning(f"Low quality answer: {result.overall_score}")
    """

    def __init__(
        self,
        relevance_threshold: float = 0.7,
        faithfulness_threshold: float = 0.8,
        answer_relevance_threshold: float = 0.6,
    ):
        self.relevance_threshold = relevance_threshold
        self.faithfulness_threshold = faithfulness_threshold
        self.answer_relevance_threshold = answer_relevance_threshold

    def evaluate(
        self,
        question: str,
        answer: str,
        retrieved_chunks: list[tuple[str, float]],  # [(text, score), ...]
        expected_answer: str | None = None,
    ) -> EvaluationResult:
        """
        Run all evaluations on a single RAG query result.

        Args:
            question: The user's original question.
            answer: The LLM's generated answer.
            retrieved_chunks: List of (chunk_text, relevance_score) tuples.
            expected_answer: Optional ground truth for comparison.

        Returns:
            EvaluationResult with scores and diagnostics.
        """
        notes = []

        # 1. Evaluate retrieval quality
        retrieval = self._evaluate_retrieval(retrieved_chunks)
        if retrieval.quality == "poor":
            notes.append("⚠️ RETRIEVAL: Chunks have low relevance — consider re-chunking or improving embeddings")

        # 2. Evaluate faithfulness
        chunk_texts = [text for text, _ in retrieved_chunks]
        faithfulness = self._evaluate_faithfulness(answer, chunk_texts)
        if faithfulness.has_hallucination:
            notes.append(f"⚠️ HALLUCINATION: {faithfulness.claims_not_in_context} sentences may not be from context")

        # 3. Evaluate answer relevance
        answer_relevance = self._evaluate_answer_relevance(question, answer)
        if answer_relevance.quality == "off-topic":
            notes.append("⚠️ RELEVANCE: Answer doesn't seem to address the question")

        # 4. Check for "I don't know" responses
        if self._is_refusal(answer):
            notes.append("ℹ️ Model correctly refused to answer (no relevant context)")

        # 5. Calculate overall score (weighted average)
        overall = (
            retrieval.avg_relevance_score * 0.3 +
            faithfulness.score * 0.4 +
            answer_relevance.score * 0.3
        )

        result = EvaluationResult(
            question=question,
            answer=answer,
            retrieval=retrieval,
            faithfulness=faithfulness,
            answer_relevance=answer_relevance,
            overall_score=round(overall, 3),
            evaluation_notes=notes,
        )

        logger.info(
            "Evaluation: overall={} retrieval={} faithfulness={} relevance={} passed={}",
            result.overall_score,
            retrieval.quality,
            faithfulness.score,
            answer_relevance.quality,
            result.passed,
        )

        return result

    # ------------------------------------------------------------------ #
    # Sub-evaluators
    # ------------------------------------------------------------------ #

    def _evaluate_retrieval(self, chunks: list[tuple[str, float]]) -> RetrievalScore:
        """
        Evaluate retrieval quality based on similarity scores.

        DE parallel: This is like checking "did my JOIN return the right rows?"
        If all chunks have high similarity scores, retrieval was good.
        If scores are low, the vector search didn't find relevant content.
        """
        if not chunks:
            return RetrievalScore(
                avg_relevance_score=0.0,
                top_score=0.0,
                min_score=0.0,
                chunks_above_threshold=0,
                total_chunks=0,
            )

        scores = [score for _, score in chunks]
        above_threshold = sum(1 for s in scores if s >= self.relevance_threshold)

        return RetrievalScore(
            avg_relevance_score=round(sum(scores) / len(scores), 4),
            top_score=max(scores),
            min_score=min(scores),
            chunks_above_threshold=above_threshold,
            total_chunks=len(chunks),
        )

    def _evaluate_faithfulness(self, answer: str, context_chunks: list[str]) -> FaithfulnessScore:
        """
        Check if the answer is grounded in the provided context.

        Method: Split the answer into sentences, check if each sentence's
        key words appear in the context. This is a simple heuristic —
        production systems use LLM-as-judge for this.

        DE parallel: Referential integrity — every foreign key must exist
        in the parent table. Here, every claim must exist in the context.
        """
        # Combine all context into one searchable text
        context_text = " ".join(context_chunks).lower()

        # Split answer into sentences
        sentences = self._split_sentences(answer)
        if not sentences:
            return FaithfulnessScore(score=1.0, claims_in_context=0, claims_not_in_context=0)

        in_context = 0
        not_in_context = 0
        flagged = []

        for sentence in sentences:
            # Skip meta-sentences (citations, disclaimers)
            if self._is_meta_sentence(sentence):
                in_context += 1
                continue

            # Extract key words from the sentence
            keywords = self._extract_keywords(sentence)
            if not keywords:
                in_context += 1
                continue

            # Check how many keywords appear in the context
            found = sum(1 for kw in keywords if kw.lower() in context_text)
            keyword_ratio = found / len(keywords)

            if keyword_ratio >= 0.5:
                in_context += 1
            else:
                not_in_context += 1
                flagged.append(sentence.strip())

        total = in_context + not_in_context
        score = in_context / total if total > 0 else 1.0

        return FaithfulnessScore(
            score=round(score, 4),
            claims_in_context=in_context,
            claims_not_in_context=not_in_context,
            flagged_sentences=flagged[:5],  # Keep top 5 for debugging
        )

    def _evaluate_answer_relevance(self, question: str, answer: str) -> AnswerRelevanceScore:
        """
        Check if the answer addresses the question.

        Method: Extract keywords from the question, check how many appear
        in the answer.

        DE parallel: "Does the output match what was requested?"
        """
        question_keywords = self._extract_keywords(question)
        if not question_keywords:
            return AnswerRelevanceScore(score=1.0, question_keywords_in_answer=0, question_keywords_total=0)

        answer_lower = answer.lower()
        found = sum(1 for kw in question_keywords if kw.lower() in answer_lower)
        score = found / len(question_keywords)

        return AnswerRelevanceScore(
            score=round(score, 4),
            question_keywords_in_answer=found,
            question_keywords_total=len(question_keywords),
        )

    # ------------------------------------------------------------------ #
    # Helper methods
    # ------------------------------------------------------------------ #

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s for s in sentences if len(s.strip()) > 10]

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """Extract meaningful keywords (skip stop words)."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "and", "but", "or", "not", "no", "nor",
            "so", "yet", "both", "either", "neither", "each", "every",
            "all", "any", "few", "more", "most", "other", "some", "such",
            "than", "too", "very", "just", "about", "also", "this", "that",
            "these", "those", "it", "its", "i", "me", "my", "we", "our",
            "you", "your", "he", "him", "his", "she", "her", "they", "them",
            "their", "what", "which", "who", "whom", "how", "when", "where",
            "why", "if", "then", "else", "while", "because", "although",
            "based", "according", "document", "chunk", "context",
        }
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        return [w for w in words if w not in stop_words]

    @staticmethod
    def _is_meta_sentence(sentence: str) -> bool:
        """Check if a sentence is a meta-reference (not a factual claim)."""
        meta_patterns = [
            r"according to",
            r"based on the",
            r"\[document chunk",
            r"\[chunk \d",
            r"the document states",
            r"as mentioned in",
            r"I don't have enough information",
            r"the context does not",
        ]
        sentence_lower = sentence.lower()
        return any(re.search(p, sentence_lower) for p in meta_patterns)

    @staticmethod
    def _is_refusal(answer: str) -> bool:
        """Check if the model refused to answer (which is correct when no context)."""
        refusal_patterns = [
            "I don't have enough information",
            "I cannot find",
            "the documents don't contain",
            "no relevant information",
            "I'm unable to answer",
            "not enough context",
        ]
        answer_lower = answer.lower()
        return any(pattern.lower() in answer_lower for pattern in refusal_patterns)
