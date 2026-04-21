"""
Amazon S3 Document Storage

Stores uploaded documents in an S3 bucket.  Each file is keyed as
``documents/{document_id}/{filename}`` so that document-level deletion
is a simple prefix-delete.

Bucket is created by infra/aws/s3.tf.
"""

from __future__ import annotations

from datetime import datetime, timezone

import boto3
from loguru import logger

from src.config import get_settings
from src.storage.base import BaseDocumentStorage, StoredDocument


class S3DocumentStorage(BaseDocumentStorage):
    """Store documents in Amazon S3."""

    def __init__(self) -> None:
        settings = get_settings()
        self._s3 = boto3.client("s3", region_name=settings.aws_region)
        self._bucket = settings.aws_s3_bucket
        logger.info("S3 storage initialised — bucket={}", self._bucket)

    def _key(self, document_id: str, filename: str = "") -> str:
        """Build the S3 object key."""
        return f"documents/{document_id}/{filename}" if filename else f"documents/{document_id}/"

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
        key = self._key(document_id, filename)
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        logger.info("Uploaded → s3://{}/{}", self._bucket, key)
        return StoredDocument(
            document_id=document_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            uploaded_at=datetime.now(timezone.utc),
            storage_path=key,
        )

    # ------------------------------------------------------------------ #
    # Download
    # ------------------------------------------------------------------ #
    async def download(self, document_id: str) -> bytes:
        # List objects under the prefix to find the filename
        prefix = self._key(document_id)
        response = self._s3.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        contents = response.get("Contents", [])
        if not contents:
            raise FileNotFoundError(f"No document found for id={document_id}")
        key = contents[0]["Key"]
        obj = self._s3.get_object(Bucket=self._bucket, Key=key)
        return obj["Body"].read()

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #
    async def delete(self, document_id: str) -> None:
        prefix = self._key(document_id)
        response = self._s3.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        objects = [{"Key": obj["Key"]} for obj in response.get("Contents", [])]
        if objects:
            self._s3.delete_objects(
                Bucket=self._bucket,
                Delete={"Objects": objects},
            )
        logger.info("Deleted document — id={}", document_id)

    # ------------------------------------------------------------------ #
    # List
    # ------------------------------------------------------------------ #
    async def list_documents(self) -> list[StoredDocument]:
        prefix = "documents/"
        paginator = self._s3.get_paginator("list_objects_v2")
        documents: list[StoredDocument] = []
        seen_ids: set[str] = set()

        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                parts = obj["Key"].split("/")
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
                        content_type="application/octet-stream",
                        size_bytes=obj["Size"],
                        uploaded_at=obj["LastModified"],
                        storage_path=obj["Key"],
                    )
                )
        return documents
