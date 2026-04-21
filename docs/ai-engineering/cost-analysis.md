# Cost Analysis — AWS vs Azure, Free Tiers, and Alternatives

## Table of Contents

- [Monthly cost summary](#monthly-cost-summary)
- [Service-by-service breakdown](#service-by-service-breakdown)
  - [LLM Inference](#llm-inference)
  - [Embeddings](#embeddings)
  - [Vector Store](#vector-store)
  - [Document Storage](#document-storage)
  - [Conversation History (Database)](#conversation-history-database)
  - [Container Hosting](#container-hosting)
  - [Container Registry](#container-registry)
  - [CI/CD Pipeline](#cicd-pipeline)
- [Free tier limits](#free-tier-limits)
- [Cost for personal account (your setup)](#cost-for-personal-account-your-setup)
- [Alternative pipelines — Why they cost more](#alternative-pipelines--why-they-cost-more)
  - [Alternative 1: AWS SageMaker instead of Bedrock](#alternative-1-aws-sagemaker-instead-of-bedrock)
  - [Alternative 2: AWS Kendra instead of OpenSearch](#alternative-2-aws-kendra-instead-of-opensearch)
  - [Alternative 3: Azure Cognitive Services instead of Azure OpenAI](#alternative-3-azure-cognitive-services-instead-of-azure-openai)
  - [Alternative 4: Self-hosted open source LLM (EC2/VM)](#alternative-4-self-hosted-open-source-llm-ec2vm)
  - [Alternative 5: AWS Step Functions + Lambda for orchestration](#alternative-5-aws-step-functions--lambda-for-orchestration)
  - [Alternative 6: Azure Data Factory for document pipeline](#alternative-6-azure-data-factory-for-document-pipeline)
  - [Alternative 7: EKS/AKS (Kubernetes) instead of Fargate/Container Apps](#alternative-7-eksaks-kubernetes-instead-of-fargatecontainer-apps)
  - [Alternative 8: AWS Glue for document ETL](#alternative-8-aws-glue-for-document-etl)
- [Decision summary table](#decision-summary-table)
- [How to minimize costs on your personal account](#how-to-minimize-costs-on-your-personal-account)
- [Cost of running run_all_labs.py on cloud](#cost-of-running-run_all_labspy-on-cloud)

---

## Monthly cost summary

### Development (your personal account)

| Service | AWS Cost/month | Azure Cost/month | Notes |
| --- | --- | --- | --- |
| LLM (pay-per-use) | ~$2–5 | ~$2–5 | Based on ~100 queries/day |
| Embeddings | ~$0.10 | ~$0.10 | Very cheap |
| Vector Store | **$0 (local)** | **$0 (Free tier)** | Use ChromaDB locally / Free AI Search |
| Document Storage | $0 (Free tier) | $0 (Free tier) | S3: 5 GB free, Blob: 5 GB free |
| Database | $0 (Free tier) | $0 (Free tier) | DynamoDB: 25 GB free, Cosmos: Free tier |
| Container Hosting | $0 (local) | $0 (local) | Run locally during development |
| **Total** | **~$2–5/month** | **~$2–5/month** | Mostly LLM token costs |

### Production (small scale: ~1000 queries/day)

| Service | AWS Cost/month | Azure Cost/month |
| --- | --- | --- |
| LLM | ~$50–100 | ~$40–80 |
| Embeddings | ~$1–2 | ~$1–2 |
| Vector Store | ~$350 (OpenSearch) | ~$75 (AI Search Basic) |
| Document Storage | ~$1 | ~$1 |
| Database | ~$5 (DynamoDB) | ~$5 (Cosmos) |
| Container Hosting | ~$30 (Fargate) | ~$20 (Container Apps) |
| Container Registry | ~$1 (ECR) | ~$5 (ACR Basic) |
| Monitoring | $0 (CloudWatch free tier) | $0 (App Insights free) |
| **Total** | **~$440/month** | **~$150/month** |

> **Key insight:** Azure is significantly cheaper for production because Azure AI Search Basic ($75/month) is much cheaper than OpenSearch Serverless (~$350/month minimum).

---

## Service-by-service breakdown

### LLM Inference

| | AWS (Bedrock - Claude 3.5 Sonnet v2) | Azure (Azure OpenAI - GPT-4o) | Local (Ollama - llama3.2) |
| --- | --- | --- | --- |
| **Input tokens** | $0.003 / 1K tokens | $0.0025 / 1K tokens | **$0** |
| **Output tokens** | $0.015 / 1K tokens | $0.01 / 1K tokens | **$0** |
| **Free tier** | None | None | Free forever |
| **Minimum cost** | $0 (pay per token) | $0 (pay per token) | $0 (runs on your machine) |
| **Per query (typical)** | ~$0.013 | ~$0.01 | **$0** |

**Why we chose this:**
- Pay-per-token = no idle costs (cloud)
- No GPU instances to manage (cloud)
- Best-in-class models (cloud)
- $0 cost for development and experimentation (local)
- Both cloud options are cheaper than OpenAI direct ($0.0025/$0.01 vs $0.005/$0.015 for GPT-4o)

### Embeddings

| | AWS (Titan Embeddings v2) | Azure (text-embedding-3-small) | Local (Ollama - nomic-embed-text) |
| --- | --- | --- | --- |
| **Cost** | $0.00002 / 1K tokens | $0.00002 / 1K tokens | **$0** |
| **Dimensions** | 1024 | 1536 | 768 |
| **Free tier** | None | None | Free forever |

**Both are extremely cheap.** A 100-page PDF with 500 chunks costs ~$0.01 to embed.

### Vector Store

**This is the most expensive service — and where choices matter most.**

| Option | Cost/month | Min cost | Managed? | Scales to zero? | Best for |
| --- | --- | --- | --- | --- | --- |
| **AWS OpenSearch Serverless** | ~$350+ | $350 (4 OCUs) | Yes | **No** (always on) | Production (>10K chunks) |
| **AWS DynamoDB (brute-force)** | **~$0** | $0 (free tier) | Yes | Yes (pay-per-request) | **Portfolio, dev, testing** |
| **Azure AI Search Free** | $0 | $0 | Yes | N/A (free) | Development |
| **Azure AI Search Basic** | $75 | $75 | Yes | No | Production |
| **ChromaDB (local)** | $0 | $0 | No (self-hosted) | N/A | Local development |
| **Pinecone Starter** | $0 | $0 (Free tier) | Yes | Yes | Quick prototypes |
| **Qdrant Cloud Free** | $0 | $0 (1 GB) | Yes | Yes | Quick prototypes |

**What we chose and why:**

- **Development:** ChromaDB (local, free, no cloud needed)
- **AWS (cheap):** DynamoDB + brute-force cosine (`VECTOR_STORE_TYPE=dynamodb`) — $0/month, suitable for < 10,000 chunks
- **AWS Production:** OpenSearch Serverless (expensive but fully managed and battle-tested for scale)
- **Azure Production:** AI Search Basic (good balance of cost and features)

**⚠️ WARNING about OpenSearch Serverless:**
The minimum is 4 OCUs (2 indexing + 2 search) at $0.24/hr each = **$0.96/hr = ~$700/month**.
Even with activity-based scaling, the minimum when your collection exists is ~$350/month.
**Do NOT create an OpenSearch Serverless collection for development.**
Use `VECTOR_STORE_TYPE=dynamodb` instead — same Bedrock LLM, same S3 storage, but $0/month for vector search.

**How DynamoDB vector search works:**
DynamoDB stores each chunk with its embedding as a JSON string. On search, all vectors for the collection are loaded and cosine similarity is computed in Python using numpy. This is O(n) — fine for < 10,000 chunks (~50ms), too slow for 100K+ chunks. See [`src/vectorstore/aws_dynamodb.py`](../../src/vectorstore/aws_dynamodb.py) and the [Vector Store Providers Deep Dive](vectorstore-providers-deep-dive.md#aws-dynamodb-the-cheap-alternative--0month-vector-store) for the full implementation.

### Document Storage

| | AWS S3 | Azure Blob Storage |
| --- | --- | --- |
| **Storage** | $0.023/GB/month | $0.02/GB/month (LRS) |
| **Free tier** | 5 GB (12 months) | 5 GB (12 months) |
| **PUT requests** | $0.005/1K | $0.005/1K |
| **GET requests** | $0.0004/1K | $0.0004/1K |

**Both are essentially free** for a personal project. 1000 documents at 1 MB each = 1 GB = ~$0.02/month.

### Conversation History (Database)

| | AWS DynamoDB | Azure Cosmos DB |
| --- | --- | --- |
| **Mode** | Pay-per-request | Serverless |
| **Read cost** | $1.25/million reads | ~$0.25/million RU |
| **Write cost** | $1.25/million writes | ~$0.25/million RU |
| **Free tier** | 25 GB + 25 RCU + 25 WCU | 1000 RU/s + 25 GB |

**Both have generous free tiers.** A personal project will stay well within free limits.

### Container Hosting

| | AWS ECS Fargate | Azure Container Apps |
| --- | --- | --- |
| **vCPU** | $0.04048/hr | $0.000024/sec (~$0.086/hr) |
| **Memory** | $0.004445/GB/hr | $0.000003/GB/sec |
| **Minimum** | ~$30/month (0.25 vCPU, 0.5 GB) | ~$20/month (0.25 vCPU, 0.5 GB) |
| **Scales to zero?** | No (min 1 task) | **Yes** (0 replicas when idle) |

**Azure Container Apps is cheaper because it can scale to zero.**

### Container Registry

| | AWS ECR | Azure ACR |
| --- | --- | --- |
| **Storage** | $0.10/GB/month | $0.167/GB/month (Basic) |
| **Free tier** | 500 MB (private, 12 months) | None |
| **Tier** | Pay per GB | $5/month (Basic) |

### CI/CD Pipeline

| GitHub Actions | Free tier |
| --- | --- |
| **Public repos** | Unlimited minutes |
| **Private repos** | 2,000 minutes/month |
| **Cost beyond free** | $0.008/minute (Linux) |

**Free for most personal projects.**

---

## Free tier limits

### AWS Free Tier (12 months)

| Service | Free amount |
| --- | --- |
| S3 | 5 GB storage, 20K GET, 2K PUT |
| DynamoDB | 25 GB, 25 RCU, 25 WCU |
| Lambda | 1M invocations, 400K GB-seconds |
| CloudWatch | 10 metrics, 5 GB logs, 3 dashboards |
| ECR | 500 MB |
| Bedrock | **No free tier** (pay per token) |
| OpenSearch Serverless | **No free tier** ($350+/month) |

### Azure Free Tier

| Service | Free amount |
| --- | --- |
| Blob Storage | 5 GB LRS |
| Cosmos DB | 1000 RU/s + 25 GB |
| AI Search | Free tier (50 MB, 3 indexes) |
| Azure Functions | 1M executions/month |
| App Insights | 5 GB logs/month |
| Azure OpenAI | **No free tier** (pay per token) |
| Container Apps | First 180K vCPU-seconds free/month |

---

## Cost for personal account (your setup)

### Recommended minimal setup

Since you want to save money, here's the cheapest way to run this project:

| Component | Choice | Cost |
| --- | --- | --- |
| LLM | Bedrock (Claude) OR Azure OpenAI (GPT-4o) | ~$2–5/month |
| Embeddings | Same provider as LLM | ~$0.10/month |
| Vector Store | **ChromaDB (local)** or Azure AI Search **Free** | **$0** |
| Document Storage | S3 Free or Blob Free | **$0** |
| Database | DynamoDB Free or Cosmos Free | **$0** |
| Hosting | **Run locally** (no cloud hosting) | **$0** |
| **Total** | | **~$2–5/month** |

### What to avoid

| Service | Why to avoid for personal use |
| --- | --- |
| OpenSearch Serverless | $350+/month minimum — use `VECTOR_STORE_TYPE=dynamodb` or ChromaDB instead |
| ECS Fargate | $30+/month — run locally instead |
| Azure AI Search Basic | $75/month — use Free tier instead |
| NAT Gateway (AWS) | $32/month — easy to create accidentally |
| Elastic IP (AWS) | $3.60/month if not attached — delete unused ones |

---

## Alternative pipelines — Why they cost more

### Alternative 1: AWS SageMaker instead of Bedrock

| | Bedrock (our choice) | SageMaker |
| --- | --- | --- |
| **Model hosting** | Managed (no instances) | You manage instances |
| **Min cost** | $0 (pay per token) | ~$100/month (ml.g5.xlarge) |
| **Scaling** | Automatic | Manual or auto-scaling |
| **GPU management** | None | You handle it |
| **When to use SageMaker** | Custom/fine-tuned models | |

**Why Bedrock is better here:**
SageMaker requires always-on GPU instances ($1.006/hr for g5.xlarge = ~$730/month).
Bedrock is serverless — you only pay when you make API calls.
SageMaker makes sense when you need a custom-trained model, not for off-the-shelf Claude/Titan.

### Alternative 2: AWS Kendra instead of OpenSearch

| | OpenSearch Serverless (our choice) | Kendra |
| --- | --- | --- |
| **Type** | General vector search | Enterprise search (RAG-focused) |
| **Min cost** | ~$350/month | ~$810/month (Developer Edition) |
| **Features** | Raw vector similarity | Semantic search, connectors |
| **RAG integration** | Manual (you build the pipeline) | Built-in RAG features |

**Why OpenSearch is better here:**
Kendra is more powerful but starts at $810/month. For a portfolio project, OpenSearch (or ChromaDB) gives you more control and costs less.

### Alternative 3: Azure Cognitive Services instead of Azure OpenAI

| | Azure OpenAI (our choice) | Cognitive Services |
| --- | --- | --- |
| **LLM quality** | GPT-4o (state-of-the-art) | No LLM capability |
| **Text analysis** | Via LLM prompts | Pre-built NLP models |
| **RAG support** | Full RAG pipeline | Not designed for RAG |

**Why Azure OpenAI is better:**
Cognitive Services doesn't have a conversational LLM. It does text analytics (sentiment, entities) but can't generate answers from context.

### Alternative 4: Self-hosted open source LLM (EC2/VM)

| | Bedrock/Azure OpenAI (our choice) | Self-hosted (Llama 3) |
| --- | --- | --- |
| **GPU cost** | $0 idle | ~$730/month (g5.xlarge) |
| **Quality** | GPT-4o / Claude (best) | Good but not as strong |
| **Maintenance** | None | You manage everything |
| **Latency** | ~1–3 seconds | ~2–5 seconds |

**Why managed is better:**
Self-hosting requires a GPU instance running 24/7 (~$730/month for AWS, ~$600/month for Azure).
You also handle model updates, CUDA drivers, and memory management.
Unless you need complete data isolation, managed APIs are cheaper and easier.

### Alternative 5: AWS Step Functions + Lambda for orchestration

| | FastAPI (our choice) | Step Functions + Lambda |
| --- | --- | --- |
| **Architecture** | Monolith (simple) | Microservices (complex) |
| **Min cost** | $30/month (Fargate) | ~$5/month (Lambda free tier) |
| **Complexity** | Low | High (state machines, IAM, etc.) |
| **Latency** | ~1s (in-memory) | ~3–5s (cold starts + state transitions) |

**Why FastAPI is better for a portfolio project:**
Step Functions are excellent for event-driven workflows but add complexity that doesn't benefit a RAG chatbot. The latency from Lambda cold starts and state machine transitions makes the user experience worse. For a real-time chat API, a single FastAPI service is simpler and faster.

**When Step Functions would be better:**
If you had a complex document ingestion pipeline with multiple stages (OCR → translate → summarize → chunk → embed), Step Functions would be ideal for managing retries and parallel processing.

### Alternative 6: Azure Data Factory for document pipeline

| | Direct upload (our choice) | Data Factory |
| --- | --- | --- |
| **Purpose** | Simple file upload → ingest | Complex ETL pipelines |
| **Min cost** | $0 | ~$50/month (pipeline runs) |
| **Use case** | Upload via API | Scheduled batch processing |

**When Data Factory would be better:**
If documents came from 10 different sources (SharePoint, Salesforce, databases) on a schedule, Data Factory would orchestrate those pipelines. For a single-upload API, it's overkill.

### Alternative 7: EKS/AKS (Kubernetes) instead of Fargate/Container Apps

| | Fargate / Container Apps (our choice) | EKS / AKS (Kubernetes) |
| --- | --- | --- |
| **Management** | Serverless containers | You manage the cluster |
| **Min cost** | ~$20–30/month | ~$75/month (EKS) / ~$100/month (AKS) |
| **Scaling** | Automatic | Auto-scaling (more config) |
| **Complexity** | Low | High (kubectl, helm, etc.) |

**Why serverless containers are better here:**
Kubernetes is designed for teams running dozens of microservices. For a single FastAPI app, EKS/AKS adds $75–100/month in cluster costs plus significant operational complexity. Fargate and Container Apps give you the same benefits (containerized, scalable) without the overhead.

### Alternative 8: AWS Glue for document ETL

| | Lambda (our choice) | Glue |
| --- | --- | --- |
| **Purpose** | Lightweight event processing | Heavy ETL (Spark) |
| **Min cost** | Free tier (1M invocations) | ~$0.44/DPU-hour |
| **Startup time** | ~1s (cold start) | ~2–5 min (Spark cluster) |

**Why Lambda is better:**
Glue spins up a full Spark cluster for each job. A single document ingestion takes seconds in Lambda but minutes in Glue (just for cluster startup). Glue makes sense when processing millions of records, not individual document uploads.

---

## Decision summary table

| Decision | Chosen | Alternative | Why chosen wins |
| --- | --- | --- | --- |
| LLM | Bedrock / Azure OpenAI / **Ollama (dev)** | SageMaker / Self-hosted | $0 idle vs $730/month GPU |
| Vector Store | OpenSearch / AI Search / **DynamoDB (cheap AWS)** / **ChromaDB (dev)** | Kendra / Pinecone | Cheaper, more control, DynamoDB is $0/month |
| Hosting | Fargate / Container Apps | EKS / AKS | Simpler, cheaper |
| Orchestration | FastAPI (monolith) | Step Functions + Lambda | Lower latency, simpler |
| Document pipeline | Lambda / Azure Functions | Glue / Data Factory | Faster startup, cheaper |
| Embeddings | Managed (Titan / OpenAI) / **nomic-embed-text (dev)** | Self-hosted (Sentence-BERT) | No GPU needed |

---

## How to minimize costs on your personal account

1. **Use ChromaDB locally** for development (no vector store cloud cost)
2. **Use Azure AI Search Free tier** when you need cloud (50 MB, 3 indexes)
3. **Use `VECTOR_STORE_TYPE=dynamodb`** on AWS for $0/month vector search (free tier)
4. **Never create OpenSearch Serverless** unless you're ready for $350+/month
4. **Run locally** — don't deploy to Fargate/Container Apps until needed
5. **Set billing alerts** in both AWS and Azure:
   - AWS: Budgets → Create budget → $10/month threshold
   - Azure: Cost Management → Budgets → $10/month threshold
6. **Delete resources when done testing** — especially anything with hourly charges
7. **Use DynamoDB on-demand** (not provisioned) — you only pay for what you use
8. **Use Cosmos DB Serverless** (not provisioned throughput) — same reason

---

## Cost of running `run_all_labs.py` on cloud

Running the full lab suite (`poetry run python scripts/run_all_labs.py`) makes real API calls. Here's what one full run costs per provider:

### Experiment count per phase

| Phase | Experiments | API Calls | Type |
| --- | --- | --- | --- |
| Phase 1 (Labs 1-2) | 1a-2d | ~8 evaluate | LLM + embedding |
| Phase 2 (Labs 3-5) | 3a-5b | ~8 evaluate + chat | LLM + embedding |
| Phase 3 (Labs 6-8) | 6a-6d, 7-8 (thinking) | ~5 evaluate + 1 suite (25 cases) | LLM + embedding |
| **Phase 4 (Labs 9-13)** | **9a-13d** | **7 chat + 22 evaluate + 1 batch upload** | **LLM + embedding** |
| Phase 5 (Labs 14-16) | 14a-16a | 2 stats/failures + 1 metrics + 1 suite (25 cases) | LLM + embedding |
| **Total** | **50 API experiments** | **~70 LLM calls** (including 2 golden suites of 25 each) | |

### Cost per full run

| Provider | LLM Cost | Embedding Cost | Vector Store Cost | Total per Run |
| --- | --- | --- | --- | --- |
| **Local (Ollama)** | $0 | $0 | $0 (ChromaDB) | **$0** |
| **AWS (Bedrock + DynamoDB)** | ~$0.90 | ~$0.01 | $0 (DynamoDB free tier) | **~$0.91** |
| **AWS (Bedrock + OpenSearch)** | ~$0.90 | ~$0.01 | $350/month (always on) | **~$0.91** + $350/month base |
| **Azure (OpenAI + AI Search Free)** | ~$0.70 | ~$0.01 | $0 (free tier) | **~$0.71** |
| **Azure (OpenAI + AI Search Basic)** | ~$0.70 | ~$0.01 | $75/month (always on) | **~$0.71** + $75/month base |

### Cost breakdown assumptions

- **Average tokens per query:** ~500 input + ~300 output = ~800 tokens
- **70 LLM calls × 800 tokens:** ~56,000 tokens total
- **AWS Bedrock (Claude 3.5 Sonnet):** 56K input × $0.003/1K + 21K output × $0.015/1K ≈ $0.49
- **Azure OpenAI (GPT-4o):** 56K input × $0.0025/1K + 21K output × $0.01/1K ≈ $0.35
- **Embeddings:** ~70 queries × 500 tokens × $0.00002/1K ≈ $0.001 (negligible)
- **Phase 4 guardrails (Labs 9a-9c):** 7 chat calls — blocked requests cost $0 (no LLM call when blocked)

### Phase 4 specifics

| Lab | Experiments | Cloud Cost Notes |
| --- | --- | --- |
| **Lab 9 (Guardrails)** | 7 chat calls (3 injection, 3 PII, 1 baseline) | Blocked requests = $0 (no LLM invoked). Only the baseline and unblocked requests cost tokens. |
| **Lab 10 (Re-ranking)** | 6 evaluate calls | Standard LLM + embedding cost. Cross-encoder re-ranking runs locally (no extra cloud cost). |
| **Lab 11 (Hybrid Search)** | 8 evaluate calls | Standard LLM + embedding cost. BM25 runs locally or in the vector store (no extra cost). |
| **Lab 12 (Bulk Upload)** | 1 batch upload + 1 evaluate | Embedding cost for 5 test docs (~25 chunks). Negligible. |
| **Lab 13 (HNSW)** | 6 evaluate calls | Standard LLM + embedding cost. HNSW settings don't change per-query cost. |

### Running labs 10× (for tuning)

If you re-run labs multiple times to compare feature flag settings (e.g., guardrails ON vs OFF, reranker ON vs OFF):

| Runs | Local | AWS (DynamoDB) | Azure (AI Search Free) |
| --- | --- | --- | --- |
| 1 run | $0 | ~$0.91 | ~$0.71 |
| 5 runs | $0 | ~$4.55 | ~$3.55 |
| 10 runs | $0 | ~$9.10 | ~$7.10 |

> **Recommendation:** Run labs locally first (Ollama = $0), then run once on each cloud provider to verify cross-provider behaviour. Total cloud cost for the complete portfolio: **~$2 one-time**.

---

## Budget Guard — Automatic Cost Protection

Both `infra/aws/` and `infra/azure/` include a **budget guard** (`budget.tf`) that automatically protects against runaway cloud costs.

### How it works

| Threshold | Action |
|---|---|
| **80% of limit (€4)** | Email warning sent to `alert_email` |
| **100% of limit (€5)** | Email + automatic resource kill switch triggered |

### AWS

- **AWS Budget** monitors tagged resources (`Project=rag-chatbot`)
- **SNS → Lambda** pipeline: at 100%, a Lambda function scales ECS to 0, deletes DynamoDB tables, and empties S3 buckets
- File: `infra/aws/budget.tf` + `infra/aws/budget_killer_lambda/handler.py`

### Azure

- **Azure Consumption Budget** scoped to the resource group
- **Action Group → Automation Runbook**: at 100%, a PowerShell runbook deletes all resources in the resource group
- File: `infra/azure/budget.tf`

### Configuration

```hcl
variable "cost_limit_eur" {
  default = 5  # €5 kill switch
}

variable "alert_email" {
  # Required — where budget warnings go
}
```

### ⚠️ Important caveat

Cloud cost reporting has a **6–24 hour lag**. The budget guard is your **safety net** (catches "I forgot to destroy"), not your primary defense. Always run:

```bash
terraform destroy  # immediately after finishing labs
```

Think of it as: `terraform destroy` = seatbelt (always use it), budget guard = airbag (catches you if you forget).
