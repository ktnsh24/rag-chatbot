"""
Azure OpenAI LLM Provider

Uses Azure OpenAI Service to:
    - Generate answers (GPT-4o)
    - Create embeddings (text-embedding-3-small)

Why Azure OpenAI (not regular OpenAI)?
    - Data stays in YOUR Azure tenant (EU region)
    - Enterprise SLA and compliance
    - Same models as OpenAI but with Azure security
    - Managed Identity auth (no API keys in production)

Cost (West Europe, GPT-4o):
    - Input:  $0.0025 / 1K tokens
    - Output: $0.01 / 1K tokens
    - A typical RAG query: ~$0.008 per query

See docs/azure-services.md for deep dive.
See docs/cost-analysis.md for cost comparison.
"""

from loguru import logger
from openai import AsyncAzureOpenAI

from src.llm.base import BaseLLM, LLMResponse


class AzureOpenAILLM(BaseLLM):
    """
    Azure OpenAI implementation of the LLM interface.

    Initialization:
        client = AzureOpenAILLM(
            endpoint="https://my-resource.openai.azure.com/",
            api_key="your-key",
            deployment_name="gpt-4o",
            api_version="2024-08-01-preview",
            embedding_deployment="text-embedding-3-small",
        )

    Authentication options:
        1. API Key (for development) — set AZURE_OPENAI_API_KEY
        2. Managed Identity (for production) — no key needed, uses Azure RBAC
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment_name: str,
        api_version: str,
        embedding_deployment: str,
    ):
        self.deployment_name = deployment_name
        self.embedding_deployment = embedding_deployment
        self._client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        logger.info(f"Azure OpenAI initialized: deployment={deployment_name}, endpoint={endpoint}")

    async def generate(self, prompt: str, context: list[str], temperature: float = 0.1) -> LLMResponse:
        """
        Send a prompt to GPT-4o via Azure OpenAI.

        Uses the ChatCompletion API with system + user messages.
        The system message contains RAG instructions.
        The user message contains the context chunks + question.
        """
        system_prompt = (
            "You are a helpful assistant that answers questions based on the provided context. "
            "Rules:\n"
            "1. ONLY use information from the context below to answer\n"
            "2. If the context doesn't contain the answer, say 'I don't have enough information to answer that'\n"
            "3. Cite which document(s) you used in your answer\n"
            "4. Be concise but thorough\n"
            "5. Use bullet points for lists\n"
        )

        context_text = "\n\n---\n\n".join(
            f"[Document chunk {i + 1}]:\n{chunk}" for i, chunk in enumerate(context)
        )

        user_message = f"Context:\n{context_text}\n\nQuestion: {prompt}"

        try:
            response = await self._client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=2048,
                top_p=0.9,
            )

            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                text=choice.message.content or "",
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                model_id=self.deployment_name,
            )

        except Exception as e:
            logger.error(f"Azure OpenAI generate error: {e}")
            raise

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate an embedding using text-embedding-3-small.

        text-embedding-3-small:
            - 1536 dimensions
            - Supports up to 8191 tokens
            - Cost: $0.00002 / 1K tokens
        """
        try:
            response = await self._client.embeddings.create(
                model=self.embedding_deployment,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Azure OpenAI embedding error: {e}")
            raise

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Batch embedding generation.

        Azure OpenAI supports batch embedding natively —
        you send multiple texts in one API call.
        """
        try:
            response = await self._client.embeddings.create(
                model=self.embedding_deployment,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Azure OpenAI batch embedding error: {e}")
            raise
