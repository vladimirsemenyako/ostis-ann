"""
Health check router
"""
import logging
from fastapi import APIRouter
from datetime import datetime
from models import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns service status and version information
    """
    logger.debug("Health check requested")
    return HealthResponse(
        status="healthy",
        service="ostis-ann-unified-service",
        version="1.0.0",
        timestamp=datetime.utcnow()
    )


@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OSTIS ANN Unified Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "chat": "/api/v1/chat",
            "documents": "/api/v1/documents"
        }
    }

