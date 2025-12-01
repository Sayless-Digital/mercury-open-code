"""
User feedback and status indicators for task management.

Provides user-friendly status messages and confirmation dialogs.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum

from .task_manager import WorkflowState
from .resume_queue import ResumePriority

logger = logging.getLogger("mercury.agents.task_management.ui_feedback")


class StatusIndicator(Enum):
    """Visual status indicators."""
    RUNNING = "⏳"
    PAUSED = "⏸️"
    CANCELLING = "🛑"
    CANCELLED = "❌"
    COMPLETED = "✅"
    FAILED = "⚠️"
    QUEUED = "📋"
    TIMEOUT = "⏰"


class UIFeedback:
    """
    User feedback and status indicator generator.
    
    Provides clear, user-friendly status messages and confirmation
    dialogs for all task management operations.
    """
    
    @staticmethod
    def get_status_message(workflow_status: Dict[str, Any]) -> str:
        """
        Generate user-friendly status message.
        
        Args:
            workflow_status: Workflow status dictionary
            
        Returns:
            Formatted status message
        """
        state = workflow_status.get("state", "unknown")
        workflow_id = workflow_status.get("workflow_id", "unknown")
        
        if state == WorkflowState.RUNNING.value:
            progress = workflow_status.get("plan_progress", {})
            total = progress.get("total", 0)
            completed = progress.get("completed", 0)
            in_progress = progress.get("in_progress", 0)
            
            if total > 0:
                return (
                    f"{StatusIndicator.RUNNING.value} Executing task "
                    f"{completed + in_progress}/{total}..."
                )
            return f"{StatusIndicator.RUNNING.value} Workflow is running..."
        
        elif state == WorkflowState.PAUSED.value:
            queue_pos = workflow_status.get("resume_queue_position")
            if queue_pos is not None:
                return (
                    f"{StatusIndicator.PAUSED.value} Workflow paused "
                    f"(resume queue position: {queue_pos + 1})"
                )
            return f"{StatusIndicator.PAUSED.value} Workflow paused"
        
        elif state == WorkflowState.CANCELLING.value:
            return f"{StatusIndicator.CANCELLING.value} Cancelling workflow, cleaning up..."
        
        elif state == WorkflowState.CANCELLED.value:
            reason = workflow_status.get("cancellation_reason", "User requested")
            return f"{StatusIndicator.CANCELLED.value} Workflow cancelled: {reason}"
        
        elif state == WorkflowState.COMPLETED.value:
            return f"{StatusIndicator.COMPLETED.value} All tasks completed successfully!"
        
        elif state == WorkflowState.FAILED.value:
            return f"{StatusIndicator.FAILED.value} Workflow failed"
        
        else:
            return f"Workflow status: {state}"
    
    @staticmethod
    def get_progress_message(workflow_status: Dict[str, Any]) -> Optional[str]:
        """
        Generate progress message with details.
        
        Args:
            workflow_status: Workflow status dictionary
            
        Returns:
            Progress message or None
        """
        progress = workflow_status.get("plan_progress")
        if not progress:
            return None
        
        total = progress.get("total", 0)
        completed = progress.get("completed", 0)
        failed = progress.get("failed", 0)
        pending = progress.get("pending", 0)
        
        if total == 0:
            return None
        
        percentage = (completed / total) * 100
        
        parts = [
            f"Progress: {completed}/{total} tasks ({percentage:.0f}%)"
        ]
        
        if failed > 0:
            parts.append(f"{failed} failed")
        
        if pending > 0:
            parts.append(f"{pending} pending")
        
        return " | ".join(parts)
    
    @staticmethod
    def get_resource_summary(workflow_status: Dict[str, Any]) -> Optional[str]:
        """
        Generate resource summary message.
        
        Args:
            workflow_status: Workflow status dictionary
            
        Returns:
            Resource summary or None
        """
        resources = workflow_status.get("resources")
        if not resources:
            return None
        
        total = resources.get("total", 0)
        if total == 0:
            return None
        
        by_type = resources.get("by_type", {})
        cleaned_up = resources.get("cleaned_up", 0)
        
        parts = [f"{total} resources tracked"]
        
        if by_type:
            type_summary = ", ".join(
                f"{count} {rtype}" for rtype, count in by_type.items()
            )
            parts.append(f"({type_summary})")
        
        if cleaned_up > 0:
            parts.append(f"{cleaned_up} cleaned up")
        
        return " | ".join(parts)
    
    @staticmethod
    def get_time_summary(workflow_status: Dict[str, Any]) -> Optional[str]:
        """
        Generate time summary message.
        
        Args:
            workflow_status: Workflow status dictionary
            
        Returns:
            Time summary or None
        """
        started_at = workflow_status.get("started_at")
        completed_at = workflow_status.get("completed_at")
        
        if not started_at:
            return None
        
        try:
            start_time = datetime.fromisoformat(started_at)
            
            if completed_at:
                end_time = datetime.fromisoformat(completed_at)
                duration = end_time - start_time
            else:
                duration = datetime.now() - start_time
            
            # Format duration
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f"Duration: {hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"Duration: {minutes}m {seconds}s"
            else:
                return f"Duration: {seconds}s"
                
        except Exception as e:
            logger.debug(f"Failed to parse time: {e}")
            return None
    
    @staticmethod
    def format_comprehensive_status(workflow_status: Dict[str, Any]) -> str:
        """
        Generate comprehensive formatted status.
        
        Args:
            workflow_status: Workflow status dictionary
            
        Returns:
            Multi-line formatted status
        """
        lines = []
        
        # Main status
        lines.append(UIFeedback.get_status_message(workflow_status))
        
        # Progress
        progress_msg = UIFeedback.get_progress_message(workflow_status)
        if progress_msg:
            lines.append(progress_msg)
        
        # Time summary
        time_msg = UIFeedback.get_time_summary(workflow_status)
        if time_msg:
            lines.append(time_msg)
        
        # Resources
        resource_msg = UIFeedback.get_resource_summary(workflow_status)
        if resource_msg:
            lines.append(resource_msg)
        
        return "\n".join(lines)
    
    @staticmethod
    def get_confirmation_dialog(
        action: str,
        workflow_id: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate confirmation dialog data.
        
        Args:
            action: Action being confirmed (cancel, pause, resume)
            workflow_id: Workflow identifier
            details: Optional additional details
            
        Returns:
            Confirmation dialog data
        """
        dialogs = {
            "cancel": {
                "title": "Cancel Workflow?",
                "message": (
                    "This will stop all running tasks and clean up resources. "
                    "This action cannot be undone."
                ),
                "confirm_text": "Cancel Workflow",
                "cancel_text": "Keep Running",
                "variant": "danger"
            },
            "pause": {
                "title": "Pause Workflow?",
                "message": (
                    "The workflow will be paused at the next safe checkpoint. "
                    "You can resume it later from this point."
                ),
                "confirm_text": "Pause",
                "cancel_text": "Keep Running",
                "variant": "warning"
            },
            "resume": {
                "title": "Resume Workflow?",
                "message": (
                    "The workflow will resume from the last checkpoint. "
                    "Previously completed tasks will not be re-executed."
                ),
                "confirm_text": "Resume",
                "cancel_text": "Cancel",
                "variant": "primary"
            },
            "timeout": {
                "title": "Task Taking Too Long",
                "message": (
                    "This task is taking longer than expected. "
                    "Would you like to cancel or continue waiting?"
                ),
                "confirm_text": "Cancel Task",
                "cancel_text": "Keep Waiting",
                "variant": "warning"
            }
        }
        
        dialog = dialogs.get(action, {
            "title": f"{action.capitalize()} Workflow?",
            "message": f"Are you sure you want to {action} this workflow?",
            "confirm_text": action.capitalize(),
            "cancel_text": "Cancel",
            "variant": "primary"
        })
        
        dialog["workflow_id"] = workflow_id
        if details:
            dialog["details"] = details
        
        return dialog
    
    @staticmethod
    def get_notification(
        event_type: str,
        workflow_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate notification data for events.
        
        Args:
            event_type: Type of event
            workflow_id: Workflow identifier
            data: Optional event data
            
        Returns:
            Notification data
        """
        notifications = {
            "workflow_started": {
                "title": "Workflow Started",
                "message": "Workflow execution has begun",
                "type": "info"
            },
            "workflow_completed": {
                "title": "Workflow Completed",
                "message": "All tasks completed successfully",
                "type": "success"
            },
            "workflow_failed": {
                "title": "Workflow Failed",
                "message": "Workflow execution failed",
                "type": "error"
            },
            "workflow_cancelled": {
                "title": "Workflow Cancelled",
                "message": "Workflow was cancelled",
                "type": "warning"
            },
            "workflow_paused": {
                "title": "Workflow Paused",
                "message": "Workflow paused at checkpoint",
                "type": "info"
            },
            "workflow_resumed": {
                "title": "Workflow Resumed",
                "message": "Workflow execution resumed",
                "type": "info"
            },
            "task_timeout": {
                "title": "Task Timeout",
                "message": "A task is taking longer than expected",
                "type": "warning"
            },
            "checkpoint_created": {
                "title": "Checkpoint Created",
                "message": "Workflow state saved",
                "type": "info"
            }
        }
        
        notification = notifications.get(event_type, {
            "title": event_type.replace("_", " ").title(),
            "message": f"Event: {event_type}",
            "type": "info"
        })
        
        notification["workflow_id"] = workflow_id
        notification["timestamp"] = datetime.now().isoformat()
        
        if data:
            notification["data"] = data
        
        return notification
    
    @staticmethod
    def format_queue_status(queue_status: Dict[str, Any]) -> str:
        """
        Format resume queue status.
        
        Args:
            queue_status: Queue status dictionary
            
        Returns:
            Formatted queue status
        """
        queue_size = queue_status.get("queue_size", 0)
        in_progress = queue_status.get("in_progress", 0)
        max_concurrent = queue_status.get("max_concurrent", 0)
        
        if queue_size == 0 and in_progress == 0:
            return "Resume queue is empty"
        
        parts = []
        
        if in_progress > 0:
            parts.append(f"{in_progress} resuming")
        
        if queue_size > 0:
            parts.append(f"{queue_size} queued")
        
        status = " | ".join(parts)
        
        if in_progress >= max_concurrent:
            status += f" (at capacity: {max_concurrent})"
        
        return f"{StatusIndicator.QUEUED.value} {status}"