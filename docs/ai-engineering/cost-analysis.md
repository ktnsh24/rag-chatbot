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

| Service | AWS Cost/month | Azure Cost/month | Notes | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| LLM (pay-per-use) | ~$2–5 | ~$2–5 | Based on ~100 queries/day | The donkey 🐴 |
| Embeddings | ~$0.10 | ~$0.10 | Very cheap | Free hay 🌿 |
| Vector Store | **$0 (local)** | **$0 (Free tier)** | Use ChromaDB locally / Free AI Search | Local barn 🏚️ |
| Document Storage | $0 (Free tier) | $0 (Free tier) | S3: 5 GB free, Blob: 5 GB free | Saddlebag check 🫏 |
| Database | $0 (Free tier) | $0 (Free tier) | DynamoDB: 25 GB free, Cosmos: Free tier | AWS depot 🏭 |
| Container Hosting | $0 (local) | $0 (local) | Run locally during development | Stable stall 🐎 |
| **Total** | **~$2–5/month** | **~$2–5/month** | Mostly LLM token costs | The donkey 🐴 |

### Production (small scale: ~1000 queries/day)

| Service | AWS Cost/month | Azure Cost/month | 🫏 Donkey |
| --- | --- | --- | --- |
| LLM | ~$50–100 | ~$40–80 | The donkey 🐴 |
| Embeddings | ~$1–2 | ~$1–2 | GPS warehouse 🗺️ |
| Vector Store | ~$350 (OpenSearch) | ~$75 (AI Search Basic) | AWS search hub 🔍 |
| Document Storage | ~$1 | ~$1 | Saddlebag check 🫏 |
| Database | ~$5 (DynamoDB) | ~$5 (Cosmos) | AWS depot 🏭 |
| Container Hosting | ~$30 (Fargate) | ~$20 (Container Apps) | Stable stall 🐎 |
| Container Registry | ~$1 (ECR) | ~$5 (ACR Basic) | Stable address 🏷️ |
| Monitoring | $0 (CloudWatch free tier) | $0 (App Insights free) | Tachograph 📊 |
| **Total** | **~$440/month** | **~$150/month** | Feed bill 🌾 |

> **Key insight:** Azure is significantly cheaper for production because Azure AI Search Basic ($75/month) is much cheaper than OpenSearch Serverless (~$350/month minimum).

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.

---

## Service-by-service breakdown

### LLM Inference

| | AWS (Bedrock - Claude 3.5 Sonnet v2) | Azure (Azure OpenAI - GPT-4o) | Local (Ollama - llama3.2) | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| **Input tokens** | $0.003 / 1K tokens | $0.0025 / 1K tokens | **$0** | Cargo unit ⚖️ |
| **Output tokens** | $0.015 / 1K tokens | $0.01 / 1K tokens | **$0** | Cargo unit ⚖️ |
| **Free tier** | None | None | Free forever | Free hay 🌿 |
| **Minimum cost** | $0 (pay per token) | $0 (pay per token) | $0 (runs on your machine) | Cargo unit ⚖️ |
| **Per query (typical)** | ~$0.013 | ~$0.01 | **$0** | Free hay 🌿 |

**Why we chose this:**
- Pay-per-token = no idle costs (cloud)
- No GPU instances to manage (cloud)
- Best-in-class models (cloud)
- $0 cost for development and experimentation (local)
- Both cloud options are cheaper than OpenAI direct ($0.0025/$0.01 vs $0.005/$0.015 for GPT-4o)

### Embeddings

| | AWS (Titan Embeddings v2) | Azure (text-embedding-3-small) | Local (Ollama - nomic-embed-text) | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| **Cost** | $0.00002 / 1K tokens | $0.00002 / 1K tokens | **$0** | Cargo unit ⚖️ |
| **Dimensions** | 1024 | 1536 | 768 | 🫏 On the route |
| **Free tier** | None | None | Free forever | Free hay 🌿 |

**Both are extremely cheap.** A 100-page PDF with 500 chunks costs ~$0.01 to embed.

### Vector Store

**This is the most expensive service — and where choices matter most.**

| Option | Cost/month | Min cost | Managed? | Scales to zero? | Best for | 🫏 Donkey |
| --- | --- | --- | --- | --- | --- | --- |
| **AWS OpenSearch Serverless** | ~$350+ | $350 (4 OCUs) | Yes | **No** (always on) | Production (>10K chunks) | AWS search hub 🔍 |
| **AWS DynamoDB (brute-force)** | **~$0** | $0 (free tier) | Yes | Yes (pay-per-request) | **Portfolio, dev, testing** | AWS depot 🏭 |
| **Azure AI Search Free** | $0 | $0 | Yes | N/A (free) | Development | Azure hub ☁️ |
| **Azure AI Search Basic** | $75 | $75 | Yes | No | Production | Azure hub ☁️ |
| **ChromaDB (local)** | $0 | $0 | No (self-hosted) | N/A | Local development | Local barn 🏚️ |
| **Pinecone Starter** | $0 | $0 (Free tier) | Yes | Yes | Quick prototypes | Free hay 🌿 |
| **Qdrant Cloud Free** | $0 | $0 (1 GB) | Yes | Yes | Quick prototypes | Free hay 🌿 |

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

| | AWS S3 | Azure Blob Storage | 🫏 Donkey |
| --- | --- | --- | --- |
| **Storage** | $0.023/GB/month | $0.02/GB/month (LRS) | Saddlebag check 🫏 |
| **Free tier** | 5 GB (12 months) | 5 GB (12 months) | Free hay 🌿 |
| **PUT requests** | $0.005/1K | $0.005/1K | Free hay 🌿 |
| **GET requests** | $0.0004/1K | $0.0004/1K | Free hay 🌿 |

**Both are essentially free** for a personal project. 1000 documents at 1 MB each = 1 GB = ~$0.02/month.

### Conversation History (Database)

| | AWS DynamoDB | Azure Cosmos DB | 🫏 Donkey |
| --- | --- | --- | --- |
| **Mode** | Pay-per-request | Serverless | 🫏 On the route |
| **Read cost** | $1.25/million reads | ~$0.25/million RU | Feed bill 🌾 |
| **Write cost** | $1.25/million writes | ~$0.25/million RU | Feed bill 🌾 |
| **Free tier** | 25 GB + 25 RCU + 25 WCU | 1000 RU/s + 25 GB | Free hay 🌿 |

**Both have generous free tiers.** A personal project will stay well within free limits.

### Container Hosting

| | AWS ECS Fargate | Azure Container Apps | 🫏 Donkey |
| --- | --- | --- | --- |
| **vCPU** | $0.04048/hr | $0.000024/sec (~$0.086/hr) | Free hay 🌿 |
| **Memory** | $0.004445/GB/hr | $0.000003/GB/sec | Trip log 📒 |
| **Minimum** | ~$30/month (0.25 vCPU, 0.5 GB) | ~$20/month (0.25 vCPU, 0.5 GB) | 🫏 On the route |
| **Scales to zero?** | No (min 1 task) | **Yes** (0 replicas when idle) | 🫏 On the route |

**Azure Container Apps is cheaper because it can scale to zero.**

### Container Registry

| | AWS ECR | Azure ACR | 🫏 Donkey |
| --- | --- | --- | --- |
| **Storage** | $0.10/GB/month | $0.167/GB/month (Basic) | Saddlebag check 🫏 |
| **Free tier** | 500 MB (private, 12 months) | None | Free hay 🌿 |
| **Tier** | Pay per GB | $5/month (Basic) | 🫏 On the route |

### CI/CD Pipeline

| GitHub Actions | Free tier | 🫏 Donkey |
| --- | --- | --- |
| **Public repos** | Unlimited minutes | 🫏 On the route |
| **Private repos** | 2,000 minutes/month | 🫏 On the route |
| **Cost beyond free** | $0.008/minute (Linux) | Feed bill 🌾 |

**Free for most personal projects.**

- 🫏 **Donkey:** The mechanics of the stable — understanding how each piece fits so you can maintain and extend the system.

---

## Free tier limits

### AWS Free Tier (12 months)

| Service | Free amount | 🫏 Donkey |
| --- | --- | --- |
| S3 | 5 GB storage, 20K GET, 2K PUT | Saddlebag check 🫏 |
| DynamoDB | 25 GB, 25 RCU, 25 WCU | AWS depot 🏭 |
| Lambda | 1M invocations, 400K GB-seconds | 🫏 On the route |
| CloudWatch | 10 metrics, 5 GB logs, 3 dashboards | Tachograph 📊 |
| ECR | 500 MB | Stable address 🏷️ |
| Bedrock | **No free tier** (pay per token) | The donkey 🐴 |
| OpenSearch Serverless | **No free tier** ($350+/month) | AWS search hub 🔍 |

### Azure Free Tier

| Service | Free amount | 🫏 Donkey |
| --- | --- | --- |
| Blob Storage | 5 GB LRS | Parcel shelf 📦 |
| Cosmos DB | 1000 RU/s + 25 GB | Azure trip-log 📒 |
| AI Search | Free tier (50 MB, 3 indexes) | Azure hub ☁️ |
| Azure Functions | 1M executions/month | Azure hub ☁️ |
| App Insights | 5 GB logs/month | Tachograph 📊 |
| Azure OpenAI | **No free tier** (pay per token) | The donkey 🐴 |
| Container Apps | First 180K vCPU-seconds free/month | Stable stall 🐎 |

- 🫏 **Donkey:** Hay that comes at no charge — the local barn and free cloud tiers let you develop without spending a penny on feed.

---

## Cost for personal account (your setup)

### Recommended minimal setup

Since you want to save money, here's the cheapest way to run this project:

| Component | Choice | Cost | 🫏 Donkey |
| --- | --- | --- | --- |
| LLM | Bedrock (Claude) OR Azure OpenAI (GPT-4o) | ~$2–5/month | The donkey 🐴 |
| Embeddings | Same provider as LLM | ~$0.10/month | The donkey 🐴 |
| Vector Store | **ChromaDB (local)** or Azure AI Search **Free** | **$0** | Local barn 🏚️ |
| Document Storage | S3 Free or Blob Free | **$0** | Saddlebag check 🫏 |
| Database | DynamoDB Free or Cosmos Free | **$0** | AWS depot 🏭 |
| Hosting | **Run locally** (no cloud hosting) | **$0** | Free hay 🌿 |
| **Total** | | **~$2–5/month** | Feed bill 🌾 |

### What to avoid

| Service | Why to avoid for personal use | 🫏 Donkey |
| --- | --- | --- |
| OpenSearch Serverless | $350+/month minimum — use `VECTOR_STORE_TYPE=dynamodb` or ChromaDB instead | AWS search hub 🔍 |
| ECS Fargate | $30+/month — run locally instead | Stable stall 🐎 |
| Azure AI Search Basic | $75/month — use Free tier instead | Azure hub ☁️ |
| NAT Gateway (AWS) | $32/month — easy to create accidentally | AWS depot 🏭 |
| Elastic IP (AWS) | $3.60/month if not attached — delete unused ones | AWS depot 🏭 |

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.

---

## Alternative pipelines — Why they cost more

### Alternative 1: AWS SageMaker instead of Bedrock

| | Bedrock (our choice) | SageMaker | 🫏 Donkey |
| --- | --- | --- | --- |
| **Model hosting** | Managed (no instances) | You manage instances | Manifest template 📋 |
| **Min cost** | $0 (pay per token) | ~$100/month (ml.g5.xlarge) | Cargo unit ⚖️ |
| **Scaling** | Automatic | Manual or auto-scaling | 🫏 On the route |
| **GPU management** | None | You handle it | 🫏 On the route |
| **When to use SageMaker** | Custom/fine-tuned models | | Alternative stable 🏗️ |

**Why Bedrock is better here:**
SageMaker requires always-on GPU instances ($1.006/hr for g5.xlarge = ~$730/month).
Bedrock is serverless — you only pay when you make API calls.
SageMaker makes sense when you need a custom-trained model, not for off-the-shelf Claude/Titan.

### Alternative 2: AWS Kendra instead of OpenSearch

| | OpenSearch Serverless (our choice) | Kendra | 🫏 Donkey |
| --- | --- | --- | --- |
| **Type** | General vector search | Enterprise search (RAG-focused) | Saddlebag check 🫏 |
| **Min cost** | ~$350/month | ~$810/month (Developer Edition) | Feed bill 🌾 |
| **Features** | Raw vector similarity | Semantic search, connectors | GPS warehouse 🗺️ |
| **RAG integration** | Manual (you build the pipeline) | Built-in RAG features | Saddlebag check 🫏 |

**Why OpenSearch is better here:**
Kendra is more powerful but starts at $810/month. For a portfolio project, OpenSearch (or ChromaDB) gives you more control and costs less.

### Alternative 3: Azure Cognitive Services instead of Azure OpenAI

| | Azure OpenAI (our choice) | Cognitive Services | 🫏 Donkey |
| --- | --- | --- | --- |
| **LLM quality** | GPT-4o (state-of-the-art) | No LLM capability | The donkey 🐴 |
| **Text analysis** | Via LLM prompts | Pre-built NLP models | The donkey 🐴 |
| **RAG support** | Full RAG pipeline | Not designed for RAG | Saddlebag check 🫏 |

**Why Azure OpenAI is better:**
Cognitive Services doesn't have a conversational LLM. It does text analytics (sentiment, entities) but can't generate answers from context.

### Alternative 4: Self-hosted open source LLM (EC2/VM)

| | Bedrock/Azure OpenAI (our choice) | Self-hosted (Llama 3) | 🫏 Donkey |
| --- | --- | --- | --- |
| **GPU cost** | $0 idle | ~$730/month (g5.xlarge) | Feed bill 🌾 |
| **Quality** | GPT-4o / Claude (best) | Good but not as strong | The donkey 🐴 |
| **Maintenance** | None | You manage everything | 🫏 On the route |
| **Latency** | ~1–3 seconds | ~2–5 seconds | 🫏 On the route |

**Why managed is better:**
Self-hosting requires a GPU instance running 24/7 (~$730/month for AWS, ~$600/month for Azure).
You also handle model updates, CUDA drivers, and memory management.
Unless you need complete data isolation, managed APIs are cheaper and easier.

### Alternative 5: AWS Step Functions + Lambda for orchestration

| | FastAPI (our choice) | Step Functions + Lambda | 🫏 Donkey |
| --- | --- | --- | --- |
| **Architecture** | Monolith (simple) | Microservices (complex) | 🫏 On the route |
| **Min cost** | $30/month (Fargate) | ~$5/month (Lambda free tier) | Stable stall 🐎 |
| **Complexity** | Low | High (state machines, IAM, etc.) | 🫏 On the route |
| **Latency** | ~1s (in-memory) | ~3–5s (cold starts + state transitions) | Trip log 📒 |

**Why FastAPI is better for a portfolio project:**
Step Functions are excellent for event-driven workflows but add complexity that doesn't benefit a RAG chatbot. The latency from Lambda cold starts and state machine transitions makes the user experience worse. For a real-time chat API, a single FastAPI service is simpler and faster.

**When Step Functions would be better:**
If you had a complex document ingestion pipeline with multiple stages (OCR → translate → summarize → chunk → embed), Step Functions would be ideal for managing retries and parallel processing.

### Alternative 6: Azure Data Factory for document pipeline

| | Direct upload (our choice) | Data Factory | 🫏 Donkey |
| --- | --- | --- | --- |
| **Purpose** | Simple file upload → ingest | Complex ETL pipelines | Pre-sort 📮 |
| **Min cost** | $0 | ~$50/month (pipeline runs) | Feed bill 🌾 |
| **Use case** | Upload via API | Scheduled batch processing | Stable door 🚪 |

**When Data Factory would be better:**
If documents came from 10 different sources (SharePoint, Salesforce, databases) on a schedule, Data Factory would orchestrate those pipelines. For a single-upload API, it's overkill.

### Alternative 7: EKS/AKS (Kubernetes) instead of Fargate/Container Apps

| | Fargate / Container Apps (our choice) | EKS / AKS (Kubernetes) | 🫏 Donkey |
| --- | --- | --- | --- |
| **Management** | Serverless containers | You manage the cluster | Stable stall 🐎 |
| **Min cost** | ~$20–30/month | ~$75/month (EKS) / ~$100/month (AKS) | Alternative stable 🏗️ |
| **Scaling** | Automatic | Auto-scaling (more config) | 🫏 On the route |
| **Complexity** | Low | High (kubectl, helm, etc.) | 🫏 On the route |

**Why serverless containers are better here:**
Kubernetes is designed for teams running dozens of microservices. For a single FastAPI app, EKS/AKS adds $75–100/month in cluster costs plus significant operational complexity. Fargate and Container Apps give you the same benefits (containerized, scalable) without the overhead.

### Alternative 8: AWS Glue for document ETL

| | Lambda (our choice) | Glue | 🫏 Donkey |
| --- | --- | --- | --- |
| **Purpose** | Lightweight event processing | Heavy ETL (Spark) | 🫏 On the route |
| **Min cost** | Free tier (1M invocations) | ~$0.44/DPU-hour | Feed bill 🌾 |
| **Startup time** | ~1s (cold start) | ~2–5 min (Spark cluster) | 🫏 On the route |

**Why Lambda is better:**
Glue spins up a full Spark cluster for each job. A single document ingestion takes seconds in Lambda but minutes in Glue (just for cluster startup). Glue makes sense when processing millions of records, not individual document uploads.

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.

---

## Decision summary table

| Decision | Chosen | Alternative | Why chosen wins | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| LLM | Bedrock / Azure OpenAI / **Ollama (dev)** | SageMaker / Self-hosted | $0 idle vs $730/month GPU | The donkey 🐴 |
| Vector Store | OpenSearch / AI Search / **DynamoDB (cheap AWS)** / **ChromaDB (dev)** | Kendra / Pinecone | Cheaper, more control, DynamoDB is $0/month | AWS search hub 🔍 |
| Hosting | Fargate / Container Apps | EKS / AKS | Simpler, cheaper | Stable stall 🐎 |
| Orchestration | FastAPI (monolith) | Step Functions + Lambda | Lower latency, simpler | Alternative stable 🏗️ |
| Document pipeline | Lambda / Azure Functions | Glue / Data Factory | Faster startup, cheaper | Alternative stable 🏗️ |
| Embeddings | Managed (Titan / OpenAI) / **nomic-embed-text (dev)** | Self-hosted (Sentence-BERT) | No GPU needed | The donkey 🐴 |

- 🫏 **Donkey:** The head groom's final checklist — all trade-offs weighed, best saddle chosen, donkey ready to dispatch.

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

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.

---

## Cost of running `run_all_labs.py` on cloud

Running the full lab suite (`poetry run python scripts/run_all_labs.py`) makes real API calls. Here's what one full run costs per provider:

### Experiment count per phase

| Phase | Experiments | API Calls | Type | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| Phase 1 (Labs 1-2) | 1a-2d | ~8 evaluate | LLM + embedding | The donkey 🐴 |
| Phase 2 (Labs 3-5) | 3a-5b | ~8 evaluate + chat | LLM + embedding | The donkey 🐴 |
| Phase 3 (Labs 6-8) | 6a-6d, 7-8 (thinking) | ~5 evaluate + 1 suite (25 cases) | LLM + embedding | The donkey 🐴 |
| **Phase 4 (Labs 9-13)** | **9a-13d** | **7 chat + 22 evaluate + 1 batch upload** | **LLM + embedding** | The donkey 🐴 |
| Phase 5 (Labs 14-16) | 14a-16a | 2 stats/failures + 1 metrics + 1 suite (25 cases) | LLM + embedding | The donkey 🐴 |
| **Total** | **50 API experiments** | **~70 LLM calls** (including 2 golden suites of 25 each) | | The donkey 🐴 |

### Cost per full run

| Provider | LLM Cost | Embedding Cost | Vector Store Cost | Total per Run | 🫏 Donkey |
| --- | --- | --- | --- | --- | --- |
| **Local (Ollama)** | $0 | $0 | $0 (ChromaDB) | **$0** | The donkey 🐴 |
| **AWS (Bedrock + DynamoDB)** | ~$0.90 | ~$0.01 | $0 (DynamoDB free tier) | **~$0.91** | The donkey 🐴 |
| **AWS (Bedrock + OpenSearch)** | ~$0.90 | ~$0.01 | $350/month (always on) | **~$0.91** + $350/month base | The donkey 🐴 |
| **Azure (OpenAI + AI Search Free)** | ~$0.70 | ~$0.01 | $0 (free tier) | **~$0.71** | The donkey 🐴 |
| **Azure (OpenAI + AI Search Basic)** | ~$0.70 | ~$0.01 | $75/month (always on) | **~$0.71** + $75/month base | The donkey 🐴 |

### Cost breakdown assumptions

- **Average tokens per query:** ~500 input + ~300 output = ~800 tokens
- **70 LLM calls × 800 tokens:** ~56,000 tokens total
- **AWS Bedrock (Claude 3.5 Sonnet):** 56K input × $0.003/1K + 21K output × $0.015/1K ≈ $0.49
- **Azure OpenAI (GPT-4o):** 56K input × $0.0025/1K + 21K output × $0.01/1K ≈ $0.35
- **Embeddings:** ~70 queries × 500 tokens × $0.00002/1K ≈ $0.001 (negligible)
- **Phase 4 guardrails (Labs 9a-9c):** 7 chat calls — blocked requests cost $0 (no LLM call when blocked)

### Phase 4 specifics

| Lab | Experiments | Cloud Cost Notes | 🫏 Donkey |
| --- | --- | --- | --- |
| **Lab 9 (Guardrails)** | 7 chat calls (3 injection, 3 PII, 1 baseline) | Blocked requests = $0 (no LLM invoked). Only the baseline and unblocked requests cost tokens. | The donkey 🐴 |
| **Lab 10 (Re-ranking)** | 6 evaluate calls | Standard LLM + embedding cost. Cross-encoder re-ranking runs locally (no extra cloud cost). | The donkey 🐴 |
| **Lab 11 (Hybrid Search)** | 8 evaluate calls | Standard LLM + embedding cost. BM25 runs locally or in the vector store (no extra cost). | The donkey 🐴 |
| **Lab 12 (Bulk Upload)** | 1 batch upload + 1 evaluate | Embedding cost for 5 test docs (~25 chunks). Negligible. | Saddlebag piece 📦 |
| **Lab 13 (HNSW)** | 6 evaluate calls | Standard LLM + embedding cost. HNSW settings don't change per-query cost. | The donkey 🐴 |

### Running labs 10× (for tuning)

If you re-run labs multiple times to compare feature flag settings (e.g., guardrails ON vs OFF, reranker ON vs OFF):

| Runs | Local | AWS (DynamoDB) | Azure (AI Search Free) | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| 1 run | $0 | ~$0.91 | ~$0.71 | Free hay 🌿 |
| 5 runs | $0 | ~$4.55 | ~$3.55 | Free hay 🌿 |
| 10 runs | $0 | ~$9.10 | ~$7.10 | Free hay 🌿 |

> **Recommendation:** Run labs locally first (Ollama = $0), then run once on each cloud provider to verify cross-provider behaviour. Total cloud cost for the complete portfolio: **~$2 one-time**.

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.

---

## Budget Guard — Automatic Cost Protection

Both `infra/aws/` and `infra/azure/` include a **budget guard** (`budget.tf`) that automatically protects against runaway cloud costs.

### How it works

| Threshold | Action | 🫏 Donkey |
|---|---| --- |
| **80% of limit (€4)** | Email warning sent to `alert_email` | 🫏 On the route |
| **100% of limit (€5)** | Email + automatic resource kill switch triggered | 🫏 On the route |

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

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.
