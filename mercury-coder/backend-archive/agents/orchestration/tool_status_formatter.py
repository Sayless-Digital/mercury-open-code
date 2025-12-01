"""
Tool Status Formatter - formats tool execution events into user-friendly messages.
"""

import logging
from typing import Dict, Any, Optional

from ..utils.path_utils import get_file_name
from ..task import WorkflowStage

logger = logging.getLogger("mercury.agents.orchestration.tool_status_formatter")


class ToolStatusFormatter:
    """
    Formats tool execution events into user-friendly status messages.
    
    Uses a mapping dictionary to avoid hard-coded tool name checks.
    """
    
    # Tool message templates: {tool_name: {status: template}}
    # Template can be a string or a callable that takes (tool_input, file_name) -> str
    TOOL_MESSAGES = {
        "read_file": {
            "executing": lambda tool_input, file_name: f"Reading file: {file_name or tool_input.get('file_path') or '...'}",
            "completed": lambda tool_input, file_name: f"Read file: {file_name or tool_input.get('file_path') or 'file'}"
        },
        "write_file": {
            "executing": lambda tool_input, file_name: f"Writing file: {file_name or tool_input.get('file_path') or '...'}",
            "completed": lambda tool_input, file_name: f"Wrote file: {file_name or tool_input.get('file_path') or 'file'}"
        },
        "edit_file": {
            "executing": lambda tool_input, file_name: f"Editing file: {file_name or tool_input.get('file_path') or '...'}",
            "completed": lambda tool_input, file_name: f"Edited file: {file_name or tool_input.get('file_path') or 'file'}"
        },
        "read_directory_tree": {
            "executing": lambda tool_input, file_name: f"Reading directory and finding files: {file_name or tool_input.get('directory_path') or tool_input.get('path', '...')}",
            "completed": lambda tool_input, file_name: f"Explored directory: {file_name or tool_input.get('directory_path') or tool_input.get('path', '...')}"
        },
        "list_directory": {
            "executing": lambda tool_input, file_name: f"Listing files: {file_name or tool_input.get('directory_path') or tool_input.get('path', '...')}",
            "completed": lambda tool_input, file_name: (
                f"Listed: {file_name}" if file_name 
                else f"Listed: {tool_input.get('directory_path') or tool_input.get('path', 'directory')}"
            )
        },
        "codebase_search": {
            "executing": lambda tool_input, file_name: (
                f"Searching codebase: {tool_input.get('query', '...')[:50]}{'...' if len(tool_input.get('query', '')) > 50 else ''}"
                if tool_input.get('query') and tool_input.get('query') != "..."
                else "Searching codebase..."
            ),
            "completed": "Search completed"
        },
        "grep": {
            "executing": lambda tool_input, file_name: (
                f"Finding matches: {tool_input.get('pattern', '...')[:30]}"
                if tool_input.get('pattern') and tool_input.get('pattern') != "..."
                else "Searching files..."
            ),
            "completed": "Search completed"
        },
        "get_file_dependencies": {
            "executing": lambda tool_input, file_name: f"Reading file and finding all dependencies: {file_name or tool_input.get('file_path', '...')}",
            "completed": lambda tool_input, file_name: f"Found dependencies: {file_name or tool_input.get('file_path', 'file')}"
        },
        "find_related_files": {
            "executing": lambda tool_input, file_name: f"Reading file and finding all relations: {file_name or tool_input.get('file_path', '...')}",
            "completed": lambda tool_input, file_name: f"Found related files: {file_name or tool_input.get('file_path', 'file')}"
        },
        "get_component_boundaries": {
            "executing": lambda tool_input, file_name: f"Analyzing components: {file_name or tool_input.get('file_path', '...')}",
            "completed": lambda tool_input, file_name: f"Analyzed components: {file_name or tool_input.get('file_path', 'file')}"
        },
        "find_similar_patterns": {
            "executing": "Finding similar patterns...",
            "completed": "Pattern search completed"
        },
        "create_directory": {
            "executing": lambda tool_input, file_name: f"Creating directory: {file_name or tool_input.get('directory_path') or tool_input.get('path', '...')}",
            "completed": lambda tool_input, file_name: (
                f"Created directory: {file_name}" if file_name
                else f"Created directory: {tool_input.get('directory_path') or tool_input.get('path', 'directory')}"
            )
        }
    }
    
    @classmethod
    def format_message(
        cls,
        tool_name: str,
        tool_status: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """
        Format a tool execution event into a user-friendly message.
        
        Args:
            tool_name: Name of the tool
            tool_status: Status ("executing" or "completed")
            tool_input: Tool input dictionary
            
        Returns:
            Formatted message string
        """
        # Extract file name for better display
        file_path = tool_input.get('file_path') or tool_input.get('path')
        file_name = get_file_name(file_path) if file_path else None
        
        # For directory operations, also check directory_path
        if not file_name and (tool_name in ["read_directory_tree", "list_directory", "create_directory"]):
            dir_path = tool_input.get('directory_path') or tool_input.get('path', '...')
            file_name = get_file_name(dir_path) if dir_path != "..." else None
        
        # Get message template for this tool and status
        tool_config = cls.TOOL_MESSAGES.get(tool_name, {})
        template = tool_config.get(tool_status)
        
        if template is None:
            # Fallback message
            if tool_status == "executing":
                return f"Using {tool_name}..."
            else:
                return f"Completed: {tool_name}"
        
        # Execute template (can be string or callable)
        if callable(template):
            try:
                # Safely extract file_name and file_path to avoid issues with special characters
                safe_file_name = str(file_name) if file_name else None
                safe_file_path = str(tool_input.get('file_path') or tool_input.get('path') or '') if tool_input else ''
                # Create a safe copy of tool_input with string values to avoid format issues
                safe_tool_input = {}
                for key, value in (tool_input or {}).items():
                    safe_tool_input[key] = str(value) if value is not None else ''
                return template(safe_tool_input, safe_file_name)
            except Exception as e:
                logger.debug("Error formatting tool message: %s", str(e))
                return f"{'Using' if tool_status == 'executing' else 'Completed'}: {tool_name}"
        else:
            return str(template) if template else f"{'Using' if tool_status == 'executing' else 'Completed'}: {tool_name}"
    
    @classmethod
    def create_callback(
        cls,
        status_emitter,
        workflow_stage: WorkflowStage = WorkflowStage.EXECUTING
    ):
        """
        Create a tool callback function for use with AgentExecutor.
        
        Args:
            status_emitter: StatusEmitter instance
            workflow_stage: Workflow stage to emit status for
            
        Returns:
            Callback function that takes tool_event dict
        """
        def tool_callback(tool_event: Dict[str, Any]):
            """Callback to emit tool execution events as workflow status."""
            # Validate tool_event structure
            if not isinstance(tool_event, dict):
                logger.warning(f"Invalid tool_event type: {type(tool_event)}")
                return
            
            tool_name = tool_event.get("name", "unknown")
            tool_status = tool_event.get("status", "executing")
            tool_input = tool_event.get("input") or {}
            tool_result = tool_event.get("result")
            
            # Ensure tool_input is a dict
            if not isinstance(tool_input, dict):
                tool_input = {}
            
            # Format message
            message = cls.format_message(tool_name, tool_status, tool_input)
            
            # Extract file name for details
            file_path = tool_input.get('file_path') or tool_input.get('path')
            file_name = get_file_name(file_path) if file_path else None
            
            # Emit as workflow status with error handling
            try:
                status_emitter.emit_status(
                    workflow_stage,
                    message,
                    {
                        "tool": {
                            "name": tool_name or "unknown",
                            "input": tool_input or {},
                            "status": tool_status or "executing",
                            "result": tool_result,
                            "file_name": file_name  # Include extracted filename for frontend
                        }
                    }
                )
            except Exception as e:
                logger.error(f"Error emitting tool status: {e}", exc_info=True)
        
        return tool_callback

