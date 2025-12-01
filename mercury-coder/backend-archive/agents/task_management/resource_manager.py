"""
Resource management for workflow tasks.

Tracks and cleans up resources allocated during task execution.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime
import threading

logger = logging.getLogger("mercury.agents.task_management.resource_manager")


class ResourceType:
    """Resource type constants."""
    FILE = "file"
    CONNECTION = "connection"
    PROCESS = "process"
    MEMORY = "memory"
    TEMPORARY = "temporary"
    OTHER = "other"


class Resource:
    """Represents a tracked resource."""
    
    def __init__(
        self,
        resource_id: str,
        resource_type: str,
        cleanup_handler: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.cleanup_handler = cleanup_handler
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.cleaned_up = False


class ResourceManager:
    """
    Manages workflow resources and cleanup handlers.
    
    Tracks resources allocated during workflow execution and ensures
    proper cleanup on cancellation or completion.
    """
    
    def __init__(self):
        """Initialize resource manager."""
        self._resources: Dict[str, Dict[str, Resource]] = {}  # workflow_id -> {resource_id -> Resource}
        self._cleanup_handlers: Dict[str, Dict[str, Callable]] = {}  # workflow_id -> {task_id -> handler}
        self._locks: Dict[str, threading.Lock] = {}
        self._main_lock = threading.Lock()
    
    def _get_lock(self, workflow_id: str) -> threading.Lock:
        """Get or create a lock for a workflow."""
        with self._main_lock:
            if workflow_id not in self._locks:
                self._locks[workflow_id] = threading.Lock()
            return self._locks[workflow_id]
    
    def register_resource(
        self,
        workflow_id: str,
        resource_id: str,
        resource_type: str,
        cleanup_handler: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a resource for tracking.
        
        Args:
            workflow_id: Workflow identifier
            resource_id: Resource identifier
            resource_type: Type of resource
            cleanup_handler: Optional cleanup function
            metadata: Additional metadata
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id not in self._resources:
                self._resources[workflow_id] = {}
            
            resource = Resource(
                resource_id=resource_id,
                resource_type=resource_type,
                cleanup_handler=cleanup_handler,
                metadata=metadata
            )
            
            self._resources[workflow_id][resource_id] = resource
            
            logger.debug(
                f"Registered resource: workflow={workflow_id}, "
                f"resource={resource_id}, type={resource_type}"
            )
    
    def register_cleanup(
        self,
        workflow_id: str,
        task_id: str,
        handler: Callable
    ) -> None:
        """
        Register a cleanup handler for a task.
        
        Args:
            workflow_id: Workflow identifier
            task_id: Task identifier
            handler: Cleanup function
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id not in self._cleanup_handlers:
                self._cleanup_handlers[workflow_id] = {}
            
            self._cleanup_handlers[workflow_id][task_id] = handler
            
            logger.debug(f"Registered cleanup handler for task {task_id}")
    
    async def cleanup_task(
        self,
        workflow_id: str,
        task_id: str
    ) -> bool:
        """
        Execute cleanup for a specific task.
        
        Args:
            workflow_id: Workflow identifier
            task_id: Task identifier
            
        Returns:
            True if cleanup succeeded
        """
        lock = self._get_lock(workflow_id)
        
        try:
            with lock:
                if workflow_id not in self._cleanup_handlers:
                    logger.debug(f"No cleanup handlers for workflow {workflow_id}")
                    return True
                
                handlers = self._cleanup_handlers[workflow_id]
                
                if task_id not in handlers:
                    logger.debug(f"No cleanup handler for task {task_id}")
                    return True
                
                handler = handlers[task_id]
            
            # Execute handler outside lock to avoid blocking
            logger.info(f"Executing cleanup for task {task_id}")
            await self._execute_handler(handler)
            
            with lock:
                del handlers[task_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Task cleanup failed for {task_id}: {e}", exc_info=True)
            return False
    
    async def cleanup_workflow(self, workflow_id: str) -> bool:
        """
        Execute cleanup for entire workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if all cleanups succeeded
        """
        success = True
        
        try:
            # Cleanup all task handlers
            lock = self._get_lock(workflow_id)
            
            with lock:
                handlers = self._cleanup_handlers.get(workflow_id, {}).copy()
            
            for task_id, handler in handlers.items():
                try:
                    logger.info(f"Cleaning up task {task_id}")
                    await self._execute_handler(handler)
                except Exception as e:
                    logger.error(f"Cleanup failed for task {task_id}: {e}")
                    success = False
            
            # Cleanup all tracked resources
            with lock:
                resources = self._resources.get(workflow_id, {}).copy()
            
            for resource_id, resource in resources.items():
                try:
                    if not resource.cleaned_up and resource.cleanup_handler:
                        logger.info(f"Cleaning up resource {resource_id}")
                        await self._execute_handler(resource.cleanup_handler)
                        resource.cleaned_up = True
                except Exception as e:
                    logger.error(f"Resource cleanup failed for {resource_id}: {e}")
                    success = False
            
            # Clear workflow data
            with lock:
                if workflow_id in self._cleanup_handlers:
                    del self._cleanup_handlers[workflow_id]
                if workflow_id in self._resources:
                    del self._resources[workflow_id]
                if workflow_id in self._locks:
                    del self._locks[workflow_id]
            
            logger.info(f"Workflow cleanup completed: {workflow_id} (success={success})")
            return success
            
        except Exception as e:
            logger.error(f"Workflow cleanup failed: {e}", exc_info=True)
            return False
    
    async def _execute_handler(self, handler: Callable) -> None:
        """Execute a cleanup handler (sync or async)."""
        if asyncio.iscoroutinefunction(handler):
            await handler()
        else:
            # Run sync handler in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, handler)
    
    def get_resources(
        self,
        workflow_id: str,
        resource_type: Optional[str] = None
    ) -> List[Resource]:
        """
        Get tracked resources for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            resource_type: Optional filter by type
            
        Returns:
            List of resources
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id not in self._resources:
                return []
            
            resources = list(self._resources[workflow_id].values())
            
            if resource_type:
                resources = [r for r in resources if r.resource_type == resource_type]
            
            return resources
    
    def has_resources(self, workflow_id: str) -> bool:
        """
        Check if workflow has tracked resources.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if resources exist
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            return workflow_id in self._resources and bool(self._resources[workflow_id])
    
    def unregister_resource(self, workflow_id: str, resource_id: str) -> bool:
        """
        Unregister a resource (already cleaned up).
        
        Args:
            workflow_id: Workflow identifier
            resource_id: Resource identifier
            
        Returns:
            True if unregistered
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id in self._resources:
                if resource_id in self._resources[workflow_id]:
                    del self._resources[workflow_id][resource_id]
                    logger.debug(f"Unregistered resource {resource_id}")
                    return True
            
            return False
    
    def get_resource_summary(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get summary of resources for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Resource summary
        """
        lock = self._get_lock(workflow_id)
        
        with lock:
            if workflow_id not in self._resources:
                return {"total": 0, "by_type": {}}
            
            resources = self._resources[workflow_id].values()
            by_type: Dict[str, int] = {}
            
            for resource in resources:
                by_type[resource.resource_type] = by_type.get(resource.resource_type, 0) + 1
            
            return {
                "total": len(resources),
                "by_type": by_type,
                "cleaned_up": sum(1 for r in resources if r.cleaned_up)
            }