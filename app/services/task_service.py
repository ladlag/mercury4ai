from sqlalchemy.orm import Session
from app.models import CrawlTask, CrawlTaskRun, Document, DocumentImage, DocumentAttachment, CrawledUrlRegistry
from app.schemas import TaskCreateRequest, TaskUpdateRequest
from typing import List, Optional, Dict, Any
import json
import yaml
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TaskService:
    @staticmethod
    def create_task(db: Session, task_data: TaskCreateRequest) -> CrawlTask:
        """Create a new crawl task"""
        task = CrawlTask(
            name=task_data.name,
            description=task_data.description,
            urls=task_data.urls,
            crawl_config=task_data.crawl_config.model_dump() if task_data.crawl_config else {},
            llm_provider=task_data.llm_provider,
            llm_model=task_data.llm_model,
            llm_params=task_data.llm_params,
            prompt_template=task_data.prompt_template,
            output_schema=task_data.output_schema,
            deduplication_enabled=task_data.deduplication_enabled,
            only_after_date=task_data.only_after_date,
            fallback_download_enabled=task_data.fallback_download_enabled,
            fallback_max_size_mb=task_data.fallback_max_size_mb,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.info(f"Created task: {task.id}")
        return task
    
    @staticmethod
    def get_task(db: Session, task_id: str) -> Optional[CrawlTask]:
        """Get task by ID"""
        return db.query(CrawlTask).filter(CrawlTask.id == task_id).first()
    
    @staticmethod
    def list_tasks(db: Session, skip: int = 0, limit: int = 100) -> List[CrawlTask]:
        """List all tasks"""
        return db.query(CrawlTask).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_task(db: Session, task_id: str, task_data: TaskUpdateRequest) -> Optional[CrawlTask]:
        """Update task"""
        task = db.query(CrawlTask).filter(CrawlTask.id == task_id).first()
        if not task:
            return None
        
        update_data = task_data.model_dump(exclude_unset=True)
        if 'crawl_config' in update_data and update_data['crawl_config']:
            update_data['crawl_config'] = update_data['crawl_config'].model_dump() if hasattr(update_data['crawl_config'], 'model_dump') else update_data['crawl_config']
        
        for key, value in update_data.items():
            setattr(task, key, value)
        
        db.commit()
        db.refresh(task)
        logger.info(f"Updated task: {task.id}")
        return task
    
    @staticmethod
    def delete_task(db: Session, task_id: str) -> bool:
        """Delete task"""
        task = db.query(CrawlTask).filter(CrawlTask.id == task_id).first()
        if not task:
            return False
        
        db.delete(task)
        db.commit()
        logger.info(f"Deleted task: {task_id}")
        return True
    
    @staticmethod
    def export_task(task: CrawlTask, format: str = 'json') -> str:
        """Export task to JSON or YAML"""
        data = {
            'name': task.name,
            'description': task.description,
            'urls': task.urls,
            'crawl_config': task.crawl_config,
            'llm_provider': task.llm_provider,
            'llm_model': task.llm_model,
            'llm_params': task.llm_params,
            'prompt_template': task.prompt_template,
            'output_schema': task.output_schema,
            'deduplication_enabled': task.deduplication_enabled,
            'only_after_date': task.only_after_date.isoformat() if task.only_after_date else None,
            'fallback_download_enabled': task.fallback_download_enabled,
            'fallback_max_size_mb': task.fallback_max_size_mb,
        }
        
        if format == 'yaml':
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)
        else:
            return json.dumps(data, indent=2, default=str)
    
    @staticmethod
    def import_task(db: Session, content: str, format: str = 'json') -> CrawlTask:
        """Import task from JSON or YAML"""
        if format == 'yaml':
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
        
        # Convert only_after_date string to datetime if present
        if data.get('only_after_date'):
            data['only_after_date'] = datetime.fromisoformat(data['only_after_date'])
        
        task_data = TaskCreateRequest(**data)
        return TaskService.create_task(db, task_data)


class RunService:
    @staticmethod
    def create_run(db: Session, task_id: str) -> CrawlTaskRun:
        """Create a new task run"""
        run = CrawlTaskRun(
            task_id=task_id,
            status='pending'
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        logger.info(f"Created run: {run.id} for task: {task_id}")
        return run
    
    @staticmethod
    def get_run(db: Session, run_id: str) -> Optional[CrawlTaskRun]:
        """Get run by ID"""
        return db.query(CrawlTaskRun).filter(CrawlTaskRun.id == run_id).first()
    
    @staticmethod
    def update_run_status(db: Session, run_id: str, status: str, **kwargs) -> Optional[CrawlTaskRun]:
        """Update run status and other fields"""
        run = db.query(CrawlTaskRun).filter(CrawlTaskRun.id == run_id).first()
        if not run:
            return None
        
        run.status = status
        for key, value in kwargs.items():
            if hasattr(run, key):
                setattr(run, key, value)
        
        db.commit()
        db.refresh(run)
        return run
    
    @staticmethod
    def get_run_documents(db: Session, run_id: str) -> List[Document]:
        """Get all documents for a run"""
        return db.query(Document).filter(Document.run_id == run_id).all()
    
    @staticmethod
    def get_run_images(db: Session, run_id: str) -> List[DocumentImage]:
        """Get all images for a run"""
        return db.query(DocumentImage).join(Document).filter(Document.run_id == run_id).all()
    
    @staticmethod
    def get_run_attachments(db: Session, run_id: str) -> List[DocumentAttachment]:
        """Get all attachments for a run"""
        return db.query(DocumentAttachment).join(Document).filter(Document.run_id == run_id).all()


class DocumentService:
    @staticmethod
    def upsert_document(db: Session, run_id: str, source_url: str, **kwargs) -> Document:
        """Upsert document (idempotent)"""
        # Check if document exists for this run and URL
        document = db.query(Document).filter(
            Document.run_id == run_id,
            Document.source_url == source_url
        ).first()
        
        if document:
            # Update existing document
            for key, value in kwargs.items():
                if hasattr(document, key):
                    setattr(document, key, value)
            logger.info(f"Updated document: {document.id}")
        else:
            # Create new document
            document = Document(
                run_id=run_id,
                source_url=source_url,
                **kwargs
            )
            db.add(document)
            logger.info(f"Created new document for URL: {source_url}")
        
        db.commit()
        db.refresh(document)
        return document
    
    @staticmethod
    def upsert_image(db: Session, document_id: str, original_url: str, **kwargs) -> DocumentImage:
        """Upsert document image (idempotent)"""
        image = db.query(DocumentImage).filter(
            DocumentImage.document_id == document_id,
            DocumentImage.original_url == original_url
        ).first()
        
        if image:
            for key, value in kwargs.items():
                if hasattr(image, key):
                    setattr(image, key, value)
        else:
            image = DocumentImage(
                document_id=document_id,
                original_url=original_url,
                **kwargs
            )
            db.add(image)
        
        db.commit()
        db.refresh(image)
        return image
    
    @staticmethod
    def upsert_attachment(db: Session, document_id: str, original_url: str, **kwargs) -> DocumentAttachment:
        """Upsert document attachment (idempotent)"""
        attachment = db.query(DocumentAttachment).filter(
            DocumentAttachment.document_id == document_id,
            DocumentAttachment.original_url == original_url
        ).first()
        
        if attachment:
            for key, value in kwargs.items():
                if hasattr(attachment, key):
                    setattr(attachment, key, value)
        else:
            attachment = DocumentAttachment(
                document_id=document_id,
                original_url=original_url,
                **kwargs
            )
            db.add(attachment)
        
        db.commit()
        db.refresh(attachment)
        return attachment


class URLRegistryService:
    @staticmethod
    def is_url_crawled(db: Session, url: str, task_id: str) -> bool:
        """Check if URL has been crawled for this task"""
        registry = db.query(CrawledUrlRegistry).filter(
            CrawledUrlRegistry.url == url,
            CrawledUrlRegistry.task_id == task_id
        ).first()
        return registry is not None
    
    @staticmethod
    def register_url(db: Session, url: str, task_id: str) -> CrawledUrlRegistry:
        """Register URL as crawled (idempotent)"""
        # Query only by URL since it has a unique constraint globally
        registry = db.query(CrawledUrlRegistry).filter(
            CrawledUrlRegistry.url == url
        ).first()
        
        if registry:
            registry.crawl_count += 1
            registry.last_crawled_at = datetime.utcnow()
            # Update task_id to the current task that crawled it
            registry.task_id = task_id
        else:
            registry = CrawledUrlRegistry(
                url=url,
                task_id=task_id
            )
            db.add(registry)
        
        db.commit()
        db.refresh(registry)
        return registry
