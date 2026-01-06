from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, Boolean, ForeignKey, BigInteger, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class CrawlTask(Base):
    __tablename__ = "crawl_task"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    urls = Column(JSON, nullable=False)  # List of URLs to crawl
    
    # crawl4ai configuration
    crawl_config = Column(JSON, nullable=False)  # Generic crawl4ai config
    
    # LLM configuration
    llm_provider = Column(String(50), nullable=True)  # openai, anthropic, etc.
    llm_model = Column(String(100), nullable=True)
    llm_params = Column(JSON, nullable=True)  # temperature, max_tokens, etc.
    prompt_template = Column(Text, nullable=True)
    output_schema = Column(JSON, nullable=True)  # JSON Schema for structured output
    
    # Incremental rules
    deduplication_enabled = Column(Boolean, default=True)
    only_after_date = Column(DateTime, nullable=True)  # For list page filtering
    
    # Fallback download configuration
    fallback_download_enabled = Column(Boolean, default=True)
    fallback_max_size_mb = Column(Integer, default=10)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    runs = relationship("CrawlTaskRun", back_populates="task", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_crawl_task_created_at', 'created_at'),
    )


class CrawlTaskRun(Base):
    __tablename__ = "crawl_task_run"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey('crawl_task.id', ondelete='CASCADE'), nullable=False)
    
    status = Column(String(50), nullable=False, default='pending')  # pending, running, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results summary
    urls_crawled = Column(Integer, default=0)
    urls_failed = Column(Integer, default=0)
    documents_created = Column(Integer, default=0)
    
    # MinIO paths
    minio_path = Column(String(500), nullable=True)  # Base path in MinIO
    manifest_path = Column(String(500), nullable=True)
    logs_path = Column(String(500), nullable=True)
    
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("CrawlTask", back_populates="runs")
    documents = relationship("Document", back_populates="run", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_crawl_task_run_task_id', 'task_id'),
        Index('idx_crawl_task_run_status', 'status'),
        Index('idx_crawl_task_run_created_at', 'created_at'),
    )


class Document(Base):
    __tablename__ = "document"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey('crawl_task_run.id', ondelete='CASCADE'), nullable=False)
    
    source_url = Column(String(2000), nullable=False)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)  # Markdown or extracted text
    structured_data = Column(JSON, nullable=True)  # LLM extracted structured data
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    crawled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # MinIO paths
    markdown_path = Column(String(500), nullable=True)
    json_path = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    run = relationship("CrawlTaskRun", back_populates="documents")
    images = relationship("DocumentImage", back_populates="document", cascade="all, delete-orphan")
    attachments = relationship("DocumentAttachment", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_document_run_id', 'run_id'),
        Index('idx_document_source_url', 'source_url'),
        Index('idx_document_crawled_at', 'crawled_at'),
    )


class DocumentImage(Base):
    __tablename__ = "document_image"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey('document.id', ondelete='CASCADE'), nullable=False)
    
    original_url = Column(String(2000), nullable=False)
    minio_path = Column(String(500), nullable=True)  # Path in MinIO if downloaded
    
    alt_text = Column(String(500), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    download_status = Column(String(50), default='pending')  # pending, success, failed, skipped
    download_method = Column(String(50), nullable=True)  # crawl4ai, fallback
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="images")
    
    __table_args__ = (
        Index('idx_document_image_document_id', 'document_id'),
        Index('idx_document_image_original_url', 'original_url'),
    )


class DocumentAttachment(Base):
    __tablename__ = "document_attachment"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey('document.id', ondelete='CASCADE'), nullable=False)
    
    original_url = Column(String(2000), nullable=False)
    minio_path = Column(String(500), nullable=True)
    
    filename = Column(String(500), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    download_status = Column(String(50), default='pending')
    download_method = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="attachments")
    
    __table_args__ = (
        Index('idx_document_attachment_document_id', 'document_id'),
        Index('idx_document_attachment_original_url', 'original_url'),
    )


class CrawledUrlRegistry(Base):
    __tablename__ = "crawled_url_registry"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(String(2000), nullable=False, unique=True)
    task_id = Column(String(36), ForeignKey('crawl_task.id', ondelete='CASCADE'), nullable=False)
    
    first_crawled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_crawled_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    crawl_count = Column(Integer, default=1, nullable=False)
    
    __table_args__ = (
        Index('idx_crawled_url_registry_url', 'url'),
        Index('idx_crawled_url_registry_task_id', 'task_id'),
    )
