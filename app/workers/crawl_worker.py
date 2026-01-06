import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
import tempfile
import uuid

from app.core.database import SessionLocal
from app.core.minio_client import minio_client
from app.services.task_service import TaskService, RunService, DocumentService, URLRegistryService
from app.services.crawler_service import CrawlerService, download_resource, generate_minio_path

logger = logging.getLogger(__name__)


async def execute_crawl_task_async(task_id: str, run_id: str):
    """Async implementation of crawl task execution"""
    db = SessionLocal()
    
    try:
        # Get task and run
        task = TaskService.get_task(db, task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        run = RunService.get_run(db, run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")
        
        # Update run status
        RunService.update_run_status(
            db, run_id, 'running',
            started_at=datetime.utcnow()
        )
        
        logger.info(f"Starting crawl task {task_id}, run {run_id}")
        
        # Prepare LLM config if provided
        llm_config = None
        if task.llm_provider and task.llm_model:
            llm_config = {
                'provider': task.llm_provider,
                'model': task.llm_model,
                'params': task.llm_params or {},
            }
        
        # Statistics
        urls_crawled = 0
        urls_failed = 0
        documents_created = 0
        
        # Process each URL
        async with CrawlerService() as crawler:
            for url in task.urls:
                try:
                    # Check if URL should be skipped (deduplication)
                    if task.deduplication_enabled:
                        if URLRegistryService.is_url_crawled(db, url, task_id):
                            logger.info(f"Skipping already crawled URL: {url}")
                            continue
                    
                    # Crawl URL
                    crawl_result = await crawler.crawl_url(
                        url=url,
                        crawl_config=task.crawl_config or {},
                        llm_config=llm_config,
                        prompt_template=task.prompt_template,
                        output_schema=task.output_schema,
                    )
                    
                    if not crawl_result['success']:
                        urls_failed += 1
                        logger.error(f"Failed to crawl {url}: {crawl_result.get('error')}")
                        continue
                    
                    urls_crawled += 1
                    
                    # Save document to database
                    document = DocumentService.upsert_document(
                        db=db,
                        run_id=run_id,
                        source_url=url,
                        title=crawl_result.get('metadata', {}).get('title'),
                        content=crawl_result.get('markdown'),
                        structured_data=crawl_result.get('structured_data'),
                        metadata=crawl_result.get('metadata'),
                    )
                    documents_created += 1
                    
                    # Save to MinIO
                    await save_document_to_minio(
                        run_id, document.id, crawl_result
                    )
                    
                    # Process images
                    images = crawl_result.get('media', {}).get('images', [])
                    for img in images:
                        await process_image(
                            db, document.id, run_id, img,
                            task.fallback_download_enabled,
                            task.fallback_max_size_mb
                        )
                    
                    # Register URL as crawled
                    URLRegistryService.register_url(db, url, task_id)
                    
                    logger.info(f"Successfully processed URL: {url}")
                    
                except Exception as e:
                    urls_failed += 1
                    logger.error(f"Error processing URL {url}: {str(e)}", exc_info=True)
        
        # Generate run manifest and resource index
        manifest = generate_run_manifest(run_id, task, urls_crawled, urls_failed, documents_created)
        resource_index = generate_resource_index(db, run_id)
        
        # Save manifest and index to MinIO
        manifest_path = generate_minio_path(run_id, 'logs', 'run_manifest.json')
        minio_client.upload_data(
            manifest_path,
            json.dumps(manifest, indent=2, default=str).encode('utf-8'),
            'application/json'
        )
        
        index_path = generate_minio_path(run_id, 'logs', 'resource_index.json')
        minio_client.upload_data(
            index_path,
            json.dumps(resource_index, indent=2, default=str).encode('utf-8'),
            'application/json'
        )
        
        # Update run with results
        today = datetime.utcnow().strftime('%Y-%m-%d')
        RunService.update_run_status(
            db, run_id, 'completed',
            completed_at=datetime.utcnow(),
            urls_crawled=urls_crawled,
            urls_failed=urls_failed,
            documents_created=documents_created,
            minio_path=f"{today}/{run_id}",
            manifest_path=manifest_path,
            logs_path=f"{today}/{run_id}/logs"
        )
        
        logger.info(f"Crawl task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error executing crawl task {task_id}: {str(e)}", exc_info=True)
        RunService.update_run_status(
            db, run_id, 'failed',
            completed_at=datetime.utcnow(),
            error_message=str(e)
        )
    finally:
        db.close()


def execute_crawl_task(task_id: str, run_id: str):
    """Synchronous wrapper for RQ worker"""
    asyncio.run(execute_crawl_task_async(task_id, run_id))


async def save_document_to_minio(run_id: str, document_id: str, crawl_result: Dict[str, Any]):
    """Save document content to MinIO"""
    try:
        # Save markdown
        if crawl_result.get('markdown'):
            markdown_path = generate_minio_path(
                run_id, 'markdown', f"{document_id}.md"
            )
            minio_client.upload_data(
                markdown_path,
                crawl_result['markdown'].encode('utf-8'),
                'text/markdown'
            )
        
        # Save structured data as JSON
        if crawl_result.get('structured_data'):
            json_path = generate_minio_path(
                run_id, 'json', f"{document_id}.json"
            )
            minio_client.upload_data(
                json_path,
                json.dumps(crawl_result['structured_data'], indent=2).encode('utf-8'),
                'application/json'
            )
        
        # Save screenshot if available
        if crawl_result.get('screenshot'):
            screenshot_path = generate_minio_path(
                run_id, 'images', f"{document_id}_screenshot.png"
            )
            minio_client.upload_data(
                screenshot_path,
                crawl_result['screenshot'],
                'image/png'
            )
        
        # Save PDF if available
        if crawl_result.get('pdf'):
            pdf_path = generate_minio_path(
                run_id, 'attachments', f"{document_id}.pdf"
            )
            minio_client.upload_data(
                pdf_path,
                crawl_result['pdf'],
                'application/pdf'
            )
            
    except Exception as e:
        logger.error(f"Error saving document to MinIO: {str(e)}")


async def process_image(
    db, document_id: str, run_id: str, image_info: Dict[str, Any],
    fallback_enabled: bool, max_size_mb: int
):
    """Process and save image"""
    try:
        image_url = image_info.get('src') or image_info.get('url')
        if not image_url:
            return
        
        alt_text = image_info.get('alt')
        
        # Try to download from crawl4ai result first
        download_status = 'pending'
        download_method = None
        minio_path = None
        size_bytes = None
        mime_type = None
        
        # Check if crawl4ai already downloaded it
        if image_info.get('downloaded_path') or image_info.get('data'):
            # Image was downloaded by crawl4ai
            download_status = 'success'
            download_method = 'crawl4ai'
            
            # Upload to MinIO
            filename = Path(image_url).name or f"image_{uuid.uuid4().hex[:8]}.jpg"
            minio_path = generate_minio_path(run_id, 'images', filename)
            
            if image_info.get('data'):
                minio_client.upload_data(minio_path, image_info['data'], 'image/jpeg')
            elif image_info.get('downloaded_path'):
                minio_client.upload_file(minio_path, image_info['downloaded_path'])
        
        # Fallback download if enabled and crawl4ai didn't download
        elif fallback_enabled and download_status == 'pending':
            download_result = await download_resource(image_url, max_size_mb)
            if download_result and download_result['success']:
                download_status = 'success'
                download_method = 'fallback'
                size_bytes = download_result['size_bytes']
                mime_type = download_result['mime_type']
                
                # Upload to MinIO
                filename = download_result['filename']
                minio_path = generate_minio_path(run_id, 'images', filename)
                minio_client.upload_data(
                    minio_path,
                    download_result['content'],
                    mime_type
                )
            else:
                download_status = 'failed'
        else:
            download_status = 'skipped'
        
        # Save to database
        DocumentService.upsert_image(
            db=db,
            document_id=document_id,
            original_url=image_url,
            minio_path=minio_path,
            alt_text=alt_text,
            size_bytes=size_bytes,
            mime_type=mime_type,
            download_status=download_status,
            download_method=download_method
        )
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")


def generate_run_manifest(
    run_id: str, task, urls_crawled: int, urls_failed: int, documents_created: int
) -> Dict[str, Any]:
    """Generate run manifest"""
    return {
        'run_id': run_id,
        'task_id': task.id,
        'task_name': task.name,
        'started_at': datetime.utcnow().isoformat(),
        'urls_crawled': urls_crawled,
        'urls_failed': urls_failed,
        'documents_created': documents_created,
        'configuration': {
            'urls': task.urls,
            'deduplication_enabled': task.deduplication_enabled,
            'llm_provider': task.llm_provider,
            'llm_model': task.llm_model,
        }
    }


def generate_resource_index(db, run_id: str) -> Dict[str, Any]:
    """Generate resource index for run"""
    documents = RunService.get_run_documents(db, run_id)
    images = RunService.get_run_images(db, run_id)
    attachments = RunService.get_run_attachments(db, run_id)
    
    return {
        'run_id': run_id,
        'generated_at': datetime.utcnow().isoformat(),
        'documents': [
            {
                'id': doc.id,
                'source_url': doc.source_url,
                'title': doc.title,
                'markdown_path': doc.markdown_path,
                'json_path': doc.json_path,
            }
            for doc in documents
        ],
        'images': [
            {
                'id': img.id,
                'original_url': img.original_url,
                'minio_path': img.minio_path,
                'download_status': img.download_status,
            }
            for img in images
        ],
        'attachments': [
            {
                'id': att.id,
                'original_url': att.original_url,
                'minio_path': att.minio_path,
                'download_status': att.download_status,
            }
            for att in attachments
        ],
    }
