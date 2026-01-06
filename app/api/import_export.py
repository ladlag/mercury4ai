from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import verify_api_key
from app.services.task_service import TaskService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}/export")
async def export_task(
    task_id: str,
    format: str = "json",
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Export task configuration to JSON or YAML"""
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if format not in ["json", "yaml"]:
        raise HTTPException(status_code=400, detail="Format must be 'json' or 'yaml'")
    
    try:
        content = TaskService.export_task(task, format)
        
        if format == "yaml":
            return PlainTextResponse(
                content=content,
                media_type="application/x-yaml",
                headers={"Content-Disposition": f"attachment; filename=task_{task_id}.yaml"}
            )
        else:
            return PlainTextResponse(
                content=content,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=task_{task_id}.json"}
            )
    except Exception as e:
        logger.error(f"Error exporting task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_task(
    content: str,
    format: str = "json",
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Import task configuration from JSON or YAML"""
    if format not in ["json", "yaml"]:
        raise HTTPException(status_code=400, detail="Format must be 'json' or 'yaml'")
    
    try:
        task = TaskService.import_task(db, content, format)
        return {
            "id": task.id,
            "name": task.name,
            "message": "Task imported successfully"
        }
    except Exception as e:
        logger.error(f"Error importing task: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")
