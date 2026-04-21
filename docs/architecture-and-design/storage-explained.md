# Document Storage — Deep Dive

> `src/storage/` — Store and retrieve the raw files users upload for RAG ingestion.

> **DE verdict: ★☆☆☆☆ — Nothing new here.** This is S3/Blob Storage CRUD — the same
> patterns you write in production DE work. But understanding _why_ an AI app needs file storage
> (separate from vector storage) is an important architectural insight.

> **Related docs:**
> - [Documents Endpoint Deep Dive](api-routes/documents-endpoint-explained.md) — the route that calls storage
> - [Chat Endpoint Deep Dive](api-routes/chat-endpoint-explained.md) — the RAG query pipeline (doesn't touch storage)
> - [Conversation History Deep Dive](history-explained.md) — the other "DE-familiar" storage layer
> - [Infrastructure Deep Dive](infra-explained.md) — Terraform that creates these resources
> - [RAG Concepts](../ai-engineering/rag-concepts.md) — chunking, embeddings, vectors explained

---

## Table of Contents

- [Document Storage — Deep Dive](#document-storage--deep-dive)
  - [Table of Contents](#table-of-contents)
  - [What This Module Does](#what-this-module-does)
  - [Why Does a RAG App Need File Storage?](#why-does-a-rag-app-need-file-storage)
  - [The Three Files](#the-three-files)
  - [base.py — The Interface](#basepy--the-interface)
  - [aws\_s3.py — Amazon S3 Implementation](#aws_s3py--amazon-s3-implementation)
    - [How objects are keyed](#how-objects-are-keyed)
    - [What you already know (nothing new)](#what-you-already-know-nothing-new)
    - [The one thing to notice](#the-one-thing-to-notice)
  - [azure\_blob.py — Azure Blob Storage Implementation](#azure_blobpy--azure-blob-storage-implementation)
    - [How blobs are named](#how-blobs-are-named)
    - [Key difference: True async](#key-difference-true-async)
  - [AWS vs Azure — Side-by-Side Comparison](#aws-vs-azure--side-by-side-comparison)
    - [The code patterns side by side](#the-code-patterns-side-by-side)
  - [The Strategy Pattern — Why This Design Matters](#the-strategy-pattern--why-this-design-matters)
  - [How Storage Fits in the RAG Pipeline](#how-storage-fits-in-the-rag-pipeline)
  - [DE vs AI Engineer — What Each Sees](#de-vs-ai-engineer--what-each-sees)
  - [Self-Check Questions](#self-check-questions)
    - [Answers](#answers)

---

## What This Module Does

One sentence: **Stores the original uploaded files (PDFs, text files) so they can be
re-downloaded or deleted later.**

That's it. No AI, no vectors, no embeddings. Pure file storage.

```
User uploads refund-policy.pdf
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  src/storage/                                       │
│                                                     │
│  aws_s3.py        → S3 bucket                       │
│  azure_blob.py    → Blob Storage container          │
│                                                     │
│  Stores raw bytes. Returns metadata (id, size, etc) │
└─────────────────────────────────────────────────────┘
```

---

## Why Does a RAG App Need File Storage?

This is the architectural question a DE should ask. The answer reveals how RAG works:

```
Document uploaded
    │
    ├──→ [1] Raw file → STORAGE (S3 / Blob)         ← this module
    │         Purpose: keep the original for re-download/delete
    │
    └──→ [2] Text → Chunk → Embed → VECTOR STORE    ← src/vectorstore/
              Purpose: enable semantic search
```

**Two copies of the data exist, serving different purposes:**

| What | Where | Format | Purpose |
| --- | --- | --- | --- |
| Original file | S3 / Blob Storage | Raw bytes (PDF, TXT) | Re-download, delete, audit trail |
| Chunks + vectors | OpenSearch / AI Search / ChromaDB | Text + vectors | Semantic search during chat |

**Why not just keep one?** Because:
- You can't reconstruct the original PDF from text chunks (formatting, images lost)
- You can't search by meaning from raw PDF bytes
- Deleting a document requires removing both the file AND its vectors

This is exactly like a data warehouse where you keep raw data in S3 _and_ transformed
data in Redshift — same principle, different technology.

---

## The Three Files

```
src/storage/
├── base.py           # Abstract interface — defines the contract
├── aws_s3.py         # AWS implementation — boto3 S3 client
└── azure_blob.py     # Azure implementation — BlobServiceClient
```

> **📝 Local mode note:** When running with `CLOUD_PROVIDER=local`, document
> storage is not yet backed by a persistent store — uploaded files are processed
> in-memory during ingestion. The chunks and embeddings are stored in ChromaDB.
> Adding a local storage backend (e.g., local filesystem) would follow the same
> `BaseStorage` interface.

---

## base.py — The Interface

```python
@dataclass
class StoredDocument:
    """Metadata about a stored document."""
    document_id: str        # UUID — unique identifier
    filename: str           # Original filename: "refund-policy.pdf"
    content_type: str       # MIME type: "application/pdf"
    size_bytes: int         # File size: 245760
    uploaded_at: datetime   # When it was stored
    storage_path: str       # Provider-specific path: "documents/abc-123/refund-policy.pdf"
```

The `BaseDocumentStorage` abstract class defines four operations:

| Method | What it does | DE equivalent |
| --- | --- | --- |
| `upload()` | Store file, return metadata | `s3.put_object()` or `INSERT INTO files` |
| `download()` | Get file bytes by ID | `s3.get_object()` or `SELECT content FROM files` |
| `delete()` | Remove file by ID | `s3.delete_object()` or `DELETE FROM files` |
| `list_documents()` | List all stored files | `s3.list_objects_v2()` or `SELECT * FROM files` |

**Key design decision:** The interface uses `document_id` (a UUID), not `filename`.
This avoids conflicts when two users upload files with the same name.

---

## aws_s3.py — Amazon S3 Implementation

### How objects are keyed

```
S3 bucket: rag-chatbot-dev-documents
    │
    └── documents/
            ├── abc-123/
            │       └── refund-policy.pdf        ← document_id = "abc-123"
            ├── def-456/
            │       └── shipping-guide.pdf       ← document_id = "def-456"
            └── ghi-789/
                    └── faq.txt                  ← document_id = "ghi-789"
```

Key pattern: `documents/{document_id}/{filename}`

This is a well-known S3 pattern you've seen before:
- One "folder" per document → prefix-based deletion is easy
- `list_objects_v2(Prefix="documents/")` → list all documents
- `delete_objects()` with prefix → clean delete of all versions

### What you already know (nothing new)

```python
# Init — standard boto3 setup
self._s3 = boto3.client("s3", region_name=settings.aws_region)
self._bucket = settings.aws_s3_bucket

# Upload — standard put_object
self._s3.put_object(Bucket=self._bucket, Key=key, Body=content, ContentType=content_type)

# Download — standard get_object
obj = self._s3.get_object(Bucket=self._bucket, Key=key)
return obj["Body"].read()

# Delete — prefix-based batch delete
self._s3.delete_objects(Bucket=self._bucket, Delete={"Objects": objects})

# List — paginated scan
paginator = self._s3.get_paginator("list_objects_v2")
```

### The one thing to notice

The class uses **synchronous** boto3 but the methods are declared `async`. This is a
pragmatic choice — FastAPI runs these in a thread pool automatically. True async would
require `aioboto3`, adding another dependency for minimal benefit in a low-traffic app.

---

## azure_blob.py — Azure Blob Storage Implementation

### How blobs are named

```
Storage account: ragchatbotdevdocs
Container: rag-chatbot-documents
    │
    └── documents/
            ├── abc-123/
            │       └── refund-policy.pdf
            ├── def-456/
            │       └── shipping-guide.pdf
            └── ghi-789/
                    └── faq.txt
```

Same naming pattern as S3 — just different terminology (container vs bucket, blob vs object).

### Key difference: True async

```python
# Azure SDK is natively async
from azure.storage.blob.aio import BlobServiceClient

# Upload — truly async
await blob_client.upload_blob(content, overwrite=True)

# Download — truly async
stream = await blob_client.download_blob()
return await stream.readall()

# Delete — async iteration
async for blob in container.list_blobs(name_starts_with=prefix):
    await blob_client.delete_blob()
```

The Azure SDK uses `aio` (async I/O) — each call is a real `await`, not a thread pool
workaround. For high-traffic apps this matters; for this project, the difference is negligible.

---

## AWS vs Azure — Side-by-Side Comparison

| Aspect | AWS S3 | Azure Blob Storage |
| --- | --- | --- |
| **SDK** | `boto3` (sync) | `azure-storage-blob` (async native) |
| **Container concept** | Bucket | Storage Account → Container |
| **Object path** | `s3://bucket/key` | `container/blob-name` |
| **Authentication** | IAM role / access key | Connection string / managed identity |
| **Upload** | `put_object()` | `upload_blob()` |
| **Download** | `get_object()["Body"].read()` | `download_blob()` → `readall()` |
| **Delete** | `delete_objects()` (batch) | Loop + `delete_blob()` (one by one) |
| **List** | Paginator pattern | `async for` iterator |
| **Encryption** | AES256 / KMS (server-side) | Azure Storage encryption (default on) |
| **Cost (10 GB)** | ~$0.23/month | ~$0.20/month |

### The code patterns side by side

```python
# AWS: Upload
self._s3.put_object(Bucket=self._bucket, Key=key, Body=content)

# Azure: Upload
await blob_client.upload_blob(content, overwrite=True)
```

```python
# AWS: List all documents (paginator)
paginator = self._s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket=self._bucket, Prefix="documents/"):
    for obj in page.get("Contents", []):
        # process obj

# Azure: List all documents (async iterator)
async for blob in container.list_blobs(name_starts_with="documents/"):
    # process blob
```

```python
# AWS: Delete (batch — one API call)
self._s3.delete_objects(Bucket=self._bucket, Delete={"Objects": objects})

# Azure: Delete (loop — one call per blob)
async for blob in container.list_blobs(name_starts_with=prefix):
    await container.get_blob_client(blob.name).delete_blob()
```

---

## The Strategy Pattern — Why This Design Matters

```
┌──────────────────────────┐
│  BaseDocumentStorage     │  ← Abstract interface
│  upload() / download()   │
│  delete() / list()       │
└────────┬─────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────────────┐
│ S3      │ │ Azure Blob       │
│ Storage │ │ Storage          │
└─────────┘ └──────────────────┘
```

This is the **Strategy Pattern** — same interface, swappable implementations. You
know this from standard DE practice (different database backends behind an interface).

**How it's used in the app:**

```python
# In main.py (simplified)
if settings.cloud_provider == "aws":
    app.state.storage = S3DocumentStorage()
elif settings.cloud_provider == "azure":
    app.state.storage = AzureBlobDocumentStorage()

# In routes — doesn't know or care which provider
storage: BaseDocumentStorage = request.app.state.storage
result = await storage.upload(document_id, filename, content, content_type)
```

The route code never imports S3 or Blob — it works with the abstract type. Switching
clouds means changing one config variable, not rewriting routes.

---

## How Storage Fits in the RAG Pipeline

Storage is used in **two** of the three endpoints:

```
POST /api/documents/upload
    │
    ├── [1] storage.upload(file)           ← STORAGE (this module)
    │       Save raw file to S3/Blob
    │
    ├── [2] Parse text from file
    ├── [3] Chunk text into pieces
    ├── [4] Embed chunks into vectors
    └── [5] Store vectors in vector DB     ← VECTOR STORE (different module)

GET /api/documents
    └── storage.list_documents()           ← STORAGE (this module)

DELETE /api/documents/{id}
    ├── storage.delete(id)                 ← STORAGE (this module)
    └── vectorstore.delete(id)             ← VECTOR STORE (different module)

POST /api/chat
    └── Does NOT use storage at all
        (Uses vector store to search, never touches raw files)
```

**Key insight:** The chat endpoint never touches file storage. It only needs the
vector store — the chunks + embeddings created during ingestion.

---

## DE vs AI Engineer — What Each Sees

| Aspect | What a DE sees | What an AI Engineer sees |
| --- | --- | --- |
| `StoredDocument` model | Standard metadata DTO | Audit trail for data lineage |
| `upload()` | S3 put_object, nothing new | Source-of-truth for re-ingestion if chunking strategy changes |
| `list_documents()` | Paginated list, standard | Knowledge base inventory — what data has the LLM seen? |
| `delete()` | Prefix delete, standard | Must delete from BOTH storage AND vector store, or orphan vectors remain |
| Strategy pattern | Clean architecture | Essential for multi-cloud — can't hardcode providers in AI apps |

---

## Self-Check Questions

Test your understanding:

1. **Why does the RAG app store files in S3 AND vectors in OpenSearch?** Why not just one?
2. **What happens if you delete a file from S3 but NOT from the vector store?** What does the chat endpoint return?
3. **What happens if two users upload different files both named "report.pdf"?** How does the system handle this?
4. **Why is `document_id` a UUID and not the filename?**
5. **The AWS implementation uses sync boto3 with `async def` methods. Why does this work?**
6. **If you needed to add Google Cloud Storage support, what would you create?** (Hint: look at the strategy pattern)

### Answers

1. S3 stores the _original file_ (for re-download/delete). Vector store stores _chunks + vectors_ (for semantic search). Different formats, different purposes — like raw zone + Redshift in a data warehouse.
2. The chat endpoint still returns answers citing that document (stale vectors). This is a bug — deletion must be atomic across both stores.
3. Each file gets a unique `document_id` (UUID). Two "report.pdf" files get different IDs, different S3 keys, no conflict.
4. UUIDs prevent filename collisions and ensure globally unique references across the system.
5. FastAPI detects that the underlying code is synchronous and runs it in a thread pool via `asyncio.run_in_executor()`. The `async def` lets it integrate with FastAPI's async router.
6. Create `src/storage/gcp_gcs.py` implementing `BaseDocumentStorage`. No changes to routes needed — just add a new provider option in `main.py`.
