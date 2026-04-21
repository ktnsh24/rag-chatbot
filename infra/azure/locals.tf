# =============================================================================
# Local Values
# =============================================================================

locals {
  # Azure resource names must be lowercase alphanumeric (no hyphens for storage)
  prefix    = "${var.project}-${var.environment}"
  prefix_sa = replace("${var.project}${var.environment}", "-", "")

  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
