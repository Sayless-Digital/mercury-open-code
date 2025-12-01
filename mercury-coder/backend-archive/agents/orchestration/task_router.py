"""
Task Router - routes simple tasks to appropriate agents.
"""

import logging
from typing import Dict, Any, Optional
import uuid

from ..task import WorkflowStage
from ..task_classifier import TaskClassifier
from ..base import BaseAgent

logger = logging.getLogger("mercury.agents.orchestration.task_router")


class TaskRouter:
    """Routes simple tasks to appropriate agents."""
    
    def __init__(
        self,
        researcher: BaseAgent,
        coder: BaseAgent,
        analyzer: BaseAgent,
        invoke_bedrock_model=None,
        model_id: Optional[str] = None,
        status_emitter=None
    ):
        """
        Initialize task router.
        
        Args:
            researcher: ResearcherAgent instance
            coder: CoderAgent instance
            analyzer: AnalyzerAgent instance
            invoke_bedrock_model: Function to invoke Bedrock model
            model_id: Model ID for LLM calls
            status_emitter: StatusEmitter instance
        """
        self.researcher = researcher
        self.coder = coder
        self.analyzer = analyzer
        self.invoke_bedrock_model = invoke_bedrock_model
        self.model_id = model_id
        self.status_emitter = status_emitter
    
    def _get_agent_action_message(self, agent_name: str, task_description: str = None) -> str:
        """Get descriptive action message for agent."""
        agent_messages = {
            "researcher": "Exploring codebase...",
            "coder": "Writing code...",
            "analyzer": "Validating code...",
            "planner": "Planning next moves...",
            "conversational": "Responding..."
        }
        
        base_message = agent_messages.get(agent_name, "Working...")
        
        # Add task-specific context if provided
        if task_description:
            if agent_name == "researcher":
                if "read" in task_description.lower():
                    return "Reading files..."
                elif "search" in task_description.lower():
                    return "Searching codebase..."
                else:
                    return "Exploring codebase..."
            elif agent_name == "coder":
                if "create" in task_description.lower() or "add" in task_description.lower():
                    return "Creating new code..."
                elif "modify" in task_description.lower() or "edit" in task_description.lower():
                    return "Modifying code..."
                else:
                    return "Writing code..."
            elif agent_name == "analyzer":
                if "syntax" in task_description.lower():
                    return "Checking syntax..."
                elif "test" in task_description.lower():
                    return "Running tests..."
                else:
                    return "Validating code..."
        
        return base_message
    
    async def execute_simple_task(
        self,
        user_request: str,
        project_path: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a simple task directly without full workflow.
        
        For conversational tasks, uses fast direct LLM call without tools.
        For tasks needing tools, routes to appropriate agent.
        """
        request_lower = user_request.lower().strip()
        
        # Use TaskClassifier for consistent conversational detection
        is_conversational = TaskClassifier.is_conversational(user_request)
        
        # Fast path for conversational tasks - direct LLM call, no tools
        if is_conversational and self.invoke_bedrock_model:
            if self.status_emitter:
                self.status_emitter.emit_status(
                    WorkflowStage.EXECUTING,
                    "Responding...",
                    {"agent": "conversational", "simple_task": True}
                )
            
            # Direct LLM call without tools for fast response
            try:
                system_prompt = """You are a helpful AI coding assistant. Respond naturally and concisely to the user's message. 
For greetings, be friendly and brief. For questions, provide helpful answers. Keep responses short unless more detail is needed."""
                
                response = await self.invoke_bedrock_model(
                    model_id=self.model_id,
                    system_prompt=system_prompt,
                    messages=[{"role": "user", "content": user_request}],
                    max_tokens=256,
                    tools=None,
                    enable_thinking=False
                )
                
                # Extract text response
                text_parts = []
                content = response.get("content", [])
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                
                response_text = "".join(text_parts) if text_parts else "Hello! How can I help you?"
                
                if self.status_emitter:
                    self.status_emitter.emit_status(
                        WorkflowStage.COMPLETED,
                        "Response ready",
                        {"agent": "conversational", "result": {"message": response_text}}
                    )
                
                return {
                    "success": True,
                    "workflow_id": str(uuid.uuid4()),
                    "agent": "conversational",
                    "result": {"message": response_text},
                    "message": response_text,
                    "simple_task": True
                }
            except Exception as e:
                logger.warning(f"Fast conversational path failed: {e}, falling back to agent")
                # Fall through to agent-based execution
        
        # Determine which agent to use for non-conversational tasks
        # Use TaskClassifier keywords for consistent classification
        if any(keyword in request_lower for keyword in TaskClassifier.SIMPLE_KEYWORDS + ["read", "show", "display", "list", "find", "search", "explore", "what", "where"]):
            agent = self.researcher
            agent_name = "researcher"
        elif any(keyword in request_lower for keyword in TaskClassifier.COMPLEX_KEYWORDS + ["write", "edit", "modify", "change", "add"]):
            agent = self.coder
            agent_name = "coder"
        elif any(keyword in request_lower for keyword in ["check", "validate", "test", "lint", "syntax", "analyze"]):
            agent = self.analyzer
            agent_name = "analyzer"
        else:
            # Default to researcher for exploration
            agent = self.researcher
            agent_name = "researcher"
        
        # Emit status with descriptive message
        action_message = self._get_agent_action_message(agent_name, user_request)
        if self.status_emitter:
            self.status_emitter.emit_status(
                WorkflowStage.EXECUTING,
                action_message,
                {
                    "agent": agent_name,
                    "simple_task": True,
                    "action": {
                        "type": agent_name,
                        "message": action_message
                    }
                }
            )
        
        # Execute task
        task = {
            "description": user_request,
            "project_path": project_path
        }
        
        result = await agent.execute(task)
        
        if result.get("success"):
            if self.status_emitter:
                self.status_emitter.emit_status(
                    WorkflowStage.COMPLETED,
                    "Task completed successfully!",
                    {"agent": agent_name, "result": result}
                )
        else:
            if self.status_emitter:
                self.status_emitter.emit_status(
                    WorkflowStage.ERROR,
                    f"Task failed: {result.get('error', 'Unknown error')}",
                    {"agent": agent_name, "error": result.get("error")}
                )
        
        return {
            "success": result.get("success"),
            "workflow_id": str(uuid.uuid4()),
            "agent": agent_name,
            "result": result,
            "simple_task": True
        }

