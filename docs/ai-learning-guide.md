# AI & ML Technologies Learning Guide

> **Who is this for?** You already know Python, FastAPI, AWS, Azure, Terraform,
> and GitHub. This guide focuses on the **AI/ML-specific** technologies used
> in this project — what they are, why we need them, and how to learn each one
> from scratch.

---

## Table of Contents

1. [The Big Picture — What Makes This an "AI" Project?](#the-big-picture)
2. [LangChain — The RAG Orchestration Framework](#langchain)
3. [Embeddings — Turning Text Into Numbers](#embeddings)
4. [Vector Stores — Searching by Meaning](#vector-stores)
5. [Large Language Models (LLMs) — The Brain](#large-language-models)
6. [Amazon Bedrock — AWS Managed LLM Service](#amazon-bedrock)
7. [Azure OpenAI — Microsoft's GPT Service](#azure-openai)
8. [Prompt Engineering — Talking to the AI](#prompt-engineering)
9. [RAG — Retrieval-Augmented Generation](#rag-pattern)
10. [OpenTelemetry — Observability for AI Apps](#opentelemetry)
11. [Pydantic — Data Validation (AI Context)](#pydantic-for-ai)
12. [Document Processing (pypdf, python-docx)](#document-processing)
13. [OpenSearch / Azure AI Search — Vector Databases](#vector-databases)
14. [Tokens & Context Windows](#tokens-and-context-windows)
15. [Recommended Learning Path](#recommended-learning-path)
16. [Free Resources & Courses](#free-resources)

---

## The Big Picture

### What you already know vs what's new

```
THINGS YOU KNOW                    NEW AI THINGS (this guide)
─────────────────                  ─────────────────────────
Python                      →     LangChain (Python library for AI chains)
FastAPI                     →     Serving AI responses via REST API
AWS (S3, DynamoDB, IAM)     →     Amazon Bedrock (managed LLM service)
Azure (Blob, Cosmos)        →     Azure OpenAI (managed GPT service)
Terraform                   →     Provisioning AI-specific resources
GitHub Actions              →     CI/CD for AI applications
SQL / Data Engineering      →     Embeddings, vectors, similarity search
```

### What makes this project "AI"?

A traditional app stores data and retrieves it with **exact queries** (SQL WHERE
clauses). This project retrieves data by **meaning** — you ask a question in
natural language, and the system finds the most relevant paragraphs, then asks
an AI model to write a human-readable answer.

That's the RAG pattern — and it uses these AI technologies:

```
User Question
    │
    ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Embedding Model │ ──▶ │  Vector Database  │ ──▶ │  LLM (GPT/Claude)│
│  (text → numbers)│     │  (search by       │     │  (generate answer)│
│                  │     │   similarity)     │     │                   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## LangChain

### What is it?

LangChain is a **Python framework** that makes it easy to build applications
with LLMs. Think of it like FastAPI for AI — it provides building blocks so
you don't have to write everything from scratch.

### Why do we need it?

Without LangChain, you'd have to manually:

- Split documents into chunks (write your own text splitting logic)
- Call embedding APIs and handle retries
- Build the prompt string with context + question
- Parse the LLM's response

With LangChain, these become one-liners.

### Where is it used in this project?

| File | What LangChain does |
|---|---|
| `src/rag/ingestion.py` | `RecursiveCharacterTextSplitter` — splits documents into chunks |
| `src/rag/chain.py` | Orchestrates the retrieval + generation pipeline |
| `src/llm/aws_bedrock.py` | Uses `langchain-aws` for Bedrock integration |

### What to learn

```
Level 1 — Understand the concept (2 hours)
├── What is a "chain"? (Input → Transform → Output)
├── What is a "text splitter"? (Big doc → small chunks)
└── What is a "retriever"? (Question → relevant chunks)

Level 2 — Hands-on basics (1 day)
├── pip install langchain
├── Create a simple chain that takes a question and calls an LLM
├── Use RecursiveCharacterTextSplitter on a PDF
└── Build a simple QA chain

Level 3 — Production patterns (1 week)
├── Custom chains and callbacks
├── Streaming responses
├── Error handling and retries
└── Evaluation and testing
```

### Quick example — what the code does

```python
# This is from src/rag/ingestion.py — here's what it does:

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Create a splitter that makes ~500 character chunks with 50 char overlap
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,      # Each chunk is ~500 characters
    chunk_overlap=50,    # 50 chars shared between consecutive chunks
    separators=[         # Try to split on these, in order:
        "\n\n",          #   1. Paragraph breaks
        "\n",            #   2. Line breaks
        ". ",            #   3. Sentence endings
        " ",             #   4. Word boundaries
    ],
)

# Input: one big string (entire document)
text = "This is a very long document about refund policies..."

# Output: list of smaller strings (chunks)
chunks = splitter.split_text(text)
# chunks = ["This is a very long...", "...refund policies state that...", ...]
```

### Try it yourself

```bash
pip install langchain langchain-text-splitters

python -c "
from langchain_text_splitters import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
chunks = splitter.split_text('Hello world. ' * 50)
print(f'Created {len(chunks)} chunks')
print(f'First chunk: {chunks[0][:80]}...')
"
```

---

## Embeddings

### What are they?

An embedding is a **list of numbers** (a vector) that represents the **meaning**
of a piece of text. Similar texts have similar numbers.

### The intuition

Imagine you could place every sentence on a map. Sentences about "refund policy"
would cluster together, and sentences about "delivery times" would cluster
somewhere else. Embeddings are the **coordinates** on that map.

```
"How do I get a refund?"          → [0.82, -0.15, 0.43, ..., 0.91]  (1536 numbers)
"What is the return policy?"      → [0.80, -0.13, 0.45, ..., 0.89]  ← SIMILAR numbers!
"When will my order arrive?"      → [0.12, 0.78, -0.34, ..., 0.23]  ← DIFFERENT numbers
```

### Why do we need them?

Traditional search finds documents with **matching keywords**:
- Query: "refund" → finds documents containing the word "refund"
- Misses: documents about "return policy" (same meaning, different words!)

Embedding search finds documents with **matching meaning**:
- Query: "How do I get my money back?" → finds "refund policy" documents
- Works even though "money back" ≠ "refund" in keyword search

### Where is it used in this project?

| File | What happens |
|---|---|
| `src/llm/base.py` | `get_embedding()` — abstract method all LLM providers implement |
| `src/llm/aws_bedrock.py` | Calls Amazon Titan Embeddings v2 to create embeddings |
| `src/llm/azure_openai.py` | Calls `text-embedding-3-small` to create embeddings |
| `src/rag/chain.py` | Embeds the user's question to search for similar chunks |

### The numbers

| Model | Dimensions | What that means |
|---|---|---|
| Amazon Titan Embeddings v2 | 1024 | Each text becomes a list of 1024 numbers |
| OpenAI text-embedding-3-small | 1536 | Each text becomes a list of 1536 numbers |

### Try it yourself (free, no API key needed)

```bash
pip install sentence-transformers

python -c "
from sentence_transformers import SentenceTransformer

# This downloads a small free model (~80 MB)
model = SentenceTransformer('all-MiniLM-L6-v2')

texts = [
    'How do I get a refund?',
    'What is the return policy?',
    'When will my order arrive?',
]

# Create embeddings
embeddings = model.encode(texts)

# Compare similarity
from numpy import dot
from numpy.linalg import norm

def cosine_similarity(a, b):
    return dot(a, b) / (norm(a) * norm(b))

print(f'refund ↔ return policy: {cosine_similarity(embeddings[0], embeddings[1]):.3f}')  # ~0.85 HIGH
print(f'refund ↔ delivery:     {cosine_similarity(embeddings[0], embeddings[2]):.3f}')  # ~0.35 LOW
"
```

This will show you that "refund" and "return policy" are ~0.85 similar (very
close), while "refund" and "delivery" are ~0.35 similar (far apart).

---

## Vector Stores

### What are they?

A vector store is a **database optimized for similarity search**. Instead of
`SELECT * FROM docs WHERE title = 'refund'`, you say
`FIND me the 5 documents most similar to this embedding vector`.

### Why can't we just use DynamoDB or PostgreSQL?

You technically *can* (PostgreSQL has pgvector extension), but:

| Feature | Traditional DB | Vector Store |
|---|---|---|
| Search by exact match | ✅ Fast | ✅ Fast |
| Search by meaning | ❌ Can't do it | ✅ Built for this |
| Scale to millions of vectors | ❌ Very slow | ✅ Optimized algorithms |
| Approximate nearest neighbour | ❌ No | ✅ HNSW, IVF algorithms |

### The algorithm: HNSW

Our OpenSearch config uses **HNSW** (Hierarchical Navigable Small World).
Think of it like a skip list for vectors:

```
Layer 2:  [A] ─────────────────── [D]           (few nodes, long jumps)
Layer 1:  [A] ──── [B] ──── [C] ── [D]         (more nodes, medium jumps)
Layer 0:  [A] [B] [C] [D] [E] [F] [G] [H]     (all nodes, short jumps)
```

To find the nearest vector to your query, start at the top layer (big jumps),
then refine at lower layers. This is why it's fast even with millions of vectors.

### Where is it used in this project?

| File | What happens |
|---|---|
| `src/vectorstore/base.py` | `BaseVectorStore` ABC — `store_vectors()`, `search()` |
| `src/vectorstore/aws_opensearch.py` | OpenSearch Serverless with k-NN plugin |
| `src/vectorstore/azure_ai_search.py` | Azure AI Search with vectorized queries |

---

## Large Language Models

### What are they?

An LLM is a neural network trained on massive amounts of text that can:

- **Understand** natural language (read and comprehend your question)
- **Generate** natural language (write a coherent answer)
- **Follow instructions** (respect rules like "only use the provided context")

### Models used in this project

| Provider | Model | What it does | Cost |
|---|---|---|---|
| AWS Bedrock | Claude 3 Sonnet | Generates answers from context | ~$3/M input tokens |
| AWS Bedrock | Titan Embeddings v2 | Converts text → numbers | ~$0.02/M tokens |
| Azure OpenAI | GPT-4o | Generates answers from context | ~$2.50/M input tokens |
| Azure OpenAI | text-embedding-3-small | Converts text → numbers | ~$0.02/M tokens |

### Key concepts

**Token**: A piece of a word. "Hello world" = 2 tokens. "Unbelievable" = 3 tokens
(un + believ + able). Most models charge per token.

**Context window**: Maximum tokens the model can process at once.
- GPT-4o: 128,000 tokens (~96,000 words)
- Claude 3 Sonnet: 200,000 tokens (~150,000 words)

**Temperature**: Controls randomness. 0.0 = deterministic (same answer every time),
1.0 = creative (different answers each time). For RAG, we use low temperature
(0.1–0.3) because we want factual, consistent answers.

### Where is it used in this project?

| File | What happens |
|---|---|
| `src/llm/base.py` | `BaseLLM` ABC — `generate()`, `get_embedding()` |
| `src/llm/aws_bedrock.py` | `BedrockLLM` — calls AWS Bedrock Converse API |
| `src/llm/azure_openai.py` | `AzureOpenAILLM` — calls Azure OpenAI Chat Completions |
| `src/rag/chain.py` | Uses `self._llm.generate()` to create the final answer |

### Try it yourself (free)

You can experiment with LLMs without writing code:

1. **ChatGPT** (free tier): [chat.openai.com](https://chat.openai.com)
2. **Claude** (free tier): [claude.ai](https://claude.ai)
3. **AWS Bedrock playground**: Available in AWS Console (pay-per-use)

To understand what our code does, try this in ChatGPT:

```
System: You are a helpful assistant. ONLY answer from the context below.

Context: "Refunds are processed within 14 days. Returns must be in original packaging."

Question: How long does a refund take?
```

This is exactly what our `src/rag/prompts.py` does — but programmatically.

---

## Amazon Bedrock

### What is it?

Bedrock is AWS's **managed AI service**. Instead of running your own GPU servers,
you call an API and AWS handles the infrastructure. Think of it like
RDS for databases — you don't manage the server, just call the API.

### Why use Bedrock instead of calling OpenAI directly?

| Feature | Direct OpenAI API | AWS Bedrock |
|---|---|---|
| Data stays in your AWS account | ❌ Goes to OpenAI servers | ✅ Stays in your VPC |
| IAM authentication | ❌ API keys only | ✅ IAM roles |
| Model choice | OpenAI models only | Claude, Llama, Titan, Mistral, etc. |
| Enterprise compliance | Varies | ✅ SOC2, HIPAA, GDPR |
| Billing | Separate OpenAI bill | Part of your AWS bill |

### Where is it used in this project?

```python
# src/llm/aws_bedrock.py — simplified version of what happens:

import boto3

# Create a Bedrock client (uses IAM, no API keys!)
client = boto3.client("bedrock-runtime", region_name="eu-west-1")

# Call the LLM — "Converse API" is Bedrock's unified interface
response = client.converse(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    messages=[
        {"role": "user", "content": [{"text": "What is the refund policy?"}]}
    ],
    inferenceConfig={"maxTokens": 2048, "temperature": 0.1},
)

answer = response["output"]["message"]["content"][0]["text"]
```

### How to learn

1. **Enable Bedrock** in your AWS Console (eu-west-1 or us-east-1)
2. **Request model access** (Claude, Titan — takes ~5 minutes to approve)
3. **Try the Playground** in the Bedrock console — chat with models in the browser
4. **Use boto3** — the Python code above is all you need to get started

### Cost for learning

- Titan Embeddings: ~$0.02 per million tokens (basically free for testing)
- Claude 3 Sonnet: ~$3 per million input tokens
- For 100 test questions: ~$0.05 total

---

## Azure OpenAI

### What is it?

Azure OpenAI gives you access to **OpenAI's models (GPT-4, GPT-4o)** but hosted
on Microsoft Azure. Same models as ChatGPT, but running in your Azure subscription.

### Why use Azure OpenAI instead of OpenAI directly?

Same reasons as Bedrock — data stays in your subscription, uses Azure AD
authentication, appears on your Azure bill, and has enterprise compliance.

### Where is it used in this project?

```python
# src/llm/azure_openai.py — simplified version:

from openai import AsyncAzureOpenAI

client = AsyncAzureOpenAI(
    azure_endpoint="https://your-resource.openai.azure.com",
    api_version="2024-10-01-preview",
    api_key="your-key",  # or use Azure AD / Managed Identity
)

response = await client.chat.completions.create(
    model="gpt-4o",        # deployment name you chose
    messages=[
        {"role": "system", "content": "Answer only from the context..."},
        {"role": "user", "content": "What is the refund policy?"},
    ],
    temperature=0.1,
    max_tokens=2048,
)

answer = response.choices[0].message.content
```

### How to learn

1. **Create an Azure OpenAI resource** in the Azure Portal
2. **Deploy a model** (e.g., gpt-4o-mini for cheap testing)
3. **Use Azure OpenAI Studio** — chat with the model in the browser
4. **Use the Python SDK** — `pip install openai` (same library, different base URL)

---

## Prompt Engineering

### What is it?

Prompt engineering is the art of **writing instructions for the LLM** to get
the best possible answers. It's like writing a clear ticket for a developer —
the better the instructions, the better the output.

### Where is it used in this project?

The file `src/rag/prompts.py` contains our prompts. Here's why each part matters:

```python
RAG_SYSTEM_PROMPT = """
You are a helpful AI assistant...     ← ROLE: tells the LLM who it is

RULES:
1. ONLY use information from the       ← CONSTRAINT: prevents hallucination
   context documents below
2. If the context does not contain      ← FALLBACK: what to do when unsure
   enough information, say so
3. Always cite which document(s)        ← FORMAT: how to structure the answer
4. Be concise but thorough              ← STYLE: tone and length
5. Use bullet points for lists          ← FORMAT: visual structure
6. Never make up information            ← CONSTRAINT: reinforces rule 1

CONTEXT DOCUMENTS:                      ← DATA: the retrieved chunks go here
{context}

USER QUESTION: {question}               ← INPUT: the user's question
"""
```

### Key techniques

| Technique | Example | Why it works |
|---|---|---|
| Role setting | "You are a helpful assistant" | Activates relevant knowledge |
| Few-shot examples | "Input: X → Output: Y" | Shows the model the expected format |
| Chain of thought | "Think step by step" | Improves reasoning accuracy |
| Constraints | "ONLY use the context" | Prevents hallucination |
| Output format | "Respond in JSON" | Gets structured output |

### How to learn

1. **Experiment in ChatGPT/Claude** — try different prompts, see what changes
2. **Read**: [Prompt Engineering Guide](https://www.promptingguide.ai/) (free)
3. **Practice**: Take a bad prompt, improve it, compare outputs
4. **Study our prompts**: Read `src/rag/prompts.py` and understand each line

---

## RAG Pattern

### What is it?

RAG (Retrieval-Augmented Generation) is a **design pattern** — not a library.
It means: "before asking the LLM, first **retrieve** relevant information,
then **augment** the prompt with it, then **generate** the answer."

### Why not just ask the LLM directly?

| Approach | Pros | Cons |
|---|---|---|
| Just ask the LLM | Simple | Hallucinations, outdated info, no private data |
| Fine-tune the LLM | Accurate for your domain | Expensive ($$$), slow to update |
| **RAG** | Accurate, up-to-date, cheap | More complex architecture |

### The RAG pipeline in this project (step by step)

#### Phase 1: Ingestion (happens when you upload a document)

```
PDF file
    │
    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Read content │ ──▶ │  Split into  │ ──▶ │  Create      │ ──▶ │  Store in    │
│  (pypdf)      │     │  chunks      │     │  embeddings  │     │  vector DB   │
│               │     │  (LangChain) │     │  (Bedrock/   │     │  (OpenSearch/ │
│               │     │              │     │   Azure)     │     │   AI Search) │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       ↓                    ↓                    ↓                     ↓
  "Full text of       ["Chunk 1...",        [[0.82, -0.15,        Stored with
   the PDF"            "Chunk 2...",         0.43, ...],          document_id
                        "Chunk 3..."]        [0.55, 0.23,         and metadata
                                              0.91, ...]]
```

**Code path:** `src/api/routes/documents.py` → `src/rag/chain.py:ingest_document()`
→ `src/rag/ingestion.py` → `src/llm/base.py:get_embedding()` → `src/vectorstore/base.py:store_vectors()`

#### Phase 2: Query (happens when you ask a question)

```
"What is the refund policy?"
    │
    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Embed the   │ ──▶ │  Search for  │ ──▶ │  Build prompt│ ──▶ │  LLM generates│
│  question    │     │  similar     │     │  with context│     │  answer       │
│  (same model)│     │  chunks      │     │  + question  │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       ↓                    ↓                    ↓                     ↓
  [0.82, -0.15,        ["Chunk 2:          "System: Answer     "Refunds are
   0.43, ...]           Refunds are         from context...     processed within
                        processed           Context: Refunds    14 days..."
                        within 14           are processed..."
                        days..."]
```

**Code path:** `src/api/routes/chat.py` → `src/rag/chain.py:query()`
→ `src/llm/base.py:get_embedding()` → `src/vectorstore/base.py:search()`
→ `src/rag/prompts.py` → `src/llm/base.py:generate()`

### How to learn

1. **Understand each step** — walk through the pipeline above
2. **Build a minimal RAG** — use this project as your guided example
3. **Read**: [RAG paper](https://arxiv.org/abs/2005.11401) (the original research)
4. **Experiment**: Upload different documents, ask questions, see what works

---

## OpenTelemetry

### What is it?

OpenTelemetry (OTel) is a **standard for application observability**. It collects
**traces** (what happened during a request), **metrics** (counters, latencies),
and **logs** — then sends them to monitoring tools.

### Why do we need it for AI apps?

AI apps have unique monitoring needs:

| What to monitor | Why |
|---|---|
| LLM latency | Models can be slow (2-30 seconds) |
| Token usage | Directly impacts cost |
| Retrieval quality | Bad retrieval = bad answers |
| Error rates | Models can fail (rate limits, timeouts) |
| Cost per request | Each chat message costs money |

### Where is it used in this project?

| File | What it does |
|---|---|
| `src/monitoring/metrics.py` | Custom `MetricsCollector` — tracks tokens, latency, costs |
| `src/api/middleware/logging.py` | Adds request_id and latency to every request |
| `pyproject.toml` | `opentelemetry-instrumentation-fastapi` — auto-instruments routes |

### How to learn

1. **Start with our custom metrics** — read `src/monitoring/metrics.py`
2. **Understand traces** — a trace = one request flowing through multiple services
3. **Free tools**: [Jaeger](https://www.jaegertracing.io/) (open-source trace viewer)
4. **CloudWatch / Application Insights** — our deployment targets already collect metrics

---

## Pydantic for AI

### What you might not know

You know Pydantic for FastAPI request/response validation. In AI projects,
Pydantic also:

1. **Validates LLM configuration** — ensures temperature is 0.0–2.0, max_tokens is
   reasonable, model names are valid
2. **Structures LLM output** — parse the model's text response into typed Python objects
3. **Manages settings** — `pydantic-settings` loads env vars with type validation

### Where is it used in this project?

| File | AI-specific use |
|---|---|
| `src/config.py` | `Settings` class — validates all cloud config (endpoints, keys, model names) |
| `src/api/models.py` | `TokenUsage` — structured token counts with cost estimation |
| `src/api/models.py` | `SourceChunk` — typed representation of retrieved document chunks |
| `src/api/models.py` | `ChatResponse` — ensures the API always returns consistent format |

### Key pattern: Settings with validation

```python
# src/config.py — this is how we safely manage AI config:

class Settings(BaseSettings):
    # Pydantic validates these at startup — typos and missing values
    # cause a clear error instead of a cryptic runtime failure

    aws_bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    llm_temperature: float = 0.1          # Pydantic ensures this is a float
    llm_max_tokens: int = 2048            # Pydantic ensures this is an int
    chunk_size: int = 500                 # Configuration, not hardcoded
    chunk_overlap: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",                  # Load from .env file
        env_file_encoding="utf-8",
    )
```

---

## Document Processing

### pypdf

A **pure Python** PDF reader. No system dependencies (unlike pdfminer or
poppler). We use it to extract text from uploaded PDFs.

```python
# src/rag/ingestion.py — what happens:
from pypdf import PdfReader

reader = PdfReader(io.BytesIO(pdf_bytes))
text = ""
for page in reader.pages:
    text += page.extract_text() or ""
# text = "Contents of the entire PDF as a string"
```

### python-docx

Reads `.docx` files (Microsoft Word). Extracts paragraphs as text:

```python
from docx import Document

doc = Document(io.BytesIO(docx_bytes))
text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
```

### Why do we need document processing?

LLMs work with **text**. PDFs and DOCX files contain text + formatting +
images + tables. We need to extract just the text before we can create
embeddings or send it to the LLM.

---

## Vector Databases

### OpenSearch Serverless (AWS)

OpenSearch is primarily a **search engine** (like Elasticsearch). AWS added
a **k-NN plugin** that turns it into a vector database.

```python
# src/vectorstore/aws_opensearch.py — simplified:

# The index has a "knn_vector" field type
index_body = {
    "mappings": {
        "properties": {
            "embedding": {
                "type": "knn_vector",           # ← This is the magic
                "dimension": 1024,              # Must match your embedding model
                "method": {
                    "name": "hnsw",             # Algorithm for fast search
                    "engine": "nmslib",
                }
            }
        }
    }
}

# Search = find vectors closest to the query embedding
search_body = {
    "query": {
        "knn": {
            "embedding": {
                "vector": query_embedding,      # [0.82, -0.15, ...]
                "k": 5                          # Return top 5 closest
            }
        }
    }
}
```

### Azure AI Search

Similar concept, different API. Azure calls it "vectorized query":

```python
# src/vectorstore/azure_ai_search.py — simplified:

from azure.search.documents.models import VectorizedQuery

vector_query = VectorizedQuery(
    vector=query_embedding,           # [0.82, -0.15, ...]
    k_nearest_neighbors=5,            # Return top 5
    fields="embedding",               # Which field to search
)

results = search_client.search(
    search_text=None,                 # No keyword search
    vector_queries=[vector_query],    # Only vector search
)
```

### How to learn

1. **Start with ChromaDB** (free, local, no cloud needed):

   ```bash
   pip install chromadb
   python -c "
   import chromadb
   client = chromadb.Client()
   collection = client.create_collection('test')
   collection.add(
       documents=['Refund policy is 14 days', 'Free shipping over 50 euros'],
       ids=['doc1', 'doc2']
   )
   results = collection.query(query_texts=['How do I return an item?'], n_results=1)
   print(results['documents'])  # → [['Refund policy is 14 days']]
   "
   ```

2. ChromaDB handles embeddings automatically — great for learning
3. Then move to OpenSearch or AI Search for production

---

## Tokens and Context Windows

### What is a token?

A token is how LLMs "read" text. It's roughly ¾ of a word:

```
Text:    "The refund policy states that returns are accepted within 14 days"
Tokens:  [The] [ref] [und] [policy] [states] [that] [returns] [are] [accepted]
         [within] [14] [days]
= 12 tokens for 11 words
```

### Why do tokens matter?

1. **Cost** — you pay per token (input + output)
2. **Context window** — there's a maximum total tokens per request
3. **Speed** — more tokens = slower response

### Token estimation in this project

```python
# src/rag/chain.py — we estimate costs:

# Rough rule: 1 token ≈ 4 characters
estimated_tokens = len(text) / 4

# Claude 3 Sonnet pricing:
cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)
```

### Token budgeting for a RAG query

```
Context window: 200,000 tokens (Claude 3 Sonnet)

System prompt:        ~200 tokens
Retrieved chunks:   ~2,000 tokens (5 chunks × 400 tokens each)
Conversation history: ~500 tokens
User question:        ~50 tokens
───────────────────────────────────
Total input:       ~2,750 tokens
Max output:         2,048 tokens (we set this limit)
───────────────────────────────────
Total:             ~4,800 tokens per request
Cost:              ~$0.003 per request (~0.3 cents)
```

---

## Recommended Learning Path

Here's the order I'd recommend learning these technologies, building on what
you already know:

### Week 1: Foundations (no cloud cost)

| Day | Topic | Activity |
|---|---|---|
| 1-2 | What are LLMs? | Chat with ChatGPT/Claude, understand tokens, temperature |
| 3 | Embeddings | Run the `sentence-transformers` example above |
| 4 | Vector search | Try ChromaDB locally (example above) |
| 5 | Prompt engineering | Write 10 different prompts, compare outputs |

### Week 2: LangChain (no cloud cost)

| Day | Topic | Activity |
|---|---|---|
| 1-2 | Text splitting | Use `RecursiveCharacterTextSplitter` on various documents |
| 3 | Chains | Build a simple chain with LangChain |
| 4-5 | Mini RAG | Build a local RAG with ChromaDB + free model |

### Week 3: Cloud Integration (minimal cost ~$1-2)

| Day | Topic | Activity |
|---|---|---|
| 1-2 | AWS Bedrock | Enable Bedrock, try the playground, call from Python |
| 3-4 | Azure OpenAI | Deploy a model, try Azure OpenAI Studio, call from Python |
| 5 | Compare | Run same question through both, compare answers |

### Week 4: This Project (minimal cost ~$2-5)

| Day | Topic | Activity |
|---|---|---|
| 1 | Setup | Clone this repo, `poetry install`, configure `.env` |
| 2 | Ingest | Upload a PDF, watch the logs, understand the pipeline |
| 3 | Query | Ask questions, check sources, understand retrieval |
| 4 | Debug | Set breakpoints (see `docs/debugging-guide.md`), step through |
| 5 | Modify | Change the prompt, adjust chunk size, see what improves |

---

## Free Resources

### Courses (all free)

| Resource | What you'll learn | Time |
|---|---|---|
| [DeepLearning.AI: LangChain for LLM Application Development](https://www.deeplearning.ai/short-courses/langchain-for-llm-application-development/) | LangChain fundamentals | 1 hour |
| [DeepLearning.AI: Building Systems with ChatGPT](https://www.deeplearning.ai/short-courses/building-systems-with-chatgpt/) | Prompt engineering, chains | 1 hour |
| [DeepLearning.AI: LangChain Chat with Your Data](https://www.deeplearning.ai/short-courses/langchain-chat-with-your-data/) | RAG pattern specifically | 1 hour |
| [AWS: Introduction to Amazon Bedrock](https://explore.skillbuilder.aws/learn/courses/17508) | Bedrock basics | 1 hour |
| [Microsoft: Azure OpenAI Service](https://learn.microsoft.com/en-us/training/modules/explore-azure-openai/) | Azure OpenAI basics | 1 hour |
| [Prompt Engineering Guide](https://www.promptingguide.ai/) | All prompt techniques | Self-paced |

### Documentation

| Resource | URL |
|---|---|
| LangChain docs | [python.langchain.com/docs](https://python.langchain.com/docs/introduction/) |
| OpenAI API reference | [platform.openai.com/docs](https://platform.openai.com/docs/) |
| AWS Bedrock docs | [docs.aws.amazon.com/bedrock](https://docs.aws.amazon.com/bedrock/) |
| Azure OpenAI docs | [learn.microsoft.com/azure/ai-services/openai](https://learn.microsoft.com/en-us/azure/ai-services/openai/) |
| ChromaDB docs | [docs.trychroma.com](https://docs.trychroma.com/) |
| OpenSearch k-NN | [opensearch.org/docs/latest/search-plugins/knn](https://opensearch.org/docs/latest/search-plugins/knn/) |

### YouTube channels

| Channel | Why |
|---|---|
| **James Briggs** | Best LangChain tutorials, practical RAG examples |
| **Fireship** | Fast overviews of AI concepts (100-second format) |
| **ArjanCodes** | Clean Python + AI architecture patterns |
| **TechWithTim** | Beginner-friendly Python AI tutorials |

### Books (optional, for deeper understanding)

| Book | Level |
|---|---|
| *Build a Large Language Model (From Scratch)* — Sebastian Raschka | Advanced |
| *Designing Machine Learning Systems* — Chip Huyen | Intermediate |
| *AI Engineering* — Chip Huyen | Intermediate |

---

## Glossary

Quick reference for AI terms you'll see in this project:

| Term | Meaning | Where in this project |
|---|---|---|
| **Embedding** | List of numbers representing text meaning | `src/llm/base.py:get_embedding()` |
| **Vector** | Same as embedding (the list of numbers) | `src/vectorstore/base.py` |
| **Chunk** | A piece of a document (~500 chars) | `src/rag/ingestion.py` |
| **Token** | Smallest unit LLMs process (~¾ word) | `src/api/models.py:TokenUsage` |
| **Context window** | Max tokens per LLM request | `src/config.py:llm_max_tokens` |
| **Temperature** | Randomness control (0=deterministic) | `src/config.py:llm_temperature` |
| **RAG** | Retrieve context, then generate answer | `src/rag/chain.py` |
| **Hallucination** | LLM makes up incorrect information | Prevented by our prompts |
| **Similarity search** | Find vectors closest to a query | `src/vectorstore/base.py:search()` |
| **Cosine similarity** | Math formula to compare vectors | Used inside vector stores |
| **k-NN** | k-Nearest Neighbours algorithm | `src/vectorstore/aws_opensearch.py` |
| **HNSW** | Fast approximate vector search algorithm | OpenSearch index configuration |
| **Prompt** | Instructions + context sent to the LLM | `src/rag/prompts.py` |
| **Inference** | Running a trained model to get predictions | Every LLM API call |
| **Fine-tuning** | Retraining a model on your data (we don't do this) | Alternative to RAG |
| **Converse API** | AWS Bedrock's unified LLM interface | `src/llm/aws_bedrock.py` |
| **Completion** | The LLM's generated response | `src/llm/azure_openai.py` |
