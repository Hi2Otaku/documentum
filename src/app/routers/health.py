from fastapi import APIRouter

from app.schemas.common import EnvelopeResponse

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
