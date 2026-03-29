"""
Document Routes — Upload, list, delete documents.

Provides:
    POST   /api/documents/upload  — Upload a document to the knowledge base
    GET    /api/documents         — List all ingested documents
    DELETE /api/documents/{id}    — Remove a document
"""

import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from loguru import logger

from src.api.models import DocumentInfo, DocumentListResponse, DocumentStatus, DocumentUploadResponse
from src.config import get_settings

router = APIRouter()

# In-memory document registry (in production, this would be in DynamoDB/CosmosDB)
_documents: dict[str, DocumentInfo] = {}

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".docx"}


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    summary="Upload Document",
    description="Upload a document to the RAG knowledge base. Supported formats: PDF, TXT, MD, CSV, DOCX.",
)
async def upload_document(request: Request, file: UploadFile = File(...)) -> DocumentUploadResponse:
    """
    Upload and ingest a document.

    Flow:
        1. Validate file type
        2. Upload to cloud storage (S3 / Blob Storage)
        3. Read the document content
        4. Split into chunks
        5. Generate embeddings for each chunk
        6. Store embeddings in the vector store (OpenSearch / AI Search)
        7. Return the document ID and chunk count
    """
    # Validate file extension
    filename = file.filename or "unknown"
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    document_id = str(uuid4())
    logger.info(f"[{document_id}] Uploading document: {filename}")

    try:
        # Read file content
        content = await file.read()
        file_size = len(content)

        # Check RAG chain for ingestion
        rag_chain = getattr(request.app.state, "rag_chain", None)
        if rag_chain is None:
            raise HTTPException(
                status_code=500,
                detail="RAG chain not initialized. Cannot ingest documents.",
            )

        # Ingest the document
        chunk_count = await rag_chain.ingest_document(
            document_id=document_id,
            filename=filename,
            content=content,
        )

        # Track in document registry
        doc_info = DocumentInfo(
            document_id=document_id,
            filename=filename,
            status=DocumentStatus.READY,
            chunk_count=chunk_count,
            uploaded_at=datetime.now(timezone.utc),
            file_size_bytes=file_size,
        )
        _documents[document_id] = doc_info

        logger.info(f"[{document_id}] Ingested: {chunk_count} chunks from {filename}")

        return DocumentUploadResponse(
            document_id=document_id,
            filename=filename,
            status=DocumentStatus.READY,
            chunk_count=chunk_count,
            message=f"Successfully ingested {filename} into {chunk_count} searchable chunks.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{document_id}] Ingestion failed: {e}")
        _documents[document_id] = DocumentInfo(
            document_id=document_id,
            filename=filename,
            status=DocumentStatus.FAILED,
            chunk_count=0,
            uploaded_at=datetime.now(timezone.utc),
            file_size_bytes=0,
        )
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {e}")


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List Documents",
    description="List all documents that have been uploaded to the knowledge base.",
)
async def list_documents() -> DocumentListResponse:
    """Returns all tracked documents with their status and chunk counts."""
    docs = list(_documents.values())
    return DocumentListResponse(documents=docs, total_count=len(docs))


@router.delete(
    "/documents/{document_id}",
    summary="Delete Document",
    description="Remove a document and its chunks from the knowledge base.",
)
async def delete_document(document_id: str, request: Request) -> dict:
    """
    Remove a document from the vector store and document registry.

    This deletes:
        1. The document from cloud storage (S3 / Blob)
        2. All vector embeddings for this document's chunks
        3. The entry from the document registry
    """
    if document_id not in _documents:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

    doc = _documents[document_id]
    logger.info(f"Deleting document: {doc.filename} ({document_id})")

    # TODO: Delete from vector store and cloud storage
    del _documents[document_id]

    return {"message": f"Document '{doc.filename}' deleted successfully", "document_id": document_id}
