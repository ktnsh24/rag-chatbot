# CI/CD Pipelines — Deep Dive

> `Dockerfile` + `.github/workflows/` — Build, test, and deploy the RAG chatbot.

> **DE verdict: ★☆☆☆☆ — Standard CI/CD, nothing new.** Dockerfile is a multi-purpose
> Python container. GitHub Actions runs lint → test → build → deploy. The same patterns
> you use in any production Python project. The only thing to notice is _what_ gets deployed (an AI app) and
> which cloud-specific deployment steps differ.

> **Related docs:**
> - [Infrastructure Deep Dive](infra-explained.md) — the Terraform these pipelines apply
> - [Document Storage Deep Dive](storage-explained.md) — the S3/Blob resources created by infra
> - [Conversation History Deep Dive](history-explained.md) — the DynamoDB/Cosmos resources

---

## Table of Contents

- [CI/CD Pipelines — Deep Dive](#cicd-pipelines--deep-dive)
  - [Table of Contents](#table-of-contents)
  - [What This Module Does](#what-this-module-does)
  - [The Four Files](#the-four-files)
  - [Dockerfile — Building the Container](#dockerfile--building-the-container)
    - [What you already know (everything)](#what-you-already-know-everything)
    - [What to notice for an AI app](#what-to-notice-for-an-ai-app)
  - [ci.yml — Lint, Test, Build](#ciyml--lint-test-build)
    - [Job 1: Lint \& Format](#job-1-lint--format)
    - [Job 2: Unit Tests](#job-2-unit-tests)
    - [Job 3: Build Docker Image](#job-3-build-docker-image)
    - [Trigger rules](#trigger-rules)
  - [deploy-aws.yml — Deploy to ECS Fargate](#deploy-awsyml--deploy-to-ecs-fargate)
    - [Step-by-step](#step-by-step)
    - [What you already know](#what-you-already-know)
    - [Manual dispatch with environment choice](#manual-dispatch-with-environment-choice)
  - [deploy-azure.yml — Deploy to Container Apps](#deploy-azureyml--deploy-to-container-apps)
    - [Step-by-step](#step-by-step-1)
    - [Key differences from AWS](#key-differences-from-aws)
  - [AWS vs Azure — Deployment Comparison](#aws-vs-azure--deployment-comparison)
    - [Cost insight for AI apps](#cost-insight-for-ai-apps)
  - [The Pipeline Flow (End to End)](#the-pipeline-flow-end-to-end)
  - [DE vs AI Engineer — What Each Sees](#de-vs-ai-engineer--what-each-sees)
    - [Why manual deploy matters more for AI](#why-manual-deploy-matters-more-for-ai)
  - [Self-Check Questions](#self-check-questions)
    - [Answers](#answers)

---

## What This Module Does

One sentence: **Automates the path from code change to running application — lint,
test, build Docker image, push to registry, deploy to cloud.**

```
git push
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  CI Pipeline (automatic on push/PR)                  │
│                                                      │
│  [1] Lint (Ruff)  →  [2] Test (pytest)  →  [3] Build│
│      check code       run unit tests        Docker   │
│      formatting       + coverage            image    │
└──────────────────────────────────────────────────────┘
    │
    ▼ (manual trigger)
┌──────────────────────────────────────────────────────┐
│  Deploy Pipeline (manual dispatch)                   │
│                                                      │
│  [4] Push image  →  [5] Terraform  →  [6] Update    │
│      to ECR/ACR      apply             service       │
└──────────────────────────────────────────────────────┘
```

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## The Four Files

```
Dockerfile                          # Container definition
.github/workflows/
├── ci.yml                          # Lint + Test + Build (automatic)
├── deploy-aws.yml                  # Deploy to AWS ECS Fargate (manual)
└── deploy-azure.yml                # Deploy to Azure Container Apps (manual)
```

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Dockerfile — Building the Container

```dockerfile
FROM python:3.12-slim AS base

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Poetry install
RUN pip install poetry==1.8.4

# Dependencies (cached layer — changes rarely)
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev

# Application code (changes often)
COPY src/ ./src/
COPY data/ ./data/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### What you already know (everything)

| Line | Pattern | DE familiarity | 🚚 Courier |
| --- | --- | --- | --- |
| `python:3.12-slim` | Slim base image | ✅ Standard practice | A featherweight depot kit — just enough planks to hold the Python courier, no extra tack rooms slowing the build. |
| `poetry install --without dev` | Prod deps only | ✅ Standard — skip test/lint deps | Dry-run trip to check the harness — poetry install --without dev: Prod deps only · ✅ Standard — skip test/lint deps |
| `virtualenvs.create false` | No venv inside container | ✅ Standard — container IS the isolation | Stall that houses the worker — virtualenvs.create false: No venv inside container · ✅ Standard — container IS the isolation |
| Layer ordering (deps → code) | Cache optimization | ✅ Standard — deps change rarely, code changes often | Courier-side view of Layer ordering (deps → code) — affects how the courier loads, reads, or delivers the parcels |
| `HEALTHCHECK` | Container health endpoint | ✅ Standard — ECS/Container Apps use this | The bell on the depot door — ECS or Container Apps ring it every few seconds to check the courier is still breathing. |
| `uvicorn` CMD | ASGI server | ✅ Standard FastAPI deployment | Door the customer knocks on — uvicorn CMD: ASGI server · ✅ Standard FastAPI deployment |

### What to notice for an AI app

**The image is the same as any FastAPI service.** There's no special "AI Dockerfile"
— the AI logic lives in Python code that Poetry installs. The cloud embedding models and
LLMs are services called via API, not local models embedded in the container.

**Note on Local mode (`CLOUD_PROVIDER=local`):** The local provider uses Ollama
running as a separate process on the host machine — it's NOT bundled in the Docker
image. You'd run `ollama serve` on the host and the container calls it via HTTP at
`OLLAMA_BASE_URL`. For cloud deployments (Bedrock, Azure OpenAI), the Dockerfile
is standard. If you wanted Ollama **inside** the container, you'd need GPU support,
NVIDIA base images, and model weights (~5-15 GB) — that's a different architecture.

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## ci.yml — Lint, Test, Build

Three sequential jobs:

```
Job 1: lint        Job 2: test        Job 3: build
  │                  │                   │
  ├─ Ruff check      ├─ pytest           ├─ docker build
  └─ Ruff format     ├─ --cov=src        ├─ tag with SHA
                     └─ Upload coverage   └─ Save as artifact
```

### Job 1: Lint & Format

```yaml
- name: Run Ruff linter
  run: poetry run ruff check src/ tests/

- name: Run Ruff formatter check
  run: poetry run ruff format --check src/ tests/
```

Standard Ruff — the same linter used in any modern Python project. No AI-specific lint rules.

### Job 2: Unit Tests

```yaml
- name: Run tests with coverage
  run: poetry run pytest --cov=src --cov-report=xml --cov-report=term
```

Standard pytest with coverage. The tests themselves might mock AI services (Bedrock,
OpenAI), but the CI configuration is identical to any Python project.

### Job 3: Build Docker Image

```yaml
- name: Build image
  run: |
    docker build -t rag-chatbot:${{ github.sha }} .
    docker tag rag-chatbot:${{ github.sha }} rag-chatbot:latest
```

Tag with git SHA for traceability. Save as artifact for deployment pipelines.

### Trigger rules

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
```

Runs on every push to main/develop and every PR to main. Standard branch protection.

- 🚚 **Courier:** Sending the courier on 25 standard test deliveries (golden dataset) to verify it returns the right packages every time.

---

## deploy-aws.yml — Deploy to ECS Fargate

```
Manual trigger → Login to AWS → Build + Push to ECR → Terraform apply → Update ECS
```

### Step-by-step

```yaml
# 1. Authenticate to AWS (OIDC — no static credentials)
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: eu-central-1

# 2. Login to ECR
- uses: aws-actions/amazon-ecr-login@v2

# 3. Build and push Docker image
- run: |
    docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
    docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

# 4. Apply Terraform (create/update infra)
- working-directory: infra/aws
  run: terraform apply -auto-approve -var="environment=dev" -var="image_tag=${{ github.sha }}"

# 5. Force ECS to pick up the new image
- run: aws ecs update-service --cluster rag-chatbot-dev --service rag-chatbot --force-new-deployment
```

### What you already know

| Step | DE familiarity | 🚚 Courier |
| --- | --- | --- |
| OIDC auth (`role-to-assume`) | ✅ Standard GitHub Actions pattern | Automated harness rig — OIDC auth (role-to-assume): ✅ Standard GitHub Actions pattern |
| ECR login + push | ✅ Standard container deployment | Robot depot-hand logs into the ECR address and pushes the freshly built courier image. |
| Terraform apply in CI | ✅ Standard — same pattern everywhere | Robot depot-hand re-applies the Terraform depot blueprint on every merge — same pattern across providers. |
| ECS force-new-deployment | ✅ Standard — triggers rolling update | Mechanical groom — ECS force-new-deployment: ✅ Standard — triggers rolling update |

### Manual dispatch with environment choice

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [dev, stg]
```

Deploy is **manual** (not automatic on push). This is a deliberate choice for a
portfolio project — you don't want accidental deploys to cloud resources that cost money.

- 🚚 **Courier:** The AWS depot — DynamoDB and OpenSearch serve as the GPS-indexed warehouse and trip-log database for couriers running the cloud route.

---

## deploy-azure.yml — Deploy to Container Apps

```
Manual trigger → Login to Azure → Login to ACR → Build + Push → Terraform apply → Update Container App
```

### Step-by-step

```yaml
# 1. Authenticate to Azure (OIDC — federated identity)
- uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

# 2. Login to ACR
- run: az acr login --name ${{ secrets.ACR_NAME }}

# 3. Build and push Docker image
- run: |
    docker build -t $ACR_NAME.azurecr.io/rag-chatbot:${{ github.sha }} .
    docker push $ACR_NAME.azurecr.io/rag-chatbot:${{ github.sha }}

# 4. Apply Terraform
- working-directory: infra/azure
  run: terraform apply -auto-approve -var="environment=dev" -var="image_tag=${{ github.sha }}"

# 5. Update Container App with new image
- run: az containerapp update --name rag-chatbot-dev --resource-group rag-chatbot-dev-rg \
       --image $ACR_NAME.azurecr.io/rag-chatbot:${{ github.sha }}
```

### Key differences from AWS

| Step | AWS | Azure | 🚚 Courier |
| --- | --- | --- | --- |
| Auth | `role-to-assume` (1 secret) | `client-id` + `tenant-id` + `subscription-id` (3 secrets) | AWS unlocks the depot address with a single role; Azure needs three IDs to reach the same door. |
| Registry login | `amazon-ecr-login` action | `az acr login` CLI | Action versus CLI — both authenticate the robot depot-hand against the registry address before pushing. |
| Image URL | `$ECR_REGISTRY/$ECR_REPOSITORY:$TAG` | `$ACR_NAME.azurecr.io/rag-chatbot:$TAG` | Full registry address where the courier's Docker image is tagged — ECR path on AWS, ACR FQDN on Azure. |
| Deploy | `aws ecs update-service --force-new-deployment` | `az containerapp update --image` | Robot dispatch clerk — Deploy: aws ecs update-service --force-new-deployment · az containerapp update --image |

- 🚚 **Courier:** The Azure hub — Azure AI Search and Cosmos DB serve as the GPS-indexed warehouse and trip-log database for couriers on the Azure route.

---

## AWS vs Azure — Deployment Comparison

| Aspect | AWS (ECS Fargate) | Azure (Container Apps) | 🚚 Courier |
| --- | --- | --- | --- |
| **Container hosting** | ECS Fargate | Azure Container Apps | Same idea, different barn brand — both run the courier-shaped container without you owning the timber. |
| **Registry** | ECR | ACR | ECR or ACR — the cloud-specific address where the built courier image is stored. |
| **Auth method** | OIDC → IAM role | OIDC → service principal | Depot keys — only authorised callers may ask the courier to deliver |
| **Secrets needed** | 1 (`AWS_ROLE_ARN`) | 4 (`CLIENT_ID`, `TENANT_ID`, `SUBSCRIPTION_ID`, `ACR_NAME`) | AWS reaches the registry with one ARN; Azure needs four secrets to authenticate to the same address. |
| **Deploy command** | `aws ecs update-service` | `az containerapp update` | Automated harness rig — Deploy command: aws ecs update-service · az containerapp update |
| **Scaling** | ECS auto-scaling (configured in task def) | Built-in scaling rules | Always-on courier stall — container that keeps the depot up 24/7 |
| **Cost (idle)** | Fargate charges per vCPU-hour | Container Apps can scale to zero | Fargate keeps the courier saddled on the clock; Container Apps lets it nap for free until a customer rings. |
| **Cost (1 vCPU, 2GB)** | ~$30/month (always running) | ~$0/month (scale to zero) | Depot's monthly feed bill — Cost (1 vCPU, 2GB): ~$30/month (always running) · ~$0/month (scale to zero) |

### Cost insight for AI apps

Azure Container Apps can **scale to zero** — $0 when nobody is using the chatbot.
ECS Fargate charges for running time even with zero traffic. For a portfolio project
with sporadic usage, Azure's scale-to-zero saves money.

- 🚚 **Courier:** The AWS depot — DynamoDB and OpenSearch serve as the GPS-indexed warehouse and trip-log database for couriers running the cloud route.

---

## The Pipeline Flow (End to End)

```
Developer makes a code change
    │
    ▼
git push to main
    │
    ▼
┌────────────────────────────────────────┐
│  CI Pipeline (ci.yml) — AUTOMATIC      │
│                                        │
│  Job 1: Ruff lint + format check       │
│          ↓ (passes)                    │
│  Job 2: pytest --cov                   │
│          ↓ (passes)                    │
│  Job 3: docker build + save artifact   │
│                                        │
│  Time: ~3 minutes                      │
└────────────────────────────────────────┘
    │
    │  Developer clicks "Run workflow" for deploy-aws or deploy-azure
    │
    ▼
┌────────────────────────────────────────┐
│  Deploy Pipeline — MANUAL              │
│                                        │
│  Step 1: Auth to cloud (OIDC)          │
│  Step 2: Login to registry (ECR/ACR)   │
│  Step 3: Build + push Docker image     │
│  Step 4: Terraform apply (infra)       │
│  Step 5: Update container service      │
│                                        │
│  Time: ~5 minutes                      │
└────────────────────────────────────────┘
    │
    ▼
Application running with new code
    │
    ▼
Health check passes → /api/health returns 200
```

- 🚚 **Courier:** The step-by-step route map showing every checkpoint the courier passes from question intake to answer delivery.

---

## DE vs AI Engineer — What Each Sees

| Aspect | What a DE sees | What an AI Engineer sees | 🚚 Courier |
| --- | --- | --- | --- |
| Dockerfile | Standard Python container | Cloud models = small image (~500MB). Local mode calls Ollama externally (not in container). Bundling models inside container would be 10GB+ with GPU deps | Small depot on wheels — the courier lives in the cloud, so the container only needs to phone its API |
| `HEALTHCHECK` | Container health | AI-specific: checks connections to LLM, vector store, not just HTTP 200 | Asks "is the courier awake, is the warehouse reachable, is the GPS stamper ready?" — not just "is the door open?" |
| CI lint + test | Standard quality gates | Tests mock AI services — real LLM calls would cost money per CI run | Robot dispatch clerk uses a fake courier during tests so every CI run doesn't burn real fuel |
| Deploy Terraform | Standard infra-as-code | Creates AI-specific resources (Bedrock IAM, OpenSearch if added) | Blueprints raise the depot plus AI-only fittings — Bedrock permissions for the courier, an OpenSearch warehouse if needed |
| Manual deploy | Safety measure | Essential for AI — deploying a broken prompt to production can cause embarrassing LLM outputs | A human opens the gate before a new shipping manifest ships — one bad prompt can spoil every customer reply |
| Image tag = git SHA | Traceability | Rollback is critical — a bad prompt change can degrade all AI responses | Instructions tucked in the pannier — Image tag = git SHA: Traceability · Rollback is critical — a bad prompt change can degrade all AI |

### Why manual deploy matters more for AI

In traditional apps, a bug usually affects one endpoint or feature. In AI apps, a
bad change to `prompts.py` or `chain.py` can make **every single response** worse.
Manual deploy gives you a gate to validate the AI behaviour before going live.

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Self-Check Questions

Test your understanding:

1. **Why does the Dockerfile install Poetry instead of using pip directly?** What's the benefit?
2. **Why is `virtualenvs.create false` set in the Dockerfile?** What would happen without it?
3. **The CI pipeline has 3 jobs: lint → test → build. Why this order?** What if you swapped test and build?
4. **Why is deploy manual (`workflow_dispatch`) instead of automatic on push to main?**
5. **How many GitHub secrets does the AWS deploy need vs Azure deploy?** Why the difference?
6. **What's the difference between `aws ecs update-service` and `az containerapp update`?**
7. **The project supports `CLOUD_PROVIDER=local` with Ollama running externally. If you wanted Ollama INSIDE the container instead, how would the Dockerfile change?**

### Answers

1. Poetry manages dependencies from `pyproject.toml` + `poetry.lock` — reproducible builds with exact version pinning. pip with `requirements.txt` works but doesn't handle dependency resolution as well.
2. Without `virtualenvs.create false`, Poetry creates a `.venv` inside the container — wasting disk space and adding confusion. The container IS the isolation; you don't need a venv inside it.
3. Lint is fastest (~10s) — fail fast on formatting issues. Test is next (~30s) — catch bugs. Build is slowest (~2min) — only build if code is clean and tests pass. Swapping test and build wastes time building images that might fail tests.
4. Cloud resources cost money. Automatic deploy on every push could trigger unwanted charges. Manual dispatch gives the developer control over when to spend money.
5. AWS: 1 secret (`AWS_ROLE_ARN`). Azure: 4 secrets (`CLIENT_ID`, `TENANT_ID`, `SUBSCRIPTION_ID`, `ACR_NAME`). AWS bundles auth into one IAM role ARN; Azure requires separate identity components.
6. Functionally equivalent — both tell the container service to pull and run a new image version. `ecs update-service --force-new-deployment` triggers a rolling update. `containerapp update --image` does the same for Container Apps.
7. You'd need: (a) NVIDIA CUDA base image instead of `python:3.12-slim`, (b) model weights downloaded or mounted (~5-15 GB), (c) GPU runtime configured, (d) image size ~10-15 GB instead of ~500 MB. The current setup keeps Ollama as an external process — the container calls it via HTTP at `OLLAMA_BASE_URL`, keeping the Docker image small.

- 🚚 **Courier:** A quick quiz for the trainee dispatch clerk — answer these to confirm the key courier delivery concepts have landed.
