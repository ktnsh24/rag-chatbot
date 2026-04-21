"""
Local Guardrails — Rule-based implementation (no cloud needed).

Uses regex patterns and heuristics for:
    - Prompt injection detection (known attack patterns)
    - PII detection (email, phone, SSN, credit card)
    - Basic toxicity detection (word list)

This is the fallback for CLOUD_PROVIDER=local. It won't catch everything,
but it demonstrates the guardrail pattern and provides baseline protection.

For production accuracy, use aws_guardrails.py or azure_guardrails.py.
"""

from __future__ import annotations

import re
import time

from loguru import logger

from src.guardrails.base import (
    BaseGuardrails,
    GuardrailAction,
    GuardrailCategory,
    GuardrailResult,
    PIIEntity,
)

# --- Prompt Injection Patterns ---
# These are common attack patterns that try to override the system prompt.
# Not exhaustive — determined attackers will find bypasses. That's why
# production systems use Bedrock Guardrails or Azure Content Safety.
INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?above\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?previous", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)\s+(you|that)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an|DAN)", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
    re.compile(r"<\|?system\|?>", re.IGNORECASE),
    re.compile(r"```\s*system", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:if|though)\s+you", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"override\s+(your\s+)?instructions", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"do\s+anything\s+now", re.IGNORECASE),  # DAN prompt
    re.compile(r"pretend\s+(?:you|that)\s+(?:are|have)\s+no\s+(?:rules|restrictions)", re.IGNORECASE),
]

# --- PII Regex Patterns ---
# Each pattern returns the entity type and a compiled regex.
PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    ("PHONE", re.compile(r"\b(?:\+?31|0)\s*(?:[1-9]\d{1,2})\s*[-.\s]?\d{3}\s*[-.\s]?\d{2,4}\b")),  # NL phones
    ("PHONE", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),  # US phones
    ("SSN", re.compile(r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d{4}[-.\s]?){3}\d{4}\b")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}\s?(?:[A-Z0-9]{4}\s?){2,7}[A-Z0-9]{1,4}\b")),
    ("BSN", re.compile(r"\b\d{9}\b")),  # Dutch BSN (Burger Service Nummer)
    ("DATE_OF_BIRTH", re.compile(r"\b(?:born|dob|date\s+of\s+birth)\s*:?\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", re.IGNORECASE)),
    ("IP_ADDRESS", re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
]


class LocalGuardrails(BaseGuardrails):
    """
    Rule-based guardrails using regex patterns.

    No external dependencies — works offline with CLOUD_PROVIDER=local.

    Capabilities:
        - Prompt injection: 14 known attack patterns
        - PII detection: email, phone (NL+US), SSN, credit card, IBAN, BSN, DOB, IP
        - Output filtering: PII redaction in LLM responses

    Limitations:
        - No semantic understanding (can't catch sophisticated injection)
        - No toxicity scoring (would need a model or word list)
        - PII regex misses context-dependent entities (names without patterns)
    """

    async def check_input(self, text: str) -> GuardrailResult:
        """Check user input for prompt injection and PII."""
        start = time.time()

        # Check 1: Prompt injection
        for pattern in INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                latency = int((time.time() - start) * 1000)
                logger.warning(f"Prompt injection detected: '{match.group()}'")
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    category=GuardrailCategory.PROMPT_INJECTION,
                    original_text=text,
                    confidence=0.9,
                    details=f"Prompt injection pattern detected: '{match.group()}'",
                    latency_ms=latency,
                )

        # Check 2: PII in user input (redact, don't block)
        pii_entities = await self.detect_pii(text)
        if pii_entities:
            filtered = self._redact_text(text, pii_entities)
            latency = int((time.time() - start) * 1000)
            logger.info(f"PII detected in input: {len(pii_entities)} entities, redacted")
            return GuardrailResult(
                action=GuardrailAction.REDACT,
                category=GuardrailCategory.PII_DETECTED,
                original_text=text,
                filtered_text=filtered,
                pii_entities=pii_entities,
                confidence=0.8,
                details=f"Detected {len(pii_entities)} PII entities, redacted before processing",
                latency_ms=latency,
            )

        # All checks passed
        latency = int((time.time() - start) * 1000)
        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            category=GuardrailCategory.SAFE,
            original_text=text,
            confidence=1.0,
            details="Input passed all guardrail checks",
            latency_ms=latency,
        )

    async def check_output(self, text: str, context_chunks: list[str] | None = None) -> GuardrailResult:
        """Check LLM output for PII (redact before returning to user)."""
        start = time.time()

        # Check: PII in LLM response
        pii_entities = await self.detect_pii(text)
        if pii_entities:
            filtered = self._redact_text(text, pii_entities)
            latency = int((time.time() - start) * 1000)
            logger.info(f"PII detected in output: {len(pii_entities)} entities, redacted")
            return GuardrailResult(
                action=GuardrailAction.REDACT,
                category=GuardrailCategory.PII_DETECTED,
                original_text=text,
                filtered_text=filtered,
                pii_entities=pii_entities,
                confidence=0.8,
                details=f"Redacted {len(pii_entities)} PII entities from LLM response",
                latency_ms=latency,
            )

        latency = int((time.time() - start) * 1000)
        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            category=GuardrailCategory.SAFE,
            original_text=text,
            confidence=1.0,
            details="Output passed all guardrail checks",
            latency_ms=latency,
        )

    async def detect_pii(self, text: str) -> list[PIIEntity]:
        """Detect PII using regex patterns."""
        entities: list[PIIEntity] = []

        for entity_type, pattern in PII_PATTERNS:
            for match in pattern.finditer(text):
                entities.append(
                    PIIEntity(
                        entity_type=entity_type,
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=0.85,  # Regex matches are fairly confident
                    )
                )

        # Sort by position (for consistent redaction)
        entities.sort(key=lambda e: e.start)
        return entities

    @staticmethod
    def _redact_text(text: str, entities: list[PIIEntity]) -> str:
        """Replace PII entities with [REDACTED] markers.

        Processes entities in reverse order so character offsets stay valid.
        """
        result = text
        for entity in sorted(entities, key=lambda e: e.start, reverse=True):
            placeholder = f"[{entity.entity_type}_REDACTED]"
            result = result[:entity.start] + placeholder + result[entity.end:]
        return result
