"""
Azure Cosmos DB Conversation History

Stores chat messages in a Cosmos DB container (SQL/NoSQL API).
Uses session_id as partition key for fast lookups within a session.

Container schema (created by infra/azure/cosmosdb.tf):
    id             (String, UUID)
    session_id     (String) — partition key
    role           (String)
    content        (String)
    timestamp      (String, ISO-8601)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from azure.cosmos.aio import CosmosClient
from loguru import logger

from src.config import get_settings
from src.history.base import BaseConversationHistory, ConversationMessage


class CosmosDBConversationHistory(BaseConversationHistory):
    """Store conversation history in Azure Cosmos DB."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = CosmosClient(
            url=settings.azure_cosmos_endpoint,
            credential=settings.azure_cosmos_key,
        )
        self._database_name = settings.azure_cosmos_database
        self._container_name = settings.azure_cosmos_container
        self._container = None
        logger.info(
            "Cosmos DB history initialised — db={} container={}",
            self._database_name,
            self._container_name,
        )

    async def _get_container(self):
        """Lazy-initialise the container client."""
        if self._container is None:
            database = self._client.get_database_client(self._database_name)
            self._container = database.get_container_client(self._container_name)
        return self._container

    # ------------------------------------------------------------------ #
    # Write
    # ------------------------------------------------------------------ #
    async def add_message(self, message: ConversationMessage) -> None:
        """Persist a message to Cosmos DB."""
        container = await self._get_container()
        item = {
            "id": str(uuid.uuid4()),
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
        }
        await container.create_item(body=item)
        logger.debug(
            "Stored message — session={} role={}",
            message.session_id,
            message.role,
        )

    # ------------------------------------------------------------------ #
    # Read
    # ------------------------------------------------------------------ #
    async def get_history(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[ConversationMessage]:
        """Retrieve the most recent messages for a session (newest last)."""
        container = await self._get_container()
        query = "SELECT TOP @limit * FROM c " "WHERE c.session_id = @session_id " "ORDER BY c.timestamp DESC"
        parameters = [
            {"name": "@limit", "value": limit},
            {"name": "@session_id", "value": session_id},
        ]
        items = []
        async for item in container.query_items(
            query=query,
            parameters=parameters,
            partition_key=session_id,
        ):
            items.append(item)

        messages = [
            ConversationMessage(
                session_id=item["session_id"],
                role=item["role"],
                content=item["content"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
            )
            for item in items
        ]
        messages.reverse()  # chronological order
        return messages

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #
    async def delete_session(self, session_id: str) -> None:
        """Remove all messages for a session."""
        container = await self._get_container()
        query = "SELECT c.id FROM c WHERE c.session_id = @session_id"
        parameters = [{"name": "@session_id", "value": session_id}]

        async for item in container.query_items(
            query=query,
            parameters=parameters,
            partition_key=session_id,
        ):
            await container.delete_item(item=item["id"], partition_key=session_id)

        logger.info("Deleted session history — session={}", session_id)
