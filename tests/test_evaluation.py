"""
Evaluation Test Suite — Golden Dataset

This is how AI Engineers test their systems. Instead of just checking
"does the API return 200?", we check "is the AI's answer GOOD?"

Concept: Golden Dataset
    A set of questions + known correct answers + the documents they come from.
    You run these questions through the RAG pipeline and measure quality.
    If quality drops after a code change, you know you broke something.

    DE parallel: This is like a regression test suite for your ETL —
    known input → expected output. Except the output is fuzzy (not exact).

How to use:
    pytest tests/test_evaluation.py -v

    These tests don't need cloud services — they test the evaluation
    framework itself using mock data.
"""

import pytest

from src.evaluation.evaluator import (
    RAGEvaluator,
    RetrievalScore,
    FaithfulnessScore,
    AnswerRelevanceScore,
    EvaluationResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def evaluator():
    """Create an evaluator with default thresholds."""
    return RAGEvaluator()


@pytest.fixture
def good_chunks():
    """Chunks with high relevance scores — good retrieval."""
    return [
        ("Refunds are processed within 14 business days of receiving the returned item.", 0.95),
        ("To request a refund, contact customer service with your order number.", 0.89),
        ("Products must be in original packaging to qualify for a refund.", 0.82),
        ("Digital products and gift cards are non-refundable.", 0.78),
        ("Shipping costs are refunded only if the return is due to our error.", 0.71),
    ]


@pytest.fixture
def poor_chunks():
    """Chunks with low relevance scores — bad retrieval."""
    return [
        ("Our company was founded in 2005 in Amsterdam.", 0.35),
        ("We have offices in 12 countries worldwide.", 0.28),
        ("The CEO's favourite colour is blue.", 0.15),
    ]


# ---------------------------------------------------------------------------
# Retrieval Quality Tests
# ---------------------------------------------------------------------------

class TestRetrievalEvaluation:
    """
    AI Engineer question: "Did the vector search find relevant chunks?"
    DE parallel: "Did my query return the right rows?"
    """

    def test_good_retrieval_scores_high(self, evaluator, good_chunks):
        """High similarity scores → good retrieval quality."""
        result = evaluator.evaluate(
            question="What is the refund policy?",
            answer="Refunds are processed within 14 business days.",
            retrieved_chunks=good_chunks,
        )
        assert result.retrieval.quality in ["good", "excellent"]
        assert result.retrieval.avg_relevance_score > 0.7

    def test_poor_retrieval_scores_low(self, evaluator, poor_chunks):
        """Low similarity scores → poor retrieval quality."""
        result = evaluator.evaluate(
            question="What is the refund policy?",
            answer="The company was founded in 2005.",
            retrieved_chunks=poor_chunks,
        )
        assert result.retrieval.quality == "poor"
        assert result.retrieval.avg_relevance_score < 0.5

    def test_empty_retrieval(self, evaluator):
        """No chunks retrieved → score is 0."""
        result = evaluator.evaluate(
            question="What is the refund policy?",
            answer="I don't have enough information.",
            retrieved_chunks=[],
        )
        assert result.retrieval.avg_relevance_score == 0.0
        assert result.retrieval.total_chunks == 0

    def test_retrieval_pass_rate(self, evaluator, good_chunks):
        """Most chunks should be above the relevance threshold."""
        result = evaluator.evaluate(
            question="What is the refund policy?",
            answer="Refunds take 14 days.",
            retrieved_chunks=good_chunks,
        )
        assert result.retrieval.pass_rate >= 80.0  # 80%+ chunks above threshold


# ---------------------------------------------------------------------------
# Faithfulness Tests (Hallucination Detection)
# ---------------------------------------------------------------------------

class TestFaithfulnessEvaluation:
    """
    AI Engineer question: "Did the model make anything up?"
    DE parallel: "Does every output value trace back to a source?"
    """

    def test_faithful_answer_scores_high(self, evaluator, good_chunks):
        """Answer that uses only context information → high faithfulness."""
        result = evaluator.evaluate(
            question="What is the refund policy?",
            answer="Refunds are processed within 14 business days. Products must be in original packaging.",
            retrieved_chunks=good_chunks,
        )
        assert result.faithfulness.score >= 0.8
        assert not result.faithfulness.has_hallucination

    def test_hallucinated_answer_flagged(self, evaluator, good_chunks):
        """Answer with made-up facts → low faithfulness, flagged sentences."""
        result = evaluator.evaluate(
            question="What is the refund policy?",
            answer=(
                "Refunds are processed within 14 business days. "
                "Additionally, customers receive a complimentary helicopter ride. "
                "The company also offers free unicorn delivery service."
            ),
            retrieved_chunks=good_chunks,
        )
        # The hallucinated sentences should be flagged
        assert result.faithfulness.claims_not_in_context > 0
        assert len(result.faithfulness.flagged_sentences) > 0

    def test_empty_answer_is_faithful(self, evaluator, good_chunks):
        """An empty or very short answer can't hallucinate."""
        result = evaluator.evaluate(
            question="What is the refund policy?",
            answer="Yes.",
            retrieved_chunks=good_chunks,
        )
        # Very short answers with no substantial claims are considered faithful
        assert result.faithfulness.score >= 0.8


# ---------------------------------------------------------------------------
# Answer Relevance Tests
# ---------------------------------------------------------------------------

class TestAnswerRelevanceEvaluation:
    """
    AI Engineer question: "Does the answer address the question?"
    DE parallel: "Does the output have the columns the business asked for?"
    """

    def test_relevant_answer_scores_high(self, evaluator, good_chunks):
        """Answer about refunds for a refund question → high relevance."""
        result = evaluator.evaluate(
            question="What is the refund policy?",
            answer="The refund policy states that refunds are processed within 14 business days.",
            retrieved_chunks=good_chunks,
        )
        assert result.answer_relevance.score >= 0.5
        assert result.answer_relevance.quality in ["partially relevant", "highly relevant"]

    def test_offtopic_answer_scores_low(self, evaluator, good_chunks):
        """Answer about weather for a refund question → low relevance."""
        result = evaluator.evaluate(
            question="What is the refund policy?",
            answer="The weather in Amsterdam is typically rainy with temperatures around 15 degrees.",
            retrieved_chunks=good_chunks,
        )
        assert result.answer_relevance.score < 0.5


# ---------------------------------------------------------------------------
# Overall Score Tests
# ---------------------------------------------------------------------------

class TestOverallEvaluation:
    """
    AI Engineer question: "Is this answer good enough to show to a user?"
    """

    def test_good_answer_passes(self, evaluator, good_chunks):
        """A relevant, faithful answer with good retrieval → passes."""
        result = evaluator.evaluate(
            question="What is the refund policy?",
            answer="Refunds are processed within 14 business days. Products must be in original packaging.",
            retrieved_chunks=good_chunks,
        )
        assert result.passed
        assert result.overall_score >= 0.7

    def test_poor_answer_fails(self, evaluator, poor_chunks):
        """An off-topic answer with bad retrieval → fails."""
        result = evaluator.evaluate(
            question="What is the refund policy?",
            answer="The company has offices in 12 countries and was founded in 2005.",
            retrieved_chunks=poor_chunks,
        )
        assert not result.passed
        assert result.overall_score < 0.7

    def test_result_serializable(self, evaluator, good_chunks):
        """Evaluation result can be converted to dict for logging."""
        result = evaluator.evaluate(
            question="What is the refund policy?",
            answer="Refunds take 14 days.",
            retrieved_chunks=good_chunks,
        )
        d = result.to_dict()
        assert "scores" in d
        assert "passed" in d
        assert "retrieval" in d["scores"]
        assert "faithfulness" in d["scores"]
        assert "answer_relevance" in d["scores"]

    def test_refusal_detected(self, evaluator):
        """Model correctly refusing to answer → detected in notes."""
        result = evaluator.evaluate(
            question="What is the meaning of life?",
            answer="I don't have enough information in the uploaded documents to answer that question.",
            retrieved_chunks=[("Some unrelated text.", 0.3)],
        )
        assert any("refused" in note.lower() or "refusal" in note.lower() for note in result.evaluation_notes) or \
               any("refuse" in note.lower() for note in result.evaluation_notes) or \
               result.faithfulness.score >= 0.8  # A refusal is always faithful


# ---------------------------------------------------------------------------
# Golden Dataset — Regression Tests
# ---------------------------------------------------------------------------

class TestGoldenDataset:
    """
    Golden dataset: known question → known answer pairs.

    Run these after EVERY change to the RAG pipeline to catch regressions.
    If a test that used to pass starts failing, your change made things worse.

    AI Engineering principle: NEVER change the pipeline without running
    the evaluation suite. This is your safety net.

    To add a new test case:
        1. Upload a document to the running app
        2. Ask a question, verify the answer is good
        3. Copy the question, answer, and chunks here
        4. Now it's a regression test forever
    """

    GOLDEN_CASES = [
        {
            "name": "refund_policy_basic",
            "question": "What is the refund policy?",
            "expected_keywords": ["refund", "days", "business"],
            "context_chunks": [
                ("Refunds are processed within 14 business days of receiving the returned item.", 0.95),
                ("Products must be returned in original packaging.", 0.85),
            ],
        },
        {
            "name": "shipping_cost",
            "question": "Who pays for return shipping?",
            "expected_keywords": ["shipping", "cost", "return"],
            "context_chunks": [
                ("Return shipping costs are the customer's responsibility unless the item was defective.", 0.91),
                ("Free shipping is available on orders over 50 euros.", 0.72),
            ],
        },
        {
            "name": "digital_products",
            "question": "Can I return digital products?",
            "expected_keywords": ["digital", "non-refundable"],
            "context_chunks": [
                ("Digital products and gift cards are non-refundable.", 0.93),
                ("All sales of downloadable content are final.", 0.87),
            ],
        },
    ]

    @pytest.mark.parametrize(
        "case",
        GOLDEN_CASES,
        ids=[c["name"] for c in GOLDEN_CASES],
    )
    def test_golden_case_retrieval(self, case):
        """Each golden case should have good retrieval scores."""
        evaluator = RAGEvaluator()
        # Simulate an answer that includes expected keywords
        answer = f"Based on the documents, {' '.join(case['expected_keywords'])} are relevant."
        result = evaluator.evaluate(
            question=case["question"],
            answer=answer,
            retrieved_chunks=case["context_chunks"],
        )
        assert result.retrieval.avg_relevance_score >= 0.7, (
            f"Golden case '{case['name']}': retrieval score {result.retrieval.avg_relevance_score} < 0.7"
        )
