# Azure Services Deep Dive

## Table of Contents

- [Overview — What Azure services we use and why](#overview)
- [Azure OpenAI Service](#azure-openai-service)
- [Azure Blob Storage](#azure-blob-storage)
- [Azure Cosmos DB](#azure-cosmos-db)
- [Azure AI Search](#azure-ai-search)
- [Azure Container Apps](#azure-container-apps)
- [Azure Monitor and App Insights](#azure-monitor-and-app-insights)
- [Azure Managed Identity](#azure-managed-identity)

---

## Overview

| Service | Purpose in this project | Cost model | 🚚 Courier |
| --- | --- | --- | --- |
| **Azure OpenAI** | LLM inference (GPT-4o) + embeddings | Pay per token | Azure-hosted depot that rents the courier by the fuel bale — GPT-4o writes answers, embeddings turn text into GPS coordinates |
| **Blob Storage** | Store uploaded documents | Pay per GB stored | Azure's document warehouse — where the courier picks up source files before pre-sorting them into chunks |
| **Cosmos DB** | Conversation history | Pay per RU (serverless) | Azure's depot logbook — Cosmos DB: Conversation history · Pay per RU (serverless) |
| **AI Search** | Vector store for embeddings | Tier-based (Free available) | Azure hub's vector index where the courier's embeddings live — billed by tier with a free option. |
| **Container Apps** | Host the FastAPI container | Pay per vCPU/memory-second | Azure's depot building for your FastAPI courier — billed by the second the courier is actually moving. |
| **Container Registry** | Docker image registry | Tier-based ($5/month Basic) | Azure hub's Docker registry address for the courier image — Basic SKU runs about $5/month. |
| **Azure Functions** | Event-driven document ingestion | Pay per execution | Sorting bench before loading — Azure Functions: Event-driven document ingestion · Pay per execution |
| **Azure Monitor** | Logs, metrics, dashboards, alerts | Free tier generous | Courier's odometer dial — Azure Monitor: Logs, metrics, dashboards, alerts · Free tier generous |
| **Managed Identity** | Passwordless auth between services | Free | Free fuel for the courier — Managed Identity: Passwordless auth between services · Free |

- 🚚 **Courier:** Think of this as the orientation briefing given to a new courier before its first delivery run — it sets the context for everything that follows.

---

## Azure OpenAI Service

### What it is

Azure-hosted version of OpenAI's models (GPT-4o, GPT-4, etc.). Same models as OpenAI, but:

- Data stays in your Azure tenant and region
- Enterprise SLA (99.9% uptime)
- Azure RBAC and networking controls
- Managed Identity support (no API keys in production)

### How we use it

1. **LLM inference** — Send question + context to GPT-4o, get an answer
2. **Embeddings** — Convert text to vectors using text-embedding-3-small

### Code location

`src/llm/azure_openai.py`

### API used

We use the **Chat Completions API** via the official `openai` Python SDK:

```python
response = await self._client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ],
    temperature=0.1,
    max_tokens=2048,
)
```

### Models to deploy

| Model | Deployment name | Purpose | Input cost | Output cost | 🚚 Courier |
| --- | --- | --- | --- | --- | --- |
| gpt-4o | `gpt-4o` | Answer generation | $0.0025/1K | $0.01/1K | The premium courier on Azure — strong and accurate, the default carrier for answer generation |
| text-embedding-3-small | `text-embedding-3-small` | Text to vectors | $0.00002/1K | N/A | Coordinates inked on the parcel — text-embedding-3-small: text-embedding-3-small · Text to vectors · $0.00002/1K · N/A |

### Setup steps

1. Create Azure OpenAI resource in Azure Portal
2. Go to Azure AI Studio
3. Deploy models (gpt-4o + text-embedding-3-small)
4. Copy endpoint + API key to `.env`

- 🚚 **Courier:** The Azure hub — Azure AI Search and Cosmos DB serve as the GPS-indexed warehouse and trip-log database for couriers on the Azure route.

---

## Azure Blob Storage

### What it is

Object storage for files (Azure's equivalent of S3).

### How we use it

Store uploaded documents.

### Terraform resource

```hcl
resource "azurerm_storage_account" "documents" {
  name                     = "ragchatbotdevdocs"
  account_tier             = "Standard"
  account_replication_type = "LRS"  # Locally redundant — cheapest
}
```

### Cost

- LRS (locally redundant): $0.02/GB/month
- Free tier: 5 GB for 12 months
- For this project: essentially free

### Why LRS and not GRS?

| Replication | Cost | Durability | Use case | 🚚 Courier |
| --- | --- | --- | --- | --- |
| **LRS** (our choice) | $0.02/GB | 11 nines (one datacenter) | Dev/personal | Free fuel for the courier — LRS (our choice): $0.02/GB · 11 nines (one datacenter) · Dev/personal |
| GRS | $0.04/GB | 16 nines (two regions) | Production | Complimentary feed allowance — GRS: $0.04/GB · 16 nines (two regions) · Production |
| ZRS | $0.025/GB | 12 nines (three zones) | Balanced | Free fuel for the courier — ZRS: $0.025/GB · 12 nines (three zones) · Balanced |

For a personal project, LRS is the cheapest option. Your documents are also on your local machine, so you can re-upload if anything happens.

- 🚚 **Courier:** Choosing between the local barn (ChromaDB), the AWS depot (DynamoDB/OpenSearch), or the Azure hub (Azure AI Search) to store the GPS-indexed parcels.

---

## Azure Cosmos DB

### What it is

A globally distributed NoSQL database. Supports multiple APIs (SQL, MongoDB, Cassandra, Gremlin, Table).

### How we use it

Store conversation history using the **SQL API** (JSON documents).

### Terraform resource

```hcl
resource "azurerm_cosmosdb_account" "main" {
  offer_type = "Standard"
  capabilities {
    name = "EnableServerless"  # Pay per request, no idle costs
  }
}
```

### Why Serverless mode?

| Mode | Cost | Idle cost | Best for | 🚚 Courier |
| --- | --- | --- | --- | --- |
| **Serverless** (our choice) | ~$0.25/million RU | **$0** | Low traffic, dev | Complimentary feed allowance — Serverless (our choice): ~$0.25/million RU · $0 · Low traffic, dev |
| Provisioned (autoscale) | $0.008/RU-hour | $$$$ | Production, steady traffic | Depot throws in free supplies — Provisioned (autoscale): $0.008/RU-hour · $$$$ · Production, steady traffic |

### Container design

```json
{
  "id": "msg-uuid",
  "session_id": "session-uuid",
  "timestamp": "2026-03-29T10:00:00Z",
  "role": "user",
  "content": "What is the refund policy?",
  "ttl": 604800
}
```

Partition key: `/session_id` — all messages in a conversation are in the same partition for fast queries.

TTL: 604800 seconds (7 days) — old conversations auto-delete.

- 🚚 **Courier:** The Azure hub — Azure AI Search and Cosmos DB serve as the GPS-indexed warehouse and trip-log database for couriers on the Azure route.

---

## Azure AI Search

### What it is

Fully managed search service with built-in vector search. Formerly called "Azure Cognitive Search."

### How we use it

Store document chunk embeddings and perform vector similarity search.

### Code location

`src/vectorstore/azure_ai_search.py`

### Tiers

| Tier | Cost/month | Storage | Indexes | Best for | 🚚 Courier |
| --- | --- | --- | --- | --- | --- |
| **Free** | $0 | 50 MB | 3 | **Development (use this!)** | Complimentary feed allowance — Free: $0 · 50 MB · 3 · Development (use this!) |
| Basic | $75 | 2 GB | 15 | Small production | Fuel-and-feed bill for keeping the courier and depot running |
| Standard S1 | $250 | 25 GB | 50 | Medium production | Fuel-and-feed bill for keeping the courier and depot running |

### Why Free tier for development?

50 MB of vector storage holds roughly:

- ~2,000 document chunks with 1536-dimensional embeddings
- That's about 20-30 typical PDF documents
- More than enough for development and testing

### Index schema

```python
fields = [
    SimpleField(name="id", type="Edm.String", key=True),
    SearchableField(name="text", type="Edm.String"),
    SimpleField(name="document_id", type="Edm.String", filterable=True),
    SearchField(
        name="embedding",
        type="Collection(Edm.Single)",
        vector_search_dimensions=1536,
        vector_search_profile_name="vector-profile",
    ),
]
```

- 🚚 **Courier:** The Azure hub — Azure AI Search and Cosmos DB serve as the GPS-indexed warehouse and trip-log database for couriers on the Azure route.

---

## Azure Container Apps

### What it is

Serverless container hosting. Like ECS Fargate but can **scale to zero** (no cost when no traffic).

### How we use it

Host the FastAPI application in production.

### Why Container Apps and not App Service or AKS?

| | Container Apps (our choice) | App Service | AKS (Kubernetes) | 🚚 Courier |
| --- | --- | --- | --- | --- |
| Scale to zero | **Yes** | No (min 1 instance) | No (min 1 node) | How the depot adds or removes couriers when delivery volume changes |
| Min cost | $0 (idle) | ~$13/month (B1) | ~$100/month | Cost of keeping the courier fed — Min cost: $0 (idle) · ~$13/month (B1) · ~$100/month |
| Complexity | Low | Low | High | Courier-side view of Complexity — affects how the courier loads, reads, or delivers the parcels |
| Container support | Docker | Docker or code | Docker | All three Azure barns happily house Docker-shaped couriers; App Service will also accept a raw courier without the crate. |

### Cost advantage

Container Apps charges per vCPU-second and memory-second. When no requests are coming in, it scales to zero replicas = **$0 idle cost**. This is perfect for a personal project that you only use during development hours.

- 🚚 **Courier:** The Azure hub — Azure AI Search and Cosmos DB serve as the GPS-indexed warehouse and trip-log database for couriers on the Azure route.

---

## Azure Monitor and App Insights

### What it is

Azure's monitoring suite. App Insights is the application performance monitoring (APM) component.

### How we use it

1. **Application logs**: Structured logs from the FastAPI app
2. **Request tracing**: End-to-end trace of each HTTP request
3. **Custom metrics**: Latency, token usage, error rates
4. **Dashboards**: Visual monitoring
5. **Alerts**: Notify when error rate spikes

### Free tier

- 5 GB of log ingestion per month
- 90 days retention for free tier
- Basic alerting included

- 🚚 **Courier:** The Azure hub — Azure AI Search and Cosmos DB serve as the GPS-indexed warehouse and trip-log database for couriers on the Azure route.

---

## Azure Managed Identity

### What it is

Passwordless authentication between Azure services. No API keys, no secrets rotation.

### How it works

1. Your Container App gets a **system-assigned managed identity** (an Azure AD identity)
2. You grant that identity permissions on other resources (Blob, Cosmos, AI Search)
3. At runtime, the app authenticates automatically — no credentials in code or env vars

### Why this matters

In development, we use API keys (stored in `.env`). In production, we use Managed Identity:

- No secrets to leak
- No secrets to rotate
- No credentials in environment variables
- Azure handles authentication transparently

This is a key production security practice that demonstrates enterprise awareness.

- 🚚 **Courier:** The Azure hub — Azure AI Search and Cosmos DB serve as the GPS-indexed warehouse and trip-log database for couriers on the Azure route.
