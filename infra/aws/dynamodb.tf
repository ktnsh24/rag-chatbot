# =============================================================================
# DynamoDB — Conversation History
# =============================================================================
# Stores chat session history for follow-up questions.
# The application reads/writes via src/history/aws_dynamodb.py.
#
# Schema:
#   - Partition key: session_id (S)  — groups messages per conversation
#   - Sort key:      timestamp  (S)  — orders messages chronologically
#   - TTL:           expires_at      — auto-deletes old conversations
# =============================================================================

resource "aws_dynamodb_table" "conversations" {
  name         = "${local.prefix}-conversations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"
  range_key    = "timestamp"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = var.environment == "prd" ? true : false
  }

  tags = {
    Purpose = "Store conversation history for follow-up questions"
  }
}
