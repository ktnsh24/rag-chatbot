# =============================================================================
# Cost Controller — AWS Budget Guard (€5 kill switch)
# =============================================================================
# Creates an AWS Budget that monitors actual spend. When cost reaches:
#   - 80% (€4): sends email warning via SNS
#   - 100% (€5): triggers Lambda to destroy all project resources
#
# This prevents accidental cloud bills when running labs.
# =============================================================================

# --- SNS Topic for Budget Alerts ---

resource "aws_sns_topic" "budget_alert" {
  name = "${local.prefix}-budget-alert"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "budget_email" {
  topic_arn = aws_sns_topic.budget_alert.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# --- AWS Budget ---

resource "aws_budgets_budget" "cost_limit" {
  name         = "${local.prefix}-cost-limit"
  budget_type  = "COST"
  limit_amount = tostring(var.cost_limit_eur)
  limit_unit   = "USD" # AWS Budgets uses USD; €5 ≈ $5.50
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = ["user:Project$${var.project}"]
  }

  # 80% warning — email only
  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.budget_alert.arn]
  }

  # 100% — email + trigger Lambda kill switch
  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.budget_alert.arn]
  }
}

# --- Lambda Kill Switch ---

data "archive_file" "budget_killer" {
  type        = "zip"
  source_dir  = "${path.module}/budget_killer_lambda"
  output_path = "${path.module}/.build/budget_killer.zip"
}

resource "aws_lambda_function" "budget_killer" {
  function_name    = "${local.prefix}-budget-killer"
  filename         = data.archive_file.budget_killer.output_path
  source_code_hash = data.archive_file.budget_killer.output_base64sha256
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 300
  memory_size      = 128

  environment {
    variables = {
      PROJECT     = var.project
      ENVIRONMENT = var.environment
      AWS_REGION_ = var.aws_region # AWS_REGION is reserved
    }
  }

  role = aws_iam_role.budget_killer_role.arn
  tags = local.common_tags
}

# Allow SNS to invoke the Lambda
resource "aws_lambda_permission" "sns_invoke" {
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.budget_killer.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.budget_alert.arn
}

# Subscribe Lambda to the SNS topic
resource "aws_sns_topic_subscription" "lambda_kill" {
  topic_arn = aws_sns_topic.budget_alert.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.budget_killer.arn
}

# --- IAM Role for Budget Killer Lambda ---

resource "aws_iam_role" "budget_killer_role" {
  name = "${local.prefix}-budget-killer-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "budget_killer_policy" {
  name = "${local.prefix}-budget-killer-policy"
  role = aws_iam_role.budget_killer_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid    = "KillResources"
        Effect = "Allow"
        Action = [
          # ECS
          "ecs:ListServices",
          "ecs:UpdateService",
          "ecs:ListClusters",
          # DynamoDB
          "dynamodb:ListTables",
          "dynamodb:DeleteTable",
          # S3 — empty + delete
          "s3:ListBucket",
          "s3:DeleteObject",
          "s3:ListAllMyBuckets",
          "s3:DeleteBucket",
          # ECR
          "ecr:DescribeRepositories",
          "ecr:DeleteRepository",
          # Lambda (self-preservation — won't delete itself)
          "lambda:ListFunctions",
          "lambda:DeleteFunction",
          # Resource tagging for discovery
          "tag:GetResources"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:ResourceTag/Project" = var.project
          }
        }
      }
    ]
  })
}
