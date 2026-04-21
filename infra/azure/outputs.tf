# =============================================================================
# Outputs
# =============================================================================
# Values needed by:
#   - CI/CD pipelines (ACR login server)
#   - Application configuration (storage account, Cosmos DB endpoint)
#   - Other Terraform stacks that reference this one
# =============================================================================

# --- Resource Group ---

output "resource_group_name" {
  description = "Azure resource group name"
  value       = azurerm_resource_group.main.name
}

# --- Blob Storage ---

output "storage_account_name" {
  description = "Blob storage account name for document storage"
  value       = azurerm_storage_account.documents.name
}

output "storage_account_primary_key" {
  description = "Blob storage account primary access key"
  value       = azurerm_storage_account.documents.primary_access_key
  sensitive   = true
}

output "storage_container_name" {
  description = "Blob storage container name"
  value       = azurerm_storage_container.documents.name
}

# --- Cosmos DB ---

output "cosmos_db_endpoint" {
  description = "Cosmos DB account endpoint"
  value       = azurerm_cosmosdb_account.main.endpoint
}

output "cosmos_db_primary_key" {
  description = "Cosmos DB primary access key"
  value       = azurerm_cosmosdb_account.main.primary_key
  sensitive   = true
}

output "cosmos_db_database_name" {
  description = "Cosmos DB database name"
  value       = azurerm_cosmosdb_sql_database.main.name
}

# --- Container Registry ---

output "acr_login_server" {
  description = "Container registry login server URL"
  value       = azurerm_container_registry.main.login_server
}

output "acr_admin_username" {
  description = "Container registry admin username"
  value       = azurerm_container_registry.main.admin_username
}

output "acr_admin_password" {
  description = "Container registry admin password"
  value       = azurerm_container_registry.main.admin_password
  sensitive   = true
}
