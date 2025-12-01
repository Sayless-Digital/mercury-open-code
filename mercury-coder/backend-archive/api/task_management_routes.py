"""
API routes for task management system.

Provides endpoints for cancel, pause, resume, and status queries.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("mercury.api.task_management")

# This will be initialized by main.py
task_manager_integration = None

router = APIRouter(prefix="/api/task-management", tags=["task-management"])


class CancelRequest(BaseModel):
    """Cancel workflow request."""
    workflow_id: str
    reason: Optional[str] = "User requested"
    user_id: Optional[str] = None


class PauseRequest(BaseModel):
    """Pause workflow request."""
    workflow_id: str
    reason: Optional[str] = "User requested"
    user_id: Optional[str] = None


class ResumeRequest(BaseModel):
    """Resume workflow request."""
    workflow_id: str
    priority: str = "normal"  # high, normal, low
    user_id: Optional[str] = None


@router.post("/cancel")
async def cancel_workflow(request: CancelRequest) -> Dict[str, Any]:
    """
    Cancel a running workflow.
    
    Gracefully stops all tasks and cleans up resources.
    """
    if not task_manager_integration:
        raise HTTPException(status_code=503, detail="Task management not initialized")
    
    try:
        success = await task_manager_integration.cancel_workflow(
            workflow_id=request.workflow_id,
            reason=request.reason,
            user_id=request.user_id
        )
        
        return {
            "success": success,
            "workflow_id": request.workflow_id,
            "message": "Workflow cancellation initiated" if success else "Failed to cancel workflow"
        }
    except Exception as e:
        logger.error(f"Cancel workflow failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause")
async def pause_workflow(request: PauseRequest) -> Dict[str, Any]:
    """
    Pause a running workflow.
    
    Creates a checkpoint and pauses execution. Can be resumed later.
    """
    if not task_manager_integration:
        raise HTTPException(status_code=503, detail="Task management not initialized")
    
    try:
        success = await task_manager_integration.pause_workflow(
            workflow_id=request.workflow_id,
            reason=request.reason,
            user_id=request.user_id
        )
        
        return {
            "success": success,
            "workflow_id": request.workflow_id,
            "message": "Workflow paused at checkpoint" if success else "Failed to pause workflow"
        }
    except Exception as e:
        logger.error(f"Pause workflow failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume")
async def resume_workflow(request: ResumeRequest) -> Dict[str, Any]:
    """
    Resume a paused workflow.
    
    Restores state from checkpoint and continues execution.
    """
    if not task_manager_integration:
        raise HTTPException(status_code=503, detail="Task management not initialized")
    
    try:
        # Map priority string to enum
        from backend.agents.task_management import ResumePriority
        priority_map = {
            "high": ResumePriority.HIGH,
            "normal": ResumePriority.NORMAL,
            "low": ResumePriority.LOW
        }
        priority = priority_map.get(request.priority.lower(), ResumePriority.NORMAL)
        
        success = await task_manager_integration.resume_workflow(
            workflow_id=request.workflow_id,
            priority=priority,
            user_id=request.user_id
        )
        
        return {
            "success": success,
            "workflow_id": request.workflow_id,
            "message": "Workflow resumed from checkpoint" if success else "Failed to resume workflow"
        }
    except Exception as e:
        logger.error(f"Resume workflow failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{workflow_id}")
async def get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """
    Get comprehensive workflow status.
    
    Returns current state, progress, and resource information.
    """
    if not task_manager_integration:
        raise HTTPException(status_code=503, detail="Task management not initialized")
    
    try:
        status = task_manager_integration.get_workflow_status(workflow_id)
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "status": status
        }
    except Exception as e:
        logger.error(f"Get workflow status failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows")
async def list_workflows() -> Dict[str, Any]:
    """
    List all workflows and their statuses.
    
    Returns summary of all managed workflows.
    """
    if not task_manager_integration:
        raise HTTPException(status_code=503, detail="Task management not initialized")
    
    try:
        workflows = task_manager_integration.get_all_workflows()
        
        return {
            "success": True,
            "count": len(workflows),
            "workflows": workflows
        }
    except Exception as e:
        logger.error(f"List workflows failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def set_task_manager_integration(integration):
    """Set the task manager integration instance."""
    global task_manager_integration
    task_manager_integration = integration
    logger.info("Task management integration configured")