"""
Guardrails Middleware — Applies input/output guardrails to the RAG pipeline.

This middleware wraps the chat endpoint:
    1. BEFORE the RAG chain: check_input() on the user's question
    2. AFTER the RAG chain: check_output() on the LLM's response

If input is blocked → return 400 with explanation (no LLM call, saves money).
If input has PII → redact PII before passing to the RAG chain.
If output has PII → redact PII before returning to the user.

The guardrail provider is selected by CLOUD_PROVIDER (same pattern as LLM/vectorstore).

Configuration (in .env):
    GUARDRAILS_ENABLED=true          # Enable/disable all guardrails
    GUARDRAILS_INPUT_ENABLED=true    # Enable/disable input checks only
    GUARDRAILS_OUTPUT_ENABLED=true   # Enable/disable output checks only
"""

from __future__ import annotations

from loguru import logger

from src.config import CloudProvider, Settings
from src.guardrails.base import BaseGuardrails, GuardrailAction, GuardrailResult


def create_guardrails(settings: Settings) -> BaseGuardrails | None:
    """
    Factory function — creates the right guardrails provider based on settings.

    Returns None if guardrails are disabled.
    """
    if not getattr(settings, "guardrails_enabled", True):
        logger.info("Guardrails disabled via settings")
        return None

    if settings.cloud_provider == CloudProvider.AWS:
        from src.guardrails.aws_guardrails import AWSGuardrails

        return AWSGuardrails(
            region=settings.aws_region,
            guardrail_id=getattr(settings, "aws_bedrock_guardrail_id", ""),
            guardrail_version=getattr(settings, "aws_bedrock_guardrail_version", "DRAFT"),
        )

    elif settings.cloud_provider == CloudProvider.AZURE:
        from src.guardrails.azure_guardrails import AzureGuardrails

        return AzureGuardrails(
            content_safety_endpoint=getattr(settings, "azure_content_safety_endpoint", ""),
            content_safety_key=getattr(settings, "azure_content_safety_key", ""),
            language_endpoint=getattr(settings, "azure_language_endpoint", ""),
            language_key=getattr(settings, "azure_language_key", ""),
        )

    else:
        from src.guardrails.local_guardrails import LocalGuardrails

        return LocalGuardrails()


async def apply_input_guardrail(
    guardrails: BaseGuardrails | None, text: str
) -> tuple[str, GuardrailResult | None]:
    """
    Apply input guardrails to user text.

    Returns:
        (processed_text, result) — processed_text may have PII redacted.
        If result.action == BLOCK, the caller should reject the request.
    """
    if guardrails is None:
        return text, None

    result = await guardrails.check_input(text)

    if result.action == GuardrailAction.BLOCK:
        logger.warning(f"Input BLOCKED: {result.details}")
        return text, result

    if result.action == GuardrailAction.REDACT:
        logger.info(f"Input REDACTED: {result.details}")
        return result.filtered_text, result

    return text, result


async def apply_output_guardrail(
    guardrails: BaseGuardrails | None, text: str, context_chunks: list[str] | None = None
) -> tuple[str, GuardrailResult | None]:
    """
    Apply output guardrails to LLM response.

    Returns:
        (processed_text, result) — processed_text may have PII redacted.
    """
    if guardrails is None:
        return text, None

    result = await guardrails.check_output(text, context_chunks)

    if result.action == GuardrailAction.BLOCK:
        logger.warning(f"Output BLOCKED: {result.details}")
        return "I cannot provide this response due to safety policies.", result

    if result.action == GuardrailAction.REDACT:
        logger.info(f"Output REDACTED: {result.details}")
        return result.filtered_text, result

    return text, result
