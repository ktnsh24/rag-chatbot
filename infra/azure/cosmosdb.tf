# =============================================================================
# Cosmos DB — Conversation History
# =============================================================================
# Stores chat session history for follow-up questions.
# The application reads/writes via src/history/azure_cosmosdb.py.
#
# Schema:
#   - Partition key: /session_id  — groups messages per conversation
#   - TTL:           default_ttl  — auto-deletes old conversations
#
# Uses serverless capacity mode — pay per request, no idle costs.
# =============================================================================

resource "azurerm_cosmosdb_account" "main" {
  name                = "${local.prefix}-cosmos"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  offer_type          = "Standard"

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

  tags = merge(local.common_tags, {
    Purpose = "Conversation history and session management"
  })
}

# Cosmos DB serverless accounts need extra time to come fully online
# after creation. Without this delay, the SQL database/container creation
# fails with "database account state is not Online".
resource "time_sleep" "wait_for_cosmos" {
  depends_on      = [azurerm_cosmosdb_account.main]
  create_duration = "60s"
}

resource "azurerm_cosmosdb_sql_database" "main" {
  name                = var.project
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name

  depends_on = [time_sleep.wait_for_cosmos]
}

resource "azurerm_cosmosdb_sql_container" "conversations" {
  name                = "conversations"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/session_id"]
  default_ttl         = var.conversation_ttl_seconds
}
