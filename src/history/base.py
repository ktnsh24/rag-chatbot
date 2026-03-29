"""
Abstract Conversation History Interface

Defines the contract for storing and retrieving conversation history.
This enables follow-up questions — the LLM can see previous messages
in the conversation.

Implementations:
    - aws_dynamodb.py  → Amazon DynamoDB
    - azure_cosmosdb.py → Azure Cosmos DB
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConversationMessage:
    """A single message in a conversation."""

    session_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime


class BaseConversationHistory(ABC):
    """Abstract conversation history store."""

    @abstractmethod
    async def add_message(self, message: ConversationMessage) -> None:
        """Store a message in the conversation history."""
        ...

    @abstractmethod
    async def get_history(self, session_id: str, limit: int = 10) -> list[ConversationMessage]:
        """Retrieve the last N messages for a session."""
        ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete all messages for a session."""
        ...
