"""
Base agent class for all specialized agents.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime

logger = logging.getLogger(f"mercury.agents.base")


def validate_task_input(task: Dict[str, Any], agent_name: str = "agent") -> Dict[str, Any]:
    """
    Validate task input using Pydantic model.
    
    Returns validated task dict, or original dict if validation fails (graceful degradation).
    
    Args:
        task: Task dictionary to validate
        agent_name: Name of agent for logging
        
    Returns:
        Validated task dictionary (or original if validation fails)
    """
    try:
        from .models import TaskInput
        validated = TaskInput(**task)
        return validated.dict()
    except Exception as e:
        # Graceful degradation: log but don't fail
        logger.debug(f"[{agent_name}] Task input validation failed: {e}, using original input")
        return task


def validate_context(context: Optional[Dict[str, Any]], agent_name: str = "agent") -> Optional[Dict[str, Any]]:
    """
    Validate agent context using Pydantic model.
    
    Returns validated context dict, or original dict if validation fails (graceful degradation).
    
    Args:
        context: Context dictionary to validate
        agent_name: Name of agent for logging
        
    Returns:
        Validated context dictionary (or original if validation fails)
    """
    if not context:
        return context
    
    try:
        from .models import AgentContextModel
        validated = AgentContextModel(**context)
        return validated.dict()
    except Exception as e:
        # Graceful degradation: log but don't fail
        logger.debug(f"[{agent_name}] Context validation failed: {e}, using original context")
        return context


class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system."""
    
    def __init__(
        self,
        name: str,
        role: str,
        tools: Optional[List[str]] = None,
        memory_manager: Optional[Any] = None,
        tool_executor: Optional[Any] = None,
        tool_recommender: Optional[Any] = None
    ):
        """
        Initialize base agent.
        
        Args:
            name: Agent name (e.g., "coder", "researcher")
            role: Agent role description
            tools: List of tool names this agent can use (None = all tools)
            memory_manager: Memory manager instance for RAG
            tool_executor: Tool executor instance
            tool_recommender: Tool recommender instance
        """
        self.name = name
        self.role = role
        self.tools = tools  # None means all tools available
        # Allow None to disable memory features - guard clauses will skip operations
        self.memory_manager = memory_manager
        self.tool_executor = tool_executor
        self.tool_recommender = tool_recommender
        
        # Agent state
        self.current_task = None
        self.work_history = []
        self.status = "idle"  # idle, working, completed, error
        
    def get_available_tools(self, all_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get tools available to this agent.
        
        Args:
            all_tools: List of all tool definitions
            
        Returns:
            Filtered list of tools this agent can use
        """
        if self.tools is None:
            return all_tools
        
        # Filter tools by name
        return [tool for tool in all_tools if tool.get("name") in self.tools]
    
    def get_system_prompt(self) -> str:
        """
        Get agent-specific system prompt.
        
        Returns:
            System prompt string
        """
        base_prompt = f"""You are a {self.role} agent in a multi-agent coding system.

Your role: {self.role}

You work as part of a team:
- **Orchestrator**: Coordinates the overall workflow
- **Planner**: Creates detailed task plans
- **Researcher**: Explores codebase and gathers information
- **Coder**: Writes and modifies code
- **Analyzer**: Validates code quality and correctness

Current agent: {self.name} ({self.role})

You have access to tools for accomplishing your tasks. Use them proactively and efficiently.
"""
        return base_prompt
    
    def get_context_for_task(
        self,
        task_description: str,
        project_path: Optional[str] = None,
        limit: int = 5,
        session_id: Optional[str] = None
    ) -> str:
        """
        Get relevant context from memory/RAG for a task using multiple retrieval strategies.
        
        Uses:
        - Vector search (semantic similarity)
        - Memory context (RAG)
        - Conversation history
        - Tool recommendations
        
        Args:
            task_description: Description of the current task
            project_path: Project path for context filtering
            limit: Maximum number of context items to retrieve
            session_id: Session ID for conversation history
            
        Returns:
            Formatted context string with all relevant information
        """
        context_parts = []
        
        # 1. Memory/RAG context (vector search + semantic similarity)
        if self.memory_manager:
            # Get context from memory using vector search
            memory_context = self.memory_manager.get_context_for_query(
                query=task_description,
                project_path=project_path,
                limit=limit
            )
            if memory_context:
                context_parts.append(f"## Relevant Memory & Context:\n{memory_context}\n")
            
            # Get conversation history if session_id provided
            if session_id:
                try:
                    conversation_history = self.memory_manager.get_optimized_conversation_history(
                        project_path=project_path,
                        session_id=session_id,
                        max_tokens=2000,  # Recent conversation context
                        keep_recent=5  # Last 5 messages
                    )
                    if conversation_history:
                        # Format recent conversation
                        recent_msgs = []
                        for msg in conversation_history[-3:]:  # Last 3 messages
                            if isinstance(msg, dict):
                                role = msg.get("role", "unknown")
                                content = msg.get("content", "")
                                if isinstance(content, list):
                                    content = " ".join([str(c) for c in content if isinstance(c, str)])
                                if content:
                                    recent_msgs.append(f"{role.capitalize()}: {content[:200]}")
                        
                        if recent_msgs:
                            context_parts.append(f"## Recent Conversation:\n" + "\n".join(recent_msgs) + "\n")
                except Exception as e:
                    # Don't fail if conversation history fails
                    logger.debug(f"Could not retrieve conversation history: {e}")
        
        # 2. Tool recommendations (semantic tool selection)
        if self.tool_recommender:
            try:
                recommended_tools = self.tool_recommender.recommend_tools(
                    query=task_description,
                    limit=5,
                    use_vector_search=True  # Use semantic search
                )
                
                if recommended_tools:
                    tool_names = [tool.get("name", "") for tool in recommended_tools if tool.get("name")]
                    if tool_names:
                        context_parts.append(f"## Recommended Tools (semantic match):\n{', '.join(tool_names)}\n")
                    
                    # Get tool context/descriptions
                    tool_context = self.tool_recommender.get_recommended_tools_context(
                        query=task_description,
                        limit=3
                    )
                    if tool_context:
                        context_parts.append(f"{tool_context}\n")
            except Exception as e:
                # Don't fail if tool recommendation fails
                logger.debug(f"Could not get tool recommendations: {e}")
        
        return "\n".join(context_parts)
    
    def get_enhanced_tools(
        self,
        all_tools: List[Dict[str, Any]],
        task_description: str
    ) -> List[Dict[str, Any]]:
        """
        Get tools for this agent, enhanced with semantic recommendations.
        
        Args:
            all_tools: All available tool definitions
            task_description: Current task description for semantic tool selection
            
        Returns:
            List of tool definitions, potentially enhanced with recommendations
        """
        # Get base available tools
        available_tools = self.get_available_tools(all_tools)
        
        # If tool recommender is available, use it to enhance tool selection
        if self.tool_recommender and task_description:
            try:
                # Get semantically recommended tools
                recommended_tools = self.tool_recommender.recommend_tools(
                    query=task_description,
                    limit=10,
                    use_vector_search=True
                )
                
                if recommended_tools:
                    recommended_names = {tool.get("name") for tool in recommended_tools if tool.get("name")}
                    
                    # Prioritize recommended tools (move them to front)
                    prioritized = []
                    remaining = []
                    
                    for tool in available_tools:
                        if tool.get("name") in recommended_names:
                            prioritized.append(tool)
                        else:
                            remaining.append(tool)
                    
                    # Return recommended tools first, then others
                    return prioritized + remaining
            except Exception as e:
                logger.debug(f"Could not enhance tools with recommendations: {e}")
        
        return available_tools
    
    @abstractmethod
    async def execute(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a task assigned to this agent.
        
        Args:
            task: Task dictionary with description, goal, etc. (validated via Pydantic)
            context: Additional context from orchestrator (validated via Pydantic)
            
        Returns:
            Result dictionary with:
            - success: bool
            - result: Any (agent-specific result)
            - message: str (human-readable message)
            - next_action: Optional[str] (suggested next action)
        """
        pass
    
    def log_work(self, action: str, details: Dict[str, Any]):
        """Log work performed by this agent."""
        self.work_history.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details
        })
        logger.info(f"[{self.name}] {action}: {details}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "current_task": self.current_task,
            "work_count": len(self.work_history)
        }


