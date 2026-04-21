# Terraform Infrastructure Guide

This project includes Terraform configurations for both AWS and Azure.
This guide walks you through every resource, how to deploy, and how to
manage your infrastructure.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Infrastructure](#aws-infrastructure)
3. [Azure Infrastructure](#azure-infrastructure)
4. [Remote State](#remote-state)
5. [Deploying](#deploying)
6. [Destroying](#destroying)
7. [Cost Impact](#cost-impact)

---

## Prerequisites

### Install Terraform

```bash
# macOS
brew install terraform

# Ubuntu / WSL
sudo apt-get update && sudo apt-get install -y gnupg software-properties-common
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Verify
terraform --version
```

### Authenticate

```bash
# AWS — configure your profile
aws configure sso --profile rag-chatbot
# or export credentials
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="eu-west-1"

# Azure — log in
az login
az account set --subscription "your-subscription-id"
```

---

## AWS Infrastructure

**Location:** `infra/aws/` — split by resource: `s3.tf`, `dynamodb.tf`, `ecr.tf`, `iam.tf`

### Resources Created

| Resource | Purpose | Free Tier? |
|---|---|---|
| `aws_s3_bucket` | Store uploaded documents | ✅ 5 GB |
| `aws_dynamodb_table` | Conversation history | ✅ 25 GB |
| `aws_ecr_repository` | Docker image registry | ✅ 500 MB |
| `aws_iam_role` | ECS task execution role | ✅ Free |
| `aws_iam_role_policy` | Least-privilege policy | ✅ Free |

### Variables

| Variable | Default | Description |
|---|---|---|
| `project_name` | `"rag-chatbot"` | Prefix for all resource names |
| `environment` | `"dev"` | Environment tag |
| `aws_region` | `"eu-west-1"` | AWS region |

### S3 Bucket

```hcl
resource "aws_s3_bucket" "documents" {
  bucket = "${var.project_name}-documents-${var.environment}"
  # Versioning enabled — protects against accidental deletes
  # Server-side encryption with AES-256
  # Public access blocked
}
```

**Why these settings?**
- **Versioning** = undo accidental overwrites
- **SSE-AES256** = encryption at rest (free, no KMS cost)
- **Block public access** = security best practice

### DynamoDB Table

```hcl
resource "aws_dynamodb_table" "conversations" {
  name         = "${var.project_name}-conversations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"
  range_key    = "timestamp"
}
```

**Why PAY_PER_REQUEST?**
- No upfront capacity planning
- Free tier covers 25 WCU + 25 RCU
- Scales automatically
- Perfect for development and low-traffic

### ECR Repository

```hcl
resource "aws_ecr_repository" "app" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}
```

### IAM Role

The ECS task role grants least-privilege access:
- S3: `GetObject`, `PutObject`, `DeleteObject`, `ListBucket`
- DynamoDB: `PutItem`, `GetItem`, `Query`, `DeleteItem`, `BatchWriteItem`
- Bedrock: `InvokeModel`
- OpenSearch: `ESHttpGet`, `ESHttpPut`, `ESHttpPost`, `ESHttpDelete`
- CloudWatch Logs: `CreateLogGroup`, `CreateLogStream`, `PutLogEvents`

---

## Azure Infrastructure

**Location:** `infra/azure/` — split by resource: `resource_group.tf`, `storage.tf`, `cosmosdb.tf`, `acr.tf`

### Resources Created

| Resource | Purpose | Free Tier? |
|---|---|---|
| `azurerm_resource_group` | Resource container | ✅ Free |
| `azurerm_storage_account` | Document storage | ✅ 5 GB LRS |
| `azurerm_storage_container` | Blob container | ✅ Included |
| `azurerm_cosmosdb_account` | Conversation history | ✅ 1000 RU/s free |
| `azurerm_cosmosdb_sql_database` | Database | ✅ Included |
| `azurerm_cosmosdb_sql_container` | Container | ✅ Included |
| `azurerm_container_registry` | Docker images | Basic SKU ~€4.20/mo |

### Variables

| Variable | Default | Description |
|---|---|---|
| `project_name` | `"ragchatbot"` | Prefix for resource names |
| `environment` | `"dev"` | Environment tag |
| `location` | `"westeurope"` | Azure region |

### Cosmos DB (Serverless)

```hcl
resource "azurerm_cosmosdb_account" "main" {
  kind       = "GlobalDocumentDB"
  # Serverless = pay only for what you use
  capabilities {
    name = "EnableServerless"
  }
}
```

**Why Serverless?**
- No minimum cost when idle
- Pay per RU consumed
- Free tier: 1000 RU/s + 25 GB
- Perfect for development

### Container Registry

```hcl
resource "azurerm_container_registry" "main" {
  sku = "Basic"
  # Basic SKU = ~€4.20/month, 10 GB storage
  # Sufficient for a portfolio project
}
```

---

## Remote State

For a portfolio project, local state is fine. For production,
use remote state:

### AWS (S3 + DynamoDB)

```hcl
terraform {
  backend "s3" {
    bucket         = "rag-chatbot-tfstate"
    key            = "aws/terraform.tfstate"
    region         = "eu-west-1"
    dynamodb_table = "rag-chatbot-tflock"
    encrypt        = true
  }
}
```

### Azure (Blob Storage)

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rag-chatbot-tfstate-rg"
    storage_account_name = "ragchatbottfstate"
    container_name       = "tfstate"
    key                  = "azure/terraform.tfstate"
  }
}
```

---

## Deploying

### AWS

```bash
cd infra/aws

# Initialise — downloads the AWS provider
terraform init

# Preview changes
terraform plan -var="environment=dev"

# Apply — creates resources
terraform apply -var="environment=dev"

# Output values (bucket name, table name, etc.)
terraform output
```

### Azure

```bash
cd infra/azure

terraform init
terraform plan -var="environment=dev"
terraform apply -var="environment=dev"
terraform output
```

### Using Workspaces

Terraform workspaces let you manage multiple environments:

```bash
# Create a staging workspace
terraform workspace new staging
terraform apply -var="environment=staging"

# Switch back to dev
terraform workspace select default
```

---

## Destroying

> ⚠️ **This deletes all resources and data permanently.**

```bash
# AWS
cd infra/aws
terraform destroy -var="environment=dev"

# Azure
cd infra/azure
terraform destroy -var="environment=dev"
```

**Tip:** Always destroy resources when you're not using them to avoid costs.

---

## Cost Impact

### AWS (all free-tier eligible)

| Resource | Monthly Cost |
|---|---|
| S3 (5 GB) | $0.00 |
| DynamoDB (on-demand) | $0.00 |
| ECR (500 MB) | $0.00 |
| IAM | $0.00 |
| **Total** | **$0.00** |

### Azure

| Resource | Monthly Cost |
|---|---|
| Storage Account (5 GB LRS) | ~$0.10 |
| Cosmos DB (serverless, free tier) | $0.00 |
| Container Registry (Basic) | ~$4.20 |
| Resource Group | $0.00 |
| **Total** | **~$4.30** |

> 💡 The Azure Container Registry is the only resource with a meaningful
> cost. You can skip it during development and push images directly to
> Azure Container Apps from your local machine.

---

## Common Issues

### "No changes. Your infrastructure matches the configuration."

This means Terraform has already created the resources. Nothing to do.

### "Error: creating S3 Bucket: BucketAlreadyExists"

S3 bucket names are globally unique. Change the `project_name` variable
or add a random suffix.

### "Error: AuthorizationFailed"

Your AWS/Azure credentials don't have permission to create the resources.
Check your IAM policies or Azure RBAC.

### State Lock

If a previous `terraform apply` was interrupted:

```bash
# Find the lock ID in the error message, then:
terraform force-unlock <LOCK_ID>
```
