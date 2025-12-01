"""
Agent context management - type-safe context passing between agents.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union

# Forward reference for LRUCacheWithTTL to avoid circular import
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .utils.cache import LRUCacheWithTTL


@dataclass
class AgentContext:
    """
    Type-safe context for passing information between agents.
    
    Attributes:
        session_id: Session identifier
        project_path: Path to the project root
        conversation_history: List of conversation messages
        completed_tasks: List of completed task IDs
        research_findings: Optional research findings from researcher agent
        plan_goal: Optional goal from planning phase
        exploration_findings: Optional findings from exploration phase
        proactive_cache: Optional proactive search cache (LRUCacheWithTTL or dict-like)
        task_results: Optional results from previous tasks
        files_changed: Optional list of modified files
    """
    session_id: Optional[str] = None
    project_path: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    research_findings: Optional[str] = None
    plan_goal: Optional[str] = None
    exploration_findings: Optional[Dict[str, Any]] = None
    proactive_cache: Optional[Any] = None  # LRUCacheWithTTL or dict-like object
    task_results: Optional[Dict[str, Any]] = None
    files_changed: Optional[List[str]] = None
    
    def for_agent(self, agent_name: str) -> Dict[str, Any]:
        """
        Filter context relevant for specific agent.
        
        Args:
            agent_name: Name of the agent (planner, researcher, coder, analyzer)
            
        Returns:
            Dictionary with filtered context
        """
        base_context = {
            "session_id": self.session_id,
            "project_path": self.project_path,
            "conversation_history": self.conversation_history,
        }
        
        # Add common fields
        if self.proactive_cache is not None:
            base_context["proactive_cache"] = self.proactive_cache
        if self.task_results is not None:
            base_context["task_results"] = self.task_results
        if self.files_changed is not None:
            base_context["files_changed"] = self.files_changed
        
        # Agent-specific context
        if agent_name == "planner":
            base_context.update({
                "plan_goal": self.plan_goal,
                "exploration_findings": self.exploration_findings,
                "research_findings": self.research_findings,
            })
        elif agent_name == "researcher":
            base_context.update({
                "plan_goal": self.plan_goal,
            })
        elif agent_name == "coder":
            base_context.update({
                "completed_tasks": self.completed_tasks,
                "research_findings": self.research_findings,
                "plan_goal": self.plan_goal,
            })
        elif agent_name == "analyzer":
            base_context.update({
                "completed_tasks": self.completed_tasks,
            })
        
        return base_context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "session_id": self.session_id,
            "project_path": self.project_path,
            "conversation_history": self.conversation_history,
            "completed_tasks": self.completed_tasks,
            "research_findings": self.research_findings,
            "plan_goal": self.plan_goal,
            "exploration_findings": self.exploration_findings,
        }
        # Add optional fields if present
        if self.proactive_cache is not None:
            result["proactive_cache"] = self.proactive_cache
        if self.task_results is not None:
            result["task_results"] = self.task_results
        if self.files_changed is not None:
            result["files_changed"] = self.files_changed
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentContext':
        """Create from dictionary."""
        return cls(
            session_id=data.get("session_id"),
            project_path=data.get("project_path"),
            conversation_history=data.get("conversation_history", []),
            completed_tasks=data.get("completed_tasks", []),
            research_findings=data.get("research_findings"),
            plan_goal=data.get("plan_goal"),
            exploration_findings=data.get("exploration_findings"),
            proactive_cache=data.get("proactive_cache"),
            task_results=data.get("task_results"),
            files_changed=data.get("files_changed"),
        )


