"""
Budget Killer Lambda — Emergency cost control.

Triggered via SNS when AWS Budget exceeds the threshold.
Finds all resources tagged with Project=rag-chatbot and shuts them down.
"""

import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PROJECT = os.environ.get("PROJECT", "rag-chatbot")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
REGION = os.environ.get("AWS_REGION_", "eu-central-1")


def lambda_handler(event: dict, context: object) -> dict:
    """SNS-triggered handler that kills all project resources."""
    logger.info("🚨 Budget killer triggered! Event: %s", json.dumps(event))

    # Parse SNS message to check if this is the 100% threshold
    for record in event.get("Records", []):
        message = record.get("Sns", {}).get("Message", "")
        logger.info("SNS message: %s", message)

    prefix = f"{PROJECT}-{ENVIRONMENT}"
    killed: list[str] = []

    # 1. Scale ECS services to 0
    killed.extend(_kill_ecs(prefix))

    # 2. Delete DynamoDB tables
    killed.extend(_kill_dynamodb(prefix))

    # 3. Empty and delete S3 buckets
    killed.extend(_kill_s3(prefix))

    summary = {
        "status": "resources_killed",
        "project": PROJECT,
        "environment": ENVIRONMENT,
        "killed_count": len(killed),
        "killed_resources": killed,
    }
    logger.info("💀 Kill summary: %s", json.dumps(summary))
    return summary


def _kill_ecs(prefix: str) -> list[str]:
    """Scale all ECS services to 0 desired count."""
    killed = []
    ecs = boto3.client("ecs", region_name=REGION)

    try:
        clusters = ecs.list_clusters()["clusterArns"]
        for cluster_arn in clusters:
            if prefix not in cluster_arn:
                continue
            services = ecs.list_services(cluster=cluster_arn)["serviceArns"]
            for service_arn in services:
                ecs.update_service(
                    cluster=cluster_arn,
                    service=service_arn,
                    desiredCount=0,
                )
                killed.append(f"ecs:scaled-to-0:{service_arn}")
                logger.info("Scaled ECS service to 0: %s", service_arn)
    except Exception:
        logger.exception("Error killing ECS services")

    return killed


def _kill_dynamodb(prefix: str) -> list[str]:
    """Delete DynamoDB tables matching project prefix."""
    killed = []
    ddb = boto3.client("dynamodb", region_name=REGION)

    try:
        tables = ddb.list_tables()["TableNames"]
        for table in tables:
            if prefix in table:
                ddb.delete_table(TableName=table)
                killed.append(f"dynamodb:deleted:{table}")
                logger.info("Deleted DynamoDB table: %s", table)
    except Exception:
        logger.exception("Error killing DynamoDB tables")

    return killed


def _kill_s3(prefix: str) -> list[str]:
    """Empty and delete S3 buckets matching project prefix."""
    killed = []
    s3 = boto3.client("s3", region_name=REGION)
    s3_resource = boto3.resource("s3", region_name=REGION)

    try:
        buckets = s3.list_buckets()["Buckets"]
        for bucket in buckets:
            name = bucket["Name"]
            if prefix not in name:
                continue
            # Empty bucket first
            bucket_obj = s3_resource.Bucket(name)
            bucket_obj.objects.all().delete()
            bucket_obj.object_versions.all().delete()
            s3.delete_bucket(Bucket=name)
            killed.append(f"s3:deleted:{name}")
            logger.info("Deleted S3 bucket: %s", name)
    except Exception:
        logger.exception("Error killing S3 buckets")

    return killed
