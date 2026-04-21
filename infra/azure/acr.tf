# =============================================================================
# Container Registry (ACR)
# =============================================================================
# Stores Docker images built by CI/CD for deployment to Container Apps.
# =============================================================================

resource "azurerm_container_registry" "main" {
  name                = "${local.prefix_sa}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = merge(local.common_tags, {
    Purpose = "Docker image registry for the RAG chatbot"
  })
}
