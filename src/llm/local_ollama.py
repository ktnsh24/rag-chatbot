"""
Ollama LLM Provider — Local Development

Uses Ollama to run LLM inference and embedding generation locally.
No cloud credentials, no API keys, no internet required.

Why Ollama?
    - Runs open-source models locally (Llama 3.2, Mistral, Phi-3, etc.)
    - Free — no per-token cost
    - Works offline — no network dependency
    - Same REST API regardless of model
    - Easy install: `curl -fsSL https://ollama.com/install.sh | sh`

Models used:
    - Generation: llama3.2 (3B params, fast on CPU) or mistral (7B, better quality)
    - Embeddings: nomic-embed-text (768 dimensions, best quality/speed ratio)

Cost:
    - $0.00 — runs on your hardware
    - Only cost is electricity + your machine's compute time
    - A typical RAG query: ~2-10 seconds on CPU, ~1-3 seconds with GPU

Setup:
    1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh
    2. Pull models: ollama pull llama3.2 && ollama pull nomic-embed-text
    3. Set CLOUD_PROVIDER=local in .env
    4. Run: uvicorn src.main:app --reload
"""

import httpx
from loguru import logger

from src.llm.base import BaseLLM, LLMResponse


class OllamaLLM(BaseLLM):
    """
    Ollama local LLM implementation.

    Initialization:
        client = OllamaLLM(
            base_url="http://localhost:11434",
            model_name="llama3.2",
            embedding_model="nomic-embed-text",
        )

    Ollama must be running locally (default: http://localhost:11434).
    Start it with: `ollama serve` (or it runs automatically after install).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama3.2",
        embedding_model: str = "nomic-embed-text",
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.embedding_model = embedding_model
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
        logger.info(f"Ollama LLM initialized: model={model_name}, embeddings={embedding_model}, url={base_url}")

    async def generate(self, prompt: str, context: list[str], temperature: float = 0.1) -> LLMResponse:
        """
        Send a prompt to a local Ollama model.

        Uses the /api/chat endpoint (OpenAI-compatible chat format).
        Same system + user message pattern as Azure OpenAI / Bedrock.
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

        context_text = "\n\n---\n\n".join(f"[Document chunk {i + 1}]:\n{chunk}" for i, chunk in enumerate(context))

        user_message = f"Context:\n{context_text}\n\nQuestion: {prompt}"

        try:
            response = await self._client.post(
                "/api/chat",
                json={
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "top_p": 0.9,
                        "num_predict": 2048,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            return LLMResponse(
                text=data["message"]["content"],
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
                model_id=self.model_name,
            )

        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama. Is it running? Start with: ollama serve")
            raise RuntimeError(
                "Ollama is not running. Start it with: ollama serve "
                "(or install: curl -fsSL https://ollama.com/install.sh | sh)"
            ) from None
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            raise

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate an embedding using a local Ollama embedding model.

        Default model: nomic-embed-text
            - 768 dimensions
            - Good quality for RAG retrieval
            - Fast on CPU (~20ms per embedding)
        """
        try:
            response = await self._client.post(
                "/api/embed",
                json={
                    "model": self.embedding_model,
                    "input": text,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"][0]

        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama. Is it running? Start with: ollama serve")
            raise RuntimeError(
                "Ollama is not running. Start it with: ollama serve "
                "(or install: curl -fsSL https://ollama.com/install.sh | sh)"
            ) from None
        except Exception as e:
            logger.error(f"Ollama embedding error: {e}")
            raise

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Batch embedding generation.

        Ollama's /api/embed endpoint supports batch input natively —
        you send a list of texts and get a list of embeddings back
        in one call (similar to Azure OpenAI's batch support).
        """
        try:
            response = await self._client.post(
                "/api/embed",
                json={
                    "model": self.embedding_model,
                    "input": texts,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"]

        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama. Is it running? Start with: ollama serve")
            raise RuntimeError(
                "Ollama is not running. Start it with: ollama serve "
                "(or install: curl -fsSL https://ollama.com/install.sh | sh)"
            ) from None
        except Exception as e:
            logger.error(f"Ollama batch embedding error: {e}")
            raise
