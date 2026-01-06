from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class CrawlConfigSchema(BaseModel):
    """Configuration for crawl4ai crawler"""
    js_code: Optional[str] = None
    wait_for: Optional[str] = None
    css_selector: Optional[str] = None
    screenshot: bool = False
    pdf: bool = False
    verbose: bool = True


class LLMConfigSchema(BaseModel):
    """LLM configuration for structured extraction"""
    provider: Optional[str] = Field(None, description="LLM provider (openai, anthropic, etc.)")
    model: Optional[str] = Field(None, description="Model name")
    api_key: Optional[str] = Field(None, description="API key for LLM provider")
    base_url: Optional[str] = Field(None, description="Base URL for LLM API")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional params like temperature")


class TaskConfigSchema(BaseModel):
    """Complete task configuration"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    urls: List[str] = Field(..., min_items=1)
    
    # Crawl configuration
    crawl_config: Optional[CrawlConfigSchema] = Field(default_factory=CrawlConfigSchema)
    
    # LLM configuration
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_params: Optional[Dict[str, Any]] = None
    prompt_template: Optional[str] = None
    output_schema: Optional[Dict[str, Any]] = None
    
    # Incremental rules
    deduplication_enabled: bool = True
    only_after_date: Optional[datetime] = None
    
    # Fallback download
    fallback_download_enabled: bool = True
    fallback_max_size_mb: int = 10

    @field_validator('urls')
    @classmethod
    def validate_urls(cls, v):
        if not v:
            raise ValueError("At least one URL is required")
        for url in v:
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid URL format: {url}")
        return v


class TaskCreateRequest(TaskConfigSchema):
    """Request schema for creating a task"""
    pass


class TaskUpdateRequest(BaseModel):
    """Request schema for updating a task"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    urls: Optional[List[str]] = None
    crawl_config: Optional[CrawlConfigSchema] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_params: Optional[Dict[str, Any]] = None
    prompt_template: Optional[str] = None
    output_schema: Optional[Dict[str, Any]] = None
    deduplication_enabled: Optional[bool] = None
    only_after_date: Optional[datetime] = None
    fallback_download_enabled: Optional[bool] = None
    fallback_max_size_mb: Optional[int] = None


class TaskResponse(BaseModel):
    """Response schema for task"""
    id: str
    name: str
    description: Optional[str]
    urls: List[str]
    crawl_config: Dict[str, Any]
    llm_provider: Optional[str]
    llm_model: Optional[str]
    llm_params: Optional[Dict[str, Any]]
    prompt_template: Optional[str]
    output_schema: Optional[Dict[str, Any]]
    deduplication_enabled: bool
    only_after_date: Optional[datetime]
    fallback_download_enabled: bool
    fallback_max_size_mb: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskRunResponse(BaseModel):
    """Response schema for task run"""
    id: str
    task_id: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    urls_crawled: int
    urls_failed: int
    documents_created: int
    minio_path: Optional[str]
    manifest_path: Optional[str]
    logs_path: Optional[str]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """Response schema for document"""
    id: str
    run_id: str
    source_url: str
    title: Optional[str]
    content: Optional[str]
    structured_data: Optional[Dict[str, Any]]
    doc_metadata: Optional[Dict[str, Any]]
    crawled_at: datetime
    markdown_path: Optional[str]
    json_path: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentImageResponse(BaseModel):
    """Response schema for document image"""
    id: str
    document_id: str
    original_url: str
    minio_path: Optional[str]
    alt_text: Optional[str]
    size_bytes: Optional[int]
    mime_type: Optional[str]
    download_status: str
    download_method: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentAttachmentResponse(BaseModel):
    """Response schema for document attachment"""
    id: str
    document_id: str
    original_url: str
    minio_path: Optional[str]
    filename: Optional[str]
    size_bytes: Optional[int]
    mime_type: Optional[str]
    download_status: str
    download_method: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class RunResultResponse(BaseModel):
    """Detailed result for a run including documents"""
    run: TaskRunResponse
    documents: List[DocumentResponse]
    images: List[DocumentImageResponse]
    attachments: List[DocumentAttachmentResponse]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    database: str
    redis: str
    minio: str
