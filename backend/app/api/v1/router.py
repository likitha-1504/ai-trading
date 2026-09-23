"""API v1 master router scaffold."""

from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health", tags=["system"])
async def health_check():
    """Liveness probe for backend engine."""
    return {"status": "ok", "service": "AI Micro-Trading Agent"}
