# AWS Services Deep Dive

## Table of Contents

- [Overview — What AWS services we use and why](#overview)
- [Amazon Bedrock](#amazon-bedrock)
- [Amazon S3](#amazon-s3)
- [Amazon DynamoDB](#amazon-dynamodb)
- [Amazon OpenSearch Serverless](#amazon-opensearch-serverless)
- [Amazon ECS Fargate](#amazon-ecs-fargate)
- [Amazon CloudWatch](#amazon-cloudwatch)
- [AWS IAM](#aws-iam)

---

## Overview

| Service | Purpose in this project | Cost model | 🫏 Donkey |
| --- | --- | --- | --- |
| **Bedrock** | LLM inference (Claude) + embeddings (Titan) | Pay per token | Cloud stable that hires the donkey by the hay bale — Claude carries questions, Titan stamps text with GPS coordinates |
| **S3** | Store uploaded documents | Pay per GB stored | AWS warehouse — pennies per month to store the donkey's source documents |
| **DynamoDB** | Conversation history + **vector store** (cheap mode) | Pay per request | AWS depot — DynamoDB: Conversation history + vector store (cheap mode) · Pay per request |
| **OpenSearch Serverless** | Vector store for embeddings (production) | Pay per OCU-hour | Amazon's index room — OpenSearch Serverless: Vector store for embeddings (production) · Pay per OCU-hour |
| **ECS Fargate** | Host the FastAPI container | Pay per vCPU/memory-hour | Stall that houses the worker — ECS Fargate: Host the FastAPI container · Pay per vCPU/memory-hour |
| **ECR** | Docker image registry | Pay per GB stored | AWS Docker registry address where the donkey image is parked — billed per gigabyte stored. |
| **Lambda** | Event-driven document ingestion | Pay per invocation | Post office pre-sort — Lambda: Event-driven document ingestion · Pay per invocation |
| **CloudWatch** | Logs, metrics, dashboards, alerts | Free tier generous | The tachograph display for the whole stable — logs, metrics, dashboards, alerts, and the first 10 GB are free. |
| **IAM** | Permissions and roles | Free | Complimentary feed allowance — IAM: Permissions and roles · Free |

- 🫏 **Donkey:** Think of this as the orientation briefing given to a new donkey before its first delivery run — it sets the context for everything that follows.

---

## Amazon Bedrock

### What it is

Amazon Bedrock is a **fully managed service for accessing foundation models** (LLMs). You call an API, get a response. No GPU instances, no model hosting, no maintenance.

### How we use it

1. **LLM inference** — Send a question + context to Claude 3.5 Sonnet, get an answer back
2. **Embeddings** — Convert text into vectors using Amazon Titan Embeddings v2

### Code location

`src/llm/aws_bedrock.py`

### API used

We use the **Converse API** (`bedrock-runtime:converse`), which is Bedrock's unified interface. It works the same for Claude, Titan, Llama, and Mistral — you don't need model-specific request formats.

```python
response = self._runtime_client.converse(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    messages=[{"role": "user", "content": [{"text": prompt}]}],
    system=[{"text": system_prompt}],
    inferenceConfig={"maxTokens": 2048, "temperature": 0.1},
)
```

### Models available

| Model | Use case | Input cost | Output cost | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| Claude 3.5 Sonnet v2 | Best for RAG (accurate, fast) | $0.003/1K | $0.015/1K | Top-tier donkey — accurate and quick, the default carrier for production deliveries |
| Claude 3 Haiku | Cheaper, faster, less accurate | $0.00025/1K | $0.00125/1K | Pony-sized donkey — cheaper hay and faster trips, but more likely to drop a detail |
| Titan Text Embeddings v2 | Convert text to vectors | $0.00002/1K | N/A | Complimentary feed allowance — Titan Text Embeddings v2: Convert text to vectors · $0.00002/1K · N/A |
| Llama 3.1 70B | Open source alternative | $0.00099/1K | $0.00099/1K | Open-source donkey — same hay rate in and out, handy when you want to swap stables later |

### IAM permissions needed

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": "*"
}
```

### How to enable model access

Bedrock models are opt-in. Go to AWS Console → Bedrock → Model access → Request access to Claude and Titan.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Amazon S3

### What it is

Simple Storage Service — object storage for files. Think of it as a cloud hard drive.

### How we use it

Store uploaded documents (PDFs, TXTs, etc.) before and after ingestion.

### Code location

`src/storage/aws_s3.py` (abstraction), `infra/aws/s3.tf` (Terraform)

### Terraform resource

```hcl
resource "aws_s3_bucket" "documents" {
  bucket = "rag-chatbot-dev-documents"
}
```

Features enabled:
- **Versioning**: Keep history of document versions
- **Server-side encryption**: AES-256 (data encrypted at rest)
- **Public access blocked**: No accidental public exposure

### Cost

- Storage: $0.023/GB/month
- Free tier: 5 GB for 12 months
- For this project: essentially free (documents are small)

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Amazon DynamoDB

### What it is

A fully managed NoSQL key-value database. Fast (single-digit millisecond latency), serverless, scales automatically.

### How we use it

Store **conversation history** — so follow-up questions understand previous context.

### Table design

```
Table: rag-chatbot-dev-conversations
Primary Key: session_id (String)
Sort Key: timestamp (String)
TTL: expires_at (auto-delete old conversations)
```

| Field | Type | Purpose | 🫏 Donkey |
| --- | --- | --- | --- |
| `session_id` | String (PK) | Groups messages in a conversation | Trip log entry — session_id: String (PK) · Groups messages in a conversation |
| `timestamp` | String (SK) | Orders messages chronologically | Timestamp stamped on the trip log entry — when the donkey set off or returned |
| `role` | String | "user" or "assistant" | Stable keys — only authorised callers may ask the donkey to deliver |
| `content` | String | The message text | The actual cargo text inside the backpack the donkey is carrying |
| `expires_at` | Number | TTL — auto-delete after 7 days | Donkey-side view of expires_at — affects how the donkey loads, reads, or delivers the cargo |

### Why DynamoDB and not PostgreSQL?

- **No server to manage**: DynamoDB is serverless
- **Pay per request**: No idle costs (on-demand mode)
- **Key-value access pattern**: We only ever query by session_id
- **TTL built-in**: Old conversations auto-delete (saves storage)
- **Free tier**: 25 GB storage + 25 read/write capacity units

### Cost

- On-demand: $1.25 per million writes, $0.25 per million reads
- Free tier covers most personal use

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Amazon OpenSearch Serverless

### What it is

A serverless version of OpenSearch (Elasticsearch fork) that supports **vector search** via k-NN plugin.

### How we use it

Store document chunk embeddings and perform similarity search.

### ⚠️ COST WARNING

OpenSearch Serverless has a **minimum cost of ~$350/month** (4 OCUs at $0.24/hr).

For development: **Use ChromaDB locally instead.**
Only deploy OpenSearch Serverless when you need cloud-based vector search.

### Code location

`src/vectorstore/aws_opensearch.py`

### Index configuration

```python
{
    "settings": {
        "index": {"knn": True}
    },
    "mappings": {
        "properties": {
            "embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib"
                }
            },
            "text": {"type": "text"},
            "document_id": {"type": "keyword"},
            "document_name": {"type": "keyword"}
        }
    }
}
```

- 🫏 **Donkey:** The warehouse robot dispatched to find the right backpack shelf — it uses GPS coordinates (embeddings) to locate the nearest relevant chunks in ~9 hops.

---

## Amazon ECS Fargate

### What it is

Run Docker containers without managing servers. You define a task (container image + resources), ECS runs it.

### How we use it

Host the FastAPI application in production.

### Fargate vs EC2

| | Fargate (our choice) | EC2 | 🫏 Donkey |
| --- | --- | --- | --- |
| Server management | None | You manage instances | Donkey-side view of Server management — affects how the donkey loads, reads, or delivers the cargo |
| Scaling | Automatic | Configure auto-scaling groups | How the stable adds or removes donkeys when delivery volume changes |
| Cost | Pay per vCPU/memory-hour | Pay per instance-hour | Fargate bills you per minute the donkey actually pulls; EC2 charges rent on the whole stall whether it works or not. |
| Minimum | ~$30/month (0.25 vCPU) | ~$10/month (t3.micro) | Fuel-and-feed bill for keeping the donkey and stable running |

### Why Fargate

For a single container app, Fargate is simpler. No SSH, no patches, no instance management.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Amazon CloudWatch

### What it is

AWS's monitoring service — logs, metrics, dashboards, and alarms.

### How we use it

1. **Logs**: Application logs from ECS tasks
2. **Metrics**: Custom metrics (latency, token usage, error rates)
3. **Dashboards**: Visual monitoring
4. **Alarms**: Alert when error rate exceeds threshold

### Free tier

- 10 custom metrics
- 5 GB log ingestion
- 3 dashboards
- 10 alarms

Generous enough for personal use.

- 🫏 **Donkey:** Running the donkey on rented pasture — AWS or Azure provides the stable so you only pay for the hay consumed.

---

## AWS IAM

### What it is

Identity and Access Management — controls who can do what in AWS.

### How we use it

The ECS task has an IAM role with these permissions:

| Permission | Resource | Why | 🫏 Donkey |
| --- | --- | --- | --- |
| `s3:GetObject`, `s3:PutObject` | Documents bucket | Read/write documents | Permission slip letting the donkey pick up and drop off parcels at the AWS warehouse |
| `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:Query` | Conversations table | Read/write history | AWS-side stable yard — dynamodb:GetItem, dynamodb:PutItem, dynamodb:Query: Conversations table · Read/write history |
| `bedrock:InvokeModel` | All models | Call Claude and Titan | Without this permission the stable manager can't wake the donkey — every chat would die at the gate |

### Principle of least privilege

Each permission is scoped to the specific resource (bucket ARN, table ARN). The role can't access any other S3 buckets or DynamoDB tables.

- 🫏 **Donkey:** The AWS depot — DynamoDB and OpenSearch serve as the GPS-indexed warehouse and trip-log database for donkeys running the cloud route.
