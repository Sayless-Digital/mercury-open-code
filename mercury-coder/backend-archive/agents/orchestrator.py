"""
Orchestrator agent - coordinates the multi-agent workflow.
"""

import logging
import asyncio
import threading
import hashlib
from typing import Dict, List, Any, Optional, Callable, Union
import uuid
from datetime import datetime

from .base import BaseAgent
from .task import Plan, Task, TaskStatus, WorkflowStage
from .planner import PlannerAgent
from .researcher import ResearcherAgent
from .coder import CoderAgent
from .analyzer import AnalyzerAgent
from .task_classifier import TaskClassifier
from .errors import AgentError
from .context import AgentContext
from .config import AgentConfig, AgentConstants
from .orchestration import StatusEmitter, TaskRouter
from .orchestration.intelligent_router import IntelligentRouter
from .orchestration.multi_agent_orchestrator import MultiAgentOrchestrator
from .orchestration.tool_status_formatter import ToolStatusFormatter
from .orchestration.workflow_cache import WorkflowCache
from .orchestration.follow_up_detector import FollowUpDetector
from .orchestration.workflow_manager import WorkflowManager

logger = logging.getLogger("mercury.agents.orchestrator")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class OrchestratorAgent(BaseAgent):
    """Orchestrator that coordinates the multi-agent workflow."""
    
    def __init__(
        self,
        memory_manager: Optional[Any] = None,
        tool_executor: Optional[Any] = None,
        tool_recommender: Optional[Any] = None,
        model_id: Optional[str] = None,
        invoke_bedrock_model: Optional[Callable] = None,
        all_tools: Optional[List[Dict[str, Any]]] = None,
        file_graph: Optional[Any] = None,
        pattern_matcher: Optional[Any] = None,
        proactive_search_manager: Optional[Any] = None,
        feedback_loop_manager: Optional[Any] = None
    ):
        super().__init__(
            name="orchestrator",
            role="Workflow Orchestrator - Coordinates all agents and manages the workflow",
            tools=None,  # Orchestrator doesn't use tools directly
            memory_manager=memory_manager,
            tool_executor=tool_executor,
            tool_recommender=tool_recommender
        )
        
        self.model_id = model_id
        self.invoke_bedrock_model = invoke_bedrock_model
        self.file_graph = file_graph
        self.pattern_matcher = pattern_matcher
        self.proactive_search_manager = proactive_search_manager
        self.feedback_loop_manager = feedback_loop_manager
        
        # Initialize status emitter first (needed for tool callback)
        self.status_emitter = StatusEmitter()
        
        # Initialize agent executor with tool callback
        if invoke_bedrock_model and all_tools:
            from .executor import AgentExecutor
            
            # Create tool callback using ToolStatusFormatter
            tool_callback = ToolStatusFormatter.create_callback(
                self.status_emitter,
                WorkflowStage.EXECUTING
            )
            
            self.agent_executor = AgentExecutor(
                model_id=model_id,
                invoke_bedrock_model=invoke_bedrock_model,
                tool_executor=tool_executor,
                all_tools=all_tools,
                tool_callback=tool_callback,
                feedback_loop_manager=feedback_loop_manager
            )
        else:
            self.agent_executor = None
        
        # Create standardized agent configuration
        agent_config = AgentConfig(
            memory_manager=memory_manager,
            tool_executor=tool_executor,
            tool_recommender=tool_recommender,
            file_graph=file_graph,
            pattern_matcher=pattern_matcher,
            proactive_search_manager=proactive_search_manager,
            feedback_loop_manager=feedback_loop_manager
        )
        
        # Initialize specialized agents with standardized configuration
        self.planner = PlannerAgent(**agent_config.get_planner_params())
        self.researcher = ResearcherAgent(**agent_config.get_researcher_params())
        self.coder = CoderAgent(**agent_config.get_coder_params())
        self.analyzer = AnalyzerAgent(**agent_config.get_analyzer_params())
        
        # Set executor on all agents
        if self.agent_executor:
            self.planner.set_executor(self.agent_executor)
            self.researcher.set_executor(self.agent_executor)
            self.coder.set_executor(self.agent_executor)
            self.analyzer.set_executor(self.agent_executor)
        
        # Current workflow state
        self.current_plan: Optional[Plan] = None
        self.workflow_stage = WorkflowStage.PLANNING
        self.agent_statuses: Dict[str, Dict] = {}
        
        # Cancellation and pause support
        self._cancelled = threading.Event()
        self._cancellation_reason: Optional[str] = None
        self._paused = threading.Event()
        self._pause_reason: Optional[str] = None
        
        # Workflow state persistence for resume
        self._saved_workflow_state: Optional[Dict[str, Any]] = None
        
        # Initialize orchestration modules (after agents are created)
        self.workflow_cache = WorkflowCache(max_size=100, ttl_seconds=3600)
        self.follow_up_detector = FollowUpDetector(memory_manager=memory_manager)
        
        # Initialize intelligent router (AI-powered semantic routing)
        self.intelligent_router = IntelligentRouter(
            invoke_bedrock_model=invoke_bedrock_model,
            model_id=model_id,
            researcher=self.researcher,
            coder=self.coder,
            analyzer=self.analyzer,
            status_emitter=self.status_emitter
        )
        
        # Initialize multi-agent orchestrator (agents communicate automatically)
        self.multi_agent_orchestrator = MultiAgentOrchestrator(
            intelligent_router=self.intelligent_router,
            researcher=self.researcher,
            coder=self.coder,
            analyzer=self.analyzer,
            planner=self.planner,
            invoke_bedrock_model=invoke_bedrock_model,
            model_id=model_id,
            status_emitter=self.status_emitter,
            max_iterations=15  # Maximum agent-to-agent interactions
        )
        
        # Keep legacy router for fallback
        self.task_router = TaskRouter(
            researcher=self.researcher,
            coder=self.coder,
            analyzer=self.analyzer,
            invoke_bedrock_model=invoke_bedrock_model,
            model_id=model_id,
            status_emitter=self.status_emitter
        )
        
        # Initialize workflow manager
        self.workflow_manager = WorkflowManager(
            researcher=self.researcher,
            planner=self.planner,
            coder=self.coder,
            analyzer=self.analyzer,
            status_emitter=self.status_emitter,
            workflow_cache=self.workflow_cache,
            get_agent_action_message=self._get_agent_action_message
        )
    
    def set_status_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback for status updates (for streaming to UI)."""
        self.status_emitter.set_callback(callback)
    
    def _get_agent_action_message(self, agent_name: str, task_description: str = None) -> str:
        """Get descriptive action message for agent."""
        return self.task_router._get_agent_action_message(agent_name, task_description)
    
    
    def cancel_workflow(self, reason: Optional[str] = None):
        """
        Cancel the current workflow.
        
        Args:
            reason: Optional reason for cancellation
        """
        self._cancelled.set()
        self._cancellation_reason = reason or "Workflow cancelled by user"
        logger.info(f"Workflow cancellation requested: {self._cancellation_reason}")
        self._emit_status(
            WorkflowStage.ERROR,
            f"Workflow cancelled: {self._cancellation_reason}",
            {"cancelled": True, "reason": self._cancellation_reason}
        )
    
    def is_cancelled(self) -> bool:
        """Check if workflow has been cancelled."""
        return self._cancelled.is_set()
    
    def pause_workflow(self, reason: Optional[str] = None):
        """
        Pause the current workflow.
        
        Args:
            reason: Optional reason for pausing
        """
        self._paused.set()
        self._pause_reason = reason or "Workflow paused by user"
        logger.info(f"Workflow pause requested: {self._pause_reason}")
        self._emit_status(
            WorkflowStage.EXECUTING,
            f"Workflow paused: {self._pause_reason}",
            {"paused": True, "reason": self._pause_reason}
        )
        
        # Save current workflow state for resume
        if self.current_plan:
            self._saved_workflow_state = {
                "plan": self.current_plan.to_dict(),
                "stage": self.workflow_stage.value,
                "pause_reason": self._pause_reason,
                "paused_at": datetime.now().isoformat()
            }
    
    def resume_workflow(self):
        """Resume a paused workflow."""
        if not self.is_paused():
            logger.warning("Attempted to resume workflow that is not paused")
            return False
        
        self._paused.clear()
        logger.info("Workflow resumed")
        self._emit_status(
            WorkflowStage.EXECUTING,
            "Workflow resumed",
            {"paused": False, "resumed": True}
        )
        return True
    
    def is_paused(self) -> bool:
        """Check if workflow is paused."""
        return self._paused.is_set()
    
    def get_saved_workflow_state(self) -> Optional[Dict[str, Any]]:
        """Get saved workflow state for resume."""
        return self._saved_workflow_state
    
    def reset_cancellation(self):
        """Reset cancellation and pause state (for new workflow)."""
        self._cancelled.clear()
        self._cancellation_reason = None
        self._paused.clear()
        self._pause_reason = None
        self._saved_workflow_state = None
    
    def _transition_to_stage(self, stage: WorkflowStage, message: str, details: Optional[Dict] = None):
        """
        Transition to a workflow stage and emit status.
        
        This is the primary method for status updates. It sets the stage and emits status.
        
        Args:
            stage: The workflow stage to transition to
            message: Status message
            details: Optional details dictionary
        """
        self.workflow_stage = stage
        self.status_emitter.transition_to_stage(stage, message, details)
    
    def _emit_status(self, stage: WorkflowStage, message: str, details: Optional[Dict] = None):
        """
        Emit status update to UI (deprecated - use _transition_to_stage instead).
        
        This method is kept for backward compatibility but should be replaced with _transition_to_stage.
        """
        # Use transition_to_stage for consistency
        self._transition_to_stage(stage, message, details)
    
    async def _should_use_full_workflow(self, user_request: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine if the request requires full workflow or can be handled directly.
        
        Uses TaskClassifier for consistent classification.
        
        Args:
            user_request: User's request text
            context: Optional context dict (e.g., {"is_empty_directory": bool})
        """
        return TaskClassifier.should_use_full_workflow(user_request, context)
    
    
    async def execute_workflow(
        self,
        user_request: str,
        project_path: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute autonomous workflow - intelligently decides complexity.
        
        Simple tasks: Direct execution with appropriate agent
        Complex tasks: Full workflow (explore → plan → execute → validate)
        
        Args:
            user_request: User's request/goal
            project_path: Project path
            session_id: Session ID
            
        Returns:
            Workflow result
        """
        logger.info(f"Starting workflow for request: {user_request[:100]}")
        self.status = "working"
        workflow_id = str(uuid.uuid4())
        
        # Reset cancellation state for new workflow
        self.reset_cancellation()
        
        # Initialize proactive search cache for this workflow
        self.workflow_cache.clear()
        
        try:
            # Check if this is a follow-up request that needs previous context
            follow_up_context = self.follow_up_detector.detect_follow_up_request(user_request, context)
            
            # If it's a follow-up to implement changes, use full workflow
            if follow_up_context and follow_up_context.get("needs_implementation"):
                logger.info(f"Detected follow-up request: {follow_up_context.get('reason')}")
                use_full_workflow = True
            else:
                # Check if directory is empty/new to inform workflow decision
                workflow_context = {}
                if project_path:
                    try:
                        # Quick check if directory is mostly empty (only config files)
                        import os
                        if os.path.exists(project_path):
                            items = os.listdir(project_path)
                            # Filter out common config files (must match researcher.py for consistency)
                            config_files = {'.git', '.gitignore', '.eslintrc.json', '.prettierrc.json', 
                                          'package.json', 'node_modules', '.vscode', '.idea', 'package-lock.json',
                                          'pnpm-lock.yaml', 'yarn.lock', 'tsconfig.json', 'jsconfig.json'}
                            code_files = [item for item in items if item not in config_files and not item.startswith('.')]
                            workflow_context["is_empty_directory"] = len(code_files) == 0
                            workflow_context["is_new_project"] = len(code_files) == 0
                    except Exception as e:
                        logger.debug(f"Could not check directory state: {e}")
                
                # Decide workflow complexity with context
                use_full_workflow = await self._should_use_full_workflow(user_request, workflow_context)
            
            logger.info(f"Workflow decision: {'FULL' if use_full_workflow else 'SIMPLE'}")
            
            if not use_full_workflow:
                # For simple creation tasks, route directly to intelligent router
                # This skips unnecessary multi-agent collaboration
                logger.info("[ORCHESTRATOR] Using intelligent router for simple task")
                
                result = await self.intelligent_router.route_task(
                    user_request, project_path, session_id, context
                )
                
                # Check if it determined full workflow is needed
                if result.get("needs_full_workflow"):
                    logger.info("[ORCHESTRATOR] Task escalated to full workflow")
                    use_full_workflow = True
                    # Continue to full workflow below
                else:
                    # Task was handled directly
                    return {
                        "success": result.get("success", True),
                        "result": result.get("result", result),
                        "message": result.get("message", "Task completed"),
                        "simple_task": True,
                        "agent": result.get("agent", "unknown")
                    }
            
            # Complex task - use full workflow
            # Check if we already have research from previous conversation
            skip_exploration = False
            explore_result = {}
            
            if follow_up_context and follow_up_context.get("needs_implementation"):
                # For follow-up requests, check if we can skip exploration
                # and go straight to planning based on previous research
                previous_findings = follow_up_context.get("previous_findings", [])
                if previous_findings:
                    logger.info("Using previous research findings, skipping exploration")
                    skip_exploration = True
                    explore_result = {
                        "success": True,
                        "findings": "\n".join(previous_findings),
                        "files_read": [],  # Will be populated during planning if needed
                        "skipped": True
                    }
                    self._transition_to_stage(
                        WorkflowStage.PLANNING,
                        "Using previous research to create plan...",
                        {
                            "agent": "planner",
                            "action": {
                                "type": "plan",
                                "message": "Creating implementation plan from previous research..."
                            }
                        }
                    )
            
            if not skip_exploration:
                # Stage 1: EXPLORING - Understand the codebase
                self._transition_to_stage(
                    WorkflowStage.EXPLORING,
                    "Exploring codebase...",
                    {
                        "agent": "researcher",
                        "action": {
                            "type": "research",
                            "message": "Exploring codebase to understand structure..."
                        }
                    }
                )
                
                explore_result = await self.workflow_manager.explore_codebase(user_request, project_path, session_id)
                
                # Defensive check: ensure explore_result is a dict
                if not isinstance(explore_result, dict):
                    logger.error(f"Exploration returned non-dict result: {type(explore_result)} - {explore_result}")
                    error_detail = f"Exploration returned invalid result type: {type(explore_result).__name__}"
                    agent_error = AgentError(
                        message=error_detail,
                        agent="orchestrator",
                        recoverable=False
                    )
                    error_dict = agent_error.to_dict()
                    error_dict.update({"stage": "exploring", "details": str(explore_result)})
                    self._transition_to_stage(
                        WorkflowStage.ERROR,
                        f"Exploration failed: {error_detail}",
                        error_dict
                    )
                    return error_dict
                
                if not explore_result.get("success"):
                    error_detail = explore_result.get("error", "Unknown exploration error")
                    logger.error(f"Exploration failed: {error_detail}")
                    logger.debug(f"Full explore_result: {explore_result}")
                    self._transition_to_stage(
                        WorkflowStage.ERROR,
                        f"Exploration failed: {error_detail}",
                        {"stage": "exploring", "details": explore_result}
                    )
                    agent_error = AgentError(
                        message=f"Exploration failed: {error_detail}",
                        agent="orchestrator",
                        recoverable=False
                    )
                    error_dict = agent_error.to_dict()
                    error_dict.update({"stage": "exploring", "details": explore_result})
                    return error_dict
                
                # Stage 2: PLANNING - Create task plan
                self._transition_to_stage(
                    WorkflowStage.PLANNING,
                    "Planning next moves...",
                    {
                        "agent": "planner",
                        "action": {
                            "type": "plan",
                            "message": "Creating detailed task plan..."
                        }
                    }
                )
            
            plan_result = await self.workflow_manager.create_plan(user_request, explore_result, project_path, context)
            if not plan_result.get("success"):
                error_detail = plan_result.get("error", "Unknown planning error")
                logger.error(f"Planning failed: {error_detail}")
                logger.debug(f"Full plan_result: {plan_result}")
                self._transition_to_stage(
                    WorkflowStage.ERROR,
                    f"Planning failed: {error_detail}",
                    {"stage": "planning", "details": plan_result}
                )
                agent_error = AgentError(
                    message=f"Planning failed: {error_detail}",
                    agent="orchestrator",
                    recoverable=False
                )
                error_dict = agent_error.to_dict()
                error_dict.update({"stage": "planning", "details": plan_result})
                return error_dict
            
            # Convert planner result to Plan object
            plan = self._create_plan_from_result(plan_result, user_request)
            if not plan:
                logger.error(f"No plan created - plan_result: {plan_result}")
                self._transition_to_stage(
                    WorkflowStage.ERROR,
                    "No plan created",
                    {"details": plan_result}
                )
                agent_error = AgentError(
                    message="No plan created",
                    agent="orchestrator",
                    recoverable=False
                )
                error_dict = agent_error.to_dict()
                error_dict.update({"details": plan_result})
                return error_dict
            
            self.current_plan = plan
            
            # Stage 3: EXECUTING - Execute tasks
            self._transition_to_stage(
                WorkflowStage.EXECUTING,
                f"Executing plan ({len(plan.tasks)} tasks)...",
                {"total_tasks": len(plan.tasks), "completed": 0}
            )
            
            execution_result = await self.workflow_manager.execute_plan(
                plan, project_path, session_id, self.is_cancelled
            )
            if not execution_result.get("success"):
                error_detail = execution_result.get("error", "Unknown execution error")
                failed_tasks = execution_result.get("failed_tasks", [])
                logger.error(f"Execution failed: {error_detail}")
                logger.debug(f"Failed tasks: {failed_tasks}")
                self._transition_to_stage(
                    WorkflowStage.ERROR,
                    f"Execution failed: {error_detail}",
                    {"stage": "executing", "failed_tasks": failed_tasks, "details": execution_result}
                )
                agent_error = AgentError(
                    message=f"Execution failed: {error_detail}",
                    agent="orchestrator",
                    recoverable=True
                )
                error_dict = agent_error.to_dict()
                error_dict.update({
                    "stage": "executing",
                    "failed_tasks": failed_tasks,
                    "details": execution_result
                })
                return error_dict
            
            # Stage 4: VALIDATING - Validate code
            self._transition_to_stage(
                WorkflowStage.VALIDATING,
                "Validating code...",
                {
                    "agent": "analyzer",
                    "action": {
                        "type": "analyze",
                        "message": "Validating code quality and correctness..."
                    }
                }
            )
            
            validation_result = await self.workflow_manager.validate_implementation(plan, project_path, session_id)
            if not validation_result.get("success"):
                self._transition_to_stage(
                    WorkflowStage.ERROR,
                    "Validation failed",
                    {"stage": "validating"}
                )
                agent_error = AgentError(
                    message="Validation failed",
                    agent="orchestrator",
                    recoverable=True
                )
                error_dict = agent_error.to_dict()
                error_dict.update({"stage": "validating"})
                return error_dict
            
            # Stage 5: COMPLETED
            self._transition_to_stage(
                WorkflowStage.COMPLETED,
                "All tasks completed successfully!",
                {"plan": plan.to_dict()}
            )
            
            self.status = "completed"
            
            return {
                "success": True,
                "workflow_id": workflow_id,
                "plan": plan.to_dict(),
                "exploration": explore_result,
                "execution": execution_result,
                "validation": validation_result
            }
            
        except Exception as e:
            agent_error = AgentError.from_exception(e, agent="orchestrator", recoverable=False)
            logger.error(f"Workflow error: {e}", exc_info=True)
            self.status = "error"
            error_dict = agent_error.to_dict()
            self._transition_to_stage(
                WorkflowStage.ERROR,
                f"Error: {agent_error.message}",
                error_dict
            )
            return error_dict
    
    def _create_plan_from_result(
        self,
        result: Dict[str, Any],
        user_request: str
    ) -> Optional[Plan]:
        """
        Convert planner result to Plan object with validation.
        
        Args:
            result: Planner result dictionary
            user_request: Original user request
            
        Returns:
            Plan object or None if creation failed
        """
        if not result.get("success"):
            return None
        
        plan_data = result.get("result", {})
        logger.debug(f"Plan data keys: {list(plan_data.keys())}")
        logger.debug(f"Plan data: {plan_data}")
        
        try:
            # Validate plan data using Pydantic model (fail fast)
            from .models import PlanDataModel, TaskDataModel
            from .task import PlanBuilder, Task, TaskStatus
            
            try:
                validated_plan = PlanDataModel(
                    plan_id=plan_data.get("plan_id", str(uuid.uuid4())),
                    goal=plan_data.get("goal", user_request),
                    tasks=plan_data.get("tasks", [])
                )
                plan_data = validated_plan.dict()
                logger.debug("Plan data validated successfully")
            except Exception as e:
                error_msg = f"Plan data validation failed: {e}"
                logger.error(error_msg)
                return None
            
            # Use PlanBuilder for early validation during construction
            plan_id = plan_data.get("plan_id", str(uuid.uuid4()))
            goal = plan_data.get("goal", user_request)
            builder = PlanBuilder(plan_id=plan_id, goal=goal)
            
            # Add tasks to builder with validation (fails fast on errors)
            tasks_data = plan_data.get("tasks", [])
            logger.info(f"Found {len(tasks_data)} tasks to add")
            
            for task_data in tasks_data:
                # Validate task data using Pydantic model (fail fast)
                try:
                    validated_task = TaskDataModel(**task_data)
                    task_data = validated_task.dict()
                except Exception as e:
                    error_msg = f"Task data validation failed: {e}"
                    logger.error(error_msg)
                    return None
                
                plan_task = Task(
                    id=task_data.get("id", str(uuid.uuid4())),
                    description=task_data.get("description", ""),
                    agent=task_data.get("agent", "coder"),
                    dependencies=task_data.get("dependencies", []),
                    status=TaskStatus.PENDING
                )
                
                # Add task to builder with validation (will raise ValueError if invalid)
                try:
                    builder.add_task(plan_task)
                except ValueError as e:
                    error_msg = f"Failed to add task '{plan_task.id}': {e}"
                    logger.error(error_msg)
                    return None
            
            # Build the plan (final validation)
            try:
                plan = builder.build()
                logger.info(f"Plan created successfully with {len(plan.tasks)} tasks")
                return plan
            except ValueError as e:
                error_msg = f"Plan build failed: {e}"
                logger.error(error_msg)
                return None
                
        except Exception as e:
            logger.error(f"Error creating Plan object: {e}", exc_info=True)
            return None
    
    
    async def execute(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute orchestrator task (runs full workflow).
        
        Args:
            task: Task dict with 'goal' or 'user_request' (validated)
            context: Additional context (validated)
            
        Returns:
            Workflow result
        """
        # Validate inputs using Pydantic models
        from .base import validate_task_input, validate_context
        task = validate_task_input(task, self.name)
        context = validate_context(context, self.name)
        
        user_request = task.get("goal") or task.get("user_request", "")
        project_path = task.get("project_path")
        session_id = task.get("session_id")
        
        return await self.execute_workflow(user_request, project_path, session_id, context)

