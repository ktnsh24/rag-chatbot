"""LLM-as-judge helpers for semantic RAG evaluation."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

from loguru import logger

from src.config import EvaluationMode, JudgeProvider, Settings
from src.llm.aws_bedrock import BedrockLLM
from src.llm.azure_openai import AzureOpenAILLM
from src.llm.base import BaseLLM
from src.llm.local_ollama import OllamaLLM


@dataclass
class LLMJudgeResult:
    """Judge scores for a single evaluated answer."""

    faithfulness: float
    answer_relevance: float
    overall: float
    passed: bool
    notes: list[str] = field(default_factory=list)
    latency_ms: int | None = None
    provider: str | None = None


class LLMJudgeEvaluator:
    """Semantic scorer that reuses the active runtime LLM."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def is_enabled(self) -> bool:
        return self._settings.eval_mode != EvaluationMode.RULE_BASED

    async def evaluate(
        self,
        llm: BaseLLM,
        question: str,
        answer: str,
        context_chunks: list[str],
        retrieval_score: float,
    ) -> LLMJudgeResult:
        started = time.perf_counter()
        prompt = self._build_prompt(question=question, answer=answer, context_chunks=context_chunks)
        raw_text, input_tokens, output_tokens = await self._call_judge_llm(llm=llm, prompt=prompt)
        latency_ms = int((time.perf_counter() - started) * 1000)
        parsed = self._parse_judge_response(raw_text)

        faithfulness = self._clamp(parsed.get("faithfulness"), fallback=0.0)
        answer_relevance = self._clamp(parsed.get("answer_relevance"), fallback=0.0)
        overall = round(retrieval_score * 0.3 + faithfulness * 0.4 + answer_relevance * 0.3, 3)
        notes = parsed.get("notes") or []
        if not isinstance(notes, list):
            notes = [str(notes)]
        notes.append(f"Judge tokens: input={input_tokens}, output={output_tokens}")

        return LLMJudgeResult(
            faithfulness=faithfulness,
            answer_relevance=answer_relevance,
            overall=overall,
            passed=overall >= 0.7,
            notes=[str(note) for note in notes],
            latency_ms=latency_ms,
            provider=self.provider_label(llm),
        )

    def provider_label(self, llm: BaseLLM) -> str:
        if isinstance(llm, OllamaLLM):
            return JudgeProvider.LOCAL.value
        if isinstance(llm, BedrockLLM):
            return JudgeProvider.AWS.value
        if isinstance(llm, AzureOpenAILLM):
            return JudgeProvider.AZURE.value
        return JudgeProvider.AUTO.value

    def _build_prompt(self, question: str, answer: str, context_chunks: list[str]) -> str:
        context_text = "\n\n---\n\n".join(context_chunks[:10]) if context_chunks else "NO CONTEXT PROVIDED"
        return "\n".join(
            [
                "You are evaluating a RAG answer.",
                'Return ONLY valid JSON with keys "faithfulness", "answer_relevance", and "notes".',
                "Scoring rules:",
                "- faithfulness: 0.0 to 1.0. Score whether the answer stays grounded in the provided context.",
                "- answer_relevance: 0.0 to 1.0. Score whether the answer actually addresses the user's question.",
                "- notes: a short list of concrete reasons for the score.",
                "- Be strict about hallucination, but do not punish safe refusals when the answer clearly admits missing context.",
                "- Do not include markdown fences or any prose outside the JSON object.",
                "",
                f"QUESTION:\n{question}",
                "",
                f"ANSWER:\n{answer}",
                "",
                f"CONTEXT:\n{context_text}",
            ]
        )

    async def _call_judge_llm(self, llm: BaseLLM, prompt: str) -> tuple[str, int, int]:
        if isinstance(llm, OllamaLLM):
            response = await llm._client.post(  # noqa: SLF001
                "/api/chat",
                json={
                    "model": llm.model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a strict RAG evaluation judge. Return only JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.0, "top_p": 0.9, "num_predict": 600},
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"], data.get("prompt_eval_count", 0), data.get("eval_count", 0)

        if isinstance(llm, BedrockLLM):
            response = llm._runtime_client.converse(  # noqa: SLF001
                modelId=llm.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                system=[{"text": "You are a strict RAG evaluation judge. Return only JSON."}],
                inferenceConfig={"maxTokens": 600, "temperature": 0.0},
            )
            usage = response.get("usage", {})
            text = response["output"]["message"]["content"][0]["text"]
            return text, usage.get("inputTokens", 0), usage.get("outputTokens", 0)

        if isinstance(llm, AzureOpenAILLM):
            response = await llm._client.chat.completions.create(  # noqa: SLF001
                model=llm.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a strict RAG evaluation judge. Return only JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=600,
                top_p=0.9,
            )
            usage = response.usage
            text = response.choices[0].message.content or ""
            return text, usage.prompt_tokens if usage else 0, usage.completion_tokens if usage else 0

        generic = await llm.generate(prompt=prompt, context=[], temperature=0.0)
        return generic.text, generic.input_tokens, generic.output_tokens

    def _parse_judge_response(self, raw_text: str) -> dict:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not match:
            logger.warning("Judge response was not valid JSON; raw text: {}", raw_text)
            return {
                "faithfulness": 0.0,
                "answer_relevance": 0.0,
                "notes": ["Judge response could not be parsed as JSON"],
            }

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.warning("Judge JSON decode failed; raw text: {}", raw_text)
            return {
                "faithfulness": 0.0,
                "answer_relevance": 0.0,
                "notes": ["Judge JSON decode failed"],
            }

    def _clamp(self, value: object, fallback: float) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return fallback
        return max(0.0, min(1.0, round(numeric, 3)))


def judge_mode_note(settings: Settings) -> str:
    """Human-readable note about current judge routing semantics."""
    if settings.eval_judge_provider == JudgeProvider.AUTO:
        return f"Judge provider auto-routed from CLOUD_PROVIDER={settings.cloud_provider.value}"
    if settings.eval_judge_provider.value != settings.cloud_provider.value:
        return (
            "Judge provider override differs from CLOUD_PROVIDER. "
            "This first implementation still reuses the active runtime provider."
        )
    return f"Judge provider pinned to {settings.eval_judge_provider.value}"