"""
Timeout management for workflow tasks.

Monitors task execution time and triggers cancellation on timeout.
"""

import logging
import asyncio
import threading
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta

logger = logging.getLogger("mercury.agents.task_management.timeout_manager")


class TimeoutManager:
    """
    Manages timeouts for tasks and workflows.
    
    Monitors execution time and triggers cancellation when timeouts occur.
    """
    
    def __init__(self, default_task_timeout: int = 300, default_workflow_timeout: int = 3600):
        """
        Initialize timeout manager.
        
        Args:
            default_task_timeout: Default task timeout in seconds (5 minutes)
            default_workflow_timeout: Default workflow timeout in seconds (1 hour)
        """
        self.default_task_timeout = default_task_timeout
        self.default_workflow_timeout = default_workflow_timeout
        
        self._task_timeouts: Dict[str, Dict[str, datetime]] = {}  # workflow_id -> {task_id -> deadline}
        self._workflow_timeouts: Dict[str, datetime] = {}  # workflow_id -> deadline
        self._timeout_callbacks: Dict[str, Dict[str, Callable]] = {}  # workflow_id -> {task_id -> callback}
        self._workflow_callbacks: Dict[str, Callable] = {}  # workflow_id -> callback
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._main_lock = threading.Lock()
        self._running = True
    
    def _get_lock(self, workflow_id: str) -> threading.Lock:
        """Get or create a lock for a workflow."""
        with self._main_lock:
            if workflow_id not in self._locks:
                self._locks[workflow_id] = threading.Lock()
            return self._locks[workflow_id]
    
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
            duration: Timeout duration in seconds
            callback: Optional callback on timeout
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id not in self._task_timeouts:
                self._task_timeouts[workflow_id] = {}
                self._timeout_callbacks[workflow_id] = {}
            
            deadline = datetime.now() + timedelta(seconds=duration)
            self._task_timeouts[workflow_id][task_id] = deadline
            
            if callback:
                self._timeout_callbacks[workflow_id][task_id] = callback
            
            logger.debug(
                f"Set timeout for task {task_id}: {duration}s "
                f"(deadline: {deadline.isoformat()})"
            )
        
        # Start monitoring if not already running
        if workflow_id not in self._monitoring_tasks:
            self._start_monitoring(workflow_id)
    
    def set_workflow_timeout(
        self,
        workflow_id: str,
        duration: int,
        callback: Optional[Callable] = None
    ) -> None:
        """
        Set timeout for entire workflow.
        
        Args:
            workflow_id: Workflow identifier
            duration: Timeout duration in seconds
            callback: Optional callback on timeout
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            deadline = datetime.now() + timedelta(seconds=duration)
            self._workflow_timeouts[workflow_id] = deadline
            
            if callback:
                self._workflow_callbacks[workflow_id] = callback
            
            logger.debug(
                f"Set workflow timeout: {duration}s "
                f"(deadline: {deadline.isoformat()})"
            )
        
        # Start monitoring if not already running
        if workflow_id not in self._monitoring_tasks:
            self._start_monitoring(workflow_id)
    
    def clear_task_timeout(self, workflow_id: str, task_id: str) -> None:
        """
        Clear timeout for a task.
        
        Args:
            workflow_id: Workflow identifier
            task_id: Task identifier
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id in self._task_timeouts:
                if task_id in self._task_timeouts[workflow_id]:
                    del self._task_timeouts[workflow_id][task_id]
                    logger.debug(f"Cleared timeout for task {task_id}")
            
            if workflow_id in self._timeout_callbacks:
                if task_id in self._timeout_callbacks[workflow_id]:
                    del self._timeout_callbacks[workflow_id][task_id]
    
    def clear_workflow_timeout(self, workflow_id: str) -> None:
        """
        Clear workflow timeout.
        
        Args:
            workflow_id: Workflow identifier
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id in self._workflow_timeouts:
                del self._workflow_timeouts[workflow_id]
                logger.debug(f"Cleared workflow timeout for {workflow_id}")
            
            if workflow_id in self._workflow_callbacks:
                del self._workflow_callbacks[workflow_id]
    
    def _start_monitoring(self, workflow_id: str) -> None:
        """Start monitoring thread for a workflow."""
        async def monitor():
            logger.info(f"Started timeout monitoring for workflow {workflow_id}")
            
            while self._running:
                try:
                    await asyncio.sleep(1)  # Check every second
                    
                    # Check task timeouts
                    timed_out_tasks = []
                    lock = self._get_lock(workflow_id)
                    
                    with lock:
                        if workflow_id in self._task_timeouts:
                            now = datetime.now()
                            for task_id, deadline in list(self._task_timeouts[workflow_id].items()):
                                if now >= deadline:
                                    timed_out_tasks.append(task_id)
                    
                    # Handle timed out tasks
                    for task_id in timed_out_tasks:
                        await self._handle_task_timeout(workflow_id, task_id)
                    
                    # Check workflow timeout
                    workflow_timed_out = False
                    with lock:
                        if workflow_id in self._workflow_timeouts:
                            if datetime.now() >= self._workflow_timeouts[workflow_id]:
                                workflow_timed_out = True
                    
                    if workflow_timed_out:
                        await self._handle_workflow_timeout(workflow_id)
                        break  # Stop monitoring after workflow timeout
                    
                    # Stop if no more timeouts to monitor
                    with lock:
                        has_task_timeouts = (
                            workflow_id in self._task_timeouts and
                            bool(self._task_timeouts[workflow_id])
                        )
                        has_workflow_timeout = workflow_id in self._workflow_timeouts
                    
                    if not has_task_timeouts and not has_workflow_timeout:
                        logger.debug(f"No more timeouts to monitor for {workflow_id}")
                        break
                        
                except Exception as e:
                    logger.error(f"Error in timeout monitoring: {e}", exc_info=True)
            
            # Clean up monitoring task
            if workflow_id in self._monitoring_tasks:
                del self._monitoring_tasks[workflow_id]
            
            logger.info(f"Stopped timeout monitoring for workflow {workflow_id}")
        
        # Create and store monitoring task
        task = asyncio.create_task(monitor())
        self._monitoring_tasks[workflow_id] = task
    
    async def _handle_task_timeout(self, workflow_id: str, task_id: str) -> None:
        """Handle task timeout."""
        logger.warning(f"Task timeout: workflow={workflow_id}, task={task_id}")
        
        lock = self._get_lock(workflow_id)
        callback = None
        
        with lock:
            # Get and remove callback
            if workflow_id in self._timeout_callbacks:
                callback = self._timeout_callbacks[workflow_id].get(task_id)
            
            # Clear timeout
            if workflow_id in self._task_timeouts:
                if task_id in self._task_timeouts[workflow_id]:
                    del self._task_timeouts[workflow_id][task_id]
        
        # Execute callback outside lock
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(workflow_id, task_id)
                else:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, callback, workflow_id, task_id)
            except Exception as e:
                logger.error(f"Timeout callback failed: {e}", exc_info=True)
    
    async def _handle_workflow_timeout(self, workflow_id: str) -> None:
        """Handle workflow timeout."""
        logger.warning(f"Workflow timeout: {workflow_id}")
        
        lock = self._get_lock(workflow_id)
        callback = None
        
        with lock:
            # Get and remove callback
            callback = self._workflow_callbacks.get(workflow_id)
            
            # Clear timeout
            if workflow_id in self._workflow_timeouts:
                del self._workflow_timeouts[workflow_id]
        
        # Execute callback outside lock
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(workflow_id)
                else:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, callback, workflow_id)
            except Exception as e:
                logger.error(f"Workflow timeout callback failed: {e}", exc_info=True)
    
    def get_remaining_time(self, workflow_id: str, task_id: Optional[str] = None) -> Optional[float]:
        """
        Get remaining time before timeout.
        
        Args:
            workflow_id: Workflow identifier
            task_id: Optional task identifier (checks workflow if None)
            
        Returns:
            Remaining seconds, or None if no timeout set
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if task_id:
                if workflow_id in self._task_timeouts:
                    deadline = self._task_timeouts[workflow_id].get(task_id)
                    if deadline:
                        remaining = (deadline - datetime.now()).total_seconds()
                        return max(0, remaining)
            else:
                if workflow_id in self._workflow_timeouts:
                    deadline = self._workflow_timeouts[workflow_id]
                    remaining = (deadline - datetime.now()).total_seconds()
                    return max(0, remaining)
        
        return None
    
    def cleanup(self, workflow_id: str) -> None:
        """
        Clean up timeout resources for a workflow.
        
        Args:
            workflow_id: Workflow identifier
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id in self._task_timeouts:
                del self._task_timeouts[workflow_id]
            
            if workflow_id in self._timeout_callbacks:
                del self._timeout_callbacks[workflow_id]
            
            if workflow_id in self._workflow_timeouts:
                del self._workflow_timeouts[workflow_id]
            
            if workflow_id in self._workflow_callbacks:
                del self._workflow_callbacks[workflow_id]
        
        # Cancel monitoring task
        if workflow_id in self._monitoring_tasks:
            task = self._monitoring_tasks[workflow_id]
            if not task.done():
                task.cancel()
            del self._monitoring_tasks[workflow_id]
        
        # Remove lock
        with self._main_lock:
            if workflow_id in self._locks:
                del self._locks[workflow_id]
        
        logger.debug(f"Cleaned up timeout resources for {workflow_id}")
    
    def shutdown(self) -> None:
        """Shutdown timeout manager."""
        self._running = False
        
        # Cancel all monitoring tasks
        for task in self._monitoring_tasks.values():
            if not task.done():
                task.cancel()
        
        self._monitoring_tasks.clear()
        logger.info("Timeout manager shut down")