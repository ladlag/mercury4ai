from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import verify_api_key
from app.core.redis_client import get_redis_client
from app.schemas import TaskRunResponse, RunResultResponse, DocumentResponse, DocumentImageResponse, DocumentAttachmentResponse
from app.services.task_service import TaskService, RunService
from rq import Queue
from rq.job import Job
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["runs"])


@router.post("/tasks/{task_id}/run", response_model=dict)
async def run_task(
    task_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Start a new crawl task run"""
    # Verify task exists
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    try:
        # Create run record
        run = RunService.create_run(db, task_id)
        
        # Enqueue job to RQ
        redis_client = get_redis_client()
        queue = Queue('crawl_tasks', connection=redis_client)
        
        job = queue.enqueue(
            'app.workers.crawl_worker.execute_crawl_task',
            task_id,
            run.id,
            job_timeout='1h',
            result_ttl=86400,  # Keep results for 24 hours
            failure_ttl=86400,
        )
        
        logger.info(f"Enqueued job {job.id} for task {task_id}, run {run.id}")
        
        return {
            "run_id": run.id,
            "task_id": task_id,
            "status": run.status,
            "job_id": job.id,
            "message": "Task run started"
        }
        
    except Exception as e:
        logger.error(f"Error starting task run: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}", response_model=TaskRunResponse)
async def get_run(
    run_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get run status and details"""
    run = RunService.get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/runs/{run_id}/result", response_model=RunResultResponse)
async def get_run_result(
    run_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get detailed run results including documents"""
    run = RunService.get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Get associated data
    documents = RunService.get_run_documents(db, run_id)
    images = RunService.get_run_images(db, run_id)
    attachments = RunService.get_run_attachments(db, run_id)
    
    return RunResultResponse(
        run=TaskRunResponse.model_validate(run),
        documents=[DocumentResponse.model_validate(doc) for doc in documents],
        images=[DocumentImageResponse.model_validate(img) for img in images],
        attachments=[DocumentAttachmentResponse.model_validate(att) for att in attachments]
    )


@router.get("/runs/{run_id}/logs")
async def get_run_logs(
    run_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get run logs information"""
    run = RunService.get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if not run.logs_path:
        raise HTTPException(status_code=404, detail="Logs not available")
    
    # Return MinIO paths
    from app.core.minio_client import minio_client
    from app.services.crawler_service import generate_minio_path
    
    manifest_url = None
    if run.manifest_path:
        manifest_url = minio_client.get_presigned_url(run.manifest_path)
    
    # Generate error log URL if errors occurred
    error_log_url = None
    if run.urls_failed > 0:
        error_log_path = generate_minio_path(run.id, 'logs', 'error_log.json')
        # Try to generate presigned URL for error log
        error_log_url = minio_client.get_presigned_url(error_log_path)
        # get_presigned_url returns None if the file doesn't exist or there's an error
    
    response = {
        "run_id": run_id,
        "logs_path": run.logs_path,
        "minio_path": run.minio_path,
        "manifest_url": manifest_url,
        "message": "Use manifest_url to download run_manifest.json, or access MinIO directly"
    }
    
    if error_log_url:
        response["error_log_url"] = error_log_url
        response["message"] += ". Error log available at error_log_url"
    
    return response
