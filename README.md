# RAG Chatbot — Enterprise Multi-Provider AI Service

A production-grade **Retrieval-Augmented Generation (RAG)** chatbot built with FastAPI, deployable to **AWS**, **Azure**, or **locally** with Ollama + ChromaDB.

This project demonstrates end-to-end AI engineering: document ingestion, vector search, LLM-powered answer generation, evaluation, cost-aware architecture, cloud-native deployment, CI/CD, monitoring, and production observability.

---

## Quick Links

### Getting Started

| Document | Description |
|---|---|
| [Getting Started](docs/setup-and-tooling/getting-started.md) | Prerequisites, installation, first run — step by step |
| [Poetry Guide](docs/setup-and-tooling/poetry-guide.md) | How Poetry works in this project, every command explained |
| [Debugging Guide](docs/setup-and-tooling/debugging-guide.md) | VS Code + PyCharm debugger setup, breakpoints, step-through |
| [Terraform Infrastructure](docs/setup-and-tooling/terraform-guide.md) | IaC for AWS + Azure |

### Architecture & Design

| Document | Description |
|---|---|
| [Architecture Overview](docs/architecture-and-design/architecture.md) | System design, data flow, cloud-agnostic pattern |
| [AWS Services Deep Dive](docs/architecture-and-design/aws-services.md) | Every AWS service used, why, and how it works |
| [Azure Services Deep Dive](docs/architecture-and-design/azure-services.md) | Every Azure service used, why, and how it works |
| [How Services Work — Under the Hood](docs/architecture-and-design/how-services-work.md) | Bedrock, OpenSearch, Azure OpenAI, AI Search — internal mechanics |
| [API Routes Explained](docs/architecture-and-design/api-routes-explained.md) | Every endpoint explained with data flow diagrams |
| [CI/CD Pipeline](docs/architecture-and-design/cicd-explained.md) | GitHub Actions — lint, test, build, deploy |
| [Storage Explained](docs/architecture-and-design/storage-explained.md) | S3, Blob Storage, and local storage patterns |
| [Conversation History](docs/architecture-and-design/history-explained.md) | DynamoDB, Cosmos DB, and in-memory history |
| [Infrastructure Explained](docs/architecture-and-design/infra-explained.md) | Terraform modules and deployment architecture |

### AI Engineering

| Document | Description |
|---|---|
| [RAG Concepts](docs/ai-engineering/rag-concepts.md) | What is RAG, embeddings, vector search, chunking — explained simply |
| [Cost Analysis](docs/ai-engineering/cost-analysis.md) | Per-service costs, free tier limits, monthly estimates |
| [LLM Interface Deep Dive](docs/ai-engineering/llm-interface-deep-dive.md) | The abstract LLM interface and strategy pattern |
| [LLM Providers Deep Dive](docs/ai-engineering/llm-providers-deep-dive.md) | Bedrock (Claude), Azure OpenAI (GPT-4o), Ollama (llama3.2) |
| [Vector Store Interface Deep Dive](docs/ai-engineering/vectorstore-interface-deep-dive.md) | The abstract vector store interface |
| [Vector Store Providers Deep Dive](docs/ai-engineering/vectorstore-providers-deep-dive.md) | OpenSearch, Azure AI Search, ChromaDB |
| [Ingestion Pipeline Deep Dive](docs/ai-engineering/ingestion-pipeline-deep-dive.md) | Read → chunk → embed → store pipeline |
| [Prompt Engineering Deep Dive](docs/ai-engineering/prompts-deep-dive.md) | System prompts, rules, template variables |
| [RAG Chain Deep Dive](docs/ai-engineering/rag-chain-deep-dive.md) | The central orchestrator — factory, ingest, query |
| [Evaluation Framework Deep Dive](docs/ai-engineering/evaluation-framework-deep-dive.md) | Retrieval, faithfulness, relevance scoring |
| [Golden Dataset Deep Dive](docs/ai-engineering/golden-dataset-deep-dive.md) | Test fixtures for AI regression testing |
| [Metrics Deep Dive](docs/ai-engineering/metrics-deep-dive.md) | Token tracking, latency, cost monitoring |

### Hands-On Labs

| Document | Description |
|---|---|
| [Phase 1 — Foundation](docs/hands-on-labs/hands-on-labs-phase-1.md) | Labs 1-3: Setup, first query, document ingestion |
| [Phase 2 — Core RAG](docs/hands-on-labs/hands-on-labs-phase-2.md) | Labs 4-5: Evaluation, multi-provider comparison |
| [Phase 3 — Production](docs/hands-on-labs/hands-on-labs-phase-3.md) | Labs 6-8: Monitoring, CI/CD, cost optimisation |
| [Phase 4 — Advanced](docs/hands-on-labs/hands-on-labs-phase-4.md) | Labs 9-13: Guardrails, re-ranking, hybrid search, HNSW |
| [Phase 5 — Observability](docs/hands-on-labs/hands-on-labs-phase-5.md) | Labs 14-16: Query logging, tracing, golden dataset |

### Testing

| Document | Description |
|---|---|
| [Testing Strategy & Inventory](docs/ai-engineering/testing.md) | 146 tests — unit, integration, E2E, feature flags |

### Reference

| Document | Description |
|---|---|
| [API Reference](docs/reference/api-reference.md) | Every endpoint, request/response, examples |
| [Pydantic Models Guide](docs/reference/pydantic-models.md) | Every model explained — every field, why it exists |
| [Monitoring & Observability](docs/reference/monitoring.md) | Metrics, dashboards, tracing, alerting |

---

## What Does This Project Do?

1. **You upload documents** (PDF, TXT, Markdown) → they get split into chunks and stored as vectors
2. **You ask a question** → the system finds the most relevant chunks from your documents
3. **An LLM reads those chunks** and generates a precise answer with source citations
4. **Everything is measured** — latency, token usage, retrieval quality, faithfulness, cost

It works on **three providers**, selected at startup via `CLOUD_PROVIDER` environment variable:

| Provider | LLM | Vector Store | Cost |
|---|---|---|---|
| **AWS** | Bedrock (Claude 3.5 Sonnet) | OpenSearch Serverless | ~$0.0065/query |
| **Azure** | Azure OpenAI (GPT-4o) | Azure AI Search | ~$0.005/query |
| **Local** | Ollama (llama3.2) | ChromaDB | **$0/query** |

### Advanced Features

| Feature | What it does | Story |
|---|---|---|
| **Guardrails** | Prompt injection detection + PII redaction (email, SSN, credit card) | I23 |
| **Re-ranking** | Cross-encoder re-scoring for better retrieval precision | I24 |
| **Hybrid Search** | BM25 keyword + vector semantic search fusion | I25 |
| **Bulk Upload** | Batch document ingestion with progress tracking | I26 |
| **HNSW Tuning** | Vector index parameter optimisation | I28 |
| **Query Logging** | Structured JSONL per-query logging with slow-query detection | I30 |
| **OpenTelemetry** | Distributed tracing + Prometheus metrics endpoint | I31 |

All features are **toggleable** via environment variables (`GUARDRAILS_ENABLED`, `RERANKER_ENABLED`, `HYBRID_SEARCH_ENABLED`).

---

## Project Structure

```
rag-chatbot/
├── .github/workflows/          # CI/CD pipelines
├── docs/                       # Documentation (organised by topic)
│   ├── ai-engineering/         #   RAG concepts, deep-dives, cost analysis, testing
│   ├── architecture-and-design/#   Architecture, cloud services, API routes
│   │   └── api-routes/         #   Per-endpoint deep-dives (6 docs)
│   ├── hands-on-labs/          #   5 phases, 16 labs, 50 automated experiments
│   ├── reference/              #   API reference, models, monitoring
│   └── setup-and-tooling/      #   Getting started, Poetry, debugging, Terraform
├── infra/                      # Terraform (AWS + Azure)
├── src/                        # Application source code
│   ├── api/                    #   FastAPI routes + middleware + models
│   │   ├── routes/             #   health.py, chat.py, documents.py, queries.py, metrics.py
│   │   └── middleware/         #   Error handling, logging, guardrails
│   ├── config.py               #   Pydantic Settings (all env vars)
│   ├── rag/                    #   RAG pipeline
│   │   ├── chain.py            #   Central orchestrator (factory + ingest + query)
│   │   ├── ingestion.py        #   Read → chunk → embed → store
│   │   ├── prompts.py          #   System prompts + template variables
│   │   ├── reranker.py         #   Cross-encoder re-ranking (I24)
│   │   └── hybrid_search.py    #   BM25 + vector fusion (I25)
│   ├── llm/                    #   LLM providers
│   │   ├── base.py             #   Abstract interface
│   │   ├── aws_bedrock.py      #   Claude 3.5 Sonnet via Bedrock
│   │   ├── azure_openai.py     #   GPT-4o via Azure OpenAI
│   │   └── local_ollama.py     #   llama3.2 via Ollama (local)
│   ├── vectorstore/            #   Vector stores
│   │   ├── base.py             #   Abstract interface
│   │   ├── aws_opensearch.py   #   Amazon OpenSearch Serverless
│   │   ├── azure_ai_search.py  #   Azure AI Search
│   │   └── local_chromadb.py   #   ChromaDB (local)
│   ├── evaluation/             #   RAG quality evaluation
│   │   ├── evaluator.py        #   Retrieval + faithfulness + relevance scoring
│   │   └── golden_dataset.py   #   Test fixtures (known Q&A pairs)
│   ├── storage/                #   Document storage (S3, Blob, local)
│   ├── history/                #   Conversation history (DynamoDB, CosmosDB)
│   ├── monitoring/             #   Metrics collection, query logging, OTel tracing
│   │   ├── metrics.py          #   In-memory MetricsCollector
│   │   ├── query_logger.py     #   Structured JSONL per-query logging (I30)
│   │   └── tracing.py          #   OpenTelemetry + Prometheus setup (I31)
│   ├── guardrails/             #   Input/output safety (I23)
│   │   ├── base.py             #   Abstract guardrail interface
│   │   ├── aws_guardrails.py   #   AWS Comprehend-based guardrails
│   │   ├── azure_guardrails.py #   Azure Content Safety guardrails
│   │   └── local_guardrails.py #   Regex-based (no cloud, $0)
│   └── ui/                     #   Simple chat frontend
├── scripts/                    # Lab runner + utilities
│   ├── run_all_labs.py         #   50 automated experiments across 5 phases
│   ├── run_cloud_labs.sh       #   One-command cloud deploy → run → destroy
│   ├── lab_analysis.py         #   Report generation + analysis
│   ├── config/                 #   Test data configuration (YAML)
│   │   └── test-data/          #   YAML configs per document
│   │       └── test-policy.yaml#   Default config (copy to use your own doc)
│   └── test-data/              #   Input documents
│       └── test-policy.txt     #   Default test document (refund policy)
├── tests/                      # 146 tests (unit + integration + E2E)
├── data/                       # Drop your documents here
├── pyproject.toml              # Poetry dependencies
├── Dockerfile                  # Container image
└── .env.example                # Environment variable template
```

---

## Quick Start

### Option 1: Local (no cloud, no cost)

```bash
# 1. Install Ollama and pull models
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
ollama pull nomic-embed-text

# 2. Install dependencies
poetry install

# 3. Configure
cp .env.example .env
# Set CLOUD_PROVIDER=local in .env

# 4. Run
poetry run uvicorn src.main:app --reload
# → http://localhost:8000
```

### Option 2: AWS or Azure

```bash
# 1. Install dependencies
poetry install

# 2. Configure
cp .env.example .env
# Set CLOUD_PROVIDER=aws (or azure) and add API keys/endpoints

# 3. Deploy + run all labs + destroy (automated)
./scripts/run_cloud_labs.sh --provider aws --email you@example.com

# Custom budget limit (default €5)
./scripts/run_cloud_labs.sh --provider aws --email you@example.com --cost-limit 15

# Use your own document instead of test-policy.txt
./scripts/run_cloud_labs.sh --provider aws --email you@example.com \
  --test-config scripts/config/test-data/my-document.yaml
```

Results saved to `scripts/lab_results/<local|aws|azure>/`.

See [Getting Started](docs/setup-and-tooling/getting-started.md) for the full step-by-step guide (Step 7 = Local, Step 8 = AWS, Step 9 = Azure).

---

## Tech Stack

| Layer | AWS | Azure | Local |
|---|---|---|---|
| **Language** | Python 3.12 | Python 3.12 | Python 3.12 |
| **Framework** | FastAPI | FastAPI | FastAPI |
| **Package Manager** | Poetry | Poetry | Poetry |
| **LLM** | Bedrock (Claude 3.5 Sonnet) | Azure OpenAI (GPT-4o) | Ollama (llama3.2) |
| **Embeddings** | Titan Embed Text v2 (1024-dim) | text-embedding-3-small (1536-dim) | nomic-embed-text (768-dim) |
| **Vector Store** | OpenSearch Serverless | Azure AI Search | ChromaDB |
| **Document Storage** | S3 | Blob Storage | Local filesystem |
| **Conversation History** | DynamoDB | Cosmos DB | In-memory |
| **Monitoring** | CloudWatch | App Insights | Console / Prometheus |
| **IaC** | Terraform | Terraform | — |
| **CI/CD** | GitHub Actions | GitHub Actions | — |
| **Container** | Docker → ECS Fargate | Docker → Container Apps | Docker (optional) |

---

## Evaluation

The project includes a rule-based evaluation framework (no LLM needed):

| Dimension | Weight | What it measures |
|---|---|---|
| **Retrieval** | 30% | Did the vector store return relevant chunks? |
| **Faithfulness** | 40% | Is the answer grounded in the context (no hallucination)? |
| **Answer Relevance** | 30% | Does the answer address the actual question? |

A **golden dataset** of 25 test cases across 7 categories covers happy paths, edge cases, PII handling, prompt injection, and adversarial inputs. Run it before every deploy to catch regressions.

📖 See [Evaluation Framework Deep Dive](docs/ai-engineering/evaluation-framework-deep-dive.md) and [Golden Dataset Deep Dive](docs/ai-engineering/golden-dataset-deep-dive.md).

---

## Documentation Structure

All documentation is in `docs/` organised by topic:

```
docs/
├── ai-engineering/                     ← RAG concepts, deep-dives, cost analysis, testing
│   ├── rag-concepts.md                 ← What is RAG? (start here if new to AI)
│   ├── *-deep-dive.md                  ← 10 deep-dive docs (one per source file)
│   ├── cost-analysis.md                ← Per-provider cost breakdown
│   └── testing.md                      ← 146 tests: unit, integration, E2E, feature flags
├── architecture-and-design/            ← System design, cloud services, API routes
│   ├── architecture.md                 ← Architecture overview
│   └── api-routes/                     ← 6 per-endpoint deep-dives
├── hands-on-labs/                      ← 5 phases, 16 labs
│   ├── hands-on-labs-phase-1.md        ← Foundation (Labs 1-3)
│   ├── hands-on-labs-phase-2.md        ← Core RAG (Labs 4-5)
│   ├── hands-on-labs-phase-3.md        ← Production (Labs 6-8)
│   ├── hands-on-labs-phase-4.md        ← Advanced (Labs 9-13) — guardrails, re-ranking, hybrid
│   └── hands-on-labs-phase-5.md        ← Observability (Labs 14-16)
├── reference/                          ← API reference, models, monitoring
└── setup-and-tooling/                  ← Getting started, Poetry, debugging
```

**Recommended reading order:**

1. [RAG Concepts](docs/ai-engineering/rag-concepts.md) — understand the fundamentals
2. [Architecture](docs/architecture-and-design/architecture.md) — see how it all fits together
3. [Getting Started](docs/setup-and-tooling/getting-started.md) — run it locally
4. [Testing](docs/ai-engineering/testing.md) — how the codebase is tested

