# =============================================================================
# Resource Group
# =============================================================================
# All Azure resources live inside this resource group.
# One RG per environment keeps things isolated and easy to tear down.
# =============================================================================

resource "azurerm_resource_group" "main" {
  name     = "${local.prefix}-rg"
  location = var.azure_region
  tags     = local.common_tags
}
