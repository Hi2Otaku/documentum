from fastapi import APIRouter

from app.schemas.common import EnvelopeResponse
from app.schemas.monitoring import HealthResponse

router = APIRouter()


@router.get("/health", response_model=EnvelopeResponse[dict])
async def health_check():
    return EnvelopeResponse(
        data={
            "status": "healthy",
            "service": "documentum-api",
            "version": "0.1.0",
        }
    )


@router.get("/health/deep", response_model=EnvelopeResponse[HealthResponse])
async def deep_health_check():
    """Deep health check with per-component breakdown.

    Unauthenticated -- designed for load balancers and Docker healthchecks.
    """
    from app.services.monitoring_service import check_all_health

    health = await check_all_health()
    return EnvelopeResponse(data=health)
