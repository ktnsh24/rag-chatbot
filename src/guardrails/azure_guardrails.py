"""
Azure Guardrails — Azure AI Content Safety + Azure AI Language.

Uses managed Azure services for:
    - Content safety: Azure AI Content Safety (hate, violence, sexual, self-harm)
    - PII detection: Azure AI Language (PII entity recognition)
    - Prompt injection: Local regex + content safety categories

Requires:
    - Azure AI Content Safety resource (endpoint + key in settings)
    - Azure AI Language resource (for PII — can reuse the same endpoint)

Cost:
    - Content Safety: $1 per 1K text records (standard tier)
    - AI Language PII: $1 per 1K text records
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


class AzureGuardrails(BaseGuardrails):
    """
    Azure-powered guardrails using AI Content Safety + AI Language.

    Azure AI Content Safety provides:
        - Harm categories: hate, violence, sexual, self-harm
        - Severity levels: 0 (safe) to 6 (severe) per category
        - Threshold-based blocking (configurable per category)

    Azure AI Language provides:
        - PII entity recognition with categories and confidence
        - Supports: person name, email, phone, address, credit card, etc.
        - Returns redacted text with entity positions
    """

    def __init__(
        self,
        content_safety_endpoint: str,
        content_safety_key: str,
        language_endpoint: str = "",
        language_key: str = "",
        severity_threshold: int = 2,
    ) -> None:
        self._severity_threshold = severity_threshold

        # Azure AI Content Safety client
        from azure.ai.contentsafety import ContentSafetyClient
        from azure.core.credentials import AzureKeyCredential

        self._safety_client = ContentSafetyClient(
            endpoint=content_safety_endpoint,
            credential=AzureKeyCredential(content_safety_key),
        )

        # Azure AI Language client (for PII) — optional
        self._language_endpoint = language_endpoint
        self._language_key = language_key

        logger.info(
            "Azure guardrails initialized — content_safety=enabled, language_pii={}",
            "enabled" if language_endpoint else "disabled (using regex fallback)",
        )

    async def check_input(self, text: str) -> GuardrailResult:
        """Check user input with Azure Content Safety + PII detection."""
        start = time.time()

        # Check 1: Prompt injection (regex — fast, free)
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

        # Check 2: Azure Content Safety
        safety_result = await self._check_content_safety(text)
        if safety_result and safety_result.action == GuardrailAction.BLOCK:
            safety_result.latency_ms = int((time.time() - start) * 1000)
            return safety_result

        # Check 3: PII detection
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
                details=f"Detected {len(pii_entities)} PII entities via Azure AI Language",
                latency_ms=latency,
            )

        latency = int((time.time() - start) * 1000)
        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            category=GuardrailCategory.SAFE,
            original_text=text,
            confidence=1.0,
            details="Input passed Azure guardrails",
            latency_ms=latency,
        )

    async def check_output(self, text: str, context_chunks: list[str] | None = None) -> GuardrailResult:
        """Check LLM output with Azure Content Safety + PII redaction."""
        start = time.time()

        # Check 1: Content Safety on output
        safety_result = await self._check_content_safety(text)
        if safety_result and safety_result.action == GuardrailAction.BLOCK:
            safety_result.latency_ms = int((time.time() - start) * 1000)
            return safety_result

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
            details="Output passed Azure guardrails",
            latency_ms=latency,
        )

    async def detect_pii(self, text: str) -> list[PIIEntity]:
        """Detect PII using Azure AI Language (or regex fallback)."""
        if self._language_endpoint and self._language_key:
            return await self._detect_pii_azure_language(text)

        # Fallback to regex
        from src.guardrails.local_guardrails import LocalGuardrails

        fallback = LocalGuardrails()
        return await fallback.detect_pii(text)

    async def _detect_pii_azure_language(self, text: str) -> list[PIIEntity]:
        """Detect PII using Azure AI Language service."""
        try:
            from azure.ai.textanalytics import TextAnalyticsClient
            from azure.core.credentials import AzureKeyCredential

            client = TextAnalyticsClient(
                endpoint=self._language_endpoint,
                credential=AzureKeyCredential(self._language_key),
            )

            response = client.recognize_pii_entities(documents=[text])
            result = response[0]

            if result.is_error:
                logger.error(f"Azure Language PII detection error: {result.error}")
                return []

            entities: list[PIIEntity] = []
            for entity in result.entities:
                entities.append(
                    PIIEntity(
                        entity_type=entity.category.upper(),
                        text=entity.text,
                        start=entity.offset,
                        end=entity.offset + entity.length,
                        confidence=entity.confidence_score,
                    )
                )

            entities.sort(key=lambda e: e.start)
            return entities

        except Exception as e:
            logger.error(f"Azure Language PII detection failed: {e}")
            from src.guardrails.local_guardrails import LocalGuardrails

            fallback = LocalGuardrails()
            return await fallback.detect_pii(text)

    async def _check_content_safety(self, text: str) -> GuardrailResult | None:
        """Check text against Azure AI Content Safety."""
        try:
            from azure.ai.contentsafety.models import AnalyzeTextOptions

            request = AnalyzeTextOptions(text=text[:10000])  # Max 10K characters
            response = self._safety_client.analyze_text(request)

            # Check each harm category against threshold
            violations = []
            for category_result in response.categories_analysis:
                if category_result.severity >= self._severity_threshold:
                    violations.append(f"{category_result.category}={category_result.severity}")

            if violations:
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    category=GuardrailCategory.TOXIC_CONTENT,
                    original_text=text,
                    confidence=0.95,
                    details=f"Azure Content Safety violations: {', '.join(violations)}",
                )

            return None  # No violations

        except Exception as e:
            logger.error(f"Azure Content Safety check failed: {e}")
            return None  # Fail open
