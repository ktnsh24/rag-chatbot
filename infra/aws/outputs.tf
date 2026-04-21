# =============================================================================
# Outputs
# =============================================================================
# Values needed by:
#   - CI/CD pipelines (ECR URL, ECS cluster name)
#   - Application .env configuration (S3 bucket, DynamoDB table)
#   - Other Terraform stacks that reference this one
# =============================================================================

# --- S3 ---

output "s3_bucket_name" {
  description = "S3 bucket name for document storage"
  value       = aws_s3_bucket.documents.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.documents.arn
}

# --- DynamoDB ---

output "dynamodb_table_name" {
  description = "DynamoDB table name for conversation history"
  value       = aws_dynamodb_table.conversations.name
}

output "dynamodb_table_arn" {
  description = "DynamoDB table ARN"
  value       = aws_dynamodb_table.conversations.arn
}

# --- ECR ---

output "ecr_repository_url" {
  description = "ECR repository URL for Docker image push/pull"
  value       = aws_ecr_repository.app.repository_url
}

# --- IAM ---

output "ecs_task_role_arn" {
  description = "IAM role ARN for ECS task (application-level permissions)"
  value       = aws_iam_role.ecs_task_role.arn
}

output "ecs_execution_role_arn" {
  description = "IAM role ARN for ECS execution (image pull, logs)"
  value       = aws_iam_role.ecs_execution_role.arn
}
