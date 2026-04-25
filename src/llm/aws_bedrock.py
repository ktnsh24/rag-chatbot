"""
Amazon Bedrock LLM Provider

Uses AWS Bedrock to:
    - Generate answers (Claude 3.5 Sonnet)
    - Create embeddings (Amazon Titan Embeddings)

Why Bedrock?
    - Managed service — no GPU instances to manage
    - Pay-per-token — no idle costs
    - Claude 3.5 Sonnet is one of the best models for RAG
    - Runs in your AWS account — data stays in your region

Cost (eu-central-1, Claude 3.5 Sonnet v2):
    - Input:  $0.003 / 1K tokens
    - Output: $0.015 / 1K tokens
    - A typical RAG query uses ~2K input + ~500 output = ~$0.01 per query

See docs/aws-services.md for deep dive.
See docs/cost-analysis.md for cost comparison.
"""

import json

import boto3
from loguru import logger

from src.llm.base import BaseLLM, LLMResponse


class BedrockLLM(BaseLLM):
    """
    AWS Bedrock implementation of the LLM interface.

    Initialization:
        client = BedrockLLM(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            region="eu-central-1"
        )

    The boto3 client picks up AWS credentials from:
        1. Environment variables (AWS_ACCESS_KEY_ID, etc.)
        2. ~/.aws/credentials
        3. IAM role (when running on ECS/Lambda)
    """

    def __init__(self, model_id: str, region: str):
        self.model_id = model_id
        self.region = region
        self._runtime_client = boto3.client("bedrock-runtime", region_name=region)
        self._embedding_model_id = "amazon.titan-embed-text-v2:0"
        logger.info(f"Bedrock LLM initialized: model={model_id}, region={region}")

    async def generate(self, prompt: str, context: list[str], temperature: float = 0.1) -> LLMResponse:
        """
        Send a prompt to Claude via Bedrock's Converse API.

        The Converse API is Bedrock's unified interface — it works the same
        for Claude, Titan, Llama, and other models. You don't need to know
        each model's native request format.
        """
        # Build the system prompt with RAG instructions
        system_prompt = (
            "You are a helpful assistant that answers questions based on the provided context. "
            "Rules:\n"
            "1. ONLY use information from the context below to answer\n"
            "2. If the context doesn't contain the answer, say 'I don't have enough information to answer that'\n"
            "3. Cite which document(s) you used in your answer\n"
            "4. Be concise but thorough\n"
            "5. Use bullet points for lists\n"
        )

        # Format context chunks
        context_text = "\n\n---\n\n".join(
            f"[Document chunk {i + 1}]:\n{chunk}" for i, chunk in enumerate(context)
        )

        # Build the user message
        user_message = f"Context:\n{context_text}\n\nQuestion: {prompt}"

        try:
            response = self._runtime_client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": user_message}]}],
                system=[{"text": system_prompt}],
                inferenceConfig={
                    "maxTokens": 2048,
                    "temperature": temperature,
                },
            )

            # Extract response
            output_text = response["output"]["message"]["content"][0]["text"]
            usage = response.get("usage", {})

            return LLMResponse(
                text=output_text,
                input_tokens=usage.get("inputTokens", 0),
                output_tokens=usage.get("outputTokens", 0),
                model_id=self.model_id,
            )

        except Exception as e:
            logger.error(f"Bedrock generate error: {e}")
            raise

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate an embedding using Amazon Titan Embeddings v2.

        Titan Embeddings v2:
            - 1024 dimensions
            - Supports up to 8192 tokens
            - Cost: $0.00002 / 1K tokens (extremely cheap)
        """
        try:
            response = self._runtime_client.invoke_model(
                modelId=self._embedding_model_id,
                body=json.dumps({"inputText": text}),
                contentType="application/json",
            )
            result = json.loads(response["body"].read())
            return result["embedding"]
        except Exception as e:
            logger.error(f"Bedrock embedding error: {e}")
            raise

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Batch embedding generation.

        Titan doesn't have a native batch API, so we call one at a time.
        For production, you'd use SageMaker batch transform.
        """
        embeddings = []
        for text in texts:
            embedding = await self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings
