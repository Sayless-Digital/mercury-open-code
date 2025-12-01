"""
Audit logging system for task management.

Provides comprehensive logging of all workflow events, state transitions,
and user actions for debugging and compliance.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import threading

logger = logging.getLogger("mercury.agents.task_management.audit_logger")


class AuditLogger:
    """
    Comprehensive audit logging for workflow lifecycle.
    
    Logs all state transitions, cancellations, errors, and user actions
    in a structured format for debugging and compliance.
    """
    
    def __init__(self, log_dir: str = "backend/task_checkpoints"):
        """
        Initialize audit logger.
        
        Args:
            log_dir: Directory for audit logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._locks: Dict[str, threading.Lock] = {}
        self._main_lock = threading.Lock()
    
    def _get_lock(self, workflow_id: str) -> threading.Lock:
        """Get or create a lock for a workflow."""
        with self._main_lock:
            if workflow_id not in self._locks:
                self._locks[workflow_id] = threading.Lock()
            return self._locks[workflow_id]
    
    def _get_log_file(self, workflow_id: str) -> Path:
        """Get audit log file path for workflow."""
        workflow_dir = self.log_dir / workflow_id
        workflow_dir.mkdir(parents=True, exist_ok=True)
        return workflow_dir / "audit_log.jsonl"
    
    def log_event(
        self,
        workflow_id: str,
        event_type: str,
        data: Dict[str, Any],
        task_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """
        Log a workflow event.
        
        Args:
            workflow_id: Workflow identifier
            event_type: Type of event (state_change, cancellation, error, etc.)
            data: Event data
            task_id: Optional task ID
            user_id: Optional user ID
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "workflow_id": workflow_id,
                "task_id": task_id,
                "event_type": event_type,
                "user_id": user_id,
                "data": data
            }
            
            log_file = self._get_log_file(workflow_id)
            lock = self._get_lock(workflow_id)
            
            with lock:
                with open(log_file, 'a') as f:
                    f.write(json.dumps(log_entry) + '\n')
            
            logger.debug(f"Logged event: {event_type} for workflow {workflow_id}")
            
        except Exception as e:
            logger.error(f"Failed to log event: {e}", exc_info=True)
    
    def log_state_change(
        self,
        workflow_id: str,
        task_id: str,
        from_state: str,
        to_state: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a state transition.
        
        Args:
            workflow_id: Workflow identifier
            task_id: Task identifier
            from_state: Previous state
            to_state: New state
            reason: Reason for transition
            metadata: Additional metadata
        """
        data = {
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "metadata": metadata or {}
        }
        self.log_event(workflow_id, "state_change", data, task_id=task_id)
    
    def log_error(
        self,
        workflow_id: str,
        error: Exception,
        task_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an error.
        
        Args:
            workflow_id: Workflow identifier
            error: Exception that occurred
            task_id: Optional task ID
            context: Additional context
        """
        data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        self.log_event(workflow_id, "error", data, task_id=task_id)
    
    def log_cancellation(
        self,
        workflow_id: str,
        reason: str,
        cancelled_by: Optional[str] = None
    ) -> None:
        """
        Log a cancellation request.
        
        Args:
            workflow_id: Workflow identifier
            reason: Cancellation reason
            cancelled_by: User who cancelled
        """
        data = {
            "reason": reason,
            "cancelled_by": cancelled_by
        }
        self.log_event(workflow_id, "cancellation", data, user_id=cancelled_by)
    
    def log_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
        checkpoint_size: int
    ) -> None:
        """
        Log checkpoint creation.
        
        Args:
            workflow_id: Workflow identifier
            checkpoint_id: Checkpoint identifier
            checkpoint_size: Size in bytes
        """
        data = {
            "checkpoint_id": checkpoint_id,
            "size_bytes": checkpoint_size
        }
        self.log_event(workflow_id, "checkpoint_created", data)
    
    def log_resume(
        self,
        workflow_id: str,
        checkpoint_id: str,
        resumed_by: Optional[str] = None
    ) -> None:
        """
        Log workflow resume.
        
        Args:
            workflow_id: Workflow identifier
            checkpoint_id: Checkpoint being resumed from
            resumed_by: User who resumed
        """
        data = {
            "checkpoint_id": checkpoint_id,
            "resumed_by": resumed_by
        }
        self.log_event(workflow_id, "resume", data, user_id=resumed_by)
    
    def get_audit_trail(
        self,
        workflow_id: str,
        event_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            event_type: Optional filter by event type
            limit: Optional limit on number of entries
            
        Returns:
            List of audit log entries
        """
        try:
            log_file = self._get_log_file(workflow_id)
            if not log_file.exists():
                return []
            
            entries = []
            lock = self._get_lock(workflow_id)
            
            with lock:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            if event_type is None or entry.get("event_type") == event_type:
                                entries.append(entry)
                        except json.JSONDecodeError:
                            continue
            
            # Apply limit if specified
            if limit:
                entries = entries[-limit:]
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit trail: {e}", exc_info=True)
            return []
    
    def export_logs(
        self,
        workflow_id: str,
        output_path: str,
        format: str = "json"
    ) -> bool:
        """
        Export audit logs to file.
        
        Args:
            workflow_id: Workflow identifier
            output_path: Output file path
            format: Export format (json or csv)
            
        Returns:
            Success status
        """
        try:
            entries = self.get_audit_trail(workflow_id)
            
            if format == "json":
                with open(output_path, 'w') as f:
                    json.dump(entries, f, indent=2)
            elif format == "csv":
                import csv
                if entries:
                    keys = entries[0].keys()
                    with open(output_path, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=keys)
                        writer.writeheader()
                        writer.writerows(entries)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Exported audit logs to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export logs: {e}", exc_info=True)
            return False
    
    def cleanup_old_logs(self, days: int = 30) -> int:
        """
        Remove audit logs older than specified days.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of log files removed
        """
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
            removed_count = 0
            
            for workflow_dir in self.log_dir.iterdir():
                if not workflow_dir.is_dir():
                    continue
                
                log_file = workflow_dir / "audit_log.jsonl"
                if log_file.exists():
                    if log_file.stat().st_mtime < cutoff_time:
                        log_file.unlink()
                        removed_count += 1
                        logger.info(f"Removed old audit log: {log_file}")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}", exc_info=True)
            return 0