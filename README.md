# RAG Chatbot — Enterprise Multi-Cloud AI Service

A production-grade **Retrieval-Augmented Generation (RAG)** chatbot built with FastAPI, deployable to both **AWS** and **Azure**.

This project demonstrates end-to-end AI engineering: document ingestion, vector search, LLM-powered answer generation, cloud-native deployment, CI/CD, monitoring, and cost-aware architecture.

---

## Quick Links

| Document | Description |
|---|---|
| [Getting Started](docs/getting-started.md) | Prerequisites, installation, first run — step by step |
| [Architecture Overview](docs/architecture.md) | System design, data flow, cloud-agnostic pattern |
| [AWS Services Deep Dive](docs/aws-services.md) | Every AWS service used, why, and how it works |
| [Azure Services Deep Dive](docs/azure-services.md) | Every Azure service used, why, and how it works |
| [Cost Analysis](docs/cost-analysis.md) | Per-service costs, free tier limits, monthly estimates, alternatives comparison |
| [Pydantic Models Guide](docs/pydantic-models.md) | Every model explained — what it is, every field, why it exists |
| [Poetry Guide](docs/poetry-guide.md) | How Poetry works in this project, every command explained |
| [Debugging Guide](docs/debugging-guide.md) | VS Code + PyCharm debugger setup, breakpoints, step-through |
| [Monitoring & Observability](docs/monitoring.md) | Metrics, dashboards, tracing, alerting |
| [CI/CD Pipeline](docs/cicd.md) | GitHub Actions — lint, test, build, deploy |
| [Terraform Infrastructure](docs/terraform.md) | IaC for AWS + Azure |
| [RAG Concepts](docs/rag-concepts.md) | What is RAG, embeddings, vector search, chunking — explained simply |
| [AI & ML Learning Guide](docs/ai-learning-guide.md) | Learn every AI technology in this project from scratch — with examples |
| [How Services Work — Under the Hood](docs/how-services-work.md) | Bedrock, OpenSearch, Azure OpenAI, AI Search — internal mechanics, API actions, data flow |
| [Thinking Like an AI Engineer](docs/ai-engineer-guide.md) | DE → AI Engineer mindset shift, evaluation framework, quality checklist, interview guide |
| [API Reference](docs/api-reference.md) | Every endpoint, request/response, examples |

---

## What Does This Project Do?

1. **You upload documents** (PDF, TXT, Markdown) → they get split into chunks and stored as vectors
2. **You ask a question** → the system finds the most relevant chunks from your documents
3. **An LLM reads those chunks** and generates a precise answer with source citations
4. **Everything is logged** — latency, token usage, retrieval quality, errors

It works identically on AWS (Bedrock + OpenSearch) and Azure (Azure OpenAI + AI Search). You pick the cloud at startup via an environment variable.

---

## Project Structure

```
rag-chatbot/
├── .github/workflows/          # CI/CD pipelines
├── docs/                       # Detailed documentation (start here)
├── infra/                      # Terraform (AWS + Azure)
├── src/                        # Application source code
│   ├── api/                    # FastAPI routes + middleware
│   ├── rag/                    # RAG pipeline (ingest, retrieve, generate)
│   ├── llm/                    # LLM providers (Bedrock, Azure OpenAI)
│   ├── vectorstore/            # Vector stores (OpenSearch, AI Search)
│   ├── storage/                # Document storage (S3, Blob)
│   ├── history/                # Conversation history (DynamoDB, CosmosDB)
│   ├── monitoring/             # Metrics, tracing, dashboards
│   └── ui/                     # Simple chat frontend
├── functions/                  # Serverless functions (Lambda, Azure Functions)
├── tests/                      # Unit + integration tests
├── data/                       # Drop your documents here
├── pyproject.toml              # Poetry dependencies
├── Dockerfile                  # Container image
└── docker-compose.yml          # Local dev environment
```

---

## Quick Start (30 seconds)

```bash
# 1. Clone
git clone <your-repo-url>
cd rag-chatbot

# 2. Install
poetry install

# 3. Configure
cp .env.example .env
# Edit .env with your API keys

# 4. Run
poetry run start
# → http://localhost:8000
```

See [Getting Started](docs/getting-started.md) for the full step-by-step guide.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| Framework | FastAPI |
| Package Manager | Poetry |
| LLM (AWS) | Amazon Bedrock (Claude 3.5 Sonnet) |
| LLM (Azure) | Azure OpenAI (GPT-4o) |
| Vector DB (AWS) | Amazon OpenSearch Serverless |
| Vector DB (Azure) | Azure AI Search |
| Document Storage (AWS) | Amazon S3 |
| Document Storage (Azure) | Azure Blob Storage |
| Conversation History (AWS) | Amazon DynamoDB |
| Conversation History (Azure) | Azure Cosmos DB |
| Monitoring | OpenTelemetry + CloudWatch / App Insights |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| Container | Docker → ECS Fargate / Azure Container Apps |

---

## Author

**Ketan Sahu** — Data Engineer → AI Engineer  
Built as a portfolio project demonstrating production-grade AI engineering across AWS and Azure.
