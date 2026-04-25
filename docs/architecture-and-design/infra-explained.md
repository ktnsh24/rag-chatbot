# Infrastructure (Terraform) — Deep Dive

> `infra/aws/` and `infra/azure/` — All cloud resources created by Terraform, split by resource type.

> **DE verdict: ★★☆☆☆ — You write Terraform daily.** The HCL syntax, modules, variables,
> outputs — all familiar. What's new is _which_ resources an AI app needs and _why_
> certain configuration choices (like OpenSearch dimensions or Cosmos DB partition keys)
> exist specifically for AI workloads.

> **Related docs:**
> - [Document Storage Deep Dive](storage-explained.md) — the code that uses S3/Blob resources
> - [Conversation History Deep Dive](history-explained.md) — the code that uses DynamoDB/Cosmos resources
> - [CI/CD Deep Dive](cicd-explained.md) — the pipelines that deploy using these resources
> - [RAG Concepts](../ai-engineering/rag-concepts.md) — why vector stores and embedding models exist
> - [Cost Analysis](../ai-engineering/cost-analysis.md) — pricing for every resource listed here

---

## Table of Contents

- [Infrastructure (Terraform) — Deep Dive](#infrastructure-terraform--deep-dive)
  - [Table of Contents](#table-of-contents)
  - [What This Module Does](#what-this-module-does)
  - [AWS Infrastructure — What Gets Created](#aws-infrastructure--what-gets-created)
    - [Resource count: 7](#resource-count-7)
  - [Azure Infrastructure — What Gets Created](#azure-infrastructure--what-gets-created)
    - [Resource count: 7](#resource-count-7-1)
  - [AWS vs Azure — Resource Mapping](#aws-vs-azure--resource-mapping)
    - [Key observation](#key-observation)
  - [DE-Familiar Resources (Nothing New)](#de-familiar-resources-nothing-new)
    - [S3 bucket](#s3-bucket)
    - [DynamoDB table](#dynamodb-table)
    - [ECR / ACR](#ecr--acr)
    - [Cosmos DB (Serverless)](#cosmos-db-serverless)
  - [AI-Specific Resources (What's New)](#ai-specific-resources-whats-new)
    - [1. Bedrock access (IAM permission)](#1-bedrock-access-iam-permission)
    - [2. DynamoDB TTL (AI-specific reasoning)](#2-dynamodb-ttl-ai-specific-reasoning)
    - [3. What's NOT created (and why it matters)](#3-whats-not-created-and-why-it-matters)
  - [Terraform Patterns You Already Know](#terraform-patterns-you-already-know)
    - [1. Variable-driven naming](#1-variable-driven-naming)
    - [2. Default tags](#2-default-tags)
    - [3. Outputs](#3-outputs)
    - [4. Provider versions pinned](#4-provider-versions-pinned)
  - [What's NOT in Terraform (and Why)](#whats-not-in-terraform-and-why)
  - [DE vs AI Engineer — What Each Sees](#de-vs-ai-engineer--what-each-sees)
  - [Self-Check Questions](#self-check-questions)
    - [Answers](#answers)

---

## What This Module Does

One sentence: **Creates all cloud resources the RAG chatbot needs — storage, databases,
container registry, container hosting, and IAM permissions.**

```
infra/
├── aws/
│   └── main.tf       # S3, DynamoDB, ECR, ECS Fargate, IAM
└── azure/
    └── main.tf       # Resource Group, Blob Storage, Cosmos DB, ACR, Container Apps
```

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## AWS Infrastructure — What Gets Created

```
terraform apply -var="environment=dev"

Creates:
┌─────────────────────────────────────────────────────────────┐
│  rag-chatbot-dev                                            │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ S3 Bucket        │  │ DynamoDB Table                   │ │
│  │ *-documents      │  │ *-conversations                  │ │
│  │ Stores: PDFs,    │  │ PK: session_id                   │ │
│  │ text files       │  │ SK: timestamp                    │ │
│  │                  │  │ TTL: 7 days                      │ │
│  │ Versioning: ON   │  │ Billing: PAY_PER_REQUEST         │ │
│  │ Encryption: AES  │  │                                  │ │
│  │ Public: BLOCKED  │  │                                  │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ ECR Repository   │  │ IAM Role                         │ │
│  │ Docker images    │  │ *-ecs-task-role                  │ │
│  │ Scan on push: ON │  │ Allows: S3, DynamoDB, Bedrock   │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
│                                                             │
│  Tags: Project=rag-chatbot, Environment=dev, ManagedBy=tf  │
└─────────────────────────────────────────────────────────────┘
```

### Resource count: 7

| # | Resource | Terraform resource type | Purpose | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| 1 | S3 bucket | `aws_s3_bucket` | Store uploaded documents | AWS warehouse for source files — the donkey reads from here at ingestion time |
| 2 | S3 versioning | `aws_s3_bucket_versioning` | Protect against accidental deletes | AWS depot 🏭 |
| 3 | S3 encryption | `aws_s3_bucket_server_side_encryption_configuration` | Encrypt at rest | Stable door 🚪 |
| 4 | S3 public block | `aws_s3_bucket_public_access_block` | Block all public access | AWS depot 🏭 |
| 5 | DynamoDB table | `aws_dynamodb_table` | Conversation history | AWS depot 🏭 |
| 6 | ECR repository | `aws_ecr_repository` | Docker image registry | Stable address 🏷️ |
| 7 | IAM role + policy | `aws_iam_role` + `aws_iam_role_policy` | Permissions for ECS tasks | AWS depot 🏭 |

- 🫏 **Donkey:** Blueprints for building the stable — run one command and the whole building appears, fences and all.

---

## Azure Infrastructure — What Gets Created

```
terraform apply -var="environment=dev"

Creates:
┌─────────────────────────────────────────────────────────────┐
│  rag-chatbot-dev-rg (Resource Group)                        │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ Storage Account  │  │ Cosmos DB Account                │ │
│  │ + Container      │  │ + Database + Container           │ │
│  │ ragchatbotdev    │  │ ragchatbotdev-cosmos             │ │
│  │ docs             │  │ /rag-chatbot/conversations       │ │
│  │                  │  │                                  │ │
│  │ Replication: LRS │  │ Partition key: /session_id       │ │
│  │ Tier: Standard   │  │ TTL: 604800 (7 days)            │ │
│  │ Access: Private  │  │ Mode: Serverless                 │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────┐                                       │
│  │ Container        │  Tags: Project=rag-chatbot            │
│  │ Registry (ACR)   │         Environment=dev               │
│  │ SKU: Basic       │         ManagedBy=terraform           │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

### Resource count: 7

| # | Resource | Terraform resource type | Purpose | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| 1 | Resource Group | `azurerm_resource_group` | Logical container for all resources | Stable stall 🐎 |
| 2 | Storage Account | `azurerm_storage_account` | Blob storage for documents | Azure warehouse for source files — same role as S3, different cloud |
| 3 | Storage Container | `azurerm_storage_container` | Container within the storage account | Portable stable — donkey ships in a sealed container that runs anywhere |
| 4 | Cosmos DB Account | `azurerm_cosmosdb_account` | NoSQL database (serverless) | Azure trip-log 📒 |
| 5 | Cosmos DB Database | `azurerm_cosmosdb_sql_database` | Database within the account | Azure trip-log 📒 |
| 6 | Cosmos DB Container | `azurerm_cosmosdb_sql_container` | Table with partition key + TTL | Azure trip-log 📒 |
| 7 | Container Registry | `azurerm_container_registry` | Docker image registry | Stable address 🏷️ |

- 🫏 **Donkey:** Blueprints for building the stable — run one command and the whole building appears, fences and all.

---

## AWS vs Azure — Resource Mapping

| Purpose | AWS Resource | Azure Resource | Same concept? | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| **Document storage** | S3 bucket | Storage Account + Container | ✅ Same — blob/object storage | Same warehouse concept on both clouds — the donkey fetches source files from either |
| **Conversation history** | DynamoDB table | Cosmos DB account + database + container | ✅ Same — NoSQL key-value store | AWS depot 🏭 |
| **Docker registry** | ECR | ACR | ✅ Same — container registry | Stable address 🏷️ |
| **Container hosting** | ECS Fargate (referenced) | Container Apps (referenced) | ✅ Same — serverless containers | Stable stall 🐎 |
| **AI model access** | Bedrock (IAM permission) | OpenAI (connection string) | ⚡ Different auth model | Same donkey-hiring idea, different paperwork — AWS uses an IAM role, Azure hands over a connection string |
| **Resource grouping** | Tags only | Resource Group (explicit) | ↔ Different approach | Label on the original mail item the backpack was sliced from |
| **IAM** | Role + inline policy | Managed identity (not shown) | ↔ Different auth model | Manifest template 📋 |

### Key observation

The AWS and Azure infra create the **same logical architecture** with different
resources. This is why the application code uses abstract interfaces (`BaseDocumentStorage`,
`BaseConversationHistory`) — the infra is different but the app doesn't care.

- 🫏 **Donkey:** The AWS depot — DynamoDB and OpenSearch serve as the GPS-indexed warehouse and trip-log database for donkeys running the cloud route.

---

## DE-Familiar Resources (Nothing New)

These are identical to what you'd create in any production DE project:

### S3 bucket

```hcl
resource "aws_s3_bucket" "documents" {
  bucket = "${local.prefix}-documents"
}
```

Standard bucket with versioning, encryption, public access block. You create these
weekly in production. Nothing to learn here.

### DynamoDB table

```hcl
resource "aws_dynamodb_table" "conversations" {
  name         = "${local.prefix}-conversations"
  billing_mode = "PAY_PER_REQUEST"     # ← good choice for dev/low traffic
  hash_key     = "session_id"
  range_key    = "timestamp"
}
```

Standard DynamoDB with composite key. `PAY_PER_REQUEST` means $0 when idle — the
right choice for a dev/portfolio project. Same pattern as any production DynamoDB table.

### ECR / ACR

```hcl
resource "aws_ecr_repository" "app" {
  name                 = local.prefix
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
}
```

Standard container registry. Same as any containerised service.

### Cosmos DB (Serverless)

```hcl
capabilities {
  name = "EnableServerless"
}
```

Serverless = pay-per-request, just like DynamoDB's `PAY_PER_REQUEST`. This is
a cost-optimization choice — no idle charges for a portfolio project.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## AI-Specific Resources (What's New)

These are the resources that exist **because** this is an AI app, not a traditional
backend:

### 1. Bedrock access (IAM permission)

```hcl
{
    Effect = "Allow"
    Action = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
    ]
    Resource = "*"
}
```

**What this is:** Permission to call AWS Bedrock (the AI model service).

**Why it's new for a DE:** In traditional apps, your ECS task talks to S3, DynamoDB,
RDS — databases and storage. Here it also talks to an **AI model** (Claude, Titan).
That requires a new IAM permission you've never needed before.

**Why `Resource = "*"`?** Bedrock model ARNs are region-specific and model-specific.
Using `*` is simpler for dev but should be scoped in production:
```hcl
# Production: scope to specific models
Resource = [
    "arn:aws:bedrock:eu-central-1::foundation-model/anthropic.claude-3-5-sonnet*",
    "arn:aws:bedrock:eu-central-1::foundation-model/amazon.titan-embed-text-v2*",
]
```

### 2. DynamoDB TTL (AI-specific reasoning)

```hcl
ttl {
    attribute_name = "expires_at"
    enabled        = true
}
```

TTL exists in regular apps too, but the **reason** here is AI-specific:
- Old conversations are useless for follow-up context
- Storing 100K old messages means higher backup costs for zero value
- Privacy — chat data shouldn't live forever

### 3. What's NOT created (and why it matters)

The comment in `infra/aws/terraform.tf` is telling:

```hcl
# NOTE: OpenSearch Serverless is NOT included due to cost (~$350/month minimum).
# See docs/cost-analysis.md for alternatives.
```

**OpenSearch Serverless** (the vector database) would be the most expensive resource
at $350/month minimum — more than all other resources combined. This is a common
AI infrastructure decision: the vector store is often the biggest cost driver.

For this portfolio project, the vector store is created manually or uses a local
alternative. In production, you'd add it to Terraform with proper capacity planning.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Terraform Patterns You Already Know

Every pattern in this infra code is one you already use:

### 1. Variable-driven naming

```hcl
variable "environment" {
  description = "Deployment environment (dev, stg, prd)"
  type        = string
  default     = "dev"
}

locals {
  prefix = "rag-chatbot-${var.environment}"
}

# Usage
bucket = "${local.prefix}-documents"   # → "rag-chatbot-dev-documents"
```

Standard Terraform pattern — `local.prefix` for consistent naming.

### 2. Default tags

```hcl
provider "aws" {
  default_tags {
    tags = {
      Project     = "rag-chatbot"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
```

Standard tagging convention: Project, Environment, ManagedBy.

### 3. Outputs

```hcl
output "s3_bucket_name" {
  value       = aws_s3_bucket.documents.id
  description = "S3 bucket for documents"
}
```

Standard outputs for CI/CD to reference. Same pattern everywhere.

### 4. Provider versions pinned

```hcl
required_providers {
  aws = {
    source  = "hashicorp/aws"
    version = "~> 5.0"
  }
}
```

Pessimistic constraint (`~>`) — allows 5.x but not 6.0. Standard Terraform best practice.

- 🫏 **Donkey:** Blueprints for building the stable — run one command and the whole building appears, fences and all.

---

## What's NOT in Terraform (and Why)

| Missing Resource | Why It's Not Here | In Production You'd Add | 🫏 Donkey |
| --- | --- | --- | --- |
| **OpenSearch Serverless** | $350/month minimum — too expensive for dev | `aws_opensearchserverless_collection` with HNSW index | AWS search hub 🔍 |
| **Azure AI Search** | Free tier is manual setup | `azurerm_search_service` with vector index config | Azure hub ☁️ |
| **Bedrock model access** | No Terraform resource needed (just IAM) | Model access is enabled per-region in AWS console | No blueprint needed — you tick a box in the AWS console to let the donkey carry Claude in that region |
| **Azure OpenAI deployment** | Requires manual provisioning | `azurerm_cognitive_deployment` for GPT-4o + embedding models | Blueprints can spin up the GPT-4o donkey and the embedding GPS stamper as cognitive deployments |
| **ECS Fargate service** | Referenced but full config omitted for simplicity | Task definition, service, ALB, target group | Stable stall 🐎 |
| **Container App** | Referenced but full config omitted | `azurerm_container_app` with ingress, scaling rules | Stable stall 🐎 |
| **VPC / Network** | Not needed for serverless resources | VPC, subnets, security groups for production | Stable yard fencing — controls which routes traffic may take in and out |

**The takeaway:** This Terraform creates the "DE-familiar" resources (storage, database,
container registry). The AI-specific resources (vector store, model endpoints) are either
too expensive for dev or require manual provisioning.

- 🫏 **Donkey:** Blueprints for building the stable — run one command and the whole building appears, fences and all.

---

## DE vs AI Engineer — What Each Sees

| Aspect | What a DE sees | What an AI Engineer sees | 🫏 Donkey |
| --- | --- | --- | --- |
| S3 bucket | Standard document storage | Raw file backup for re-ingestion when chunking strategy changes | The original parcel store — needed if you ever change how the donkey cuts chunks and need to re-pack |
| DynamoDB table | Standard session store | Token budget storage — each row becomes input tokens | AWS depot 🏭 |
| DynamoDB TTL | Standard data retention | Context window management — old conversations are worthless tokens | AWS depot 🏭 |
| ECR repository | Standard container registry | Same — no AI difference | Stable address 🏷️ |
| IAM `bedrock:InvokeModel` | New permission, never used before | The permission that enables the entire AI pipeline | First permission DEs ever grant the donkey — without it, the stable manager can't dispatch a single delivery |
| Missing OpenSearch | "Why isn't the vector store here?" | Cost decision — $350/month for a portfolio project is wasteful | AWS search hub 🔍 |
| `PAY_PER_REQUEST` | Standard dev billing mode | Essential for AI apps — query patterns are unpredictable and bursty | Fuel-and-feed bill for keeping the donkey and stable running |

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Self-Check Questions

Test your understanding:

1. **Name the 7 AWS resources created.** Which ones are DE-familiar and which are AI-specific?
2. **Why is OpenSearch Serverless NOT in Terraform?** What would you add for production?
3. **Why does the IAM role include `bedrock:InvokeModel`?** What DE-familiar AWS permission is this analogous to?
4. **Map each AWS resource to its Azure equivalent.** Which AWS resource has NO direct Azure equivalent?
5. **Why is DynamoDB billing set to `PAY_PER_REQUEST` instead of provisioned capacity?**
6. **The Azure Cosmos DB uses serverless mode. What is the DynamoDB equivalent of this choice?**
7. **If you needed to add the vector store to Terraform, what resource type would you use?** (AWS and Azure)

### Answers

1. S3 bucket (DE), S3 versioning (DE), S3 encryption (DE), S3 public block (DE), DynamoDB (DE), ECR (DE), IAM role with Bedrock permission (AI-specific). 6 DE-familiar, 1 AI-specific.
2. $350/month minimum — too expensive for a dev/portfolio project. For production: `aws_opensearchserverless_collection` with vector search index configured for 1024 dimensions (matching Titan Embeddings).
3. The ECS task needs to call Bedrock to generate embeddings and LLM responses. Analogous to `dynamodb:GetItem` or `s3:GetObject` — a permission to use an AWS service.
4. S3 → Storage Account + Container, DynamoDB → Cosmos DB, ECR → ACR, IAM Role → Managed Identity. The `aws_s3_bucket_public_access_block` has no direct Azure equivalent (Azure uses network rules instead).
5. PAY_PER_REQUEST = $0 when idle, pay only for actual reads/writes. Perfect for dev/portfolio where usage is sporadic. Provisioned capacity would cost ~$5-10/month even with zero traffic.
6. `EnableServerless` capability in Cosmos DB = `PAY_PER_REQUEST` in DynamoDB. Both are pay-per-use with zero idle cost.
7. AWS: `aws_opensearchserverless_collection` (or `aws_opensearch_domain` for managed). Azure: `azurerm_search_service` (with SKU "free" for dev or "basic" for production).

- 🫏 **Donkey:** A quick quiz for the trainee stable hand — answer these to confirm the key donkey delivery concepts have landed.
