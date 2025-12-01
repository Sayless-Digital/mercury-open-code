"""
Workflow Manager - manages workflow state and coordinates plan execution.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..task import Plan, Task, TaskStatus, WorkflowStage
from ..errors import AgentError
from ..context import AgentContext
from ..config import AgentConstants

logger = logging.getLogger("mercury.agents.orchestration.workflow_manager")


class WorkflowManager:
    """
    Manages workflow state and coordinates plan execution.
    
    Handles:
    - Workflow state management
    - Plan execution coordination
    - Task dependency resolution
    - Task retry logic
    """
    
    def __init__(
        self,
        researcher: Any,
        planner: Any,
        coder: Any,
        analyzer: Any,
        status_emitter: Any,
        workflow_cache: Any,
        get_agent_action_message: callable
    ):
        """
        Initialize workflow manager.
        
        Args:
            researcher: ResearcherAgent instance
            planner: PlannerAgent instance
            coder: CoderAgent instance
            analyzer: AnalyzerAgent instance
            status_emitter: StatusEmitter instance
            workflow_cache: WorkflowCache instance
            get_agent_action_message: Function to get action messages
        """
        self.researcher = researcher
        self.planner = planner
        self.coder = coder
        self.analyzer = analyzer
        self.status_emitter = status_emitter
        self.workflow_cache = workflow_cache
        self._get_agent_action_message = get_agent_action_message
        
        # Workflow state
        self.current_plan: Optional[Plan] = None
        self.workflow_stage = WorkflowStage.PLANNING
    
    def _get_agent(self, agent_name: str) -> Optional[Any]:
        """Get agent by name."""
        agents = {
            "researcher": self.researcher,
            "planner": self.planner,
            "coder": self.coder,
            "analyzer": self.analyzer
        }
        return agents.get(agent_name)
    
    async def explore_codebase(
        self,
        user_request: str,
        project_path: Optional[str],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Stage 1: Explore codebase.
        
        Args:
            user_request: User's request
            project_path: Project path
            session_id: Session ID
            
        Returns:
            Exploration result
        """
        logger.info(f"Starting codebase exploration for: {user_request[:100]}")
        task = {
            "description": f"Explore codebase to understand structure for: {user_request}",
            "goal": user_request,
            "project_path": project_path
        }
        
        # Enhanced context with session_id for memory/RAG access and proactive cache
        agent_context = AgentContext(
            session_id=session_id,
            project_path=project_path,
            proactive_cache=self.workflow_cache
        )
        context_dict = agent_context.to_dict()
        
        try:
            result = await self.researcher.execute(task, context=context_dict)
            
            # Defensive check: ensure result is a dict
            if not isinstance(result, dict):
                logger.error(f"Researcher returned non-dict result: {type(result)} - {result}")
                agent_error = AgentError(
                    message=f"Exploration returned invalid result type: {type(result).__name__}",
                    agent="orchestrator",
                    recoverable=False
                )
                return agent_error.to_dict()
            
            logger.info(f"Exploration result: success={result.get('success')}, error={result.get('error', 'none')}")
            if not result.get("success"):
                logger.debug(f"Exploration error details: {result}")
                logger.error(f"Researcher returned failure: {result.get('error', 'Unknown error')}")
            return result
        except Exception as e:
            agent_error = AgentError.from_exception(e, agent="orchestrator", recoverable=False)
            logger.error(f"Exploration exception: {e}", exc_info=True)
            return agent_error.to_dict()
    
    async def create_plan(
        self,
        user_request: str,
        exploration_result: Dict[str, Any],
        project_path: Optional[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Stage 2: Create task plan.
        
        Args:
            user_request: User's request
            exploration_result: Result from exploration phase
            project_path: Project path
            context: Optional context
            
        Returns:
            Plan creation result
        """
        # Build planning context with previous research/recommendations
        planning_context = {}
        
        if context:
            # Include conversation history for follow-up requests
            recent_messages = context.get("recent_messages", [])
            conversation_history = context.get("conversation_history", [])
            
            # Extract previous recommendations/findings
            previous_findings = []
            for msg in reversed(recent_messages + conversation_history[-5:]):
                content = ""
                if isinstance(msg, dict):
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        content = " ".join([str(c) for c in content if isinstance(c, str)])
                else:
                    content = str(msg)
                
                # Look for recommendations, improvements, suggestions
                if any(term in content.lower() for term in [
                    "recommendation", "improvement", "enhancement", "should", 
                    "consider", "add", "implement", "suggest", "finding"
                ]):
                    previous_findings.append(content[:500])  # Store relevant snippet
                    if len(previous_findings) >= 2:  # Get last 2 relevant messages
                        break
            
            if previous_findings:
                planning_context["previous_recommendations"] = "\n\n".join(previous_findings)
                planning_context["is_follow_up"] = True
        
        # Include exploration findings
        # Defensive check: handle case where result might be a string
        result_data = exploration_result.get("result", {})
        if isinstance(result_data, str):
            # If result is a string, wrap it in a dict
            exploration_findings = {"findings": result_data, "message": result_data}
        elif isinstance(result_data, dict):
            exploration_findings = result_data
        else:
            exploration_findings = {}
        
        if exploration_result.get("skipped"):
            # Use previous findings if exploration was skipped
            findings_str = exploration_result.get("findings", "")
            if isinstance(findings_str, str):
                exploration_findings = {"findings": findings_str, "message": findings_str}
            elif isinstance(findings_str, dict):
                exploration_findings = findings_str
        
        task = {
            "description": f"Create plan for: {user_request}",
            "goal": user_request,
            "project_path": project_path,
            "exploration_findings": exploration_findings,
            "previous_recommendations": planning_context.get("previous_recommendations", "")
        }
        
        # Pass context to planner (include proactive cache)
        agent_context = AgentContext(
            session_id=context.get("session_id") if context else None,
            project_path=project_path,
            conversation_history=context.get("conversation_history", []) if context else [],
            research_findings=planning_context.get("previous_recommendations", ""),
            exploration_findings=planning_context.get("exploration_findings"),
            proactive_cache=self.workflow_cache
        )
        planner_context = agent_context.for_agent("planner")
        planner_context.update(planning_context)  # Include other planning context
        
        result = await self.planner.execute(task, context=planner_context)
        logger.info(f"Planner result: success={result.get('success')}, error={result.get('error', 'none')}")
        
        return result
    
    async def execute_plan(
        self,
        plan: Plan,
        project_path: Optional[str],
        session_id: Optional[str],
        is_cancelled: callable,
        is_paused: callable = None
    ) -> Dict[str, Any]:
        """
        Stage 3: Execute plan tasks.
        
        Args:
            plan: Plan to execute
            project_path: Project path
            session_id: Session ID
            is_cancelled: Function to check if workflow is cancelled
            is_paused: Function to check if workflow is paused
            
        Returns:
            Execution result
        """
        executed_tasks = []
        task_results = {}
        
        while True:
            # Check for cancellation before getting next task
            if is_cancelled():
                logger.info("Workflow cancelled, stopping plan execution")
                break
            
            # Check for pause before getting next task
            if is_paused and is_paused():
                logger.info("Workflow paused, waiting for resume...")
                # Wait for resume or cancellation
                while is_paused():
                    if is_cancelled():
                        logger.info("Workflow cancelled while paused")
                        break
                    await asyncio.sleep(0.5)  # Check every 500ms
                
                if is_cancelled():
                    break
                
                logger.info("Workflow resumed, continuing execution")
                self.status_emitter.transition_to_stage(
                    WorkflowStage.EXECUTING,
                    "Workflow resumed",
                    {"resumed": True}
                )
                
            next_task = plan.get_next_task()
            if not next_task:
                break
            
            # Update task status
            next_task.status = TaskStatus.IN_PROGRESS
            next_task.started_at = datetime.now()
            
            # Emit status with descriptive action message
            action_message = self._get_agent_action_message(next_task.agent, next_task.description)
            self.status_emitter.transition_to_stage(
                WorkflowStage.EXECUTING,
                action_message,
                {
                    "task_id": next_task.id,
                    "agent": next_task.agent,
                    "progress": plan.get_progress(),
                    "action": {
                        "type": next_task.agent,
                        "message": action_message
                    }
                }
            )
            
            # Get the appropriate agent
            agent = self._get_agent(next_task.agent)
            if not agent:
                next_task.status = TaskStatus.FAILED
                next_task.error = f"Unknown agent: {next_task.agent}"
                continue
            
            # Prepare enhanced task context
            agent_context = AgentContext(
                session_id=session_id,
                project_path=project_path,
                completed_tasks=[str(t.id) for t in executed_tasks],
                plan_goal=plan.goal,
                proactive_cache=self.workflow_cache,
                task_results=task_results
            )
            task_context = agent_context.for_agent(next_task.agent)
            # Add plan_goal explicitly (already in context but ensure it's there)
            task_context["plan_goal"] = plan.goal
            
            # Execute task with retry logic
            retry_count = 0
            max_retries = AgentConstants.MAX_TASK_RETRIES
            task_succeeded = False
            
            while retry_count <= max_retries and not task_succeeded:
                # Check for cancellation and pause before each attempt
                if is_cancelled():
                    logger.info(f"Workflow cancelled, stopping task execution")
                    next_task.status = TaskStatus.CANCELLED
                    next_task.error = "Workflow cancelled"
                    next_task.completed_at = datetime.now()
                    break
                
                # Check for pause
                if is_paused and is_paused():
                    logger.info(f"Workflow paused during task {next_task.id}")
                    next_task.status = TaskStatus.PAUSED
                    # Wait for resume or cancellation
                    while is_paused():
                        if is_cancelled():
                            logger.info("Workflow cancelled while paused")
                            next_task.status = TaskStatus.CANCELLED
                            next_task.error = "Workflow cancelled while paused"
                            next_task.completed_at = datetime.now()
                            break
                        await asyncio.sleep(0.5)
                    
                    if is_cancelled():
                        break
                    
                    # Resume - set back to in progress
                    logger.info(f"Workflow resumed, continuing task {next_task.id}")
                    next_task.status = TaskStatus.IN_PROGRESS
                
                try:
                    if retry_count > 0:
                        logger.info(f"[WORKFLOW_MANAGER] Retrying task {next_task.id} (attempt {retry_count + 1}/{max_retries + 1})")
                        await asyncio.sleep(AgentConstants.RETRY_DELAY_SECONDS * retry_count)  # Exponential backoff
                    
                    logger.info(f"Executing task {next_task.id}: {next_task.description}")
                    logger.info(f"Agent assigned: {next_task.agent} (agent type: {type(agent).__name__})")
                    logger.debug(f"Agent: {next_task.agent}")
                    result = await agent.execute(
                        {
                            "description": next_task.description,
                            "project_path": project_path,
                            "task_id": next_task.id,
                            "retry_count": retry_count  # Pass retry count for agent awareness
                        },
                        context=task_context
                    )
                    
                    logger.info(f"Task {next_task.id} result: success={result.get('success')}")
                    
                    if result.get("success"):
                        logger.info(f"Task {next_task.id} completed successfully")
                        next_task.status = TaskStatus.COMPLETED
                        next_task.completed_at = datetime.now()
                        next_task.result = result
                        executed_tasks.append(next_task)
                        task_results[next_task.id] = result
                        task_succeeded = True
                    else:
                        error_msg = result.get("error", "Task failed")
                        error_recoverable = result.get("recoverable", True)
                        
                        # If error is not recoverable, don't retry
                        if not error_recoverable:
                            logger.warning(f"[WORKFLOW_MANAGER] Task {next_task.id} failed with non-recoverable error: {error_msg}")
                            next_task.status = TaskStatus.FAILED
                            next_task.error = error_msg
                            next_task.completed_at = datetime.now()
                            break
                        
                        # If we've exhausted retries, mark as failed
                        if retry_count >= max_retries:
                            logger.error(f"Task {next_task.id} failed after {max_retries + 1} attempts: {error_msg}")
                            next_task.status = TaskStatus.FAILED
                            next_task.error = f"{error_msg} (failed after {max_retries + 1} attempts)"
                            next_task.completed_at = datetime.now()
                            # Emit status about failure
                            self.status_emitter.transition_to_stage(
                                WorkflowStage.EXECUTING,
                                f"Task failed: {next_task.description[:50]}...",
                                {
                                    "task_id": next_task.id,
                                    "error": error_msg,
                                    "retries": retry_count + 1
                                }
                            )
                        else:
                            logger.warning(f"[WORKFLOW_MANAGER] Task {next_task.id} failed (attempt {retry_count + 1}), will retry: {error_msg}")
                            retry_count += 1
                            
                except Exception as e:
                    agent_error = AgentError.from_exception(e, agent=next_task.agent, recoverable=True)
                    logger.error(f"Task execution exception: {e}", exc_info=True)
                    
                    # If we've exhausted retries, mark as failed
                    if retry_count >= max_retries:
                        next_task.status = TaskStatus.FAILED
                        next_task.error = f"{agent_error.message} (failed after {max_retries + 1} attempts)"
                        next_task.completed_at = datetime.now()
                        break
                    else:
                        retry_count += 1
                        await asyncio.sleep(AgentConstants.RETRY_DELAY_SECONDS * retry_count)
            
            # Update progress
            progress = plan.get_progress()
            self.status_emitter.transition_to_stage(
                WorkflowStage.EXECUTING,
                f"Task {next_task.id} {'completed' if next_task.status == TaskStatus.COMPLETED else 'failed'}",
                {"progress": progress}
            )
        
        # Log execution summary
        progress = plan.get_progress()
        logger.info(f"Execution summary: Total={progress['total']}, Completed={progress['completed']}, Failed={progress['failed']}, Pending={progress['pending']}")
        
        # Log failed tasks details
        failed_tasks_list = [t for t in plan.tasks if t.status == TaskStatus.FAILED]
        if failed_tasks_list:
            logger.warning(f"Failed tasks: {len(failed_tasks_list)}")
            for task in failed_tasks_list:
                logger.error(f"Task {task.id} ({task.agent}): {task.description} - Error: {task.error}")
        
        return {
            "success": not plan.has_failed_tasks(),
            "executed_tasks": len(executed_tasks),
            "failed_tasks": sum(1 for t in plan.tasks if t.status == TaskStatus.FAILED),
            "failed_tasks_details": [t.to_dict() for t in failed_tasks_list],
            "plan": plan.to_dict()
        }
    
    async def validate_implementation(
        self,
        plan: Plan,
        project_path: Optional[str],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Stage 4: Validate implementation.
        
        Args:
            plan: Plan that was executed
            project_path: Project path
            session_id: Session ID
            
        Returns:
            Validation result
        """
        # Get all files that were modified
        modified_files = []
        for task in plan.tasks:
            if task.status == TaskStatus.COMPLETED and task.agent == "coder":
                result = task.result or {}
                files = result.get("result", {}).get("files_modified", [])
                modified_files.extend(files)
        
        if not modified_files:
            return {"success": True, "message": "No files to validate"}
        
        # Create validation task
        task = {
            "description": f"Validate code quality for modified files: {', '.join(modified_files)}",
            "project_path": project_path,
            "files_changed": modified_files
        }
        
        # Enhanced context with session_id for memory/RAG access and proactive cache
        agent_context = AgentContext(
            session_id=session_id,
            project_path=project_path,
            completed_tasks=[str(t.id) for t in plan.tasks if t.status == TaskStatus.COMPLETED],
            proactive_cache=self.workflow_cache,
            files_changed=modified_files
        )
        context_dict = agent_context.for_agent("analyzer")
        
        result = await self.analyzer.execute(task, context=context_dict)
        return result

