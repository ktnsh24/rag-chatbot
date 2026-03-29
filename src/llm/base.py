"""
Abstract LLM Interface

This defines the contract that every LLM provider must follow.
Both aws_bedrock.py and azure_openai.py implement this interface.

Why abstract classes?
    - The RAG chain doesn't care whether it talks to Bedrock or Azure OpenAI
    - You can swap providers by changing one environment variable
    - Tests can use a mock LLM that returns predictable answers
    - This is the "Strategy Pattern" — same interface, different implementations
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """
    Standardized response from any LLM provider.

    Fields:
        text: The generated text (the answer).
        input_tokens: How many tokens were in the prompt.
        output_tokens: How many tokens the model generated.
        model_id: Which model was used (for logging/debugging).
    """

    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model_id: str = ""


class BaseLLM(ABC):
    """
    Abstract base class for LLM providers.

    Every LLM provider must implement:
        - generate(): Send a prompt, get a response
        - get_embedding(): Convert text to a vector (for semantic search)
    """

    @abstractmethod
    async def generate(self, prompt: str, context: list[str], temperature: float = 0.1) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user's question (or full prompt with instructions).
            context: List of document chunks to include as context.
            temperature: Creativity level (0.0 = deterministic, 1.0 = creative).

        Returns:
            LLMResponse with the generated text and token usage.
        """
        ...

    @abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        """
        Convert text into a vector embedding.

        Args:
            text: The text to embed (a document chunk or a user query).

        Returns:
            A list of floats representing the text in vector space.
            Similar texts will have similar vectors (high cosine similarity).

        Why this matters:
            - This is how we turn "meaning" into math
            - A question like "What is the refund policy?" becomes [0.12, -0.45, 0.78, ...]
            - A document chunk about refunds becomes a similar vector
            - We find matches by comparing these vectors (cosine similarity)
        """
        ...

    @abstractmethod
    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Convert multiple texts into embeddings in one API call.

        More efficient than calling get_embedding() in a loop because:
            - One network round-trip instead of N
            - Providers batch internally for faster processing

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        ...
