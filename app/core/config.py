from pydantic_settings import BaseSettings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_KEY: str = "your-secure-api-key-change-this"
    
    # Database Configuration
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "mercury4ai"
    POSTGRES_USER: str = "mercury4ai"
    POSTGRES_PASSWORD: str = "mercury4ai_password"
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # MinIO Configuration
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "mercury4ai"
    MINIO_SECURE: bool = False
    
    # Worker Configuration
    WORKER_CONCURRENCY: int = 2
    
    # Crawl Configuration
    FALLBACK_DOWNLOAD_ENABLED: bool = True
    FALLBACK_DOWNLOAD_MAX_SIZE_MB: int = 10
    
    # LLM Configuration
    DEFAULT_LLM_PROVIDER: str = "openai"
    DEFAULT_LLM_MODEL: str = "gpt-4"
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Don't fail if .env file is missing - use defaults
        extra = "ignore"


# Initialize settings
settings = Settings()

# Warn if using default API key
if settings.API_KEY == "your-secure-api-key-change-this":
    logger.warning(
        "Using default API_KEY. Please set a secure API_KEY in production via environment variable or .env file."
    )
