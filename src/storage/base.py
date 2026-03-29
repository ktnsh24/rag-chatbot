"""
Abstract Document Storage Interface

Defines the contract for storing and retrieving raw document files
(PDFs, text files, etc.) that users upload for RAG ingestion.

Implementations:
    - aws_s3.py      → Amazon S3
    - azure_blob.py  → Azure Blob Storage
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StoredDocument:
    """Metadata about a stored document."""

    document_id: str
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    storage_path: str  # provider-specific key / blob name


class BaseDocumentStorage(ABC):
    """Abstract document storage."""

    @abstractmethod
    async def upload(
        self,
        document_id: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> StoredDocument:
        """Upload a document and return its metadata."""
        ...

    @abstractmethod
    async def download(self, document_id: str) -> bytes:
        """Download a document's raw bytes."""
        ...

    @abstractmethod
    async def delete(self, document_id: str) -> None:
        """Delete a document from storage."""
        ...

    @abstractmethod
    async def list_documents(self) -> list[StoredDocument]:
        """List all stored documents."""
        ...
