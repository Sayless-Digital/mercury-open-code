"""
Agent error handling - consistent error formats across all agents.
"""

import traceback
from typing import Dict, Any, Optional


class AgentError(Exception):
    """
    Standard exception for agent errors with consistent formatting.
    
    Attributes:
        message: Error message
        agent: Name of the agent that raised the error
        recoverable: Whether the error is recoverable
        traceback_str: Optional traceback string
    """
    
    def __init__(
        self,
        message: str,
        agent: str,
        recoverable: bool = False,
        traceback_str: Optional[str] = None
    ):
        """
        Initialize agent error.
        
        Args:
            message: Error message
            agent: Name of the agent
            recoverable: Whether error is recoverable
            traceback_str: Optional traceback string (if None, will be generated)
        """
        super().__init__(message)
        self.message = message
        self.agent = agent
        self.recoverable = recoverable
        self.traceback_str = traceback_str or traceback.format_exc()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary format for consistent error returns.
        
        Returns:
            Dictionary with error information
        """
        return {
            "success": False,
            "error": self.message,
            "agent": self.agent,
            "recoverable": self.recoverable,
            "traceback": self.traceback_str
        }
    
    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        agent: str,
        recoverable: bool = False
    ) -> 'AgentError':
        """
        Create AgentError from an exception.
        
        Args:
            exception: The exception to wrap
            agent: Name of the agent
            recoverable: Whether error is recoverable
            
        Returns:
            AgentError instance
        """
        return cls(
            message=str(exception),
            agent=agent,
            recoverable=recoverable,
            traceback_str=traceback.format_exc()
        )












