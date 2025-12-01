"""
Cancellation management for workflow tasks.

Handles graceful cancellation with cleanup and rollback support.
"""

import logging
import threading
import asyncio
from typing import Dict, Optional, Callable, Any, Set
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger("mercury.agents.task_management.cancellation")


class CancellationState(Enum):
    """Cancellation states."""
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class CancellationManager:
    """
    Manages workflow cancellation with graceful shutdown.
    
    Provides:
    - Cancellation flag management
    - Safe cancellation points
    - Timeout handling for cancellation
    - Rollback coordination
    """
    
    def __init__(self, default_timeout: int = 30):
        """
        Initialize cancellation manager.
        
        Args:
            default_timeout: Default timeout for cancellation in seconds
        """
        self.default_timeout = default_timeout
        self._cancellation_flags: Dict[str, threading.Event] = {}
        self._cancellation_reasons: Dict[str, str] = {}
        self._cancellation_states: Dict[str, CancellationState] = {}
        self._cancellation_times: Dict[str, datetime] = {}
        self._safe_points: Dict[str, Set[str]] = {}
        self._rollback_handlers: Dict[str, Dict[str, Callable]] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._main_lock = threading.Lock()
    
    def _get_lock(self, workflow_id: str) -> threading.Lock:
        """Get or create a lock for a workflow."""
        with self._main_lock:
            if workflow_id not in self._locks:
                self._locks[workflow_id] = threading.Lock()
            return self._locks[workflow_id]
    
    def request_cancellation(
        self,
        workflow_id: str,
        reason: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Request workflow cancellation.
        
        Args:
            workflow_id: Workflow identifier
            reason: Reason for cancellation
            timeout: Timeout in seconds (uses default if None)
            
        Returns:
            True if cancellation was requested
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            # Check if already cancelled
            if workflow_id in self._cancellation_flags:
                current_state = self._cancellation_states.get(
                    workflow_id,
                    CancellationState.NOT_REQUESTED
                )
                if current_state in [CancellationState.COMPLETED, CancellationState.REQUESTED]:
                    logger.warning(f"Cancellation already requested for workflow {workflow_id}")
                    return False
            
            # Create cancellation flag
            if workflow_id not in self._cancellation_flags:
                self._cancellation_flags[workflow_id] = threading.Event()
            
            # Set flag and metadata
            self._cancellation_flags[workflow_id].set()
            self._cancellation_reasons[workflow_id] = reason or "Cancellation requested"
            self._cancellation_states[workflow_id] = CancellationState.REQUESTED
            self._cancellation_times[workflow_id] = datetime.now()
            
            logger.info(
                f"Cancellation requested for workflow {workflow_id}: "
                f"{self._cancellation_reasons[workflow_id]}"
            )
            
            return True
    
    def is_cancelled(self, workflow_id: str) -> bool:
        """
        Check if workflow is cancelled.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if cancelled
        """
        if workflow_id not in self._cancellation_flags:
            return False
        return self._cancellation_flags[workflow_id].is_set()
    
    def get_cancellation_reason(self, workflow_id: str) -> Optional[str]:
        """
        Get cancellation reason.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Cancellation reason or None
        """
        return self._cancellation_reasons.get(workflow_id)
    
    def get_cancellation_state(self, workflow_id: str) -> CancellationState:
        """
        Get current cancellation state.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Current cancellation state
        """
        return self._cancellation_states.get(
            workflow_id,
            CancellationState.NOT_REQUESTED
        )
    
    def mark_safe_point(self, workflow_id: str, checkpoint_id: str) -> None:
        """
        Mark a safe cancellation point.
        
        Args:
            workflow_id: Workflow identifier
            checkpoint_id: Checkpoint identifier
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id not in self._safe_points:
                self._safe_points[workflow_id] = set()
            self._safe_points[workflow_id].add(checkpoint_id)
            logger.debug(f"Marked safe point {checkpoint_id} for workflow {workflow_id}")
    
    def wait_for_safe_point(
        self,
        workflow_id: str,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for a safe cancellation point.
        
        Args:
            workflow_id: Workflow identifier
            timeout: Timeout in seconds
            
        Returns:
            True if safe point reached before timeout
        """
        if not self.is_cancelled(workflow_id):
            return True
        
        timeout = timeout or self.default_timeout
        start_time = datetime.now()
        
        while True:
            if (datetime.now() - start_time).total_seconds() > timeout:
                logger.warning(
                    f"Timeout waiting for safe point in workflow {workflow_id}"
                )
                return False
            
            # Check if we have any safe points
            lock = self._get_lock(workflow_id)
            with lock:
                if workflow_id in self._safe_points and self._safe_points[workflow_id]:
                    return True
            
            # Sleep briefly before checking again
            import time
            time.sleep(0.1)
    
    def register_rollback_handler(
        self,
        workflow_id: str,
        task_id: str,
        handler: Callable[[], None]
    ) -> None:
        """
        Register a rollback handler for a task.
        
        Args:
            workflow_id: Workflow identifier
            task_id: Task identifier
            handler: Rollback function to call
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id not in self._rollback_handlers:
                self._rollback_handlers[workflow_id] = {}
            self._rollback_handlers[workflow_id][task_id] = handler
            logger.debug(f"Registered rollback handler for task {task_id}")
    
    async def execute_rollback(
        self,
        workflow_id: str,
        task_id: Optional[str] = None
    ) -> bool:
        """
        Execute rollback for workflow or specific task.
        
        Args:
            workflow_id: Workflow identifier
            task_id: Optional specific task ID (rolls back all if None)
            
        Returns:
            True if rollback succeeded
        """
        lock = self._get_lock(workflow_id)
        
        try:
            with lock:
                if workflow_id not in self._rollback_handlers:
                    logger.debug(f"No rollback handlers for workflow {workflow_id}")
                    return True
                
                handlers = self._rollback_handlers[workflow_id]
                
                if task_id:
                    # Rollback specific task
                    if task_id in handlers:
                        logger.info(f"Executing rollback for task {task_id}")
                        await self._execute_handler(handlers[task_id])
                        del handlers[task_id]
                else:
                    # Rollback all tasks
                    logger.info(f"Executing rollback for all tasks in workflow {workflow_id}")
                    for tid, handler in list(handlers.items()):
                        try:
                            await self._execute_handler(handler)
                        except Exception as e:
                            logger.error(f"Rollback failed for task {tid}: {e}")
                    handlers.clear()
                
                return True
                
        except Exception as e:
            logger.error(f"Rollback execution failed: {e}", exc_info=True)
            return False
    
    async def _execute_handler(self, handler: Callable) -> None:
        """Execute a rollback handler (sync or async)."""
        if asyncio.iscoroutinefunction(handler):
            await handler()
        else:
            # Run sync handler in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, handler)
    
    def complete_cancellation(self, workflow_id: str, success: bool = True) -> None:
        """
        Mark cancellation as complete.
        
        Args:
            workflow_id: Workflow identifier
            success: Whether cancellation succeeded
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if success:
                self._cancellation_states[workflow_id] = CancellationState.COMPLETED
                logger.info(f"Cancellation completed for workflow {workflow_id}")
            else:
                self._cancellation_states[workflow_id] = CancellationState.FAILED
                logger.error(f"Cancellation failed for workflow {workflow_id}")
    
    def reset_cancellation(self, workflow_id: str) -> None:
        """
        Reset cancellation state (for new workflow).
        
        Args:
            workflow_id: Workflow identifier
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id in self._cancellation_flags:
                self._cancellation_flags[workflow_id].clear()
                del self._cancellation_flags[workflow_id]
            
            if workflow_id in self._cancellation_reasons:
                del self._cancellation_reasons[workflow_id]
            
            if workflow_id in self._cancellation_states:
                del self._cancellation_states[workflow_id]
            
            if workflow_id in self._cancellation_times:
                del self._cancellation_times[workflow_id]
            
            if workflow_id in self._safe_points:
                del self._safe_points[workflow_id]
            
            if workflow_id in self._rollback_handlers:
                del self._rollback_handlers[workflow_id]
            
            logger.debug(f"Reset cancellation state for workflow {workflow_id}")
    
    def check_timeout(self, workflow_id: str) -> bool:
        """
        Check if cancellation has timed out.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if timed out
        """
        if workflow_id not in self._cancellation_times:
            return False
        
        cancel_time = self._cancellation_times[workflow_id]
        elapsed = (datetime.now() - cancel_time).total_seconds()
        
        if elapsed > self.default_timeout:
            logger.warning(
                f"Cancellation timeout for workflow {workflow_id} "
                f"(elapsed: {elapsed}s)"
            )
            return True
        
        return False
    
    def cleanup(self, workflow_id: str) -> None:
        """
        Clean up cancellation resources.
        
        Args:
            workflow_id: Workflow identifier
        """
        self.reset_cancellation(workflow_id)
        
        # Remove lock
        with self._main_lock:
            if workflow_id in self._locks:
                del self._locks[workflow_id]