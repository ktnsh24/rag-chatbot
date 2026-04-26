# Pydantic Models Guide — Every Model Explained

## Table of Contents

- [What is Pydantic?](#what-is-pydantic)
- [How Pydantic is used in this project](#how-pydantic-is-used-in-this-project)
- [Model 1: Settings (config.py)](#model-1-settings-configpy)
- [Model 2: ChatRequest](#model-2-chatrequest)
- [Model 3: ChatResponse](#model-3-chatresponse)
- [Model 4: SourceChunk](#model-4-sourcechunk)
- [Model 5: TokenUsage](#model-5-tokenusage)
- [Model 6: DocumentUploadResponse](#model-6-documentuploadresponse)
- [Pydantic patterns used in this project](#pydantic-patterns-used-in-this-project)
- [How FastAPI uses Pydantic](#how-fastapi-uses-pydantic)

> 📖 **Want to see how these models are used in the actual routes?** Each route has
> its own deep dive showing exactly where each model is constructed and returned:
> [Health](../architecture-and-design/api-routes/health-endpoint-explained.md) (`HealthResponse`, `ServiceHealth`) ·
> [Chat](../architecture-and-design/api-routes/chat-endpoint-explained.md) (`ChatRequest`, `ChatResponse`, `Source`) ·
> [Documents](../architecture-and-design/api-routes/documents-endpoint-explained.md) (`DocumentUploadResponse`, `DocumentInfo`) ·
> [Evaluate](../architecture-and-design/api-routes/evaluate-endpoint-explained.md) (`EvaluateSingleRequest`, `EvaluateSuiteResponse`, `EvaluationScoreDetail`) ·
> Queries (`QueryLogRecord`) · Metrics (Prometheus text output).
> See the [Overview](../architecture-and-design/api-routes-explained.md) for how they all fit together.

---

## What is Pydantic?

Pydantic is a **data validation library** for Python. It uses Python type hints to:

1. **Validate data** — check that values are the right type, within range, not empty
2. **Parse data** — convert raw JSON/dict into typed Python objects
3. **Serialize data** — convert Python objects back to JSON/dict
4. **Document data** — auto-generate API schemas (used by Swagger UI)

### Without Pydantic

```python
# You get a raw dict — no validation, no autocomplete
def chat(body: dict):
    question = body.get("question")  # Could be None, could be int, could be anything
    if not question:
        raise ValueError("question is required")
    if not isinstance(question, str):
        raise TypeError("question must be a string")
    if len(question) > 5000:
        raise ValueError("question too long")
```

### With Pydantic

```python
# Pydantic validates everything automatically
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)

def chat(body: ChatRequest):
    # body.question is guaranteed to be a non-empty string <= 5000 chars
    # If validation fails, FastAPI returns 422 with a clear error message
    print(body.question)  # Safe — always a valid string
```

- 🚚 **Courier:** The shipping manifest template — every field is typed and validated before the courier is loaded, preventing mispackaged deliveries.

---

## How Pydantic is used in this project

Pydantic models appear in **three roles**:

| Role | Example | What it does | 🚚 Courier |
| --- | --- | --- | --- |
| **Request model** | `ChatRequest` | Validates incoming JSON from the client | ChatRequest is the shipping manifest the customer hands in — Pydantic checks it's filled out before any courier leaves. |
| **Response model** | `ChatResponse` | Defines the shape of the JSON we return | ChatResponse is the signed receipt the courier hands back — same fields every time so customers know what to expect. |
| **Settings model** | `Settings` | Reads and validates environment variables | Settings is the depot's shipping manifest — read once at boot, validated, then every courier trots to the same rules. |

When FastAPI sees `def chat(body: ChatRequest)`:
1. It reads the raw JSON from the HTTP request body
2. It creates a `ChatRequest` object (running all validators)
3. If validation fails → automatic 422 response with details
4. If validation passes → your function receives a clean, typed object

- 🚚 **Courier:** The shipping manifest template — every field is typed and validated before the courier is loaded, preventing mispackaged deliveries.

---

## Model 1: Settings (config.py)

**File:** `src/config.py`

```python
class Settings(BaseSettings):
```

**What it is:** The central configuration object. Reads ALL settings from environment variables or `.env` file.

**Why BaseSettings instead of BaseModel?**
- `BaseModel` only accepts data you pass explicitly
- `BaseSettings` automatically reads from environment variables

| Field | Type | Default | Env Variable | Purpose | 🚚 Courier |
| --- | --- | --- | --- | --- | --- |
| `cloud_provider` | `CloudProvider` | `local` | `CLOUD_PROVIDER` | Controls which cloud backends to use | Picks which barn — local fuel shed or AWS/Azure depot — handles the courier's deliveries. |
| `app_name` | `str` | `rag-chatbot` | `APP_NAME` | Service name in logs | Courier's trip log — every delivery's details written to disk for later review |
| `app_env` | `AppEnvironment` | `dev` | `APP_ENV` | Environment (affects logging) | Depot gate guard — app_env: AppEnvironment · dev · APP_ENV · Environment (affects logging) |
| `app_port` | `int` | `8000` | `APP_PORT` | Server port | Courier-side view of app_port — affects how the courier loads, reads, or delivers the parcels |
| `log_level` | `str` | `INFO` | `LOG_LEVEL` | Logging verbosity | Depot gate guard — log_level: str · INFO · LOG_LEVEL · Logging verbosity |
| `rag_top_k` | `int` | `5` | `RAG_TOP_K` | Chunks retrieved per query | Sets how many parcel pockets the courier grabs per delivery — five chunks fetched each query. |
| `rag_chunk_size` | `int` | `1000` | `RAG_CHUNK_SIZE` | Max characters per chunk | Caps each parcel pocket at 1000 characters so no single chunk overstuffs the courier's load. |
| `rag_chunk_overlap` | `int` | `200` | `RAG_CHUNK_OVERLAP` | Overlap between chunks | Sews 200 characters of overlap between adjacent parcel pockets so the courier never loses context at the edges. |
| `aws_region` | `str` | `eu-central-1` | `AWS_REGION` | AWS region | Amazon's loading dock — aws_region: str · eu-central-1 · AWS_REGION · AWS region |
| `aws_bedrock_model_id` | `str` | Claude 3.5 Sonnet | `AWS_BEDROCK_MODEL_ID` | Bedrock model | Which AWS-depot courier breed shows up to write the answer |
| `aws_opensearch_endpoint` | `str` | `""` | `AWS_OPENSEARCH_ENDPOINT` | OpenSearch URL | AWS search hub — aws_opensearch_endpoint: str · "" · AWS_OPENSEARCH_ENDPOINT · OpenSearch URL |
| `aws_s3_bucket_name` | `str` | `rag-chatbot-documents` | `AWS_S3_BUCKET_NAME` | S3 bucket | The AWS warehouse name where source documents are uploaded for the courier to fetch |
| `aws_dynamodb_table_name` | `str` | `rag-chatbot-conversations` | `AWS_DYNAMODB_TABLE_NAME` | DynamoDB table (history) | Amazon's loading dock — aws_dynamodb_table_name: str · rag-chatbot-conversations · AWS_DYNAMODB_TABLE_NAME · DynamoDB table (history) |
| `aws_dynamodb_vector_table_name` | `str` | `rag-chatbot-vectors` | `AWS_DYNAMODB_VECTOR_TABLE_NAME` | DynamoDB table (vector store — cheap alternative to OpenSearch) | OpenSearch sorting office — aws_dynamodb_vector_table_name: str · rag-chatbot-vectors · AWS_DYNAMODB_VECTOR_TABLE_NAME · DynamoDB table (vector store — cheap alternative to OpenSearch) |
| `vector_store_type` | `VectorStoreType` | `auto` | `VECTOR_STORE_TYPE` | Override vector store: `auto` (default for provider) or `dynamodb` ($0/month) | AWS depot — vector_store_type: VectorStoreType · auto · VECTOR_STORE_TYPE · Override vector store: auto (default for provider) or dynamodb ($0/month) |
| `azure_openai_endpoint` | `str` | `""` | `AZURE_OPENAI_ENDPOINT` | Azure OpenAI URL | The street address of the Azure-hub depot where the courier reports for work |
| `azure_openai_api_key` | `str` | `""` | `AZURE_OPENAI_API_KEY` | Azure OpenAI key | The depot-gate password that lets you summon the Azure-hub courier |
| `azure_openai_deployment_name` | `str` | `gpt-4o` | `AZURE_OPENAI_DEPLOYMENT_NAME` | Model deployment | Which specific Azure-hub courier (by name) gets dispatched for each delivery |
| `azure_search_endpoint` | `str` | `""` | `AZURE_SEARCH_ENDPOINT` | AI Search URL | URL of the Azure hub where the courier looks up GPS coordinates during retrieval. |
| `azure_search_api_key` | `str` | `""` | `AZURE_SEARCH_API_KEY` | AI Search key | Secret key the courier shows at the Azure hub gate before it can run vector queries. |
| `ollama_base_url` | `str` | `http://localhost:11434` | `OLLAMA_BASE_URL` | Ollama REST API URL | Front-door address of the local barn where the laptop courier lives |
| `ollama_model` | `str` | `llama3.2` | `OLLAMA_MODEL` | Ollama chat model | Which local barn courier breed writes the answers on your laptop |
| `ollama_embedding_model` | `str` | `nomic-embed-text` | `OLLAMA_EMBEDDING_MODEL` | Ollama embedding model | The local barn worker that converts text into GPS coordinates for warehouse storage |
| `chroma_collection_name` | `str` | `rag-chatbot` | `CHROMA_COLLECTION_NAME` | ChromaDB collection | Name of the stall inside the local barn where ChromaDB keeps this project's chunk vectors. |
| `chroma_persist_directory` | `str` | `""` | `CHROMA_PERSIST_DIRECTORY` | ChromaDB storage path (empty = in-memory) | Folder on disk where the local barn stores chunks; empty means the courier forgets after restart. |
| `enable_tracing` | `bool` | `False` | `ENABLE_TRACING` | OpenTelemetry tracing | Tachograph reading — recorded on every courier trip and shown on the dashboard |
| `query_log_enabled` | `bool` | `True` | `QUERY_LOG_ENABLED` | Structured per-query JSONL logging (I30) | Depot gate guard — query_log_enabled: bool · True · QUERY_LOG_ENABLED · Structured per-query JSONL logging (I30) |
| `query_log_dir` | `str` | `logs/queries` | `QUERY_LOG_DIR` | Directory for daily JSONL log files | Courier's trip log — every delivery's details written to disk for later review |

**How it works:**

```python
settings = get_settings()
# → reads .env file
# → reads environment variables (overrides .env)
# → validates every field
# → returns a typed Settings object

settings.cloud_provider  # → CloudProvider.LOCAL
settings.app_port        # → 8000
settings.rag_top_k       # → 5
```

- 🚚 **Courier:** Adjusting the bag fit and route preferences so the courier delivers to the right address every time.

---

## Model 2: ChatRequest

**File:** `src/api/models.py`

```python
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    session_id: str | None = Field(default=None)
    top_k: int | None = Field(default=None, ge=1, le=20)
```

**What it is:** The JSON body sent by the client to `POST /api/chat`.

| Field | Type | Required? | Validation | Purpose | 🚚 Courier |
| --- | --- | --- | --- | --- | --- |
| `question` | `str` | **Yes** | 1–5000 chars | The user's question | Depot broke down — courier couldn't complete the trip, customer sees an error |
| `session_id` | `str` or `None` | No | None | Links follow-up questions together | Line scribbled in the trip ledger — session_id: str or None · No · None · Links follow-up questions together |
| `top_k` | `int` or `None` | No | 1–20 if provided | Override default chunk count | Per-request override telling the courier to grab between 1 and 20 parcel pockets instead of the default. |

**What happens on invalid input:**

```json
// Request with empty question:
{"question": ""}

// FastAPI returns 422:
{
  "detail": [{
    "type": "string_too_short",
    "loc": ["body", "question"],
    "msg": "String should have at least 1 character",
    "ctx": {"min_length": 1}
  }]
}
```

- 🚚 **Courier:** The shipping manifest template — every field is typed and validated before the courier is loaded, preventing mispackaged deliveries.

---

## Model 3: ChatResponse

**File:** `src/api/models.py`

```python
class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    session_id: str
    request_id: UUID
    cloud_provider: CloudProvider
    latency_ms: int
    token_usage: TokenUsage | None
```

**What it is:** The JSON returned to the client after a chat query.

| Field | Type | Purpose | 🚚 Courier |
| --- | --- | --- | --- |
| `answer` | `str` | The AI-generated answer | What the courier wrote and brought back to the customer |
| `sources` | `list[SourceChunk]` | Which document chunks were used (citations) | List of parcel pockets the courier actually used as citations when writing the answer. |
| `session_id` | `str` | Session ID for follow-up questions | Trip log entry — session_id: str · Session ID for follow-up questions |
| `request_id` | `UUID` | Unique ID for debugging/tracing | Tracking number stamped on every courier trip — quote it to find this exact delivery in the logs |
| `cloud_provider` | `CloudProvider` | Which cloud processed this request | Courier-side view of cloud_provider — affects how the courier loads, reads, or delivers the parcels |
| `latency_ms` | `int` | Total processing time | Depot's monthly feed bill — latency_ms: int · Total processing time |
| `token_usage` | `TokenUsage` or `None` | Token counts for cost tracking | Tachograph reading of how much fuel the courier burned producing this answer, used for cost tracking. |

- 🚚 **Courier:** The shipping manifest template — every field is typed and validated before the courier is loaded, preventing mispackaged deliveries.

---

## Model 4: SourceChunk

**What it is:** A single piece of evidence that the LLM used. This is what makes RAG transparent.

| Field | Type | Purpose | 🚚 Courier |
| --- | --- | --- | --- |
| `document_name` | `str` | Which file this chunk came from | Label on the parcel pocket showing which original document this chunk was torn from. |
| `chunk_text` | `str` | The actual text content | The actual fuel inside the parcel pocket — raw text the courier reads when composing answers. |
| `relevance_score` | `float` (0.0–1.0) | How similar to the question (1.0 = perfect) | Routing tag on the parcel — relevance_score: float (0.0–1.0) · How similar to the question (1.0 = perfect) |
| `page_number` | `int` or `None` | Page in original PDF | Which page of the original mail the parcel came from |

- 🚚 **Courier:** parcel-sized pieces of parcels with overlapping edges, so no sentence is cut off at a seam.

---

## Model 5: TokenUsage

**What it is:** How many tokens the LLM consumed. Critical for cost tracking.

| Field | Type | Purpose | 🚚 Courier |
| --- | --- | --- | --- |
| `input_tokens` | `int` | Tokens in the prompt (question + context) | Fuel loaded into the courier on the way in — the question plus retrieved context. |
| `output_tokens` | `int` | Tokens in the generated answer | Fuel burned by the courier on the way out — every token in the generated answer. |
| `total_tokens` | `int` | Sum of input + output | Combined fuel tally of input plus output, used to compute the trip's full delivery cost. |
| `estimated_cost_usd` | `float` | Estimated cost based on model pricing | What this trip cost in fuel — printed on the receipt so the depot owner can tally up the month. |

**Why this matters:**

LLM APIs charge per token. A token is roughly 4 characters or 0.75 words.

Example cost calculation (Claude 3.5 Sonnet):
- Question + context = 2000 input tokens × $0.003/1K = $0.006
- Generated answer = 500 output tokens × $0.015/1K = $0.0075
- Total per query = **$0.0135**
- 100 queries/day = **$1.35/day**

- 🚚 **Courier:** The shipping manifest template — every field is typed and validated before the courier is loaded, preventing mispackaged deliveries.

---

## Model 6: DocumentUploadResponse

**What it is:** Returned after uploading a document.

| Field | Type | Purpose | 🚚 Courier |
| --- | --- | --- | --- |
| `document_id` | `str` | Unique ID for this document | Courier-side view of document_id — affects how the courier loads, reads, or delivers the parcels |
| `filename` | `str` | Original filename | Label on the original mail item the parcel was sliced from |
| `status` | `DocumentStatus` | pending / processing / ready / failed | Where this parcel is in the post-office flow — queued, being sorted, shelved and ready, or rejected |
| `chunk_count` | `int` | How many searchable chunks were created | Number of parcel pockets the post office sliced this document into during ingestion. |
| `message` | `str` | Human-readable status | Courier-side view of message — affects how the courier loads, reads, or delivers the parcels |

- 🚚 **Courier:** The parcels being ingested — split into parcel-sized chunks, GPS-stamped, and shelved in the warehouse for the courier to retrieve later.

---

## Pydantic patterns used in this project

### Pattern 1: Field with validation

```python
question: str = Field(..., min_length=1, max_length=5000)
```

The `...` means required. `Field()` adds validation rules.

### Pattern 2: Optional fields with defaults

```python
session_id: str | None = Field(default=None)
```

`str | None` means "string or None". Python 3.10+ syntax.

### Pattern 3: Enum validation

```python
class CloudProvider(str, Enum):
    AWS = "aws"
    AZURE = "azure"
    LOCAL = "local"

cloud_provider: CloudProvider  # Accepts "aws", "azure", or "local"
```

### Pattern 4: Forward references

```python
token_usage: "TokenUsage | None"  # Quoted because TokenUsage is defined later
ChatResponse.model_rebuild()      # Resolves the forward reference
```

### Pattern 5: BaseSettings for config

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    app_port: int = Field(default=8000)
    # Reads APP_PORT from env, falls back to 8000
```

- 🚚 **Courier:** The shipping manifest template — every field is typed and validated before the courier is loaded, preventing mispackaged deliveries.

---

## How FastAPI uses Pydantic

FastAPI and Pydantic are deeply integrated:

1. **Request validation**: `def chat(body: ChatRequest)` — FastAPI deserializes JSON → ChatRequest
2. **Response serialization**: `response_model=ChatResponse` — FastAPI serializes ChatResponse → JSON
3. **API documentation**: Pydantic models auto-generate OpenAPI/Swagger schemas
4. **Error responses**: Validation errors return structured 422 responses

This means you get:
- Auto-generated Swagger UI at `/docs`
- Automatic request validation
- Automatic response serialization
- Type-safe code (your IDE knows every field)

- 🚚 **Courier:** The depot's front door — defined entry points where questions arrive and answers depart.
