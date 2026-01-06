from redis import Redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def get_redis_client() -> Redis:
    """Get Redis client"""
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=False
    )


def check_redis_connection() -> bool:
    """Check if Redis is accessible"""
    try:
        client = get_redis_client()
        client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection check failed: {e}")
        return False
