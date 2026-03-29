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
- [Model 7: DocumentInfo](#model-7-documentinfo)
- [Model 8: DocumentListResponse](#model-8-documentlistresponse)
- [Model 9: HealthResponse](#model-9-healthresponse)
- [Model 10: ServiceHealth](#model-10-servicehealth)
- [Model 11: ErrorResponse](#model-11-errorresponse)
- [Pydantic patterns used in this project](#pydantic-patterns-used-in-this-project)
- [How FastAPI uses Pydantic](#how-fastapi-uses-pydantic)

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

---

## How Pydantic is used in this project

Pydantic models appear in **three roles**:

| Role | Example | What it does |
| --- | --- | --- |
| **Request model** | `ChatRequest` | Validates incoming JSON from the client |
| **Response model** | `ChatResponse` | Defines the shape of the JSON we return |
| **Settings model** | `Settings` | Reads and validates environment variables |

When FastAPI sees `def chat(body: ChatRequest)`:
1. It reads the raw JSON from the HTTP request body
2. It creates a `ChatRequest` object (running all validators)
3. If validation fails → automatic 422 response with details
4. If validation passes → your function receives a clean, typed object

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

| Field | Type | Default | Env Variable | Purpose |
| --- | --- | --- | --- | --- |
| `cloud_provider` | `CloudProvider` | `aws` | `CLOUD_PROVIDER` | Controls which cloud backends to use |
| `app_name` | `str` | `rag-chatbot` | `APP_NAME` | Service name in logs |
| `app_env` | `AppEnvironment` | `dev` | `APP_ENV` | Environment (affects logging) |
| `app_port` | `int` | `8000` | `APP_PORT` | Server port |
| `log_level` | `str` | `INFO` | `LOG_LEVEL` | Logging verbosity |
| `rag_top_k` | `int` | `5` | `RAG_TOP_K` | Chunks retrieved per query |
| `rag_chunk_size` | `int` | `1000` | `RAG_CHUNK_SIZE` | Max characters per chunk |
| `rag_chunk_overlap` | `int` | `200` | `RAG_CHUNK_OVERLAP` | Overlap between chunks |
| `aws_region` | `str` | `eu-central-1` | `AWS_REGION` | AWS region |
| `aws_bedrock_model_id` | `str` | Claude 3.5 Sonnet | `AWS_BEDROCK_MODEL_ID` | Bedrock model |
| `aws_opensearch_endpoint` | `str` | `""` | `AWS_OPENSEARCH_ENDPOINT` | OpenSearch URL |
| `aws_s3_bucket_name` | `str` | `rag-chatbot-documents` | `AWS_S3_BUCKET_NAME` | S3 bucket |
| `aws_dynamodb_table_name` | `str` | `rag-chatbot-conversations` | `AWS_DYNAMODB_TABLE_NAME` | DynamoDB table |
| `azure_openai_endpoint` | `str` | `""` | `AZURE_OPENAI_ENDPOINT` | Azure OpenAI URL |
| `azure_openai_api_key` | `str` | `""` | `AZURE_OPENAI_API_KEY` | Azure OpenAI key |
| `azure_openai_deployment_name` | `str` | `gpt-4o` | `AZURE_OPENAI_DEPLOYMENT_NAME` | Model deployment |
| `azure_search_endpoint` | `str` | `""` | `AZURE_SEARCH_ENDPOINT` | AI Search URL |
| `azure_search_api_key` | `str` | `""` | `AZURE_SEARCH_API_KEY` | AI Search key |
| `enable_tracing` | `bool` | `False` | `ENABLE_TRACING` | OpenTelemetry tracing |

**How it works:**

```python
settings = get_settings()
# → reads .env file
# → reads environment variables (overrides .env)
# → validates every field
# → returns a typed Settings object

settings.cloud_provider  # → CloudProvider.AWS
settings.app_port        # → 8000
settings.rag_top_k       # → 5
```

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

| Field | Type | Required? | Validation | Purpose |
| --- | --- | --- | --- | --- |
| `question` | `str` | **Yes** | 1–5000 chars | The user's question |
| `session_id` | `str` or `None` | No | None | Links follow-up questions together |
| `top_k` | `int` or `None` | No | 1–20 if provided | Override default chunk count |

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

| Field | Type | Purpose |
| --- | --- | --- |
| `answer` | `str` | The AI-generated answer |
| `sources` | `list[SourceChunk]` | Which document chunks were used (citations) |
| `session_id` | `str` | Session ID for follow-up questions |
| `request_id` | `UUID` | Unique ID for debugging/tracing |
| `cloud_provider` | `CloudProvider` | Which cloud processed this request |
| `latency_ms` | `int` | Total processing time |
| `token_usage` | `TokenUsage` or `None` | Token counts for cost tracking |

---

## Model 4: SourceChunk

**What it is:** A single piece of evidence that the LLM used. This is what makes RAG transparent.

| Field | Type | Purpose |
| --- | --- | --- |
| `document_name` | `str` | Which file this chunk came from |
| `chunk_text` | `str` | The actual text content |
| `relevance_score` | `float` (0.0–1.0) | How similar to the question (1.0 = perfect) |
| `page_number` | `int` or `None` | Page in original PDF |

---

## Model 5: TokenUsage

**What it is:** How many tokens the LLM consumed. Critical for cost tracking.

| Field | Type | Purpose |
| --- | --- | --- |
| `input_tokens` | `int` | Tokens in the prompt (question + context) |
| `output_tokens` | `int` | Tokens in the generated answer |
| `total_tokens` | `int` | Sum of input + output |
| `estimated_cost_usd` | `float` | Estimated cost based on model pricing |

**Why this matters:**

LLM APIs charge per token. A token is roughly 4 characters or 0.75 words.

Example cost calculation (Claude 3.5 Sonnet):
- Question + context = 2000 input tokens × $0.003/1K = $0.006
- Generated answer = 500 output tokens × $0.015/1K = $0.0075
- Total per query = **$0.0135**
- 100 queries/day = **$1.35/day**

---

## Model 6: DocumentUploadResponse

**What it is:** Returned after uploading a document.

| Field | Type | Purpose |
| --- | --- | --- |
| `document_id` | `str` | Unique ID for this document |
| `filename` | `str` | Original filename |
| `status` | `DocumentStatus` | pending / processing / ready / failed |
| `chunk_count` | `int` | How many searchable chunks were created |
| `message` | `str` | Human-readable status |

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

cloud_provider: CloudProvider  # Only accepts "aws" or "azure"
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
