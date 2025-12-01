"""
Central task management system for agent workflows.

Coordinates all task lifecycle operations including cancellation,
pause/resume, state persistence, and resource cleanup.
"""

import logging
import asyncio
import threading
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from enum import Enum

from ..task import Plan, Task, TaskStatus, WorkflowStage
from .checkpoint_manager import CheckpointManager
from .state_transition_manager import StateTransitionManager
from .cancellation_manager import CancellationManager
from .resource_manager import ResourceManager
from .timeout_manager import TimeoutManager
from .resume_queue import ResumeQueue, ResumePriority
from .audit_logger import AuditLogger

logger = logging.getLogger("mercury.agents.task_management.task_manager")


class WorkflowState(Enum):
    """Overall workflow state."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskManager:
    """
    Central task management system.
    
    Coordinates all aspects of task lifecycle management:
    - Workflow state tracking
    - Cancellation and pause/resume
    - State persistence via checkpoints
    - Resource cleanup
    - Timeout management
    - Priority-based resume queue
    - Comprehensive audit logging
    """
    
    def __init__(
        self,
        storage_dir: str = "backend/task_checkpoints",
        default_task_timeout: int = 300,
        default_workflow_timeout: int = 3600,
        max_checkpoints: int = 10,
        max_concurrent_resumes: int = 3
    ):
        """
        Initialize task manager.
        
        Args:
            storage_dir: Directory for checkpoints and logs
            default_task_timeout: Default task timeout in seconds
            default_workflow_timeout: Default workflow timeout in seconds
            max_checkpoints: Maximum checkpoints per workflow
            max_concurrent_resumes: Maximum concurrent resume operations
        """
        # Initialize subsystems
        self.audit_logger = AuditLogger(log_dir=storage_dir)
        self.checkpoint_manager = CheckpointManager(
            storage_dir=storage_dir,
            max_checkpoints=max_checkpoints
        )
        self.state_transition_manager = StateTransitionManager(
            audit_logger=self.audit_logger
        )
        self.cancellation_manager = CancellationManager(
            default_timeout=default_task_timeout
        )
        self.resource_manager = ResourceManager()
        self.timeout_manager = TimeoutManager(
            default_task_timeout=default_task_timeout,
            default_workflow_timeout=default_workflow_timeout
        )
        self.resume_queue = ResumeQueue(
            max_concurrent_resumes=max_concurrent_resumes
        )
        
        # Workflow tracking
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._workflow_states: Dict[str, WorkflowState] = {}
        self._workflow_plans: Dict[str, Plan] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._main_lock = threading.Lock()
        
        logger.info("TaskManager initialized")
    
    def _get_lock(self, workflow_id: str) -> threading.Lock:
        """Get or create a lock for a workflow."""
        with self._main_lock:
            if workflow_id not in self._locks:
                self._locks[workflow_id] = threading.Lock()
            return self._locks[workflow_id]
    
    def create_workflow(
        self,
        workflow_id: str,
        user_request: str,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Initialize a new workflow.
        
        Args:
            workflow_id: Unique workflow identifier
            user_request: User's request description
            config: Optional workflow configuration
            
        Returns:
            True if created successfully
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id in self._workflows:
                logger.warning(f"Workflow {workflow_id} already exists")
                return False
            
            # Initialize workflow data
            self._workflows[workflow_id] = {
                "workflow_id": workflow_id,
                "user_request": user_request,
                "config": config or {},
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None
            }
            
            self._workflow_states[workflow_id] = WorkflowState.CREATED
            
            # Log creation
            self.audit_logger.log_event(
                workflow_id=workflow_id,
                event_type="workflow_created",
                data={"user_request": user_request, "config": config}
            )
            
            logger.info(f"Created workflow: {workflow_id}")
            return True
    
    def start_workflow(self, workflow_id: str, plan: Optional[Plan] = None) -> bool:
        """
        Start a workflow.
        
        Args:
            workflow_id: Workflow identifier
            plan: Optional execution plan
            
        Returns:
            True if started successfully
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id not in self._workflows:
                logger.error(f"Workflow {workflow_id} not found")
                return False
            
            current_state = self._workflow_states.get(workflow_id)
            if current_state != WorkflowState.CREATED:
                logger.warning(f"Workflow {workflow_id} already started")
                return False
            
            # Store plan if provided
            if plan:
                self._workflow_plans[workflow_id] = plan
            
            # Update state
            self._workflows[workflow_id]["started_at"] = datetime.now().isoformat()
            self._workflow_states[workflow_id] = WorkflowState.RUNNING
            
            # Log start
            self.audit_logger.log_event(
                workflow_id=workflow_id,
                event_type="workflow_started",
                data={"plan_tasks": len(plan.tasks) if plan else 0}
            )
            
            logger.info(f"Started workflow: {workflow_id}")
            return True
    
    def cancel_workflow(
        self,
        workflow_id: str,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Cancel a running workflow.
        
        Args:
            workflow_id: Workflow identifier
            reason: Cancellation reason
            user_id: User who requested cancellation
            
        Returns:
            True if cancellation initiated
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            current_state = self._workflow_states.get(workflow_id)
            
            if current_state not in [WorkflowState.RUNNING, WorkflowState.PAUSED]:
                logger.warning(f"Cannot cancel workflow {workflow_id} in state {current_state}")
                return False
            
            # Update state
            self._workflow_states[workflow_id] = WorkflowState.CANCELLING
            
            # Request cancellation
            self.cancellation_manager.request_cancellation(
                workflow_id=workflow_id,
                reason=reason
            )
            
            # Log cancellation
            self.audit_logger.log_cancellation(
                workflow_id=workflow_id,
                reason=reason or "User requested",
                cancelled_by=user_id
            )
            
            logger.info(f"Cancellation requested for workflow: {workflow_id}")
            return True
    
    async def complete_cancellation(self, workflow_id: str) -> bool:
        """
        Complete workflow cancellation with cleanup.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if completed successfully
        """
        try:
            # Execute rollback if needed
            await self.cancellation_manager.execute_rollback(workflow_id)
            
            # Cleanup resources
            await self.resource_manager.cleanup_workflow(workflow_id)
            
            # Clear timeouts
            self.timeout_manager.cleanup(workflow_id)
            
            # Update state
            lock = self._get_lock(workflow_id)
            with lock:
                self._workflow_states[workflow_id] = WorkflowState.CANCELLED
                self._workflows[workflow_id]["completed_at"] = datetime.now().isoformat()
            
            # Mark cancellation complete
            self.cancellation_manager.complete_cancellation(workflow_id, success=True)
            
            # Log completion
            self.audit_logger.log_event(
                workflow_id=workflow_id,
                event_type="cancellation_completed",
                data={"success": True}
            )
            
            logger.info(f"Cancellation completed for workflow: {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Cancellation completion failed: {e}", exc_info=True)
            self.cancellation_manager.complete_cancellation(workflow_id, success=False)
            return False
    
    def pause_workflow(
        self,
        workflow_id: str,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Pause a running workflow.
        
        Args:
            workflow_id: Workflow identifier
            reason: Pause reason
            user_id: User who requested pause
            
        Returns:
            True if paused successfully
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            current_state = self._workflow_states.get(workflow_id)
            
            if current_state != WorkflowState.RUNNING:
                logger.warning(f"Cannot pause workflow {workflow_id} in state {current_state}")
                return False
            
            # Create checkpoint before pausing
            plan = self._workflow_plans.get(workflow_id)
            checkpoint_data = self._create_checkpoint_data(workflow_id, plan)
            checkpoint_id = self.checkpoint_manager.create_checkpoint(
                workflow_id=workflow_id,
                state_data=checkpoint_data
            )
            
            if not checkpoint_id:
                logger.error(f"Failed to create checkpoint for workflow {workflow_id}")
                return False
            
            # Update state
            self._workflow_states[workflow_id] = WorkflowState.PAUSED
            
            # Log pause
            self.audit_logger.log_event(
                workflow_id=workflow_id,
                event_type="workflow_paused",
                data={
                    "reason": reason or "User requested",
                    "checkpoint_id": checkpoint_id,
                    "paused_by": user_id
                }
            )
            
            # Log checkpoint
            checkpoint_size = self.checkpoint_manager.get_checkpoint_size(
                workflow_id, checkpoint_id
            )
            self.audit_logger.log_checkpoint(
                workflow_id=workflow_id,
                checkpoint_id=checkpoint_id,
                checkpoint_size=checkpoint_size
            )
            
            logger.info(f"Paused workflow: {workflow_id} at checkpoint {checkpoint_id}")
            return True
    
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
            user_id: User who requested resume
            
        Returns:
            True if resume queued successfully
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            current_state = self._workflow_states.get(workflow_id)
            
            if current_state != WorkflowState.PAUSED:
                logger.warning(f"Cannot resume workflow {workflow_id} in state {current_state}")
                return False
            
            # Add to resume queue
            success = self.resume_queue.enqueue_resume(
                workflow_id=workflow_id,
                priority=priority,
                requested_by=user_id
            )
            
            if success:
                self.audit_logger.log_event(
                    workflow_id=workflow_id,
                    event_type="resume_queued",
                    data={
                        "priority": priority.name,
                        "requested_by": user_id
                    }
                )
                logger.info(f"Queued resume for workflow: {workflow_id}")
            
            return success
    
    async def execute_resume(self, workflow_id: str) -> bool:
        """
        Execute workflow resume from checkpoint.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if resumed successfully
        """
        try:
            # Restore from checkpoint
            checkpoint_data = self.checkpoint_manager.restore_checkpoint(workflow_id)
            
            if not checkpoint_data:
                logger.error(f"Failed to restore checkpoint for workflow {workflow_id}")
                return False
            
            # Restore plan and state
            plan_data = checkpoint_data.get("plan")
            if plan_data:
                # Reconstruct plan (would need Plan.from_dict method)
                # For now, just log
                logger.info(f"Restored plan with {len(plan_data.get('tasks', []))} tasks")
            
            # Update state
            lock = self._get_lock(workflow_id)
            with lock:
                self._workflow_states[workflow_id] = WorkflowState.RUNNING
            
            # Log resume
            self.audit_logger.log_resume(
                workflow_id=workflow_id,
                checkpoint_id=checkpoint_data.get("checkpoint_id", "unknown")
            )
            
            logger.info(f"Resumed workflow: {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Resume failed: {e}", exc_info=True)
            return False
    
    def complete_workflow(
        self,
        workflow_id: str,
        success: bool = True,
        error: Optional[str] = None
    ) -> bool:
        """
        Mark workflow as completed.
        
        Args:
            workflow_id: Workflow identifier
            success: Whether workflow succeeded
            error: Optional error message
            
        Returns:
            True if marked complete
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if success:
                self._workflow_states[workflow_id] = WorkflowState.COMPLETED
            else:
                self._workflow_states[workflow_id] = WorkflowState.FAILED
            
            self._workflows[workflow_id]["completed_at"] = datetime.now().isoformat()
            
            # Log completion
            self.audit_logger.log_event(
                workflow_id=workflow_id,
                event_type="workflow_completed",
                data={"success": success, "error": error}
            )
            
            logger.info(f"Workflow completed: {workflow_id} (success={success})")
            return True
    
    def _create_checkpoint_data(
        self,
        workflow_id: str,
        plan: Optional[Plan]
    ) -> Dict[str, Any]:
        """Create checkpoint data structure."""
        data = {
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat(),
            "state": self._workflow_states.get(workflow_id, WorkflowState.CREATED).value,
            "workflow_data": self._workflows.get(workflow_id, {})
        }
        
        if plan:
            data["plan"] = plan.to_dict()
            data["completed_tasks"] = [
                t.id for t in plan.tasks if t.status == TaskStatus.COMPLETED
            ]
            current_task = plan.get_next_task()
            if current_task:
                data["current_task_id"] = current_task.id
        
        return data
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get comprehensive workflow status.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Status dictionary
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            workflow_data = self._workflows.get(workflow_id, {})
            state = self._workflow_states.get(workflow_id, WorkflowState.CREATED)
            plan = self._workflow_plans.get(workflow_id)
            
            status = {
                "workflow_id": workflow_id,
                "state": state.value,
                "is_cancelled": self.cancellation_manager.is_cancelled(workflow_id),
                "is_paused": state == WorkflowState.PAUSED,
                "created_at": workflow_data.get("created_at"),
                "started_at": workflow_data.get("started_at"),
                "completed_at": workflow_data.get("completed_at"),
                "user_request": workflow_data.get("user_request")
            }
            
            # Add plan progress if available
            if plan:
                status["plan_progress"] = plan.get_progress()
            
            # Add cancellation info
            if self.cancellation_manager.is_cancelled(workflow_id):
                status["cancellation_reason"] = self.cancellation_manager.get_cancellation_reason(workflow_id)
            
            # Add resource info
            status["resources"] = self.resource_manager.get_resource_summary(workflow_id)
            
            # Add queue info if paused
            if state == WorkflowState.PAUSED:
                queue_pos = self.resume_queue.get_position(workflow_id)
                status["resume_queue_position"] = queue_pos
            
            return status
    
    async def cleanup_workflow(self, workflow_id: str) -> bool:
        """
        Clean up all workflow resources.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if cleaned up successfully
        """
        try:
            # Cleanup all subsystems
            await self.resource_manager.cleanup_workflow(workflow_id)
            self.timeout_manager.cleanup(workflow_id)
            self.cancellation_manager.cleanup(workflow_id)
            self.checkpoint_manager.cleanup_workflow(workflow_id)
            
            # Remove from tracking
            lock = self._get_lock(workflow_id)
            with lock:
                if workflow_id in self._workflows:
                    del self._workflows[workflow_id]
                if workflow_id in self._workflow_states:
                    del self._workflow_states[workflow_id]
                if workflow_id in self._workflow_plans:
                    del self._workflow_plans[workflow_id]
            
            # Remove lock
            with self._main_lock:
                if workflow_id in self._locks:
                    del self._locks[workflow_id]
            
            logger.info(f"Cleaned up workflow: {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Workflow cleanup failed: {e}", exc_info=True)
            return False
    
    def get_all_workflows(self) -> List[Dict[str, Any]]:
        """
        Get status of all workflows.
        
        Returns:
            List of workflow status dictionaries
        """
        with self._main_lock:
            workflow_ids = list(self._workflows.keys())
        
        return [self.get_workflow_status(wf_id) for wf_id in workflow_ids]
    
    def shutdown(self) -> None:
        """Shutdown task manager and cleanup resources."""
        logger.info("Shutting down TaskManager...")
        
        # Stop timeout monitoring
        self.timeout_manager.shutdown()
        
        # Stop resume queue processing
        self.resume_queue.stop_processing()
        
        logger.info("TaskManager shut down complete")