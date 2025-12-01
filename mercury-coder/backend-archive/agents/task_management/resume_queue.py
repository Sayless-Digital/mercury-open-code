"""
Resume queue for managing workflow resume requests with priority.

Handles prioritized resume operations for paused workflows.
"""

import logging
import asyncio
import threading
from typing import Dict, List, Optional, Set
from datetime import datetime
from enum import Enum
import heapq

logger = logging.getLogger("mercury.agents.task_management.resume_queue")


class ResumePriority(Enum):
    """Resume priority levels."""
    HIGH = 1
    NORMAL = 2
    LOW = 3


class ResumeRequest:
    """Represents a workflow resume request."""
    
    def __init__(
        self,
        workflow_id: str,
        priority: ResumePriority,
        requested_at: datetime,
        requested_by: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        self.workflow_id = workflow_id
        self.priority = priority
        self.requested_at = requested_at
        self.requested_by = requested_by
        self.metadata = metadata or {}
    
    def __lt__(self, other: 'ResumeRequest') -> bool:
        """Compare for priority queue (lower priority value = higher priority)."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        # If same priority, earlier request goes first
        return self.requested_at < other.requested_at
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "priority": self.priority.value,
            "requested_at": self.requested_at.isoformat(),
            "requested_by": self.requested_by,
            "metadata": self.metadata
        }


class ResumeQueue:
    """
    Priority-based queue for workflow resume requests.
    
    Manages resume operations with priority levels and prevents
    concurrent resume attempts for the same workflow.
    """
    
    def __init__(self, max_concurrent_resumes: int = 3):
        """
        Initialize resume queue.
        
        Args:
            max_concurrent_resumes: Maximum concurrent resume operations
        """
        self.max_concurrent_resumes = max_concurrent_resumes
        self._queue: List[ResumeRequest] = []
        self._in_progress: Set[str] = set()
        self._completed: Set[str] = set()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._processing = False
    
    def enqueue_resume(
        self,
        workflow_id: str,
        priority: ResumePriority = ResumePriority.NORMAL,
        requested_by: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add a resume request to the queue.
        
        Args:
            workflow_id: Workflow identifier
            priority: Resume priority level
            requested_by: User who requested resume
            metadata: Additional metadata
            
        Returns:
            True if enqueued successfully
        """
        with self._lock:
            # Check if already in queue or in progress
            if workflow_id in self._in_progress:
                logger.warning(f"Workflow {workflow_id} is already being resumed")
                return False
            
            if any(req.workflow_id == workflow_id for req in self._queue):
                logger.warning(f"Workflow {workflow_id} is already in resume queue")
                return False
            
            # Create and add request
            request = ResumeRequest(
                workflow_id=workflow_id,
                priority=priority,
                requested_at=datetime.now(),
                requested_by=requested_by,
                metadata=metadata
            )
            
            heapq.heappush(self._queue, request)
            
            logger.info(
                f"Enqueued resume request: workflow={workflow_id}, "
                f"priority={priority.name}, queue_size={len(self._queue)}"
            )
            
            # Notify waiting threads
            self._condition.notify()
            
            return True
    
    def dequeue_resume(self, timeout: Optional[float] = None) -> Optional[ResumeRequest]:
        """
        Get next resume request from queue.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            Next resume request, or None if queue is empty/timeout
        """
        with self._condition:
            # Wait for queue to have items or timeout
            if not self._queue:
                if timeout:
                    self._condition.wait(timeout)
                else:
                    return None
            
            # Check if we can process more
            if len(self._in_progress) >= self.max_concurrent_resumes:
                logger.debug("Max concurrent resumes reached, waiting...")
                return None
            
            if not self._queue:
                return None
            
            # Get highest priority request
            request = heapq.heappop(self._queue)
            self._in_progress.add(request.workflow_id)
            
            logger.info(
                f"Dequeued resume request: workflow={request.workflow_id}, "
                f"priority={request.priority.name}"
            )
            
            return request
    
    def complete_resume(self, workflow_id: str, success: bool = True) -> None:
        """
        Mark a resume operation as complete.
        
        Args:
            workflow_id: Workflow identifier
            success: Whether resume succeeded
        """
        with self._lock:
            if workflow_id in self._in_progress:
                self._in_progress.remove(workflow_id)
                
                if success:
                    self._completed.add(workflow_id)
                
                logger.info(
                    f"Completed resume: workflow={workflow_id}, success={success}"
                )
                
                # Notify waiting threads
                self._condition.notify()
    
    def remove_from_queue(self, workflow_id: str) -> bool:
        """
        Remove a workflow from the queue (cancel resume).
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if removed
        """
        with self._lock:
            # Remove from queue
            original_size = len(self._queue)
            self._queue = [req for req in self._queue if req.workflow_id != workflow_id]
            heapq.heapify(self._queue)  # Restore heap property
            
            removed = original_size != len(self._queue)
            
            if removed:
                logger.info(f"Removed workflow {workflow_id} from resume queue")
            
            return removed
    
    def reprioritize(self, workflow_id: str, new_priority: ResumePriority) -> bool:
        """
        Change priority of a queued resume request.
        
        Args:
            workflow_id: Workflow identifier
            new_priority: New priority level
            
        Returns:
            True if reprioritized
        """
        with self._lock:
            # Find and update request
            for request in self._queue:
                if request.workflow_id == workflow_id:
                    old_priority = request.priority
                    request.priority = new_priority
                    
                    # Restore heap property
                    heapq.heapify(self._queue)
                    
                    logger.info(
                        f"Reprioritized workflow {workflow_id}: "
                        f"{old_priority.name} -> {new_priority.name}"
                    )
                    
                    return True
            
            return False
    
    def get_queue_status(self) -> Dict:
        """
        Get current queue status.
        
        Returns:
            Queue status dictionary
        """
        with self._lock:
            return {
                "queue_size": len(self._queue),
                "in_progress": len(self._in_progress),
                "completed": len(self._completed),
                "max_concurrent": self.max_concurrent_resumes,
                "queued_workflows": [req.workflow_id for req in self._queue]
            }
    
    def get_position(self, workflow_id: str) -> Optional[int]:
        """
        Get position of workflow in queue.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Position (0-indexed), or None if not in queue
        """
        with self._lock:
            # Sort queue by priority to get actual order
            sorted_queue = sorted(self._queue)
            for i, request in enumerate(sorted_queue):
                if request.workflow_id == workflow_id:
                    return i
            
            return None
    
    def is_in_progress(self, workflow_id: str) -> bool:
        """
        Check if workflow resume is in progress.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if in progress
        """
        with self._lock:
            return workflow_id in self._in_progress
    
    def is_completed(self, workflow_id: str) -> bool:
        """
        Check if workflow resume is completed.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if completed
        """
        with self._lock:
            return workflow_id in self._completed
    
    def clear_completed(self) -> int:
        """
        Clear completed workflows from tracking.
        
        Returns:
            Number of workflows cleared
        """
        with self._lock:
            count = len(self._completed)
            self._completed.clear()
            logger.debug(f"Cleared {count} completed workflows")
            return count
    
    def clear(self) -> None:
        """Clear the entire queue."""
        with self._lock:
            self._queue.clear()
            self._in_progress.clear()
            self._completed.clear()
            logger.info("Cleared resume queue")
    
    async def process_queue(
        self,
        resume_handler: callable,
        max_iterations: Optional[int] = None
    ) -> int:
        """
        Process resume queue with a handler function.
        
        Args:
            resume_handler: Async function to handle resume (workflow_id, metadata)
            max_iterations: Optional limit on iterations
            
        Returns:
            Number of resumes processed
        """
        processed = 0
        iterations = 0
        
        self._processing = True
        
        try:
            while self._processing:
                if max_iterations and iterations >= max_iterations:
                    break
                
                # Get next request
                request = self.dequeue_resume(timeout=1.0)
                
                if request is None:
                    # No more requests or at capacity
                    await asyncio.sleep(0.5)
                    iterations += 1
                    continue
                
                # Process resume
                try:
                    logger.info(f"Processing resume for workflow {request.workflow_id}")
                    success = await resume_handler(request.workflow_id, request.metadata)
                    self.complete_resume(request.workflow_id, success)
                    processed += 1
                except Exception as e:
                    logger.error(f"Resume handler failed: {e}", exc_info=True)
                    self.complete_resume(request.workflow_id, False)
                
                iterations += 1
            
            return processed
            
        finally:
            self._processing = False
    
    def stop_processing(self) -> None:
        """Stop queue processing."""
        self._processing = False