"""
Checkpoint management for workflow state persistence.

Handles saving and restoring workflow state at safe checkpoints.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import threading
import hashlib

logger = logging.getLogger("mercury.agents.task_management.checkpoint")


class CheckpointManager:
    """
    Manages checkpoint creation, storage, and restoration.
    
    Provides persistent state management for workflows, enabling
    pause and resume functionality.
    """
    
    def __init__(
        self,
        storage_dir: str = "backend/task_checkpoints",
        max_checkpoints: int = 10,
        enable_compression: bool = False
    ):
        """
        Initialize checkpoint manager.
        
        Args:
            storage_dir: Directory for checkpoint storage
            max_checkpoints: Maximum checkpoints to keep per workflow
            enable_compression: Whether to compress checkpoint data
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_checkpoints = max_checkpoints
        self.enable_compression = enable_compression
        
        # In-memory cache for recent checkpoints
        self._checkpoint_cache: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._main_lock = threading.Lock()
    
    def _get_lock(self, workflow_id: str) -> threading.Lock:
        """Get or create a lock for a workflow."""
        with self._main_lock:
            if workflow_id not in self._locks:
                self._locks[workflow_id] = threading.Lock()
            return self._locks[workflow_id]
    
    def _get_checkpoint_dir(self, workflow_id: str) -> Path:
        """Get checkpoint directory for a workflow."""
        checkpoint_dir = self.storage_dir / workflow_id / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return checkpoint_dir
    
    def _generate_checkpoint_id(self, workflow_id: str) -> str:
        """Generate unique checkpoint ID."""
        timestamp = datetime.now().isoformat()
        data = f"{workflow_id}_{timestamp}"
        hash_obj = hashlib.md5(data.encode())
        return f"cp_{hash_obj.hexdigest()[:12]}"
    
    def create_checkpoint(
        self,
        workflow_id: str,
        state_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Create a checkpoint for workflow state.
        
        Args:
            workflow_id: Workflow identifier
            state_data: State data to checkpoint (includes plan, tasks, etc.)
            
        Returns:
            Checkpoint ID if successful, None otherwise
        """
        try:
            lock = self._get_lock(workflow_id)
            
            with lock:
                checkpoint_id = self._generate_checkpoint_id(workflow_id)
                
                # Add checkpoint metadata
                checkpoint_data = {
                    "checkpoint_id": checkpoint_id,
                    "workflow_id": workflow_id,
                    "timestamp": datetime.now().isoformat(),
                    "state": state_data
                }
                
                # Validate checkpoint data
                if not self._validate_checkpoint(checkpoint_data):
                    logger.error("Checkpoint validation failed")
                    return None
                
                # Save to disk
                checkpoint_file = self._get_checkpoint_dir(workflow_id) / f"{checkpoint_id}.json"
                with open(checkpoint_file, 'w') as f:
                    json.dump(checkpoint_data, f, indent=2)
                
                # Update latest checkpoint link
                latest_file = self._get_checkpoint_dir(workflow_id) / "latest.json"
                with open(latest_file, 'w') as f:
                    json.dump(checkpoint_data, f, indent=2)
                
                # Cache checkpoint
                cache_key = f"{workflow_id}_{checkpoint_id}"
                self._checkpoint_cache[cache_key] = checkpoint_data
                
                # Cleanup old checkpoints
                self._cleanup_old_checkpoints(workflow_id)
                
                logger.info(f"Created checkpoint {checkpoint_id} for workflow {workflow_id}")
                return checkpoint_id
                
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}", exc_info=True)
            return None
    
    def restore_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Restore workflow state from checkpoint.
        
        Args:
            workflow_id: Workflow identifier
            checkpoint_id: Optional specific checkpoint ID (uses latest if None)
            
        Returns:
            Restored state data, or None if not found
        """
        try:
            lock = self._get_lock(workflow_id)
            
            with lock:
                # Check cache first
                if checkpoint_id:
                    cache_key = f"{workflow_id}_{checkpoint_id}"
                    if cache_key in self._checkpoint_cache:
                        logger.debug(f"Restored checkpoint from cache: {checkpoint_id}")
                        return self._checkpoint_cache[cache_key]["state"]
                
                # Load from disk
                if checkpoint_id:
                    checkpoint_file = self._get_checkpoint_dir(workflow_id) / f"{checkpoint_id}.json"
                else:
                    # Use latest checkpoint
                    checkpoint_file = self._get_checkpoint_dir(workflow_id) / "latest.json"
                
                if not checkpoint_file.exists():
                    logger.warning(f"Checkpoint file not found: {checkpoint_file}")
                    return None
                
                with open(checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)
                
                # Validate checkpoint
                if not self._validate_checkpoint(checkpoint_data):
                    logger.error("Restored checkpoint failed validation")
                    return None
                
                # Update cache
                cache_key = f"{workflow_id}_{checkpoint_data['checkpoint_id']}"
                self._checkpoint_cache[cache_key] = checkpoint_data
                
                logger.info(
                    f"Restored checkpoint {checkpoint_data['checkpoint_id']} "
                    f"for workflow {workflow_id}"
                )
                return checkpoint_data["state"]
                
        except Exception as e:
            logger.error(f"Failed to restore checkpoint: {e}", exc_info=True)
            return None
    
    def list_checkpoints(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        List all checkpoints for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            List of checkpoint metadata
        """
        try:
            checkpoint_dir = self._get_checkpoint_dir(workflow_id)
            checkpoints = []
            
            for checkpoint_file in sorted(checkpoint_dir.glob("cp_*.json")):
                try:
                    with open(checkpoint_file, 'r') as f:
                        data = json.load(f)
                        checkpoints.append({
                            "checkpoint_id": data["checkpoint_id"],
                            "timestamp": data["timestamp"],
                            "size_bytes": checkpoint_file.stat().st_size
                        })
                except Exception as e:
                    logger.warning(f"Failed to read checkpoint {checkpoint_file}: {e}")
                    continue
            
            return checkpoints
            
        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}", exc_info=True)
            return []
    
    def delete_checkpoint(self, workflow_id: str, checkpoint_id: str) -> bool:
        """
        Delete a specific checkpoint.
        
        Args:
            workflow_id: Workflow identifier
            checkpoint_id: Checkpoint to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            lock = self._get_lock(workflow_id)
            
            with lock:
                checkpoint_file = self._get_checkpoint_dir(workflow_id) / f"{checkpoint_id}.json"
                if checkpoint_file.exists():
                    checkpoint_file.unlink()
                    
                    # Remove from cache
                    cache_key = f"{workflow_id}_{checkpoint_id}"
                    if cache_key in self._checkpoint_cache:
                        del self._checkpoint_cache[cache_key]
                    
                    logger.info(f"Deleted checkpoint {checkpoint_id}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete checkpoint: {e}", exc_info=True)
            return False
    
    def _validate_checkpoint(self, checkpoint_data: Dict[str, Any]) -> bool:
        """
        Validate checkpoint data structure.
        
        Args:
            checkpoint_data: Checkpoint data to validate
            
        Returns:
            True if valid
        """
        required_fields = ["checkpoint_id", "workflow_id", "timestamp", "state"]
        
        for field in required_fields:
            if field not in checkpoint_data:
                logger.error(f"Missing required field in checkpoint: {field}")
                return False
        
        # Validate state data has minimum required fields
        state = checkpoint_data.get("state", {})
        if not isinstance(state, dict):
            logger.error("Checkpoint state must be a dictionary")
            return False
        
        return True
    
    def _cleanup_old_checkpoints(self, workflow_id: str) -> None:
        """
        Remove old checkpoints beyond max limit.
        
        Args:
            workflow_id: Workflow identifier
        """
        try:
            checkpoints = self.list_checkpoints(workflow_id)
            
            if len(checkpoints) > self.max_checkpoints:
                # Sort by timestamp and keep only the newest
                checkpoints.sort(key=lambda x: x["timestamp"])
                to_remove = checkpoints[:-self.max_checkpoints]
                
                for checkpoint in to_remove:
                    self.delete_checkpoint(workflow_id, checkpoint["checkpoint_id"])
                    logger.debug(f"Cleaned up old checkpoint: {checkpoint['checkpoint_id']}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old checkpoints: {e}", exc_info=True)
    
    def cleanup_workflow(self, workflow_id: str) -> bool:
        """
        Remove all checkpoints for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if successful
        """
        try:
            lock = self._get_lock(workflow_id)
            
            with lock:
                workflow_dir = self.storage_dir / workflow_id
                if workflow_dir.exists():
                    import shutil
                    shutil.rmtree(workflow_dir)
                    logger.info(f"Cleaned up workflow directory: {workflow_id}")
                
                # Clear from cache
                keys_to_remove = [k for k in self._checkpoint_cache.keys() if k.startswith(workflow_id)]
                for key in keys_to_remove:
                    del self._checkpoint_cache[key]
                
                # Remove lock
                if workflow_id in self._locks:
                    del self._locks[workflow_id]
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to cleanup workflow: {e}", exc_info=True)
            return False
    
    def get_checkpoint_size(self, workflow_id: str, checkpoint_id: str) -> int:
        """
        Get size of a checkpoint in bytes.
        
        Args:
            workflow_id: Workflow identifier
            checkpoint_id: Checkpoint identifier
            
        Returns:
            Size in bytes, or 0 if not found
        """
        try:
            checkpoint_file = self._get_checkpoint_dir(workflow_id) / f"{checkpoint_id}.json"
            if checkpoint_file.exists():
                return checkpoint_file.stat().st_size
            return 0
        except Exception as e:
            logger.error(f"Failed to get checkpoint size: {e}")
            return 0