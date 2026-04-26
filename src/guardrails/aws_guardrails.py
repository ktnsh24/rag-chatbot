"""
AWS Guardrails — Bedrock Guardrails + Amazon Comprehend.

Uses managed AWS services for:
    - Content safety: Bedrock Guardrails API (deny topics, content filters, word filters)
    - PII detection: Amazon Comprehend (DetectPiiEntities)
    - Prompt injection: Bedrock Guardrails content policy + local regex fallback

Requires:
    - Bedrock Guardrails configured in the AWS console (guardrail ID in settings)
    - Comprehend permissions: comprehend:DetectPiiEntities

Cost:
    - Bedrock Guardrails: $0.75 per 1K text units (1 unit = 1 character)
    - Comprehend PII: $0.0001 per unit (1 unit = 100 characters, min 3 units)
    - For a portfolio with ~100 queries/day: ~$0.01/day
"""

from __future__ import annotations

import time

from loguru import logger

from src.guardrails.base import (
    BaseGuardrails,
    GuardrailAction,
    GuardrailCategory,
    GuardrailResult,
    PIIEntity,
)
from src.guardrails.local_guardrails import INJECTION_PATTERNS


class AWSGuardrails(BaseGuardrails):
    """
    AWS-powered guardrails using Bedrock Guardrails + Amazon Comprehend.

    Bedrock Guardrails provides:
        - Content filters (hate, insults, sexual, violence — with severity levels)
        - Denied topics (custom topics that should be blocked)
        - Word filters (custom blocked words/phrases)
        - PII filters (built-in PII detection with redaction)

    Amazon Comprehend provides:
        - DetectPiiEntities: finds PII with entity types and confidence scores
        - More granular than Bedrock's built-in PII (separate confidence per entity)
    """

    def __init__(self, region: str, guardrail_id: str = "", guardrail_version: str = "DRAFT") -> None:
        import boto3

        self._region = region
        self._guardrail_id = guardrail_id
        self._guardrail_version = guardrail_version

        session = boto3.Session(region_name=region)
        self._bedrock_client = session.client("bedrock-runtime") if guardrail_id else None
        self._comprehend_client = session.client("comprehend")

        logger.info(
            "AWS guardrails initialized — region={}, guardrail_id={}, comprehend=enabled",
            region,
            guardrail_id or "(none — using regex fallback for injection)",
        )

    async def check_input(self, text: str) -> GuardrailResult:
        """Check user input using Bedrock Guardrails + Comprehend PII."""
        start = time.time()

        # Check 1: Prompt injection (regex first — fast, free)
        for pattern in INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                latency = int((time.time() - start) * 1000)
                logger.warning(f"Prompt injection detected (regex): '{match.group()}'")
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    category=GuardrailCategory.PROMPT_INJECTION,
                    original_text=text,
                    confidence=0.9,
                    details=f"Prompt injection pattern: '{match.group()}'",
                    latency_ms=latency,
                )

        # Check 2: Bedrock Guardrails content policy (if configured)
        if self._bedrock_client and self._guardrail_id:
            bedrock_result = await self._check_bedrock_guardrail(text, "INPUT")
            if bedrock_result and bedrock_result.action == GuardrailAction.BLOCK:
                bedrock_result.latency_ms = int((time.time() - start) * 1000)
                return bedrock_result

        # Check 3: PII detection via Comprehend
        pii_entities = await self.detect_pii(text)
        if pii_entities:
            from src.guardrails.local_guardrails import LocalGuardrails

            filtered = LocalGuardrails._redact_text(text, pii_entities)
            latency = int((time.time() - start) * 1000)
            return GuardrailResult(
                action=GuardrailAction.REDACT,
                category=GuardrailCategory.PII_DETECTED,
                original_text=text,
                filtered_text=filtered,
                pii_entities=pii_entities,
                confidence=0.9,
                details=f"Comprehend detected {len(pii_entities)} PII entities",
                latency_ms=latency,
            )

        latency = int((time.time() - start) * 1000)
        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            category=GuardrailCategory.SAFE,
            original_text=text,
            confidence=1.0,
            details="Input passed AWS guardrails",
            latency_ms=latency,
        )

    async def check_output(self, text: str, context_chunks: list[str] | None = None) -> GuardrailResult:
        """Check LLM output using Bedrock Guardrails + Comprehend PII."""
        start = time.time()

        # Check 1: Bedrock Guardrails output policy
        if self._bedrock_client and self._guardrail_id:
            bedrock_result = await self._check_bedrock_guardrail(text, "OUTPUT")
            if bedrock_result and bedrock_result.action == GuardrailAction.BLOCK:
                bedrock_result.latency_ms = int((time.time() - start) * 1000)
                return bedrock_result

        # Check 2: PII in output
        pii_entities = await self.detect_pii(text)
        if pii_entities:
            from src.guardrails.local_guardrails import LocalGuardrails

            filtered = LocalGuardrails._redact_text(text, pii_entities)
            latency = int((time.time() - start) * 1000)
            return GuardrailResult(
                action=GuardrailAction.REDACT,
                category=GuardrailCategory.PII_DETECTED,
                original_text=text,
                filtered_text=filtered,
                pii_entities=pii_entities,
                confidence=0.9,
                details=f"Redacted {len(pii_entities)} PII entities from output",
                latency_ms=latency,
            )

        latency = int((time.time() - start) * 1000)
        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            category=GuardrailCategory.SAFE,
            original_text=text,
            confidence=1.0,
            details="Output passed AWS guardrails",
            latency_ms=latency,
        )

    async def detect_pii(self, text: str) -> list[PIIEntity]:
        """Detect PII using Amazon Comprehend DetectPiiEntities."""
        try:
            response = self._comprehend_client.detect_pii_entities(
                Text=text[:5000],  # Comprehend max is 5,000 UTF-8 bytes
                LanguageCode="en",
            )

            entities: list[PIIEntity] = []
            for entity in response.get("Entities", []):
                entities.append(
                    PIIEntity(
                        entity_type=entity["Type"],  # NAME, EMAIL, PHONE, SSN, etc.
                        text=text[entity["BeginOffset"] : entity["EndOffset"]],
                        start=entity["BeginOffset"],
                        end=entity["EndOffset"],
                        confidence=entity.get("Score", 0.0),
                    )
                )

            entities.sort(key=lambda e: e.start)
            return entities

        except Exception as e:
            logger.error(f"Comprehend PII detection failed: {e}")
            # Fallback to regex-based detection
            from src.guardrails.local_guardrails import LocalGuardrails

            fallback = LocalGuardrails()
            return await fallback.detect_pii(text)

    async def _check_bedrock_guardrail(self, text: str, source: str) -> GuardrailResult | None:
        """Apply Bedrock Guardrails to text.

        Args:
            text: Content to check.
            source: "INPUT" for user input, "OUTPUT" for LLM response.
        """
        try:
            response = self._bedrock_client.apply_guardrail(
                guardrailIdentifier=self._guardrail_id,
                guardrailVersion=self._guardrail_version,
                source=source,
                content=[{"text": {"text": text}}],
            )

            action = response.get("action", "NONE")
            if action == "GUARDRAIL_INTERVENED":
                outputs = response.get("outputs", [])
                output_text = outputs[0]["text"] if outputs else "Content blocked by guardrail"
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    category=GuardrailCategory.TOXIC_CONTENT,
                    original_text=text,
                    filtered_text=output_text,
                    confidence=0.95,
                    details=f"Bedrock Guardrail intervened (source={source})",
                )

            return None  # No intervention

        except Exception as e:
            logger.error(f"Bedrock Guardrails check failed: {e}")
            return None  # Fail open — don't block on errors
