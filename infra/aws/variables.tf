# =============================================================================
# Input Variables
# =============================================================================

variable "project" {
  description = "Project name, used in resource naming and tagging"
  type        = string
  default     = "rag-chatbot"
}

variable "environment" {
  description = "Deployment environment (dev, stg, prd)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "stg", "prd"], var.environment)
    error_message = "Environment must be one of: dev, stg, prd."
  }
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "eu-central-1"
}

variable "image_tag" {
  description = "Docker image tag to deploy to ECS"
  type        = string
  default     = "latest"
}

variable "conversation_ttl_days" {
  description = "Number of days to keep conversation history before auto-deletion"
  type        = number
  default     = 7
}

# --- Cost Controller ---

variable "cost_limit_eur" {
  description = "Monthly budget limit in EUR — resources are killed when exceeded"
  type        = number
  default     = 5
}

variable "alert_email" {
  description = "Email address for budget alerts (80% warning + 100% kill notification)"
  type        = string
}
