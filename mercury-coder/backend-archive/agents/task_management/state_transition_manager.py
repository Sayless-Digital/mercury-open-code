"""
State transition management for task workflows.

Validates state transitions and emits events for tracking.
"""

import logging
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime
import threading
from enum import Enum

from ..task import TaskStatus, WorkflowStage

logger = logging.getLogger("mercury.agents.task_management.state_transition")


class StateTransitionManager:
    """
    Manages valid state transitions and event emission.
    
    Ensures state transitions follow valid paths and logs all changes.
    """
    
    # Valid state transitions for TaskStatus
    VALID_TASK_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
        TaskStatus.PENDING: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
        TaskStatus.IN_PROGRESS: {
            TaskStatus.PAUSED,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED
        },
        TaskStatus.PAUSED: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
        TaskStatus.COMPLETED: set(),  # Terminal state
        TaskStatus.FAILED: set(),  # Terminal state
        TaskStatus.CANCELLED: set(),  # Terminal state
    }
    
    # Valid workflow stage transitions
    VALID_WORKFLOW_TRANSITIONS: Dict[WorkflowStage, Set[WorkflowStage]] = {
        WorkflowStage.PLANNING: {WorkflowStage.EXPLORING, WorkflowStage.ERROR},
        WorkflowStage.EXPLORING: {WorkflowStage.PLANNING, WorkflowStage.EXECUTING, WorkflowStage.ERROR},
        WorkflowStage.EXECUTING: {WorkflowStage.VALIDATING, WorkflowStage.ERROR, WorkflowStage.EXECUTING},
        WorkflowStage.VALIDATING: {WorkflowStage.COMPLETED, WorkflowStage.ERROR},
        WorkflowStage.COMPLETED: set(),  # Terminal state
        WorkflowStage.ERROR: set(),  # Terminal state
    }
    
    def __init__(self, audit_logger: Optional[Any] = None, status_emitter: Optional[Any] = None):
        """
        Initialize state transition manager.
        
        Args:
            audit_logger: AuditLogger instance for logging transitions
            status_emitter: StatusEmitter for UI updates
        """
        self.audit_logger = audit_logger
        self.status_emitter = status_emitter
        self._transition_history: Dict[str, List[Dict[str, Any]]] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._main_lock = threading.Lock()
        self._event_callbacks: List[Callable] = []
    
    def _get_lock(self, workflow_id: str) -> threading.Lock:
        """Get or create a lock for a workflow."""
        with self._main_lock:
            if workflow_id not in self._locks:
                self._locks[workflow_id] = threading.Lock()
            return self._locks[workflow_id]
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for transition events.
        
        Args:
            callback: Function to call on transitions
        """
        self._event_callbacks.append(callback)
    
    def validate_task_transition(
        self,
        from_state: TaskStatus,
        to_state: TaskStatus
    ) -> bool:
        """
        Validate if a task state transition is allowed.
        
        Args:
            from_state: Current state
            to_state: Desired state
            
        Returns:
            True if transition is valid
        """
        if from_state == to_state:
            return True  # No-op transition
        
        valid_targets = self.VALID_TASK_TRANSITIONS.get(from_state, set())
        return to_state in valid_targets
    
    def validate_workflow_transition(
        self,
        from_stage: WorkflowStage,
        to_stage: WorkflowStage
    ) -> bool:
        """
        Validate if a workflow stage transition is allowed.
        
        Args:
            from_stage: Current stage
            to_stage: Desired stage
            
        Returns:
            True if transition is valid
        """
        if from_stage == to_stage:
            return True  # No-op transition
        
        valid_targets = self.VALID_WORKFLOW_TRANSITIONS.get(from_stage, set())
        return to_stage in valid_targets
    
    def transition_task(
        self,
        workflow_id: str,
        task_id: str,
        from_state: TaskStatus,
        to_state: TaskStatus,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Execute a task state transition.
        
        Args:
            workflow_id: Workflow identifier
            task_id: Task identifier
            from_state: Current state
            to_state: Desired state
            reason: Reason for transition
            metadata: Additional metadata
            
        Returns:
            True if transition succeeded
            
        Raises:
            ValueError: If transition is invalid
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            # Validate transition
            if not self.validate_task_transition(from_state, to_state):
                error_msg = f"Invalid task transition: {from_state.value} -> {to_state.value}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Record transition
            transition_record = {
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "from_state": from_state.value,
                "to_state": to_state.value,
                "reason": reason,
                "metadata": metadata or {}
            }
            
            if workflow_id not in self._transition_history:
                self._transition_history[workflow_id] = []
            self._transition_history[workflow_id].append(transition_record)
            
            # Log to audit logger
            if self.audit_logger:
                self.audit_logger.log_state_change(
                    workflow_id=workflow_id,
                    task_id=task_id,
                    from_state=from_state.value,
                    to_state=to_state.value,
                    reason=reason,
                    metadata=metadata
                )
            
            # Emit event
            event_data = {
                "type": "task_transition",
                "workflow_id": workflow_id,
                "task_id": task_id,
                "from_state": from_state.value,
                "to_state": to_state.value,
                "reason": reason,
                "metadata": metadata
            }
            self._emit_event(event_data)
            
            logger.info(
                f"Task transition: workflow={workflow_id}, task={task_id}, "
                f"{from_state.value} -> {to_state.value}"
            )
            
            return True
    
    def transition_workflow(
        self,
        workflow_id: str,
        from_stage: WorkflowStage,
        to_stage: WorkflowStage,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Execute a workflow stage transition.
        
        Args:
            workflow_id: Workflow identifier
            from_stage: Current stage
            to_stage: Desired stage
            message: Status message
            details: Additional details
            
        Returns:
            True if transition succeeded
            
        Raises:
            ValueError: If transition is invalid
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            # Validate transition
            if not self.validate_workflow_transition(from_stage, to_stage):
                error_msg = f"Invalid workflow transition: {from_stage.value} -> {to_stage.value}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Record transition
            transition_record = {
                "timestamp": datetime.now().isoformat(),
                "from_stage": from_stage.value,
                "to_stage": to_stage.value,
                "message": message,
                "details": details or {}
            }
            
            if workflow_id not in self._transition_history:
                self._transition_history[workflow_id] = []
            self._transition_history[workflow_id].append(transition_record)
            
            # Log to audit logger
            if self.audit_logger:
                self.audit_logger.log_event(
                    workflow_id=workflow_id,
                    event_type="workflow_transition",
                    data={
                        "from_stage": from_stage.value,
                        "to_stage": to_stage.value,
                        "message": message,
                        "details": details
                    }
                )
            
            # Emit to status emitter if available
            if self.status_emitter:
                self.status_emitter.transition_to_stage(to_stage, message or "", details)
            
            # Emit event to callbacks
            event_data = {
                "type": "workflow_transition",
                "workflow_id": workflow_id,
                "from_stage": from_stage.value,
                "to_stage": to_stage.value,
                "message": message,
                "details": details
            }
            self._emit_event(event_data)
            
            logger.info(
                f"Workflow transition: workflow={workflow_id}, "
                f"{from_stage.value} -> {to_stage.value}"
            )
            
            return True
    
    def _emit_event(self, event_data: Dict[str, Any]) -> None:
        """Emit event to all registered callbacks."""
        for callback in self._event_callbacks:
            try:
                callback(event_data)
            except Exception as e:
                logger.error(f"Error in transition callback: {e}", exc_info=True)
    
    def get_transition_history(
        self,
        workflow_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transition history for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            limit: Optional limit on number of entries
            
        Returns:
            List of transition records
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            history = self._transition_history.get(workflow_id, [])
            if limit:
                return history[-limit:]
            return history.copy()
    
    def clear_history(self, workflow_id: str) -> None:
        """
        Clear transition history for a workflow.
        
        Args:
            workflow_id: Workflow identifier
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id in self._transition_history:
                del self._transition_history[workflow_id]
            if workflow_id in self._locks:
                del self._locks[workflow_id]