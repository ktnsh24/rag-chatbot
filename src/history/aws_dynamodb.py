"""
Amazon DynamoDB Conversation History

Stores chat messages in a DynamoDB table with session_id as partition key
and timestamp as sort key.  This gives O(1) lookups by session and natural
time ordering.

Table schema (created by infra/aws/main.tf):
    PK  = session_id  (String)
    SK  = timestamp    (String, ISO-8601)
    role    (String)
    content (String)
"""

from __future__ import annotations

from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from loguru import logger

from src.config import get_settings
from src.history.base import BaseConversationHistory, ConversationMessage


class DynamoDBConversationHistory(BaseConversationHistory):
    """Store conversation history in Amazon DynamoDB."""

    def __init__(self) -> None:
        settings = get_settings()
        session = boto3.Session(region_name=settings.aws_region)
        dynamodb = session.resource("dynamodb")
        self.table = dynamodb.Table(settings.aws_dynamodb_table)
        logger.info(
            "DynamoDB history initialised — table={}",
            settings.aws_dynamodb_table,
        )

    # ------------------------------------------------------------------ #
    # Write
    # ------------------------------------------------------------------ #
    async def add_message(self, message: ConversationMessage) -> None:
        """Persist a message to DynamoDB."""
        item = {
            "session_id": message.session_id,
            "timestamp": message.timestamp.isoformat(),
            "role": message.role,
            "content": message.content,
        }
        self.table.put_item(Item=item)
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
        response = self.table.query(
            KeyConditionExpression=Key("session_id").eq(session_id),
            ScanIndexForward=False,  # newest first
            Limit=limit,
        )
        messages = [
            ConversationMessage(
                session_id=item["session_id"],
                role=item["role"],
                content=item["content"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
            )
            for item in response.get("Items", [])
        ]
        messages.reverse()  # chronological order
        return messages

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #
    async def delete_session(self, session_id: str) -> None:
        """Remove all messages for a session (paginated scan + batch delete)."""
        response = self.table.query(
            KeyConditionExpression=Key("session_id").eq(session_id),
            ProjectionExpression="session_id, #ts",
            ExpressionAttributeNames={"#ts": "timestamp"},
        )
        with self.table.batch_writer() as batch:
            for item in response.get("Items", []):
                batch.delete_item(
                    Key={
                        "session_id": item["session_id"],
                        "timestamp": item["timestamp"],
                    }
                )
        logger.info("Deleted session history — session={}", session_id)
