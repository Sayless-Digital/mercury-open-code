"""
Integration layer between TaskManager and OrchestratorAgent.

Provides seamless integration of task management capabilities
into the existing orchestrator workflow.
"""

import logging
from typing import Dict, Any, Optional, Callable
import uuid

from .task_manager import TaskManager, WorkflowState
from .resume_queue import ResumePriority
from ..task import Plan, WorkflowStage

logger = logging.getLogger("mercury.agents.task_management.integration")


class OrchestratorIntegration:
    """
    Integration layer for TaskManager with OrchestratorAgent.
    
    Wraps orchestrator workflows with task management capabilities:
    - Cancel/pause/resume support
    - State persistence
    - Resource cleanup
    - Comprehensive logging
    """
    
    def __init__(
        self,
        orchestrator: Any,
        task_manager: Optional[TaskManager] = None
    ):
        """
        Initialize integration.
        
        Args:
            orchestrator: OrchestratorAgent instance
            task_manager: Optional TaskManager (creates new if None)
        """
        self.orchestrator = orchestrator
        self.task_manager = task_manager or TaskManager()
        
        # Link status emitter for UI updates
        if hasattr(orchestrator, 'status_emitter'):
            self.task_manager.state_transition_manager.status_emitter = orchestrator.status_emitter
        
        logger.info("OrchestratorIntegration initialized")
    
    async def execute_workflow_with_management(
        self,
        user_request: str,
        project_path: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute workflow with full task management.
        
        Args:
            user_request: User's request
            project_path: Project path
            session_id: Session ID
            context: Additional context
            workflow_id: Optional workflow ID (generates if None)
            
        Returns:
            Workflow result with management metadata
        """
        # Generate workflow ID if not provided
        workflow_id = workflow_id or str(uuid.uuid4())
        
        try:
            # Create workflow in task manager
            self.task_manager.create_workflow(
                workflow_id=workflow_id,
                user_request=user_request,
                config={
                    "project_path": project_path,
                    "session_id": session_id
                }
            )
            
            # Set workflow timeout
            self.task_manager.timeout_manager.set_workflow_timeout(
                workflow_id=workflow_id,
                duration=3600,  # 1 hour
                callback=self._handle_workflow_timeout
            )
            
            # Register cancellation check
            original_is_cancelled = self.orchestrator.is_cancelled
            
            def enhanced_is_cancelled():
                """Check both orchestrator and task manager cancellation."""
                return (
                    original_is_cancelled() or
                    self.task_manager.cancellation_manager.is_cancelled(workflow_id)
                )
            
            # Temporarily replace cancellation check
            self.orchestrator.is_cancelled = enhanced_is_cancelled
            
            try:
                # Start workflow
                self.task_manager.start_workflow(workflow_id)
                
                # Execute orchestrator workflow
                result = await self.orchestrator.execute_workflow(
                    user_request=user_request,
                    project_path=project_path,
                    session_id=session_id,
                    context=context
                )
                
                # Check if cancelled
                if enhanced_is_cancelled():
                    await self.task_manager.complete_cancellation(workflow_id)
                    result["managed"] = True
                    result["workflow_id"] = workflow_id
                    result["cancelled"] = True
                    return result
                
                # Store plan if available
                if self.orchestrator.current_plan:
                    self.task_manager._workflow_plans[workflow_id] = self.orchestrator.current_plan
                
                # Complete workflow
                success = result.get("success", False)
                error = result.get("error") if not success else None
                self.task_manager.complete_workflow(
                    workflow_id=workflow_id,
                    success=success,
                    error=error
                )
                
                # Add management metadata
                result["managed"] = True
                result["workflow_id"] = workflow_id
                result["management_status"] = self.task_manager.get_workflow_status(workflow_id)
                
                return result
                
            finally:
                # Restore original cancellation check
                self.orchestrator.is_cancelled = original_is_cancelled
                
        except Exception as e:
            logger.error(f"Managed workflow execution failed: {e}", exc_info=True)
            
            # Mark as failed
            self.task_manager.complete_workflow(
                workflow_id=workflow_id,
                success=False,
                error=str(e)
            )
            
            return {
                "success": False,
                "error": str(e),
                "managed": True,
                "workflow_id": workflow_id
            }
        finally:
            # Cleanup resources (keep checkpoint for potential resume)
            await self.task_manager.resource_manager.cleanup_workflow(workflow_id)
    
    async def cancel_workflow(
        self,
        workflow_id: str,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Cancel a managed workflow.
        
        Args:
            workflow_id: Workflow identifier
            reason: Cancellation reason
            user_id: User who requested
            
        Returns:
            True if cancelled
        """
        # Cancel in task manager
        success = self.task_manager.cancel_workflow(
            workflow_id=workflow_id,
            reason=reason,
            user_id=user_id
        )
        
        if success:
            # Also cancel in orchestrator
            self.orchestrator.cancel_workflow(reason)
        
        return success
    
    async def pause_workflow(
        self,
        workflow_id: str,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Pause a managed workflow.
        
        Args:
            workflow_id: Workflow identifier
            reason: Pause reason
            user_id: User who requested
            
        Returns:
            True if paused
        """
        # Pause in task manager (creates checkpoint)
        success = self.task_manager.pause_workflow(
            workflow_id=workflow_id,
            reason=reason,
            user_id=user_id
        )
        
        if success:
            # Also pause in orchestrator
            self.orchestrator.pause_workflow(reason)
        
        return success
    
    async def resume_workflow(
        self,
        workflow_id: str,
        priority: ResumePriority = ResumePriority.NORMAL,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Resume a paused workflow.
        
        Args:
            workflow_id: Workflow identifier
            priority: Resume priority
            user_id: User who requested
            
        Returns:
            True if resumed
        """
        # Add to resume queue
        queued = await self.task_manager.resume_workflow(
            workflow_id=workflow_id,
            priority=priority,
            user_id=user_id
        )
        
        if not queued:
            return False
        
        # Process resume (would typically be handled by background worker)
        return await self.task_manager.execute_resume(workflow_id)
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get comprehensive workflow status.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Status dictionary
        """
        return self.task_manager.get_workflow_status(workflow_id)
    
    def get_all_workflows(self) -> list:
        """Get status of all managed workflows."""
        return self.task_manager.get_all_workflows()
    
    async def _handle_workflow_timeout(self, workflow_id: str) -> None:
        """Handle workflow timeout."""
        logger.warning(f"Workflow {workflow_id} timed out")
        
        # Cancel workflow
        await self.cancel_workflow(
            workflow_id=workflow_id,
            reason="Workflow timed out"
        )
    
    def register_cleanup_handler(
        self,
        workflow_id: str,
        task_id: str,
        handler: Callable
    ) -> None:
        """
        Register cleanup handler for a task.
        
        Args:
            workflow_id: Workflow identifier
            task_id: Task identifier
            handler: Cleanup function
        """
        self.task_manager.resource_manager.register_cleanup(
            workflow_id=workflow_id,
            task_id=task_id,
            handler=handler
        )
    
    def register_resource(
        self,
        workflow_id: str,
        resource_id: str,
        resource_type: str,
        cleanup_handler: Optional[Callable] = None
    ) -> None:
        """
        Register a resource for tracking.
        
        Args:
            workflow_id: Workflow identifier
            resource_id: Resource identifier
            resource_type: Resource type
            cleanup_handler: Optional cleanup function
        """
        self.task_manager.resource_manager.register_resource(
            workflow_id=workflow_id,
            resource_id=resource_id,
            resource_type=resource_type,
            cleanup_handler=cleanup_handler
        )
    
    def set_task_timeout(
        self,
        workflow_id: str,
        task_id: str,
        duration: int,
        callback: Optional[Callable] = None
    ) -> None:
        """
        Set timeout for a task.
        
        Args:
            workflow_id: Workflow identifier
            task_id: Task identifier
            duration: Timeout in seconds
            callback: Optional callback
        """
        self.task_manager.timeout_manager.set_task_timeout(
            workflow_id=workflow_id,
            task_id=task_id,
            duration=duration,
            callback=callback or self._handle_task_timeout
        )
    
    async def _handle_task_timeout(self, workflow_id: str, task_id: str) -> None:
        """Handle task timeout."""
        logger.warning(f"Task {task_id} in workflow {workflow_id} timed out")
        
        # Log timeout
        self.task_manager.audit_logger.log_event(
            workflow_id=workflow_id,
            event_type="task_timeout",
            data={"task_id": task_id},
            task_id=task_id
        )