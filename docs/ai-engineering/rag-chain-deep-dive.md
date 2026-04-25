# Deep Dive: RAG Chain Orchestrator — `src/rag/chain.py`

> **Study order:** #13 · **Difficulty:** ★★★★☆ (this is the central orchestrator — every concept comes together here)  
> **File:** [`src/rag/chain.py`](../../src/rag/chain.py)  
> **Prerequisite:** [#12 — Prompt Engineering](prompts-deep-dive.md) · [#7 — LLM Interface](llm-interface-deep-dive.md) · [#9 — Vector Store Interface](vectorstore-interface-deep-dive.md)  
> **Part of:** [Architecture Overview](../architecture-and-design/architecture.md)

---

## Table of Contents

1. [Why This File Matters](#why-this-file-matters)
2. [DE Parallel — The RAG Chain Is an ETL Orchestrator](#de-parallel--the-rag-chain-is-an-etl-orchestrator)
3. [Architecture Overview](#architecture-overview)
4. [The Factory Pattern — `create()` Method](#the-factory-pattern--create-method)
5. [Provider-Specific Factories](#provider-specific-factories)
6. [The Ingestion Pipeline — `ingest_document()`](#the-ingestion-pipeline--ingest_document)
7. [The Query Pipeline — `query()`](#the-query-pipeline--query)
8. [Cost Estimation — `_estimate_cost()`](#cost-estimation--_estimate_cost)
9. [How Everything Connects — Full Data Flow](#how-everything-connects--full-data-flow)
10. [Cloud vs Local — Configuration Differences](#cloud-vs-local--configuration-differences)
11. [What Goes Wrong — Common Failure Modes](#what-goes-wrong--common-failure-modes)
12. [Self-Test Questions](#self-test-questions)
13. [What to Study Next](#what-to-study-next)

---

## Why This File Matters

This is the **most important file in the entire application**. Every other file is a component — this file wires them all together. If the LLM interface is an engine and the vector store is a database, `chain.py` is the **assembly line** that connects engine, database, embeddings, prompts, and chunking into a working RAG pipeline.

| What you'll learn | DE parallel | 🫏 Donkey |
|---|---| --- |
| Factory pattern for multi-provider setup | Database connection factory (`get_engine('postgres')` vs `get_engine('mysql')`) | The stable foreman picks the right donkey for the cloud (AWS Bedrock vs Azure OpenAI vs local Ollama) at startup |
| Ingestion pipeline orchestration | ETL pipeline — extract, transform, load | Pre-sort 📮 |
| Query pipeline orchestration | Read-path pipeline — query, join, format, return | Robot hand 🤖 |
| Cost estimation per provider | Cloud cost monitoring per service | Tachograph 📊 |
| Dependency injection | Airflow's `provide_session` decorator | Trip log 📒 |

- 🫏 **Donkey:** Think of this as the orientation briefing given to a new donkey before its first delivery run — it sets the context for everything that follows.

---

## DE Parallel — The RAG Chain Is an ETL Orchestrator

```
DATA ENGINEER                              AI ENGINEER
────────────────                           ──────────────
Airflow DAG:                               RAGChain:
  task_1: extract(source)                    step_1: read_document(content)
  task_2: transform(data)                    step_2: chunk_document(text)
  task_3: load(warehouse)                    step_3: embed(chunks)
                                             step_4: store(vectors)

Each task uses a different                 Each step uses a different
  operator (S3, SQL, DBT)                    component (chunker, embedder, store)

The DAG doesn't do the work —              The chain doesn't do the work —
  it orchestrates the operators                it orchestrates the components
```

**Key insight:** Just as an Airflow DAG is useless without operators, `RAGChain` is useless without its components. It coordinates the workflow — it doesn't implement any AI logic itself.

- 🫏 **Donkey:** The donkey checks its backpack full of retrieved document chunks before answering — no guessing from memory.

---

## Architecture Overview

```
                           RAGChain
                     ┌────────────────────┐
                     │                    │
                     │  llm: BaseLLM      │──── BedrockLLM / AzureOpenAILLM / OllamaLLM
                     │  vector_store:     │──── OpenSearchVectorStore / AzureAISearchVectorStore / ChromaDBVectorStore
                     │    BaseVectorStore │
                     │  settings:         │──── Settings (Pydantic)
                     │    Settings        │
                     │                    │
                     │  create()          │──── Factory method (reads settings.cloud_provider)
                     │  ingest_document() │──── Write path (4 steps)
                     │  query()           │──── Read path (5 steps)
                     │  _estimate_cost()  │──── Cost tracking
                     │                    │
                     └────────────────────┘
```

The class takes three dependencies:
- **`llm`** — any class implementing `BaseLLM` (generate + embed)
- **`vector_store`** — any class implementing `BaseVectorStore` (store + search)
- **`settings`** — the Pydantic Settings object with all configuration

- 🫏 **Donkey:** Like a stable floor plan showing where the donkey enters, where the backpacks are loaded, and which route it takes to the customer.

---

## The Factory Pattern — `create()` Method

```python
@classmethod
def create(cls) -> "RAGChain":
    """Factory method that creates a RAGChain with the appropriate backends."""
    settings = Settings()

    if settings.cloud_provider == CloudProvider.AWS:
        llm, vector_store = cls._create_aws_backends(settings)
    elif settings.cloud_provider == CloudProvider.AZURE:
        llm, vector_store = cls._create_azure_backends(settings)
    elif settings.cloud_provider == CloudProvider.LOCAL:
        llm, vector_store = cls._create_local_backends(settings)
    else:
        raise ValueError(f"Unsupported cloud provider: {settings.cloud_provider}")

    return cls(llm=llm, vector_store=vector_store, settings=settings)
```

**Why a factory?** Because the caller (`main.py`) shouldn't know which backends exist. It just calls:

```python
chain = RAGChain.create()
```

And the correct backends are selected based on `CLOUD_PROVIDER` environment variable.

**DE parallel — database connection factory:**

```python
# You've written code like this before:
def get_engine(db_type: str):
    if db_type == "postgres":
        return create_engine("postgresql://...")
    elif db_type == "mysql":
        return create_engine("mysql://...")
    elif db_type == "sqlite":
        return create_engine("sqlite:///local.db")

# Same pattern. Different backends, same interface.
```

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Provider-Specific Factories

Each factory returns a `(llm, vector_store)` tuple with the correct constructor arguments:

### AWS Factory

```python
@staticmethod
def _create_aws_backends(settings: Settings) -> tuple[BaseLLM, BaseVectorStore]:
    llm = BedrockLLM(
        model_id=settings.aws_bedrock_model_id,      # "anthropic.claude-3-5-sonnet-..."
        region=settings.aws_region,                    # "eu-west-1"
    )
    vector_store = OpenSearchVectorStore(
        endpoint=settings.aws_opensearch_endpoint,     # "https://vpc-xxx.es.amazonaws.com"
        index_name=settings.aws_opensearch_index,      # "rag-documents"
        region=settings.aws_region,                    # "eu-west-1"
    )
    return llm, vector_store
```

### Azure Factory

```python
@staticmethod
def _create_azure_backends(settings: Settings) -> tuple[BaseLLM, BaseVectorStore]:
    llm = AzureOpenAILLM(
        endpoint=settings.azure_openai_endpoint,           # "https://xxx.openai.azure.com"
        api_key=settings.azure_openai_api_key,             # from Key Vault
        deployment_name=settings.azure_openai_deployment,  # "gpt-4o"
        api_version=settings.azure_openai_api_version,     # "2024-02-15-preview"
    )
    vector_store = AzureAISearchVectorStore(
        endpoint=settings.azure_search_endpoint,           # "https://xxx.search.windows.net"
        api_key=settings.azure_search_api_key,             # from Key Vault
        index_name=settings.azure_search_index,            # "rag-documents"
    )
    return llm, vector_store
```

### 🏠 Local Factory

```python
@staticmethod
def _create_local_backends(settings: Settings) -> tuple[BaseLLM, BaseVectorStore]:
    llm = OllamaLLM(
        base_url=settings.ollama_base_url,                 # "http://localhost:11434"
        model_name=settings.ollama_model_name,             # "llama3.2"
        embedding_model=settings.ollama_embedding_model,   # "nomic-embed-text"
    )
    vector_store = ChromaDBVectorStore(
        collection_name=settings.chroma_collection_name,      # "rag-chatbot"
        persist_directory=settings.chroma_persist_directory,   # "./data/chromadb"
    )
    return llm, vector_store
```

**Complete configuration comparison:**

| Setting | AWS | AWS (cheap) | Azure | Local | 🫏 Donkey |
|---|---|---|---|---| --- |
| **Env var** | `CLOUD_PROVIDER=aws` | `CLOUD_PROVIDER=aws` | `CLOUD_PROVIDER=azure` | `CLOUD_PROVIDER=local` | AWS depot 🏭 |
| **Extra env** | — | `VECTOR_STORE_TYPE=dynamodb` | — | — | AWS depot 🏭 |
| **LLM class** | `BedrockLLM` | `BedrockLLM` | `AzureOpenAILLM` | `OllamaLLM` | Which donkey breed shows up at the stable's front door to do the writing |
| **LLM model** | Claude 3.5 Sonnet | Claude 3.5 Sonnet | GPT-4o | llama3.2 | The specific donkey assigned — older, faster, or smarter — that actually writes the answer |
| **Vector store** | `OpenSearchVectorStore` | `DynamoDBVectorStore` | `AzureAISearchVectorStore` | `ChromaDBVectorStore` | AWS search hub 🔍 |
| **Vector cost** | ~$350/month | **~$0/month** | $0–75/month | $0 | Feed bill 🌾 |
| **Embedding source** | Amazon Titan | Amazon Titan | Azure text-embedding-3 | nomic-embed-text | GPS stamp 📍 |
| **Auth** | IAM (SigV4) | IAM (SigV4) | API key | None | Stable door 🚪 |
| **Cost** | ~$0.0065/query | ~$0.0065/query | ~$0.005/query | **$0** | Feed bill 🌾 |

- 🫏 **Donkey:** Choosing which stable to work with — AWS Bedrock, Azure OpenAI, or a local Ollama barn each offer different donkeys at different prices.

---

## The Ingestion Pipeline — `ingest_document()`

This is the **write path** — storing documents so they can be queried later.

```python
async def ingest_document(
    self, document_id: str, filename: str, content: str
) -> int:
    """Ingest a document: chunk it, embed it, store it. Returns chunk count."""

    # Step 1: Read the raw content
    text = read_document(content, filename)

    # Step 2: Split into chunks
    chunks = chunk_document(text, chunk_size=500, chunk_overlap=50)

    # Step 3: Get embeddings for all chunks (batch)
    embeddings = await self.llm.get_embeddings_batch(
        [c.text for c in chunks]
    )

    # Step 4: Store in vector store
    await self.vector_store.store_vectors(
        document_id=document_id,
        chunks=chunks,
        embeddings=embeddings,
    )

    return len(chunks)
```

**Visualised as a pipeline:**

```
PDF file → [Read] → plain text → [Chunk] → 50 chunks → [Embed] → 50 vectors → [Store] → Vector DB
                                  ~~~~~~~~              ~~~~~~~~~~              ~~~~~~~~~~
                                  500 chars each        1536-dim each           Indexed for search
```

**DE parallel — ETL pipeline:**

```
CSV file → [Extract] → raw rows → [Transform] → cleaned rows → [Load] → Data warehouse
```

| Ingestion step | DE parallel | What it does | 🫏 Donkey |
|---|---|---| --- |
| `read_document()` | `pandas.read_csv()` | Extracts raw text from PDF/TXT | Donkey-side view of read_document() — affects how the donkey loads, reads, or delivers the cargo |
| `chunk_document()` | Data partitioning / windowing | Splits text into 500-char windows with 50-char overlap | Slices raw mail into backpack-sized chunks with overlapping edges so sentences don't split mid-word |
| `get_embeddings_batch()` | `df.apply(transform_fn)` | Converts each chunk to a 1536-dim vector | GPS-stamps each backpack chunk with coordinates so the warehouse knows where to shelve it |
| `store_vectors()` | `df.to_sql(warehouse)` | Indexes vectors for similarity search | Shelves GPS-stamped backpacks in the warehouse so the robot can find them by coordinates later |

**Why batch embeddings?** One API call for 50 chunks is faster and cheaper than 50 separate calls. This is the same principle as batch `INSERT` vs row-by-row `INSERT`.

- 🫏 **Donkey:** Post office pre-sorting: mail is split into backpack-sized chunks, stamped with GPS coordinates (embeddings), and shelved in the warehouse before the donkey ever arrives.

---

## The Query Pipeline — `query()`

This is the **read path** — answering user questions.

```python
async def query(
    self, question: str, session_id: str | None = None, top_k: int = 5
) -> dict:
    """Query the RAG pipeline. Returns answer + sources + token usage."""

    # Step 1: Embed the question
    question_embedding = await self.llm.get_embedding(question)

    # Step 2: Search for similar chunks
    results = await self.vector_store.search(
        query_vector=question_embedding, top_k=top_k
    )

    # Step 3: Build context from retrieved chunks
    context_texts = []
    for i, result in enumerate(results):
        context_texts.append(f"[Document chunk {i+1}]: {result.text}")
    context = "\n---\n".join(context_texts)

    # Step 4: Generate answer using LLM
    response = await self.llm.generate(
        question=question, context=context
    )

    # Step 5: Build response with sources and cost
    token_usage = {
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "estimated_cost": self._estimate_cost(
            response.input_tokens, response.output_tokens
        ),
    }

    return {
        "answer": response.text,
        "sources": [
            {"text": r.text[:200], "score": r.score, "document_id": r.document_id}
            for r in results
        ],
        "token_usage": token_usage,
    }
```

**Visualised as a pipeline:**

```
"What is the refund policy?"
    │
    ▼
[Step 1: Embed question] ──→ [0.12, -0.34, 0.56, ...] (1536-dim vector)
    │
    ▼
[Step 2: Vector search]  ──→ 5 most similar chunks (with scores)
    │
    ▼
[Step 3: Build context]  ──→ "[Document chunk 1]: Refunds take 14 days...\n---\n[Document chunk 2]: ..."
    │
    ▼
[Step 4: LLM generate]   ──→ "Based on the documents, refunds are processed within 14 business days..."
    │
    ▼
[Step 5: Build response]  ──→ { answer, sources, token_usage }
```

**DE parallel — read query pipeline:**

| Query step | DE parallel | What it does | 🫏 Donkey |
|---|---|---| --- |
| Embed question | Build query parameters | Convert question to searchable format | Stable inspector — checks the code is tidy before letting the donkey out |
| Vector search | `SELECT * WHERE similarity > threshold ORDER BY score LIMIT 5` | Find relevant data | GPS warehouse robot finds the 5 nearest backpack coordinates to the question in ~9 HNSW hops |
| Build context | JOIN results into a single payload | Combine search results | Closest SQL/DE concept — for engineers who think in tables not GPS coordinates |
| LLM generate | Apply business logic / stored procedure | Transform data into answer | The donkey reads the delivery note plus the backpack and writes the final reply |
| Build response | Format as API response | Package result for caller | Stable door 🚪 |

- 🫏 **Donkey:** The warehouse robot dispatched to find the right backpack shelf — it uses GPS coordinates (embeddings) to locate the nearest relevant chunks in ~9 hops.

---

## Cost Estimation — `_estimate_cost()`

```python
def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
    """Estimate the cost of an LLM call based on the provider."""
    if self.settings.cloud_provider == CloudProvider.LOCAL:
        return 0.0

    if self.settings.cloud_provider == CloudProvider.AWS:
        input_cost = (input_tokens / 1000) * 0.003
        output_cost = (output_tokens / 1000) * 0.015
    elif self.settings.cloud_provider == CloudProvider.AZURE:
        input_cost = (input_tokens / 1000) * 0.0025
        output_cost = (output_tokens / 1000) * 0.01

    return round(input_cost + output_cost, 6)
```

**Cost per 1000 tokens:**

| Provider | Input | Output | Typical query cost (~845 input, ~200 output) | 🫏 Donkey |
|---|---|---|---| --- |
| AWS (Claude 3.5 Sonnet) | $0.003 | $0.015 | **$0.0055** | The premium AWS donkey — eats the most hay per delivery but writes the sharpest answers |
| Azure (GPT-4o) | $0.0025 | $0.010 | **$0.0041** | The Azure-hub donkey — slightly cheaper hay rate per delivery than the AWS one |
| Local (Ollama) | $0.000 | $0.000 | **$0.0000** | The local barn donkey — eats no metered hay because it runs on your own laptop |

**Monthly cost projection at 1000 queries/day:**

```
AWS:   1000 × $0.0055 × 30 = $165/month
Azure: 1000 × $0.0041 × 30 = $123/month
Local: 1000 × $0.0000 × 30 = $0/month (but you pay for the hardware)
```

**Output tokens cost 3-5x more than input tokens.** That's why prompt rules like "be concise" and "under 500 words" save real money.

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.

---

## How Everything Connects — Full Data Flow

```
User uploads document               User asks question
─────────────────────               ───────────────────
     │                                    │
     ▼                                    ▼
POST /documents                      POST /chat
     │                                    │
     ▼                                    ▼
route calls                          route calls
chain.ingest_document()              chain.query()
     │                                    │
     ├─ read_document()                   ├─ llm.get_embedding(question)
     ├─ chunk_document()                  ├─ vector_store.search(embedding)
     ├─ llm.get_embeddings_batch()        ├─ format context with prompts.py
     └─ vector_store.store_vectors()      ├─ llm.generate(question, context)
                                          └─ _estimate_cost()
                                               │
                                               ▼
                                          { answer, sources, token_usage }
```

**The chain is the hub.** Every route goes through it. Every component is accessed through it. Change the chain, and you change the entire application's behaviour.

- 🫏 **Donkey:** The step-by-step route map showing every checkpoint the donkey passes from question intake to answer delivery.

---

## Cloud vs Local — Configuration Differences

Setting up the chain for each provider:

### AWS Setup

```bash
# .env
CLOUD_PROVIDER=aws
AWS_REGION=eu-west-1
AWS_BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
AWS_OPENSEARCH_ENDPOINT=https://vpc-rag-xxx.eu-west-1.es.amazonaws.com
AWS_OPENSEARCH_INDEX=rag-documents

# Auth: IAM role attached to ECS task (no keys in env)
```

### Azure Setup

```bash
# .env
CLOUD_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://my-openai.openai.azure.com
AZURE_OPENAI_API_KEY=sk-xxx
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_SEARCH_ENDPOINT=https://my-search.search.windows.net
AZURE_SEARCH_API_KEY=xxx
AZURE_SEARCH_INDEX=rag-documents
```

### 🏠 Local Setup

```bash
# .env
CLOUD_PROVIDER=local
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_NAME=llama3.2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
CHROMA_COLLECTION_NAME=rag-chatbot
CHROMA_PERSIST_DIRECTORY=./data/chromadb

# Prerequisites:
# 1. ollama pull llama3.2
# 2. ollama pull nomic-embed-text
# 3. pip install chromadb
```

- 🫏 **Donkey:** Adjusting the bag fit and route preferences so the donkey delivers to the right address every time.

---

## What Goes Wrong — Common Failure Modes

| Problem | Symptom | Cause | Fix | 🫏 Donkey |
|---|---|---|---| --- |
| `ValueError: Unsupported cloud provider` | App crashes on startup | `CLOUD_PROVIDER` not set or misspelled | Set `CLOUD_PROVIDER=local` in `.env` | Stable refuses to open because the donkey doesn't know which warehouse to deliver to — set the provider in `.env` |
| `ConnectionRefusedError` (local) | Ingestion fails | Ollama not running | `ollama serve` in a separate terminal | The local barn donkey isn't awake yet — boot it before asking it to deliver |
| Empty search results | "I don't have enough information" | Documents not ingested yet | Upload documents first via `POST /documents` | Pre-sort 📮 |
| High latency (>5s) | Slow responses | LLM is slow (especially local) | Use a smaller model or increase hardware | The donkey is plodding — swap in a lighter breed or feed it stronger hardware |
| Token limit exceeded | API error from LLM | Too many chunks in context (`top_k` too high) | Reduce `top_k` from 5 to 3 | Backpack overstuffed with hay — the donkey can't carry it; pack fewer chunks |
| Zero cost in metrics | Metrics show $0.000 | Using local provider | Expected — local is free | Feed bill 🌾 |
| Stale embeddings | Old documents still returned | Vectors not deleted after re-upload | Implement delete + re-ingest flow | Pre-sort 📮 |

- 🫏 **Donkey:** When the donkey returns empty-hooved — use the trip log and bag inspection checklist to find what went wrong.

---

## Self-Test Questions

### Tier 1 — Must understand

- [ ] What does the `create()` factory method do and why is it a `@classmethod`?
- [ ] What are the 4 steps of `ingest_document()`? What does each step produce?
- [ ] What are the 5 steps of `query()`? What does each step produce?
- [ ] Why does `_create_local_backends()` return `$0` for cost?

### Tier 2 — Should understand

- [ ] Why are embeddings generated in batch for ingestion but single for query?
- [ ] How does `top_k` affect both cost and answer quality?
- [ ] What happens if `vector_store.search()` returns 0 results?
- [ ] How would you add a 4th provider (e.g., Google Vertex AI)?

### Tier 3 — AI engineering territory

- [ ] What's the latency breakdown for a typical query? Which step is slowest?
- [ ] How would you implement caching to avoid re-embedding the same question?
- [ ] If output tokens cost 5x more than input, what architectural decisions reduce output?
- [ ] How would you implement streaming responses (show answer as it generates)?

- 🫏 **Donkey:** Sending the donkey on 25 standard test deliveries (golden dataset) to verify it returns the right packages every time.

---

## What to Study Next

You now understand the central orchestrator. Next:

- **File #14:** [`src/evaluation/evaluator.py`](evaluation-framework-deep-dive.md) — how to measure whether the chain is producing good answers
- **File #15:** [`src/evaluation/golden_dataset.py`](golden-dataset-deep-dive.md) — the test cases that validate the chain end-to-end

📖 **Related docs:**
- [Prompt Engineering Deep Dive (#12)](prompts-deep-dive.md) — the templates this chain uses
- [LLM Interface Deep Dive (#7)](llm-interface-deep-dive.md) — the `BaseLLM` abstraction
- [Vector Store Interface Deep Dive (#9)](vectorstore-interface-deep-dive.md) — the `BaseVectorStore` abstraction
- [Ingestion Pipeline Deep Dive (#11)](ingestion-pipeline-deep-dive.md) — deeper look at chunking
- [Cost Analysis](cost-analysis.md)

- 🫏 **Donkey:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
