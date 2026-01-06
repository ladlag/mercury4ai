from fastapi import APIRouter, Depends
from app.core.database import check_db_connection
from app.core.redis_client import check_redis_connection
from app.core.minio_client import minio_client
from app.schemas import HealthResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    db_status = "healthy" if check_db_connection() else "unhealthy"
    redis_status = "healthy" if check_redis_connection() else "unhealthy"
    minio_status = "healthy" if minio_client.check_connection() else "unhealthy"
    
    overall_status = "healthy" if all([
        db_status == "healthy",
        redis_status == "healthy",
        minio_status == "healthy"
    ]) else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        database=db_status,
        redis=redis_status,
        minio=minio_status
    )
