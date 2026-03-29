# Getting Started — Step by Step

## Table of Contents

- [What you need before starting](#what-you-need-before-starting)
- [Step 1 — Install Python 3.12](#step-1--install-python-312)
- [Step 2 — Install Poetry](#step-2--install-poetry)
- [Step 3 — Clone the repository](#step-3--clone-the-repository)
- [Step 4 — Create the virtual environment](#step-4--create-the-virtual-environment)
- [Step 5 — Install dependencies](#step-5--install-dependencies)
- [Step 6 — Configure environment variables](#step-6--configure-environment-variables)
- [Step 7 — Connect to AWS](#step-7--connect-to-aws)
- [Step 8 — Connect to Azure](#step-8--connect-to-azure)
- [Step 9 — Start the server](#step-9--start-the-server)
- [Step 10 — Upload your first document](#step-10--upload-your-first-document)
- [Step 11 — Ask your first question](#step-11--ask-your-first-question)
- [Troubleshooting](#troubleshooting)

---

## What you need before starting

| Tool | Version | Why you need it |
| --- | --- | --- |
| **Python** | 3.12+ | The app is written in Python |
| **Poetry** | 1.8+ | Package manager (manages dependencies + virtual environment) |
| **Git** | 2.40+ | Version control |
| **AWS CLI** | 2.x | Connect to AWS services |
| **Azure CLI** | 2.x | Connect to Azure services |
| **Docker** | 24+ | Build container images (optional, for deployment) |
| **Terraform** | 1.5+ | Deploy infrastructure (optional, for deployment) |
| **VS Code** or **PyCharm** | Latest | IDE with debugger |

### Check what is already installed

Run these commands to check what you already have:

```bash
python3 --version      # Need 3.12+
poetry --version       # Need 1.8+
git --version          # Need 2.40+
aws --version          # Need 2.x
az --version           # Need 2.x
docker --version       # Optional
terraform --version    # Optional
```

---

## Step 1 — Install Python 3.12

### On Ubuntu / WSL

```bash
# Add the deadsnakes PPA (has newer Python versions)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# Install Python 3.12
sudo apt install python3.12 python3.12-venv python3.12-dev

# Verify
python3.12 --version
# → Python 3.12.x
```

### On macOS

```bash
brew install python@3.12
python3.12 --version
```

### Why Python 3.12?

- Latest stable version with full type hint support
- Better error messages than older versions
- Required by some dependencies (Pydantic v2 works best on 3.12+)

---

## Step 2 — Install Poetry

### What is Poetry?

Poetry is a **Python package manager**. It replaces `pip` + `requirements.txt` + `venv` with a single tool.

Think of it like:
- `pip install` → `poetry add`
- `requirements.txt` → `pyproject.toml` (what you want) + `poetry.lock` (exact versions)
- `python -m venv .venv` → Poetry creates it automatically

### Install Poetry

```bash
# Official installer (recommended)
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH (add this to your ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"

# Verify
poetry --version
# → Poetry (version 1.8.x)
```

### Configure Poetry for this project

```bash
# Tell Poetry to create the virtual environment inside the project folder
# This creates .venv/ in the project root (makes VS Code auto-detect it)
poetry config virtualenvs.in-project true

# Tell Poetry to use Python 3.12
poetry env use python3.12
```

### Why `virtualenvs.in-project true`?

By default, Poetry creates virtual environments in `~/.cache/pypoetry/virtualenvs/`.
Setting `in-project = true` creates `.venv/` inside the project folder.

Why this matters:
- VS Code and PyCharm auto-detect `.venv/` in the project root
- You can see exactly which packages are installed
- Each project has its own isolated environment
- Easy to delete and recreate: `rm -rf .venv && poetry install`

See [Poetry Guide](poetry-guide.md) for the full deep dive on how Poetry works in this project.

---

## Step 3 — Clone the repository

```bash
cd ~/maestro  # or wherever you keep your projects
git clone <your-repo-url> rag-chatbot
cd rag-chatbot
```

---

## Step 4 — Create the virtual environment

```bash
# Poetry creates the .venv/ folder and installs Python 3.12 into it
poetry env use python3.12

# Verify
poetry env info
# Should show:
#   Virtualenv
#   Python:   3.12.x
#   Path:     /home/ketan-odido/maestro/rag-chatbot/.venv
```

### What is a virtual environment?

A virtual environment is an **isolated Python installation**. When you run `poetry install`, packages are installed into `.venv/` — not your system Python.

Why?
- Project A needs `pydantic==2.9` and Project B needs `pydantic==1.10`
- Without venvs, you can only have one version installed
- With venvs, each project has its own isolated packages

---

## Step 5 — Install dependencies

```bash
poetry install
```

What this does:
1. Reads `pyproject.toml` (your dependency list)
2. Resolves compatible versions of all packages
3. Creates `poetry.lock` (locks exact versions)
4. Installs everything into `.venv/`

You should see output like:

```
Installing dependencies from lock file

Package operations: 87 installs, 0 updates, 0 removals

  - Installing pydantic-core (2.23.4)
  - Installing pydantic (2.9.2)
  - Installing fastapi (0.115.2)
  ...
```

### Activate the virtual environment

```bash
source .venv/bin/activate
```

You will see `(rag-chatbot-py3.12)` at the start of your terminal prompt.

To deactivate later:

```bash
deactivate
```

---

## Step 6 — Configure environment variables

```bash
# Copy the example file
cp .env.example .env

# Open in your editor
code .env   # VS Code
# or
nano .env   # Terminal editor
```

### Minimum configuration for AWS

```bash
CLOUD_PROVIDER=aws
APP_ENV=dev
AWS_REGION=eu-central-1
AWS_BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Minimum configuration for Azure

```bash
CLOUD_PROVIDER=azure
APP_ENV=dev
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

### Load the .env file

The app loads `.env` automatically via Pydantic Settings. But if you need the variables in your terminal:

```bash
set -a && source .env && set +a
```

---

## Step 7 — Connect to AWS

### 7a. Install AWS CLI

```bash
# Ubuntu / WSL
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version
```

### 7b. Configure AWS credentials

You have two options:

**Option A: Access keys (simplest for personal account)**

```bash
aws configure
# AWS Access Key ID: <paste your key>
# AWS Secret Access Key: <paste your secret>
# Default region name: eu-central-1
# Default output format: json
```

Get your access keys from: AWS Console → IAM → Users → Your User → Security credentials → Create access key

**Option B: SSO (if your account uses AWS Organizations)**

```bash
aws configure sso --profile rag-chatbot
# SSO session name: rag-chatbot
# SSO start URL: https://your-org.awsapps.com/start
# SSO region: eu-central-1
# Account ID: <your account id>
# Role name: <your role>
# CLI default region: eu-central-1
```

### 7c. Enable Bedrock model access

Bedrock models are not enabled by default. You need to request access:

1. Go to AWS Console → Amazon Bedrock → Model access
2. Click "Manage model access"
3. Enable:
   - **Anthropic → Claude 3.5 Sonnet v2** (for LLM)
   - **Amazon → Titan Text Embeddings V2** (for embeddings)
4. Wait for approval (usually instant for personal accounts)

### 7d. Verify AWS connectivity

```bash
aws sts get-caller-identity
# Should show your account ID and ARN

aws bedrock list-foundation-models --region eu-central-1 --query "modelSummaries[?contains(modelId, 'claude')].[modelId]" --output table
# Should list Claude models
```

### Cost-saving tip for AWS

- **Bedrock**: Pay-per-token only. No idle costs. A typical development session costs < $1.
- **S3**: First 5 GB free. Practically free for document storage.
- **DynamoDB**: Pay-per-request mode. Free tier: 25 GB + 25 WCU + 25 RCU.
- **⚠️ OpenSearch Serverless**: ~$350/month minimum. **Do NOT create this for development.**
  - For local development, use ChromaDB (free, in-memory) instead.
  - Only deploy OpenSearch when you're ready for production.

---

## Step 8 — Connect to Azure

### 8a. Install Azure CLI

```bash
# Ubuntu / WSL
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az --version
```

### 8b. Login to Azure

```bash
az login
# Opens a browser — sign in with your Azure account
# Returns your subscription details

# Set the active subscription (if you have multiple)
az account set --subscription "your-subscription-id"
```

### 8c. Create Azure OpenAI resource

1. Go to Azure Portal → Create a resource → "Azure OpenAI"
2. Select your subscription and resource group
3. Region: **West Europe** (cheapest in EU)
4. Pricing tier: **Standard S0**
5. After creation, go to the resource → Keys and Endpoint
6. Copy the **Endpoint** and **Key 1** to your `.env` file

### 8d. Deploy models in Azure OpenAI

1. Go to Azure AI Studio (https://ai.azure.com)
2. Select your Azure OpenAI resource
3. Go to Deployments → Create deployment
4. Deploy:
   - **gpt-4o** (for LLM) — deployment name: `gpt-4o`
   - **text-embedding-3-small** (for embeddings) — deployment name: `text-embedding-3-small`

### 8e. Verify Azure connectivity

```bash
az account show
# Should show your subscription

# Test Azure OpenAI
curl -X POST "https://your-resource.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview" \
  -H "api-key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}], "max_tokens": 10}'
```

### Cost-saving tips for Azure

- **Azure OpenAI**: Pay-per-token. Development costs < $1/day.
- **Blob Storage**: First 5 GB free (LRS). Practically free.
- **Cosmos DB Serverless**: Pay per RU. Free tier available (1000 RU/s + 25 GB).
- **Azure AI Search Free tier**: Free (50 MB, 3 indexes) — perfect for development.
- **⚠️ Azure AI Search Basic**: ~$75/month. Only upgrade when you need more than 50 MB.

---

## Step 9 — Start the server

```bash
# Make sure venv is activated
source .venv/bin/activate

# Start with auto-reload (restarts when you change code)
poetry run uvicorn src.main:app --reload --port 8000

# Or use the shortcut
poetry run start
```

You should see:

```
INFO     Starting rag-chatbot
INFO     Environment: dev
INFO     Cloud Provider: aws
INFO     Port: 8000
INFO     Startup complete — ready to serve requests
INFO     Uvicorn running on http://0.0.0.0:8000
```

Open in your browser:
- **Chat UI**: http://localhost:8000/static/index.html
- **Swagger docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/api/health

---

## Step 10 — Upload your first document

Using Swagger UI (http://localhost:8000/docs):

1. Find `POST /api/documents/upload`
2. Click "Try it out"
3. Click "Choose File" and select a PDF or TXT file
4. Click "Execute"

Using curl:

```bash
# Upload a text file
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@/path/to/your/document.pdf"
```

Expected response:

```json
{
  "document_id": "abc-123",
  "filename": "document.pdf",
  "status": "ready",
  "chunk_count": 45,
  "message": "Successfully ingested document.pdf into 45 searchable chunks."
}
```

---

## Step 11 — Ask your first question

Using Swagger UI:

1. Find `POST /api/chat`
2. Click "Try it out"
3. Enter:
   ```json
   {
     "question": "What is this document about?"
   }
   ```
4. Click "Execute"

Using curl:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?"}'
```

Expected response:

```json
{
  "answer": "Based on the uploaded documents, this document covers...",
  "sources": [
    {
      "document_name": "document.pdf",
      "chunk_text": "...",
      "relevance_score": 0.89,
      "page_number": 3
    }
  ],
  "session_id": "session-uuid",
  "latency_ms": 1250,
  "token_usage": {
    "input_tokens": 1500,
    "output_tokens": 300,
    "total_tokens": 1800,
    "estimated_cost_usd": 0.009
  }
}
```

---

## Troubleshooting

### "Import could not be resolved"

Poetry didn't install to the right venv. Fix:

```bash
rm -rf .venv
poetry env use python3.12
poetry install
source .venv/bin/activate
```

### "RAG chain not initialized"

Cloud credentials are missing or wrong. Check:

```bash
# AWS
aws sts get-caller-identity

# Azure
az account show
```

### "ModuleNotFoundError"

Virtual environment not activated. Run:

```bash
source .venv/bin/activate
which python  # Should point to .venv/bin/python
```

### Port 8000 already in use

```bash
# Find what's using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use a different port
poetry run uvicorn src.main:app --reload --port 9000
```
