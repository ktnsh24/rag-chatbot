# =============================================================================
# AWS Infrastructure — Terraform
# =============================================================================
# This creates all AWS resources for the RAG Chatbot.
#
# Resources created:
#   - S3 bucket (document storage)
#   - DynamoDB table (conversation history)
#   - ECR repository (Docker images)
#   - ECS Fargate cluster + service (container hosting)
#   - IAM roles + policies
#
# NOTE: OpenSearch Serverless is NOT included due to cost (~$350/month minimum).
# See docs/cost-analysis.md for alternatives.
#
# Usage:
#   cd infra/aws
#   terraform init
#   terraform plan -var="environment=dev"
#   terraform apply -var="environment=dev"
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "rag-chatbot"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# --- Variables ---

variable "environment" {
  description = "Deployment environment (dev, stg, prd)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-central-1"
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

locals {
  prefix = "rag-chatbot-${var.environment}"
}

# --- S3 Bucket (Document Storage) ---

resource "aws_s3_bucket" "documents" {
  bucket = "${local.prefix}-documents"

  tags = {
    Purpose = "Store uploaded documents for RAG ingestion"
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- DynamoDB Table (Conversation History) ---

resource "aws_dynamodb_table" "conversations" {
  name         = "${local.prefix}-conversations"
  billing_mode = "PAY_PER_REQUEST" # No idle costs — pay only for reads/writes
  hash_key     = "session_id"
  range_key    = "timestamp"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Purpose = "Store conversation history for follow-up questions"
  }
}

# --- ECR Repository ---

resource "aws_ecr_repository" "app" {
  name                 = local.prefix
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Purpose = "Docker image registry for the RAG chatbot"
  }
}

# --- IAM Role for ECS Task ---

resource "aws_iam_role" "ecs_task_role" {
  name = "${local.prefix}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "${local.prefix}-ecs-task-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:DeleteObject",
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:DeleteItem",
        ]
        Resource = aws_dynamodb_table.conversations.arn
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ]
        Resource = "*"
      },
    ]
  })
}

# --- Outputs ---

output "s3_bucket_name" {
  value       = aws_s3_bucket.documents.id
  description = "S3 bucket for documents"
}

output "dynamodb_table_name" {
  value       = aws_dynamodb_table.conversations.name
  description = "DynamoDB table for conversations"
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.app.repository_url
  description = "ECR repository URL"
}
