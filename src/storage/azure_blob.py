"""
Azure Blob Storage Document Storage

Stores uploaded documents in an Azure Blob Storage container.
Each blob is named ``documents/{document_id}/{filename}``.

Resources are created by infra/azure/storage.tf.
"""

from __future__ import annotations

from datetime import datetime, timezone

from azure.storage.blob.aio import BlobServiceClient
from loguru import logger

from src.config import get_settings
from src.storage.base import BaseDocumentStorage, StoredDocument


class AzureBlobDocumentStorage(BaseDocumentStorage):
    """Store documents in Azure Blob Storage."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string,
        )
        self._container_name = settings.azure_storage_container
        logger.info(
            "Azure Blob storage initialised — container={}",
            self._container_name,
        )

    def _blob_name(self, document_id: str, filename: str = "") -> str:
        return f"documents/{document_id}/{filename}" if filename else f"documents/{document_id}/"

    async def _get_container(self):
        return self._client.get_container_client(self._container_name)

    # ------------------------------------------------------------------ #
    # Upload
    # ------------------------------------------------------------------ #
    async def upload(
        self,
        document_id: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> StoredDocument:
        container = await self._get_container()
        blob_name = self._blob_name(document_id, filename)
        blob_client = container.get_blob_client(blob_name)
        await blob_client.upload_blob(
            content,
            overwrite=True,
            content_settings={"content_type": content_type},
        )
        logger.info("Uploaded → {}/{}", self._container_name, blob_name)
        return StoredDocument(
            document_id=document_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            uploaded_at=datetime.now(timezone.utc),
            storage_path=blob_name,
        )

    # ------------------------------------------------------------------ #
    # Download
    # ------------------------------------------------------------------ #
    async def download(self, document_id: str) -> bytes:
        container = await self._get_container()
        prefix = f"documents/{document_id}/"
        async for blob in container.list_blobs(name_starts_with=prefix):
            blob_client = container.get_blob_client(blob.name)
            stream = await blob_client.download_blob()
            return await stream.readall()
        raise FileNotFoundError(f"No document found for id={document_id}")

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #
    async def delete(self, document_id: str) -> None:
        container = await self._get_container()
        prefix = f"documents/{document_id}/"
        async for blob in container.list_blobs(name_starts_with=prefix):
            blob_client = container.get_blob_client(blob.name)
            await blob_client.delete_blob()
        logger.info("Deleted document — id={}", document_id)

    # ------------------------------------------------------------------ #
    # List
    # ------------------------------------------------------------------ #
    async def list_documents(self) -> list[StoredDocument]:
        container = await self._get_container()
        prefix = "documents/"
        documents: list[StoredDocument] = []
        seen_ids: set[str] = set()

        async for blob in container.list_blobs(name_starts_with=prefix):
            parts = blob.name.split("/")
            if len(parts) < 3:
                continue
            doc_id = parts[1]
            if doc_id in seen_ids:
                continue
            seen_ids.add(doc_id)
            documents.append(
                StoredDocument(
                    document_id=doc_id,
                    filename=parts[2] if len(parts) > 2 else "",
                    content_type=blob.content_settings.content_type or "application/octet-stream",
                    size_bytes=blob.size or 0,
                    uploaded_at=blob.last_modified or datetime.now(timezone.utc),
                    storage_path=blob.name,
                )
            )
        return documents
