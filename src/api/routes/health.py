"""
Health Check Route

Provides:
    GET /api/health — overall app health + individual service checks
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from src.api.models import HealthResponse, HealthStatus, ServiceHealth
from src.config import get_settings

router = APIRouter()

# Track app start time for uptime calculation
_start_time = datetime.now(timezone.utc)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the health status of the application and all backend services.",
)
async def health_check(request: Request) -> HealthResponse:
    """
    Checks connectivity to all backend services.

    What it checks (depends on CLOUD_PROVIDER):
        AWS:   S3, OpenSearch, DynamoDB, Bedrock
        Azure: Blob Storage, AI Search, Cosmos DB, Azure OpenAI

    Returns:
        - "healthy" if all services respond
        - "degraded" if some services are down but the app can still work
        - "unhealthy" if critical services (LLM or vector store) are down
    """
    settings = get_settings()
    services: list[ServiceHealth] = []

    # Check if RAG chain is initialized
    rag_chain = getattr(request.app.state, "rag_chain", None)
    if rag_chain is None:
        services.append(
            ServiceHealth(
                name="rag_chain",
                status=HealthStatus.UNHEALTHY,
                message="RAG chain not initialized — check cloud credentials",
            )
        )
    else:
        services.append(
            ServiceHealth(
                name="rag_chain",
                status=HealthStatus.HEALTHY,
                message="RAG chain initialized and ready",
            )
        )

    # Determine overall status
    statuses = [s.status for s in services]
    if HealthStatus.UNHEALTHY in statuses:
        overall = HealthStatus.UNHEALTHY
    elif HealthStatus.DEGRADED in statuses:
        overall = HealthStatus.DEGRADED
    else:
        overall = HealthStatus.HEALTHY

    uptime = int((datetime.now(timezone.utc) - _start_time).total_seconds())

    return HealthResponse(
        status=overall,
        cloud_provider=settings.cloud_provider.value,
        services=services,
        uptime_seconds=uptime,
    )
