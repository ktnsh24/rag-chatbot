# 🎯 30-Day AI Engineering Learning Plan

> **Goal:** Learn AI engineering theory AND understand every line of the RAG chatbot code.
> **Time:** ~2 hours per day (1h theory + 1h code).
> **Approach:** Each day's theory directly maps to specific code files and line numbers.

---

## How to Use This Plan

Every day has 4 parts:

| Part | Time | What |
|---|---|---|
| 📖 **Read** | 30 min | Theory section from the docs |
| 💻 **Study** | 30 min | Specific code file with line numbers to focus on |
| ✏️ **Exercise** | 20 min | Small hands-on task to cement the learning |
| 📝 **Write** | 10 min | One-paragraph summary in your own words |

**Rule:** Don't skip the exercise. Reading without doing = forgetting within 48 hours.

---

## WEEK 1 — What Is an LLM and How Does It Work?

### Day 1 (Tue): What Is a Language Model?

**📖 Read:** `docs/ai-theory-roadmap.md` → Chapter 1, Section 1.1 "What Is an LLM?"
- Focus on: What is a transformer, what is attention, what is a token
- Key concept: An LLM takes in a sequence of tokens and predicts the next token

**💻 Study:** `src/llm/base.py` (96 lines — read ALL of it)
- Line 20-37: `LLMResponse` dataclass — see `input_tokens`, `output_tokens`. These are the tokens from the theory
- Line 39-51: `BaseLLM` — abstract class. Two methods: `generate()` and `get_embedding()`
- Line 52-62: `generate()` signature — `prompt: str, context: list[str], temperature: float`
  - `prompt` = the user's question (which gets tokenized into tokens)
  - `context` = document chunks (also tokenized)
  - `temperature` = controls randomness (0.0 = deterministic, 1.0 = creative)

**✏️ Exercise:** Write down answers to:
1. If Claude 3.5 Sonnet has a 200K token context window and 1 token ≈ 4 characters, how many characters fit in one prompt?
2. Why does `generate()` take `context: list[str]` separately from `prompt`? (Hint: look at how it's used in `chain.py` line 186-190)
3. Why does `LLMResponse` track `input_tokens` and `output_tokens` separately? (Hint: they have different prices)

**📝 Write:** In your own words, what is an LLM and what are tokens?

---

### Day 2 (Wed): How Bedrock Calls the LLM

**📖 Read:** `docs/ai-theory-roadmap.md` → Chapter 1, Section 1.2 "Transformer Architecture"
- Focus on: self-attention mechanism (don't memorize the math — understand the intuition)
- Key concept: attention lets the model focus on relevant parts of the input

**💻 Study:** `src/llm/aws_bedrock.py` (read ALL — ~130 lines)
- Constructor: see `model_id`, `region` — these configure WHICH model on WHICH endpoint
- `generate()` method: see how it builds the API request to Bedrock
  - `messages` list with `role` and `content` — this is the chat format
  - `system` prompt — the RAG instructions (from `prompts.py`)
  - `max_tokens` — limits how long the response can be
  - The response parsing — extracting `text`, `input_tokens`, `output_tokens`
- `get_embedding()` method: see how it calls the Titan embedding model
  - Different model ID for embeddings vs text generation
  - Returns a `list[float]` — this is the vector

**✏️ Exercise:**
1. Find the line where the system prompt is set. What does it tell the LLM to do?
2. Find where `temperature` is passed. What happens if you set it to 0.0? What about 1.0?
3. Find the embedding call. What model does it use? How many dimensions does the vector have?

**📝 Write:** Explain how a Python application sends a question to Bedrock and gets back an answer.

---

### Day 3 (Thu): Azure OpenAI — Same Interface, Different Cloud

**📖 Read:** `docs/ai-theory-roadmap.md` → Chapter 1, Section 1.3 "Key LLM Parameters"
- Focus on: temperature, top_p, max_tokens, stop sequences
- Key concept: same concepts apply to ALL LLM providers

**💻 Study:** `src/llm/azure_openai.py` (read ALL — ~130 lines)
- Compare with `aws_bedrock.py` side-by-side:
  - Same methods: `generate()`, `get_embedding()`, `get_embeddings_batch()`
  - Different SDK: `openai` client vs `boto3` client
  - Different model names: `gpt-4o` vs `claude-3.5-sonnet`
  - Same return type: `LLMResponse`

**✏️ Exercise:**
1. Open both files side-by-side. List 3 things that are IDENTICAL and 3 things that are DIFFERENT
2. If you wanted to add Google Gemini support, what would you need to create? (Hint: just a new file implementing `BaseLLM`)
3. Why is `embedding_deployment` a separate parameter from the main model `deployment_name`?

**📝 Write:** Explain the Strategy Pattern using these two files as an example. Why is it useful?

---

### Day 4 (Fri): Embeddings — Turning Text into Numbers

**📖 Read:** `docs/ai-theory-roadmap.md` → Chapter 2 "Embeddings and Vector Representations" (Sections 2.1-2.3)
- Focus on: what is an embedding, what is a vector, what is cosine similarity
- Key concept: similar meanings → similar vectors → close in space

**💻 Study:** `src/vectorstore/base.py` (103 lines — read ALL)
- Line 8-20: `SearchResult` dataclass — see `text`, `score`, `document_name`
  - `score` = cosine similarity (0 to 1) — this IS the math from the theory
- Line 22+: `BaseVectorStore` abstract class
  - `store_vectors()` — takes text chunks + their embedding vectors, stores them
  - `search()` — takes a query embedding, finds the top_k nearest stored vectors
  - `delete_document()` — removes all vectors for a document

**✏️ Exercise:**
1. The `SearchResult` has a `score` field. If score = 0.95, what does that mean? What about 0.12?
2. In `store_vectors()`, why do we pass BOTH `texts` and `embeddings`? Why not just embeddings?
3. Draw this on paper: 3 document chunks as dots in 2D space. Then a question as a dot. Draw an arrow from the question to the nearest chunk. That arrow IS vector search.

**📝 Write:** Explain embeddings to a non-technical person. Use an analogy (e.g., GPS coordinates for meaning).

---

### Day 5 (Sat/Mon): Vector Search in Practice — OpenSearch

**📖 Read:** `docs/how-services-work.md` → "OpenSearch Serverless" section
- Focus on: how k-NN (k-Nearest Neighbors) search works
- Key concept: the vector database runs cosine similarity at scale (millions of vectors, milliseconds)

**💻 Study:** `src/vectorstore/aws_opensearch.py` (164 lines — read ALL)
- Constructor: `endpoint`, `index_name`, `region` — connects to the OpenSearch cluster
- `store_vectors()`: see how it builds the document with both the `text` field AND the `embedding` field
- `search()`: this is the KEY method:
  - It takes `query_embedding` (the question as a vector)
  - Builds a k-NN query: "find me the `top_k` vectors closest to this one"
  - Returns `SearchResult` objects with `score` (cosine similarity)

**✏️ Exercise:**
1. Find the k-NN query in the `search()` method. What parameters does it set?
2. If `top_k=5`, how many chunks come back? Why not return ALL chunks?
3. Compare `aws_opensearch.py` with `azure_ai_search.py` — same interface, different vendor. List the differences.

**📝 Write:** Explain the full embedding pipeline: text → embedding → store → query → retrieve.

---

## WEEK 2 — The RAG Pattern (Core of the Project)

### Day 6: Document Ingestion — Read, Chunk, Embed, Store

**📖 Read:** `docs/rag-concepts.md` (336 lines — read ALL)
- Focus on: what is chunking, why overlap matters, the chunk size formula
- Key formula: `chunks ≈ (doc_length - overlap) / (chunk_size - overlap)`

**💻 Study:** `src/rag/ingestion.py` (112 lines — read ALL)
- Line 29-54: `read_document()` — dispatcher based on file extension (.pdf, .txt, .md, .docx)
- Line 57-69: `_read_pdf()` — uses `pypdf` to extract text page by page
- Line 79-112: `chunk_document()` — THE chunking function
  - `RecursiveCharacterTextSplitter` — splits on `\n\n` → `\n` → `. ` → ` ` → `""`
  - `chunk_size=1000` — max 1000 characters per chunk
  - `chunk_overlap=200` — 200 characters overlap between chunks
  - The overlap ensures no sentence is cut in half

**✏️ Exercise:**
1. Calculate: a 50,000 character document with chunk_size=1000 and overlap=200 → how many chunks?
2. Why does the splitter try `\n\n` first, then `\n`, then `. `? What's the logic?
3. What happens if you set `chunk_overlap=0`? What information might you lose?
4. What happens if you set `chunk_size=5000`? Bigger chunks → what tradeoff?

**📝 Write:** Explain the chunking tradeoff: small chunks = precise but may miss context, large chunks = more context but less precise.

---

### Day 7: Prompts — The Instructions That Control the LLM

**📖 Read:** `docs/ai-theory-roadmap.md` → Chapter 3 "Prompt Engineering"
- Focus on: system prompts, user prompts, few-shot examples, chain-of-thought
- Key concept: the prompt IS the program — how you write it determines the quality of answers

**💻 Study:** `src/rag/prompts.py` (60 lines — read ALL, every word matters)
- `RAG_SYSTEM_PROMPT` — this tells the LLM:
  - You are a helpful assistant
  - Use ONLY the provided context to answer
  - If the context doesn't contain the answer, say "I don't know"
  - Cite your sources
- `RAG_CONVERSATIONAL_PROMPT` — adds conversation history handling
- `SUMMARIZE_PROMPT` — for document summarization

**✏️ Exercise:**
1. Read `RAG_SYSTEM_PROMPT`. What happens if you remove the line "If the context doesn't contain the answer, say I don't know"? (Hint: hallucination)
2. Write an ALTERNATIVE system prompt that is more strict (e.g., "Only respond with bullet points")
3. Write a system prompt for a different use case: a customer support bot that can ONLY answer questions about returns and refunds
4. Why is the system prompt SEPARATE from the user's question? (Hint: look at how `generate()` uses them in `aws_bedrock.py`)

**📝 Write:** Explain why prompts are the most important part of a RAG system — more important than the model choice.

---

### Day 8: The RAG Chain — How Everything Connects

**📖 Read:** `docs/architecture.md` (207 lines — read ALL)
- Focus on: the data flow diagram
- Key concept: RAGChain is the orchestrator that ties LLM + VectorStore + Ingestion together

**💻 Study:** `src/rag/chain.py` (232 lines — read ALL, this is the heart of the project)
- Line 24-38: Class + constructor — takes `BaseLLM` and `BaseVectorStore` (abstractions!)
- Line 43-61: `create()` factory method — reads `CLOUD_PROVIDER` env var, builds the right backends
- Line 104-141: `ingest_document()` — the 4-step pipeline:
  1. `read_document()` → raw text (ingestion.py)
  2. `chunk_document()` → list of chunks (ingestion.py)
  3. `get_embeddings_batch()` → list of vectors (llm)
  4. `store_vectors()` → saved to database (vectorstore)
- Line 143-212: `query()` — the 5-step pipeline:
  1. `get_embedding(question)` → query vector
  2. `search(query_embedding, top_k)` → relevant chunks
  3. Build context from chunks
  4. `generate(prompt, context)` → LLM answer
  5. Build response with sources + token usage

**✏️ Exercise:**
1. Trace a complete request through the code. Start at `chat.py` line 62 (`rag_chain.query()`), follow it into `chain.py` `query()`, and list every function call in order
2. In `query()` line 178: what happens when `search_results` is empty? Why is this check important?
3. In `ingest_document()`: if you have a 100-page PDF (500,000 chars), how many API calls are made to the embedding model? (Hint: it calls `get_embeddings_batch()` once with all chunks)
4. Find `_estimate_cost()`. What does Claude cost per 1000 input tokens? Per 1000 output tokens? Why is output more expensive?

**📝 Write:** Draw the RAG pipeline on paper: Upload flow (read→chunk→embed→store) and Query flow (embed→search→generate→return).

---

### Day 9: The API Layer — FastAPI Routes

**📖 Read:** `docs/api-reference.md` (309 lines — read ALL)
- Focus on: every endpoint, request/response format
- Key concept: the API is a thin layer — it validates input, calls RAGChain, formats output

**💻 Study:** `src/api/routes/chat.py` (110 lines — read ALL, this is Day 8's chain.py called from HTTP)
- Line 28-38: Route decorator — defines `POST /api/chat`
- Line 45: `request_id = uuid4()` — unique ID for every request (for tracing)
- Line 49-53: Check if RAG chain exists — defensive coding
- Line 59-63: Call `rag_chain.query()` — THIS is where Day 8's code gets called
- Line 67-79: Build `SourceChunk` list from raw results — mapping dict → Pydantic model
- Line 82-88: Build `TokenUsage` — tracking how many tokens were used + cost

Then study: `src/api/routes/documents.py` (151 lines — read ALL)
- `POST /api/documents/upload` — calls `chain.ingest_document()`
- `GET /api/documents` — lists uploaded documents
- `DELETE /api/documents/{document_id}` — removes from vector store + storage

**✏️ Exercise:**
1. In `chat.py` line 59: `body.session_id or str(uuid4())`. What does this mean? When is a new session ID created vs reusing an existing one?
2. In `documents.py`: find the upload endpoint. What file types does it accept? Where is that validated?
3. What HTTP status code is returned when the RAG chain is not initialized? Why 500 and not 400?
4. If you wanted to add a `GET /api/chat/history` endpoint, what would you need to read from? (Hint: `src/history/`)

**📝 Write:** Explain the difference between the API layer (routes) and the business logic layer (chain.py). Why separate them?

---

### Day 10: Pydantic Models — Data Validation

**📖 Read:** `docs/pydantic-models.md` (307 lines — read ALL)
- Focus on: what Pydantic does, why validation matters, Field() options
- Key concept: Pydantic guarantees that data is correct BEFORE your code processes it

**💻 Study:** `src/api/models.py` (read ALL)
- `ChatRequest` — what the user sends: `question`, `session_id`, `top_k`
  - `question: str = Field(min_length=1, max_length=10000)` — validated!
  - `top_k: int | None = Field(default=None, ge=1, le=50)` — between 1 and 50, or None
- `ChatResponse` — what we return: `answer`, `sources`, `token_usage`, `latency_ms`
- `SourceChunk` — one piece of evidence: `document_name`, `chunk_text`, `relevance_score`
- `TokenUsage` — cost tracking: `input_tokens`, `output_tokens`, `estimated_cost_usd`
- `DocumentUploadResponse` — result of uploading: `document_id`, `chunks_created`

Then: `src/config.py` (read ALL)
- `CloudProvider` enum — `AWS` or `AZURE`
- `Settings(BaseSettings)` — all env vars with types, defaults, validation
  - `@lru_cache` on `get_settings()` — singleton pattern (read from env once)

**✏️ Exercise:**
1. What happens if someone sends `{"question": ""}` (empty string)? How does Pydantic handle it?
2. What happens if someone sends `{"question": "test", "top_k": 100}`? (Hint: `le=50`)
3. In `Settings`: find `rag_chunk_size`. What's the default? Can you change it without modifying code? (Hint: env var)
4. Why does `ChatResponse` include `cloud_provider`? Why would the frontend need to know which cloud is being used?

**📝 Write:** Explain why input validation is critical in an AI API. What could go wrong without it?

---

## WEEK 3 — Production AI Engineering

### Day 11: Config and Environment Management

**📖 Read:** `docs/getting-started.md` → Environment Variables section
- Key concept: ALL behavior is controlled by env vars — zero hardcoded secrets

**💻 Study:** `src/config.py` (read ALL)
- `BaseSettings` with `model_config = SettingsConfigDict(env_file=".env")` — loads from .env file
- Every field maps to an env var: `cloud_provider` → `CLOUD_PROVIDER`
- See how AWS and Azure each have their own group of settings
- `@lru_cache` on `get_settings()` — called hundreds of times but env is read once

Then: `src/main.py` (read ALL)
- `lifespan()` — async context manager that sets up and tears down the RAG chain
- `create_app()` — FastAPI factory that registers routes, middleware, CORS
- See how `settings` flows into `RAGChain.create(settings)` on startup

**✏️ Exercise:**
1. Create a `.env.example` file with all required env vars for AWS (find them all in `config.py`)
2. What happens if `CLOUD_PROVIDER` is missing? Where does the error occur?
3. What does `@lru_cache` do on `get_settings()`? Why is it important?
4. In `main.py` `lifespan()`: what happens if the RAG chain fails to initialize?

---

### Day 12: Document Storage — S3 and Blob

**📖 Read:** `docs/aws-services.md` → S3 section + `docs/azure-services.md` → Blob section
- Key concept: we store the ORIGINAL documents separately from the vector embeddings

**💻 Study:** `src/storage/base.py` (56 lines), then `src/storage/aws_s3.py` (118 lines)
- `BaseDocumentStorage`: `upload()`, `download()`, `delete()`, `list_documents()`
- `S3DocumentStorage`: see how `boto3` S3 client is used
  - `upload()` → `s3_client.put_object()` — stores raw bytes in S3
  - `download()` → `s3_client.get_object()` — retrieves raw bytes
  - The bucket name comes from `settings`
- Then compare with `azure_blob.py` — same interface, different SDK

**✏️ Exercise:**
1. Why do we store the original document AND the chunks? Why not just the chunks?
2. What happens if S3 upload succeeds but vector store fails? (Hint: think about consistency)
3. In `list_documents()`: what metadata is returned? How could you add `upload_date`?

---

### Day 13: Conversation History — DynamoDB and CosmosDB

**📖 Read:** `docs/how-services-work.md` → DynamoDB section
- Key concept: conversation history lets the chatbot remember previous messages

**💻 Study:** `src/history/base.py` (read ALL), then `src/history/aws_dynamodb.py` (read ALL)
- `BaseConversationHistory`: `add_message()`, `get_history()`, `clear_history()`
- `DynamoDBConversationHistory`:
  - Table schema: `session_id` (partition key) + `timestamp` (sort key)
  - `add_message()` → `table.put_item()` with `session_id`, `role`, `content`, `timestamp`
  - `get_history()` → `table.query()` with `session_id` → returns messages sorted by time
  - `max_history` — only keep last N messages (context window management!)

**✏️ Exercise:**
1. Why is `max_history` important? What happens if you send 100 previous messages to the LLM?
2. The DynamoDB table uses `session_id` + `timestamp`. Why both? Why not just `session_id`?
3. How would you add a "summarize old messages" feature? (Hint: when history > max, summarize the oldest messages into one summary message)

---

### Day 14: Monitoring and Metrics

**📖 Read:** `docs/monitoring.md` (46 lines), then `docs/ai-engineer-guide.md` → Monitoring section
- Key concept: you can't improve what you don't measure

**💻 Study:** `src/monitoring/metrics.py` (110 lines — read ALL)
- `MetricsCollector` class — tracks:
  - `total_requests` — how many chat requests
  - `total_errors` — how many failed
  - `total_tokens_used` — cost tracking
  - `average_latency_ms` — performance
  - `requests_per_minute` — load
- `record_chat_request()` — called from `chat.py` after each request

Then: `src/api/middleware/logging.py` (60 lines — read ALL)
- `RequestLoggingMiddleware` — logs every incoming request:
  - Method, path, status code, duration
  - This is observability — you can trace what happened in production

**✏️ Exercise:**
1. What 3 metrics would you look at FIRST if users report slow responses?
2. How would you add a `retrieval_quality` metric? (Hint: average score from vector search)
3. Why track `estimated_cost_usd`? What decision would you make if cost is too high?

---

### Day 15: Evaluation — How Do You Know It's Working?

**📖 Read:** `docs/ai-theory-roadmap.md` → Chapter 7 "Evaluation"
- Focus on: retrieval quality, faithfulness, answer relevance — the 3 pillars
- Key concept: AI systems need DIFFERENT testing than traditional software

**💻 Study:** `src/evaluation/evaluator.py` (read ALL)
- `RAGEvaluator` class with 3 methods:
  - `retrieval_quality()` — do the retrieved chunks actually contain the answer?
  - `faithfulness()` — is the answer supported by the chunks (not hallucinated)?
  - `answer_relevance()` — does the answer actually address the question?
- Each method explains its scoring logic in docstrings

Then: `src/evaluation/golden_dataset.py` (read ALL)
- 5 test cases, each with: `question`, `expected_answer`, `expected_source`
- These are regression tests — if you change the system, run these to verify quality didn't drop

Then: `tests/test_evaluation.py` (read ALL)
- See how evaluation tests are structured
- Mock the RAG chain, run evaluations, assert scores

**✏️ Exercise:**
1. Write 3 NEW golden dataset entries for a hypothetical "HR Policy" chatbot
2. What's the difference between `faithfulness` and `answer_relevance`? Give an example where one is high and the other is low
3. If `retrieval_quality` is low but `faithfulness` is high, what's the problem? Where in the pipeline would you fix it?

---

## WEEK 4 — Infrastructure, Deployment, Advanced Topics

### Day 16: Poetry and Dependencies

**📖 Read:** `docs/poetry-guide.md` (325 lines — read ALL)
- Key concept: Poetry manages Python dependencies, virtual environments, and packaging

**💻 Study:** `pyproject.toml` (read ALL)
- `[tool.poetry.dependencies]` — production dependencies
  - `fastapi`, `uvicorn` — web framework
  - `boto3`, `openai` — cloud SDKs
  - `langchain-text-splitters` — chunking
  - `pypdf`, `python-docx` — document readers
  - `loguru` — logging
  - `pydantic-settings` — configuration
- `[tool.poetry.group.dev.dependencies]` — dev-only
  - `pytest`, `ruff`, `mypy` — testing and linting

**✏️ Exercise:**
1. Run `cd /home/ketan-odido/maestro/rag-chatbot && cat pyproject.toml`
2. Count: how many production dependencies? How many dev dependencies?
3. Why is `boto3` a production dependency but `pytest` is not?

---

### Day 17: Docker and Containerization

**💻 Study:** `Dockerfile` (read ALL)
- Multi-stage build: builder stage → production stage
- See how Poetry installs dependencies without dev packages
- See the `CMD` — how the container starts uvicorn

**✏️ Exercise:**
1. What base image is used? Why not `python:3.12` (the full image)?
2. Why does the Dockerfile copy `pyproject.toml` and `poetry.lock` BEFORE copying source code?
3. What port does the container expose?

---

### Day 18-19: Terraform (AWS + Azure)

**📖 Read:** `docs/terraform.md` (337 lines — read ALL)

**💻 Study Day 18:** `infra/aws/main.tf` (read ALL)
- Map every resource to the Python code that uses it:
  - `aws_s3_bucket` → `storage/aws_s3.py`
  - `aws_dynamodb_table` → `history/aws_dynamodb.py`
  - `aws_opensearch` → `vectorstore/aws_opensearch.py`
  - `aws_ecs_service` → runs the Docker container

**💻 Study Day 19:** `infra/azure/main.tf` (read ALL)
- Same exercise: map every resource to Python code

**✏️ Exercise:**
1. If you run `terraform apply` for AWS, what 6+ resources are created?
2. What IAM permissions does the ECS task need? (Find the IAM role in the Terraform)
3. How much does the OpenSearch Serverless collection cost per month? (Check `docs/cost-analysis.md`)

---

### Day 20: CI/CD Pipeline

**📖 Read:** `docs/cicd.md` (77 lines)

**💻 Study:** `.github/workflows/ci.yml`, `deploy-aws.yml`, `deploy-azure.yml`
- CI: lint (ruff) → type check (mypy) → test (pytest) → build Docker → push to ECR
- Deploy: pull image → update ECS service → health check

**✏️ Exercise:**
1. What happens if a test fails in CI? Does the deployment still run?
2. What triggers the CI pipeline? (push to main? pull request? both?)
3. What secret env vars are needed in GitHub Actions?

---

### Day 21: Full Request Trace — End to End

**📖 Read:** Nothing new — this is a synthesis day

**💻 Exercise (the big one):** Trace a COMPLETE request through the entire codebase. Write it out step by step:

```
1. User sends POST /api/chat with {"question": "What is the refund policy?"}
2. FastAPI routes to chat.py line ___
3. ___
4. ___
... (fill in every step with file name and line number)
... until the response is returned to the user
```

You should be able to list 15-20 steps. If you can do this from memory, you understand the project.

---

### Days 22-25: Agents and MCP (Theory Heavy)

**📖 Read:** `docs/ai-theory-roadmap.md` → Chapter 5 "Agents" + Chapter 6 "MCP"
- Day 22: What is an AI agent? Tool use, ReAct pattern, planning
- Day 23: What is MCP? Server, client, tools, resources
- Day 24: How would you upgrade this RAG chatbot into an agent?
- Day 25: Hands-on: sketch a design for a RAG agent with web search tool

---

### Days 26-28: Testing Deep Dive

**💻 Study:** `tests/test_ingestion.py`, `tests/test_chat.py`, `tests/test_evaluation.py`

- Day 26: Unit testing with mocks — how to test without real AWS/Azure
- Day 27: Write a NEW test: test that chunking with overlap=0 produces more chunks than overlap=200
- Day 28: Write a NEW golden dataset test case and run the evaluation

---

### Days 29-30: Interview Prep

**📖 Read:** `docs/ai-engineer-guide.md` (442 lines)

**✏️ Exercise Day 29:** Answer these questions out loud (as if in an interview):
1. "Walk me through the architecture of your RAG system"
2. "How do you evaluate the quality of your RAG responses?"
3. "What's the difference between embeddings and LLM generation?"
4. "How did you handle multi-cloud support?"
5. "What would you change if you had to scale to 1000 requests/second?"

**✏️ Exercise Day 30:** Draw the entire architecture on a whiteboard from memory. If you can draw it and explain every component, **you're ready**.

---

## Quick Reference: File → Concept Map

| File | Lines | AI Concept | Day |
|---|---|---|---|
| `src/llm/base.py` | 96 | What is an LLM interface | 1 |
| `src/llm/aws_bedrock.py` | ~130 | How to call an LLM API | 2 |
| `src/llm/azure_openai.py` | ~130 | Cloud-agnostic pattern | 3 |
| `src/vectorstore/base.py` | 103 | What are embeddings | 4 |
| `src/vectorstore/aws_opensearch.py` | 164 | Vector search in practice | 5 |
| `src/rag/ingestion.py` | 112 | Chunking theory | 6 |
| `src/rag/prompts.py` | 60 | Prompt engineering | 7 |
| `src/rag/chain.py` | 232 | RAG pattern (the core) | 8 |
| `src/api/routes/chat.py` | 110 | API design for AI | 9 |
| `src/api/models.py` | ~170 | Data validation | 10 |
| `src/config.py` | ~130 | Environment management | 11 |
| `src/storage/aws_s3.py` | 118 | Document storage | 12 |
| `src/history/aws_dynamodb.py` | ~120 | Conversation memory | 13 |
| `src/monitoring/metrics.py` | 110 | AI observability | 14 |
| `src/evaluation/evaluator.py` | ~150 | AI evaluation | 15 |
| `pyproject.toml` | ~80 | Dependency management | 16 |
| `Dockerfile` | ~40 | Containerization | 17 |
| `infra/aws/main.tf` | ~200 | Infrastructure as Code | 18 |
| `tests/test_evaluation.py` | ~120 | Testing AI systems | 26-28 |

---

## The 3 Rules

1. **Don't skip exercises.** Reading without doing = forgetting.
2. **Write notes every day.** Your 📝 summaries become your interview answers.
3. **If stuck on theory, look at the code. If stuck on code, read the theory.** They explain each other.
