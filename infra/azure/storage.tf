# =============================================================================
# Blob Storage — Document Storage
# =============================================================================
# Stores uploaded documents (PDF, TXT, Markdown) for RAG ingestion.
# The application reads from here via src/storage/azure_blob.py.
# =============================================================================

resource "azurerm_storage_account" "documents" {
  name                     = "${local.prefix_sa}docs"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = merge(local.common_tags, {
    Purpose = "Store uploaded documents for RAG ingestion"
  })
}

resource "azurerm_storage_container" "documents" {
  name                  = "documents"
  storage_account_name  = azurerm_storage_account.documents.name
  container_access_type = "private"
}
