"""
Status Emitter - handles status updates and callbacks for workflow stages.
"""

import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from ..task import WorkflowStage

logger = logging.getLogger("mercury.agents.orchestration.status_emitter")


class StatusEmitter:
    """Handles status updates and callbacks for workflow stages."""
    
    def __init__(self, status_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Initialize status emitter.
        
        Args:
            status_callback: Optional callback function for status updates
        """
        self.status_callback: Optional[Callable[[Dict[str, Any]], None]] = status_callback
        self.current_stage = WorkflowStage.PLANNING
    
    def set_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Set callback for status updates.
        
        Args:
            callback: Function that takes a status dict and returns None
        """
        self.status_callback = callback
    
    def emit_status(
        self,
        stage: WorkflowStage,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Emit status update to UI.
        
        Args:
            stage: The workflow stage
            message: Status message
            details: Optional details dictionary
        """
        self.current_stage = stage
        # Safely log message - escape any curly braces that might be interpreted as format placeholders
        # Use % formatting to avoid issues with f-strings and user content
        safe_message = str(message).replace("{", "{{").replace("}", "}}") if message else ""
        logger.info("[STATUS] %s - %s", stage.value, message)
        
        if self.status_callback:
            status_update = {
                "type": "workflow_status",
                "stage": stage.value,
                "message": message,  # Keep original message for callback
                "details": details or {},
                "timestamp": datetime.now().isoformat()
            }
            try:
                self.status_callback(status_update)
            except Exception as e:
                logger.error("Status callback error: %s", str(e), exc_info=True)
        else:
            logger.debug("No status callback set - status updates will not be sent")
    
    def transition_to_stage(
        self,
        stage: WorkflowStage,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Transition to a workflow stage and emit status.
        
        Always sets stage before emitting status to ensure consistency.
        
        Args:
            stage: The workflow stage to transition to
            message: Status message
            details: Optional details dictionary
        """
        self.current_stage = stage
        self.emit_status(stage, message, details)

