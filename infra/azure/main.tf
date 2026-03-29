# =============================================================================
# Azure Infrastructure — Terraform
# =============================================================================
# This creates all Azure resources for the RAG Chatbot.
#
# Resources created:
#   - Resource Group
#   - Blob Storage account + container (document storage)
#   - Cosmos DB account + database + container (conversation history)
#   - Container Registry (Docker images)
#   - Container App Environment + Container App (hosting)
#
# NOTE: Azure AI Search (Free tier) has limits: 50 MB, 3 indexes.
# See docs/cost-analysis.md for details.
#
# Usage:
#   cd infra/azure
#   terraform init
#   terraform plan -var="environment=dev"
#   terraform apply -var="environment=dev"
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

# --- Variables ---

variable "environment" {
  description = "Deployment environment (dev, stg, prd)"
  type        = string
  default     = "dev"
}

variable "azure_region" {
  description = "Azure region"
  type        = string
  default     = "westeurope"
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

locals {
  prefix = "ragchatbot${var.environment}"
  # Azure resource names must be lowercase alphanumeric
  rg_name = "rag-chatbot-${var.environment}-rg"
}

# --- Resource Group ---

resource "azurerm_resource_group" "main" {
  name     = local.rg_name
  location = var.azure_region

  tags = {
    Project     = "rag-chatbot"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# --- Storage Account (Blob — Document Storage) ---

resource "azurerm_storage_account" "documents" {
  name                     = "${local.prefix}docs"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS" # Locally redundant — cheapest option

  tags = {
    Purpose = "Store uploaded documents for RAG ingestion"
  }
}

resource "azurerm_storage_container" "documents" {
  name                  = "rag-chatbot-documents"
  storage_account_name  = azurerm_storage_account.documents.name
  container_access_type = "private"
}

# --- Cosmos DB (Conversation History) ---

resource "azurerm_cosmosdb_account" "main" {
  name                = "${local.prefix}-cosmos"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  offer_type          = "Standard"

  # Serverless = pay per request (cheapest for low traffic)
  capabilities {
    name = "EnableServerless"
  }

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
  }

  tags = {
    Purpose = "Conversation history and session management"
  }
}

resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "rag-chatbot"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "conversations" {
  name                = "conversations"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/session_id"]

  default_ttl = 604800 # 7 days — auto-delete old conversations
}

# --- Container Registry ---

resource "azurerm_container_registry" "main" {
  name                = "${local.prefix}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic" # Cheapest tier — 10 GB storage

  tags = {
    Purpose = "Docker image registry"
  }
}

# --- Outputs ---

output "resource_group_name" {
  value       = azurerm_resource_group.main.name
  description = "Azure resource group name"
}

output "storage_account_name" {
  value       = azurerm_storage_account.documents.name
  description = "Blob storage account for documents"
}

output "cosmos_db_endpoint" {
  value       = azurerm_cosmosdb_account.main.endpoint
  description = "Cosmos DB endpoint"
}

output "acr_login_server" {
  value       = azurerm_container_registry.main.login_server
  description = "Container registry login server"
}
