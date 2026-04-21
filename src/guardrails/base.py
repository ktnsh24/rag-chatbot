"""
Abstract Guardrails Interface

Defines the contract for guardrails:
    - check_input(): Validate user input before it reaches the RAG chain
    - check_output(): Validate LLM output before it reaches the user
    - detect_pii(): Identify personally identifiable information

Implementations:
    - aws_guardrails.py    → Bedrock Guardrails + Amazon Comprehend
    - azure_guardrails.py  → Azure AI Content Safety + Azure AI Language
    - local_guardrails.py  → Regex patterns + rule-based (no cloud)

Why abstract classes?
    - Same pattern as BaseLLM and BaseVectorStore — swap providers via env var
    - The middleware doesn't care which cloud is running the safety checks
    - Tests use a mock guardrail that always passes/fails predictably
    - DE parallel: like data validation — same contract, different implementations
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class GuardrailAction(str, Enum):
    """What to do when a guardrail triggers."""

    ALLOW = "allow"  # Content is safe
    BLOCK = "block"  # Content should be blocked entirely
    REDACT = "redact"  # Content allowed, but PII/sensitive data redacted


class GuardrailCategory(str, Enum):
    """Categories of guardrail violations."""

    PROMPT_INJECTION = "prompt_injection"
    TOXIC_CONTENT = "toxic_content"
    PII_DETECTED = "pii_detected"
    OFF_TOPIC = "off_topic"
    HALLUCINATION_SIGNAL = "hallucination_signal"
    SAFE = "safe"


@dataclass
class PIIEntity:
    """A detected PII entity in the text."""

    entity_type: str  # "EMAIL", "PHONE", "SSN", "NAME", "CREDIT_CARD", etc.
    text: str  # The actual PII text found
    start: int  # Character offset start
    end: int  # Character offset end
    confidence: float  # 0.0 to 1.0


@dataclass
class GuardrailResult:
    """
    Result from a guardrail check.

    Fields:
        action: What to do (allow, block, redact).
        category: What type of violation was detected.
        original_text: The input text that was checked.
        filtered_text: The text after any redaction (same as original if no PII).
        pii_entities: List of PII entities found (empty if none).
        confidence: Confidence in the detection (0.0–1.0).
        details: Human-readable explanation of the decision.
        latency_ms: How long the check took.
    """

    action: GuardrailAction
    category: GuardrailCategory
    original_text: str
    filtered_text: str = ""
    pii_entities: list[PIIEntity] = field(default_factory=list)
    confidence: float = 0.0
    details: str = ""
    latency_ms: int = 0

    def __post_init__(self) -> None:
        if not self.filtered_text:
            self.filtered_text = self.original_text


class BaseGuardrails(ABC):
    """
    Abstract base class for guardrail providers.

    Every guardrail provider must implement:
        - check_input(): Validate user input (before RAG chain)
        - check_output(): Validate LLM output (before response)
        - detect_pii(): Find PII in text
    """

    @abstractmethod
    async def check_input(self, text: str) -> GuardrailResult:
        """
        Validate user input before it reaches the RAG chain.

        Checks for:
            - Prompt injection attempts ("ignore previous instructions...")
            - Toxic/harmful content
            - PII in user queries (optionally redact before embedding)

        Args:
            text: The user's input question.

        Returns:
            GuardrailResult with action (allow/block/redact).
        """
        ...

    @abstractmethod
    async def check_output(self, text: str, context_chunks: list[str] | None = None) -> GuardrailResult:
        """
        Validate LLM output before returning to the user.

        Checks for:
            - PII in the generated response (redact if found)
            - Hallucination signals (answer contradicts context)
            - Unsafe/inappropriate content in the response

        Args:
            text: The LLM's generated response.
            context_chunks: The document chunks used as context (for hallucination check).

        Returns:
            GuardrailResult with action and filtered_text (PII redacted).
        """
        ...

    @abstractmethod
    async def detect_pii(self, text: str) -> list[PIIEntity]:
        """
        Detect personally identifiable information in text.

        Detects: names, emails, phone numbers, SSNs, credit card numbers,
        addresses, dates of birth, passport numbers, etc.

        Args:
            text: Text to scan for PII.

        Returns:
            List of PIIEntity objects with type, location, and confidence.
        """
        ...
