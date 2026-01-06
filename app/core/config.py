from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Dict, Any
from pydantic import field_validator
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
    
    # LLM Configuration (Optional defaults)
    DEFAULT_LLM_PROVIDER: Optional[str] = "openai"
    DEFAULT_LLM_MODEL: Optional[str] = "gpt-4"
    DEFAULT_LLM_API_KEY: Optional[str] = None
    DEFAULT_LLM_BASE_URL: Optional[str] = None
    DEFAULT_LLM_TEMPERATURE: Optional[float] = None
    DEFAULT_LLM_MAX_TOKENS: Optional[int] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_ignore_empty=True,
    )
    
    @field_validator('API_KEY')
    @classmethod
    def warn_default_api_key(cls, v: str) -> str:
        """Warn if using default API key"""
        if v == "your-secure-api-key-change-this":
            logger.warning(
                "Using default API_KEY. Please set a secure API_KEY in production via environment variable or .env file."
            )
        return v
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    def get_default_llm_params(self) -> Optional[Dict[str, Any]]:
        """Get default LLM parameters as a dictionary"""
        params = {}
        
        if self.DEFAULT_LLM_API_KEY:
            params['api_key'] = self.DEFAULT_LLM_API_KEY
        if self.DEFAULT_LLM_BASE_URL:
            params['base_url'] = self.DEFAULT_LLM_BASE_URL
        if self.DEFAULT_LLM_TEMPERATURE is not None:
            params['temperature'] = self.DEFAULT_LLM_TEMPERATURE
        if self.DEFAULT_LLM_MAX_TOKENS is not None:
            params['max_tokens'] = self.DEFAULT_LLM_MAX_TOKENS
        
        return params if params else None


# Initialize settings
settings = Settings()
