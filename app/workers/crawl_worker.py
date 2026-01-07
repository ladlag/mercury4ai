import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import tempfile
import uuid

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.minio_client import minio_client
from app.core.config import settings
from app.models import CrawlTask, Document
from app.services.task_service import TaskService, RunService, DocumentService, URLRegistryService
from app.services.crawler_service import CrawlerService, download_resource, generate_minio_path

# Configure logging for RQ workers
# This ensures that all application logs are visible when worker processes tasks
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True  # Override any existing configuration
)

logger = logging.getLogger(__name__)


def merge_llm_config(task: CrawlTask) -> Optional[Dict[str, Any]]:
    """
    Merge task-specific LLM config with default config from settings.
    Task-specific config takes precedence over defaults.
    
    Args:
        task: CrawlTask instance
    
    Returns:
        Dictionary with merged LLM configuration or None if no LLM config is available
    """
    # If task has provider and model, use task config
    llm_provider = task.llm_provider or settings.DEFAULT_LLM_PROVIDER
    llm_model = task.llm_model or settings.DEFAULT_LLM_MODEL
    
    # Check if we have enough info to use LLM
    if not llm_provider or not llm_model:
        return None
    
    # Start with default params from settings
    default_params = settings.get_default_llm_params() or {}
    
    # Merge with task-specific params (task params override defaults)
    task_params = task.llm_params or {}
    merged_params = {**default_params, **task_params}
    
    # Check if we have an API key (required for LLM)
    if not merged_params.get('api_key'):
        logger.warning(f"No API key found for LLM provider {llm_provider}. LLM extraction will be skipped.")
        return None
    
    return {
        'provider': llm_provider,
        'model': llm_model,
        'params': merged_params,
    }


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
        logger.info(f"Task name: {task.name}, URLs to crawl: {len(task.urls)}")
        
        # Prepare LLM config using defaults if task config is incomplete
        llm_config = merge_llm_config(task)
        if llm_config:
            logger.info(f"LLM config: provider={llm_config['provider']}, model={llm_config['model']}")
            # Check if API key is present
            if llm_config.get('params', {}).get('api_key'):
                logger.debug("API key is configured in LLM params")
            else:
                logger.warning("API key is missing in LLM params - extraction may fail")
        else:
            logger.info("No LLM config available - will perform basic crawling without structured extraction")
        
        # Log prompt and schema configuration
        if task.prompt_template:
            logger.info(f"Prompt template configured: {len(task.prompt_template)} chars")
        else:
            logger.warning("No prompt_template configured - LLM extraction will be skipped even if LLM config is present")
        
        if task.output_schema:
            logger.info(f"Output schema configured: {len(str(task.output_schema))} chars")
        else:
            logger.info("No output_schema configured (optional for LLM extraction)")
        
        # Statistics
        urls_crawled = 0
        urls_failed = 0
        documents_created = 0
        
        # Track detailed errors for each URL
        error_details = []
        
        # Get verbose setting from crawl_config for backward compatibility
        # Note: In crawl4ai 0.7.8+, verbose is no longer passed to the crawler.
        # Logging verbosity is now controlled by Python logging configuration (see module-level logging.basicConfig).
        verbose = (task.crawl_config or {}).get('verbose', True)
        logger.info(f"Verbose setting from config: {verbose} (legacy parameter, not used by crawl4ai 0.7.8+)")
        
        # Process each URL
        async with CrawlerService(verbose=verbose) as crawler:
            for idx, url in enumerate(task.urls, 1):
                try:
                    logger.info(f"Processing URL {idx}/{len(task.urls)}: {url}")
                    
                    # Check if URL should be skipped (deduplication)
                    if task.deduplication_enabled:
                        if URLRegistryService.is_url_crawled(db, url, task_id):
                            logger.info(f"Skipping already crawled URL: {url}")
                            continue
                    
                    # Crawl URL
                    logger.info(f"Starting crawl for URL: {url}")
                    prompt_preview = (task.prompt_template or '')[:100] if task.prompt_template is not None else 'None'
                    logger.debug(f"Task prompt_template: {prompt_preview}...")
                    logger.debug(f"Task output_schema keys: {list(task.output_schema.keys()) if task.output_schema else 'None'}")
                    crawl_result = await crawler.crawl_url(
                        url=url,
                        crawl_config=task.crawl_config or {},
                        llm_config=llm_config,
                        prompt_template=task.prompt_template,
                        output_schema=task.output_schema,
                    )
                    
                    if not crawl_result['success']:
                        urls_failed += 1
                        error_msg = crawl_result.get('error', 'Unknown error')
                        logger.error(f"Failed to crawl {url}: {error_msg}")
                        error_details.append({
                            'url': url,
                            'error': error_msg,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        continue
                    
                    urls_crawled += 1
                    
                    # Save document to database
                    logger.debug(f"Saving document to database for {url}")
                    document = DocumentService.upsert_document(
                        db=db,
                        run_id=run_id,
                        source_url=url,
                        title=crawl_result.get('metadata', {}).get('title'),
                        content=crawl_result.get('markdown'),
                        structured_data=crawl_result.get('structured_data'),
                        doc_metadata=crawl_result.get('metadata'),
                    )
                    documents_created += 1
                    logger.info(f"Document saved with ID: {document.id}")
                    
                    # Save to MinIO and update document with paths
                    logger.debug(f"Saving document artifacts to MinIO for {url}")
                    await save_document_to_minio(
                        db, run_id, document, crawl_result
                    )
                    
                    # Process images
                    images = crawl_result.get('media', {}).get('images', [])
                    if images:
                        logger.info(f"Processing {len(images)} images for {url}")
                        for img in images:
                            await process_image(
                                db, document.id, run_id, img,
                                task.fallback_download_enabled,
                                task.fallback_max_size_mb
                            )
                        logger.debug(f"Completed processing {len(images)} images for {url}")
                    
                    # Register URL as crawled
                    URLRegistryService.register_url(db, url, task_id)
                    
                    # Log success once at the end
                    logger.info(f"Successfully processed URL {idx}/{len(task.urls)}: {url}")
                    
                except Exception as e:
                    # Rollback the session to clear any pending transactions
                    db.rollback()
                    urls_failed += 1
                    error_msg = str(e)
                    logger.error(f"Error processing URL {url}: {error_msg}", exc_info=True)
                    error_details.append({
                        'url': url,
                        'error': error_msg,
                        'timestamp': datetime.utcnow().isoformat()
                    })
        
        # Generate run manifest and resource index
        logger.info(f"Generating run manifest and resource index for run {run_id}")
        manifest = generate_run_manifest(
            run_id=run_id,
            task=task,
            llm_config=llm_config,
            urls_crawled=urls_crawled,
            urls_failed=urls_failed,
            documents_created=documents_created,
            error_details=error_details
        )
        resource_index = generate_resource_index(
            db=db,
            run_id=run_id,
            has_errors=bool(error_details)
        )
        
        # Save manifest and index to MinIO
        manifest_path = generate_minio_path(run_id, 'logs', 'run_manifest.json')
        minio_client.upload_data(
            manifest_path,
            json.dumps(manifest, indent=2, default=str).encode('utf-8'),
            'application/json'
        )
        logger.info(f"Saved run manifest to MinIO: {manifest_path}")
        
        index_path = generate_minio_path(run_id, 'logs', 'resource_index.json')
        minio_client.upload_data(
            index_path,
            json.dumps(resource_index, indent=2, default=str).encode('utf-8'),
            'application/json'
        )
        logger.info(f"Saved resource index to MinIO: {index_path}")
        
        # Save error log if there are any errors
        if error_details:
            error_log_path = generate_minio_path(run_id, 'logs', 'error_log.json')
            error_log = {
                'run_id': run_id,
                'task_id': task_id,
                'generated_at': datetime.utcnow().isoformat(),
                'total_errors': len(error_details),
                'errors': error_details
            }
            minio_client.upload_data(
                error_log_path,
                json.dumps(error_log, indent=2, default=str).encode('utf-8'),
                'application/json'
            )
            logger.info(f"Saved error log for run {run_id} with {len(error_details)} errors")
        
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
        logger.info(f"Summary: {urls_crawled} URLs crawled, {urls_failed} failed, {documents_created} documents created")
        
    except Exception as e:
        logger.error(f"Error executing crawl task {task_id}: {str(e)}", exc_info=True)
        # Rollback the session before trying to update run status
        db.rollback()
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


async def save_document_to_minio(db: Session, run_id: str, document: Document, crawl_result: Dict[str, Any]):
    """Save document content to MinIO and update document with paths"""
    try:
        markdown_path = None
        markdown_fit_path = None
        json_path = None
        
        # Save raw markdown (original, unprocessed)
        if crawl_result.get('markdown'):
            markdown_path = generate_minio_path(
                run_id, 'markdown', f"{document.id}.md"
            )
            minio_client.upload_data(
                markdown_path,
                crawl_result['markdown'].encode('utf-8'),
                'text/markdown'
            )
            logger.info(f"Saved raw markdown to MinIO: {markdown_path}")
        else:
            logger.warning(f"No raw markdown content to save for document {document.id}")
        
        # Save fit markdown (cleaned by crawl4ai - first-level cleaning)
        if crawl_result.get('markdown_fit'):
            markdown_fit_path = generate_minio_path(
                run_id, 'markdown', f"{document.id}_cleaned.md"
            )
            minio_client.upload_data(
                markdown_fit_path,
                crawl_result['markdown_fit'].encode('utf-8'),
                'text/markdown'
            )
            logger.info(f"Saved cleaned markdown (fit) to MinIO: {markdown_fit_path}")
            
            # Log cleaning statistics
            if crawl_result.get('markdown'):
                original_len = len(crawl_result['markdown'])
                cleaned_len = len(crawl_result['markdown_fit'])
                reduction = ((original_len - cleaned_len) / original_len * 100) if original_len > 0 else 0
                logger.info(f"Crawl4ai cleaning: {original_len} -> {cleaned_len} chars (reduced {reduction:.1f}%)")
        
        # Save structured data as JSON (second-level cleaning by LLM with custom schema)
        if crawl_result.get('structured_data'):
            json_path = generate_minio_path(
                run_id, 'json', f"{document.id}.json"
            )
            minio_client.upload_data(
                json_path,
                json.dumps(crawl_result['structured_data'], indent=2, ensure_ascii=False).encode('utf-8'),
                'application/json'
            )
            logger.info(f"Saved structured data (LLM extraction) to MinIO: {json_path}")
        
        # Save screenshot if available
        if crawl_result.get('screenshot'):
            screenshot_path = generate_minio_path(
                run_id, 'images', f"{document.id}_screenshot.png"
            )
            minio_client.upload_data(
                screenshot_path,
                crawl_result['screenshot'],
                'image/png'
            )
            logger.info(f"Saved screenshot to MinIO: {screenshot_path}")
        
        # Save PDF if available
        if crawl_result.get('pdf'):
            pdf_path = generate_minio_path(
                run_id, 'attachments', f"{document.id}.pdf"
            )
            minio_client.upload_data(
                pdf_path,
                crawl_result['pdf'],
                'application/pdf'
            )
            logger.info(f"Saved PDF to MinIO: {pdf_path}")
        
        # Update document with paths if they were generated
        should_update = False
        if markdown_path and document.markdown_path != markdown_path:
            document.markdown_path = markdown_path
            should_update = True
        if json_path and document.json_path != json_path:
            document.json_path = json_path
            should_update = True
        
        if should_update:
            db.commit()
            db.refresh(document)
            logger.debug(f"Updated document {document.id} with MinIO paths")
            
    except Exception as e:
        logger.error(f"Error saving document to MinIO: {str(e)}", exc_info=True)


async def process_image(
    db, document_id: str, run_id: str, image_info: Dict[str, Any],
    fallback_enabled: bool, max_size_mb: int
):
    """Process and save image"""
    try:
        image_url = image_info.get('src') or image_info.get('url')
        if not image_url:
            logger.debug(f"Skipping image with no URL (document_id: {document_id})")
            return
        
        logger.debug(f"Processing image: {image_url}")
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
            logger.debug(f"Image downloaded by crawl4ai: {image_url}")
            
            # Upload to MinIO
            filename = Path(image_url).name or f"image_{uuid.uuid4().hex[:8]}.jpg"
            minio_path = generate_minio_path(run_id, 'images', filename)
            
            if image_info.get('data'):
                minio_client.upload_data(minio_path, image_info['data'], 'image/jpeg')
                logger.info(f"Uploaded image data to MinIO: {minio_path}")
            elif image_info.get('downloaded_path'):
                minio_client.upload_file(minio_path, image_info['downloaded_path'])
                logger.info(f"Uploaded image file to MinIO: {minio_path}")
        
        # Fallback download if enabled and crawl4ai didn't download
        elif fallback_enabled and download_status == 'pending':
            logger.debug(f"Attempting fallback download for: {image_url}")
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
                logger.info(f"Fallback download successful, uploaded to MinIO: {minio_path}")
            else:
                download_status = 'failed'
                logger.warning(f"Fallback download failed for: {image_url}")
        else:
            download_status = 'skipped'
            logger.debug(f"Image download skipped (fallback disabled): {image_url}")
        
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
        logger.debug(f"Saved image metadata to database: {image_url} (status: {download_status})")
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}", exc_info=True)


def generate_run_manifest(
    run_id: str,
    *,
    task: CrawlTask,
    llm_config: Optional[Dict[str, Any]],
    urls_crawled: int,
    urls_failed: int,
    documents_created: int,
    error_details: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Generate run manifest"""
    # Use llm_config if available, otherwise fall back to task config
    if llm_config:
        llm_provider = llm_config.get('provider')
        llm_model = llm_config.get('model')
    else:
        llm_provider = task.llm_provider
        llm_model = task.llm_model
    
    manifest = {
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
            'llm_provider': llm_provider,
            'llm_model': llm_model,
        }
    }
    
    # Include error summary if there are errors
    if error_details:
        manifest['errors'] = {
            'total_errors': len(error_details),
            'error_log_available': True,
            'error_summary': error_details[:5]  # Include first 5 errors in manifest
        }
    
    return manifest


def generate_resource_index(db, run_id: str, has_errors: bool = False) -> Dict[str, Any]:
    """Generate resource index for run"""
    documents = RunService.get_run_documents(db, run_id)
    images = RunService.get_run_images(db, run_id)
    attachments = RunService.get_run_attachments(db, run_id)
    
    index = {
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
    
    # Add error log reference if errors occurred
    if has_errors:
        index['error_log_available'] = True
        index['error_log_path'] = generate_minio_path(run_id, 'logs', 'error_log.json')
    
    return index
