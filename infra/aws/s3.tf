# =============================================================================
# S3 — Document Storage
# =============================================================================
# Stores uploaded documents (PDF, TXT, Markdown) for RAG ingestion.
# The application reads from here via src/storage/aws_s3.py.
# =============================================================================

resource "aws_s3_bucket" "documents" {
  bucket = "${local.prefix}-documents"

  tags = {
    Purpose = "Store uploaded documents for RAG ingestion"
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
