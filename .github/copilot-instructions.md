# Copilot Instructions — RAG Chatbot

## Project Overview

Enterprise-grade **Retrieval-Augmented Generation (RAG)** chatbot built with FastAPI.
Multi-cloud: deployable to **AWS** (Bedrock + OpenSearch), **Azure** (Azure OpenAI + AI Search), or **locally** (Ollama + ChromaDB).

**Owner**: Ketan Sahu (ketan-odido)

## Tech Stack

- **Language**: Python 3.12
- **Framework**: FastAPI + Uvicorn
- **Package Manager**: Poetry
- **LLM Orchestration**: LangChain
- **LLM Providers**: AWS Bedrock (Claude), Azure OpenAI (GPT-4o), Ollama (llama3.2)
- **Vector Stores**: AWS OpenSearch, Azure AI Search, ChromaDB (local)
- **Storage**: AWS S3, Azure Blob Storage, local filesystem
- **Conversation History**: AWS DynamoDB, Azure Cosmos DB, in-memory
- **Monitoring**: OpenTelemetry, Prometheus, Loguru
- **Infrastructure**: Terraform (AWS + Azure modules)
- **CI/CD**: GitHub Actions (ci.yml, deploy-aws.yml, deploy-azure.yml)
- **Linting**: Ruff (line-length 120, Python 3.12 target)
- **Testing**: pytest + pytest-asyncio + pytest-cov (146 tests)
- **Pre-commit**: ruff lint + format, YAML/TOML checks, trailing whitespace

## Project Structure

```
src/
├── api/            # FastAPI routes and middleware
├── config.py       # Pydantic Settings configuration
├── evaluation/     # RAG evaluation framework (retrieval, faithfulness, relevance)
├── guardrails/     # Content safety (Azure AI Content Safety)
├── history/        # Conversation history (DynamoDB, Cosmos DB, in-memory)
├── llm/            # Abstract LLM interface + providers (Bedrock, Azure OpenAI, Ollama)
├── main.py         # App entrypoint
├── monitoring/     # OpenTelemetry, Prometheus metrics, token tracking
├── rag/            # RAG chain orchestrator (factory, ingest, query)
├── storage/        # Document storage (S3, Blob, local)
├── ui/             # Jinja2 templates for web UI
└── vectorstore/    # Abstract vector store + providers (OpenSearch, AI Search, ChromaDB)
tests/              # Unit, integration, E2E tests
infra/              # Terraform modules (AWS + Azure)
scripts/            # Helper scripts
docs/               # Comprehensive documentation (architecture, AI engineering, labs)
```

## Coding Conventions

- **Style**: Follow Ruff rules — `E, F, I, W, UP, B, SIM, RUF` (E501 ignored)
- **Line length**: 120 characters max
- **Imports**: isort with `src` as known first-party
- **Type hints**: Use Python 3.12 type hints everywhere (no `Optional`, use `X | None`)
- **Config**: Use Pydantic Settings (`src/config.py`) for all configuration
- **Patterns**: Strategy pattern for LLM/vectorstore providers; factory pattern in RAG chain
- **Async**: Use async/await for API routes and I/O operations
- **Logging**: Use Loguru (not stdlib logging)
- **Error handling**: Raise specific exceptions; never silently swallow errors

## Testing

- Run tests: `poetry run pytest`
- Run with coverage: `poetry run pytest --cov=src`
- Lint: `poetry run ruff check src tests`
- Format check: `poetry run ruff format --check src tests`
- Test paths: `tests/` directory
- Async mode: `auto` (pytest-asyncio)
- AWS mocking: use `moto` for S3, DynamoDB, Lambda

## Common Tasks

- **Start locally**: `poetry run start` (or `uvicorn src.main:app --reload`)
- **Install deps**: `poetry install` (add `--extras local` for ChromaDB)
- **Add dependency**: `poetry add <package>`
- **Run pre-commit**: `poetry run pre-commit run --all-files`

## Preferences

- Prefer small, focused functions over large monoliths
- Write docstrings for public functions/classes
- Keep provider implementations behind abstract interfaces
- When adding a new provider, follow the existing strategy pattern
- Always add/update tests when changing functionality
- Use `httpx.AsyncClient` for async HTTP in tests
