"""
Multi-Agent Orchestrator - Enables agents to communicate and collaborate.

Instead of routing once, this orchestrator routes AFTER EVERY AGENT ACTION,
allowing agents to work together dynamically to complete complex goals.

Architecture:
  User Request
       ↓
  [AI Router] → Decides which agent should act
       ↓
  [Agent 1] → Performs action
       ↓
  [AI Router] → Decides next action (same agent, different agent, or done?)
       ↓
  [Agent 2] → Performs action
       ↓
  ... (continues until goal is reached)
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from .model_selector import ModelSelector, TaskComplexity

logger = logging.getLogger("mercury.agents.orchestration.multi_agent_orchestrator")


class AgentAction(Enum):
    """Types of agent actions."""
    RESEARCH = "research"  # Researcher explores/searches
    CODE = "code"  # Coder writes/modifies code
    ANALYZE = "analyze"  # Analyzer validates/tests
    PLAN = "plan"  # Planner creates task breakdown
    

class NextStepDecision(Enum):
    """Possible next steps after an agent completes work."""
    CONTINUE_SAME_AGENT = "continue_same"  # Same agent continues
    SWITCH_AGENT = "switch_agent"  # Different agent takes over
    TASK_COMPLETE = "task_complete"  # Goal achieved
    NEEDS_USER_INPUT = "needs_user_input"  # Blocked, needs user
    

class MultiAgentOrchestrator:
    """
    Orchestrates multi-agent collaboration with automatic routing after each action.
    
    This enables agents to work together dynamically:
    - Researcher finds information
    - Router decides: "Now let's code it" → switches to Coder
    - Coder writes files  
    - Router decides: "Let's validate" → switches to Analyzer
    - Analyzer checks quality
    - Router decides: "Needs improvement" → back to Coder
    - Coder improves
    - Router decides: "Done!" → completes
    """
    
    def __init__(
        self,
        intelligent_router,
        researcher,
        coder,
        analyzer,
        planner,
        invoke_bedrock_model,
        model_id: str,
        status_emitter=None,
        max_iterations: int = 15
    ):
        """
        Initialize multi-agent orchestrator.
        
        Args:
            intelligent_router: IntelligentRouter instance for routing decisions
            researcher: ResearcherAgent instance
            coder: CoderAgent instance
            analyzer: AnalyzerAgent instance
            planner: PlannerAgent instance
            invoke_bedrock_model: Function to call LLM for routing decisions
            model_id: Model ID for default/smart operations
            status_emitter: For emitting progress updates
            max_iterations: Maximum agent interactions before forcing completion
        """
        self.intelligent_router = intelligent_router
        self.researcher = researcher
        self.coder = coder
        self.analyzer = analyzer
        self.planner = planner
        self.invoke_bedrock_model = invoke_bedrock_model
        self.model_id = model_id  # Default smart model
        self.status_emitter = status_emitter
        self.max_iterations = max_iterations
        
        # Initialize model selector for intelligent model choice
        self.model_selector = ModelSelector()
        
        # Conversation history for multi-agent collaboration
        self.agent_conversation: List[Dict[str, Any]] = []
        
    def _get_agent(self, agent_name: str):
        """Get agent instance by name."""
        agents = {
            "researcher": self.researcher,
            "coder": self.coder,
            "analyzer": self.analyzer,
            "planner": self.planner
        }
        return agents.get(agent_name)
    
    async def decide_next_step(
        self,
        user_goal: str,
        conversation_history: List[Dict[str, Any]],
        last_agent: Optional[str] = None,
        last_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use AI to decide what should happen next in the multi-agent workflow.
        
        Args:
            user_goal: Original user's goal/request
            conversation_history: History of agent actions and results
            last_agent: Name of agent that just completed work
            last_result: Result from the last agent's action
            
        Returns:
            Dict with:
            - next_step: NextStepDecision enum
            - next_agent: Name of agent to use next (if switching)
            - reasoning: Explanation of the decision
            - message_to_agent: Instructions for the next agent
        """
        # Build context for routing decision
        context = f"""
Goal: {user_goal}

Conversation History:
"""
        
        for i, entry in enumerate(conversation_history[-5:], 1):  # Last 5 interactions
            agent = entry.get("agent", "unknown")
            action = entry.get("action", "")
            result_summary = str(entry.get("result", ""))[:200]  # Truncate
            context += f"\n{i}. {agent}: {action}\n   Result: {result_summary}\n"
        
        if last_agent and last_result:
            context += f"\n\nLast Action:\nAgent: {last_agent}\nResult: {last_result}\n"
        
        # System prompt for routing decision
        system_prompt = """You are a multi-agent orchestration AI. Your job is to decide what should happen NEXT in a collaborative workflow where multiple specialized agents work together.

**Available Agents:**
- researcher: Explores codebase, searches web, gathers information
- coder: Writes code, creates files, modifies existing code  
- analyzer: Validates code, checks quality, runs tests
- planner: Breaks down complex tasks into steps

**Your Decision Framework:**
1. **Analyze** the goal and what's been done so far
2. **Determine** if the goal is complete or what's missing
3. **Decide** which agent should act next (or if we're done)
4. **Explain** your reasoning clearly

**Next Step Options:**
- CONTINUE_SAME_AGENT: Current agent should continue (e.g., coder needs to create more files)
- SWITCH_AGENT: Different agent should take over (e.g., researcher found info, now coder should implement)
- TASK_COMPLETE: Goal is fully achieved, workflow done
- NEEDS_USER_INPUT: Blocked, need clarification from user

**Example Decision Flow:**
Goal: "create a landing page"
1. researcher: Searches for modern design examples → SWITCH_AGENT to coder
2. coder: Creates HTML/CSS/JS files → SWITCH_AGENT to analyzer  
3. analyzer: Validates design quality → SWITCH_AGENT to coder (needs improvements)
4. coder: Improves design → SWITCH_AGENT to analyzer
5. analyzer: Validates - looks good → TASK_COMPLETE

RESPOND ONLY WITH JSON:
{
  "next_step": "CONTINUE_SAME_AGENT|SWITCH_AGENT|TASK_COMPLETE|NEEDS_USER_INPUT",
  "next_agent": "researcher|coder|analyzer|planner (if switching)",
  "reasoning": "Clear explanation of why this is the right next step",
  "message_to_agent": "Specific instructions for the next agent about what to do",
  "confidence": 0.0-1.0
}"""

        user_message = f"""{context}

Based on the goal and conversation history, what should happen NEXT?

Respond with JSON only."""

        try:
            # Use fast model for routing decisions (much faster and cheaper)
            routing_model = self.model_selector.select_model_for_routing()
            logger.debug(f"[MULTI-AGENT] Using model for routing: {routing_model}")
            
            # Call LLM for routing decision
            response = await self.invoke_bedrock_model(
                model_id=routing_model,
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                max_tokens=512,
                tools=None,
                enable_thinking=False
            )
            
            # Extract response
            text_parts = []
            for block in response.get("content", []):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            
            response_text = "".join(text_parts)
            
            # Parse JSON
            import json
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                decision = json.loads(json_str)
            else:
                raise ValueError("No JSON in response")
            
            # Convert string to enum
            next_step_str = decision.get("next_step", "TASK_COMPLETE").upper()
            try:
                next_step = NextStepDecision[next_step_str]
            except KeyError:
                logger.warning(f"Unknown next_step: {next_step_str}, defaulting to TASK_COMPLETE")
                next_step = NextStepDecision.TASK_COMPLETE
            
            return {
                "next_step": next_step,
                "next_agent": decision.get("next_agent"),
                "reasoning": decision.get("reasoning", ""),
                "message_to_agent": decision.get("message_to_agent", ""),
                "confidence": decision.get("confidence", 0.8)
            }
            
        except Exception as e:
            logger.error(f"Next step decision failed: {e}", exc_info=True)
            # Fallback: assume task complete if error
            return {
                "next_step": NextStepDecision.TASK_COMPLETE,
                "next_agent": None,
                "reasoning": f"Error in routing: {e}",
                "message_to_agent": "",
                "confidence": 0.5
            }
    
    async def execute_collaborative_workflow(
        self,
        user_request: str,
        project_path: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a collaborative multi-agent workflow where agents communicate.
        
        This is the main entry point. It:
        1. Routes to initial agent
        2. Agent performs work
        3. Routes to next agent (or same agent, or completion)
        4. Repeat until goal is achieved
        
        Args:
            user_request: User's goal/request
            project_path: Project path
            session_id: Session ID
            context: Additional context
            
        Returns:
            Final result with full agent conversation history
        """
        logger.info(f"[MULTI-AGENT] Starting collaborative workflow for: {user_request[:100]}")
        
        # Reset conversation history
        self.agent_conversation = []
        
        # Initial routing decision
        initial_routing = await self.intelligent_router.analyze_intent(user_request, context)
        initial_decision, initial_intent, initial_reasoning = initial_routing
        
        logger.info(f"[MULTI-AGENT] Initial routing: {initial_decision.value}, intent: {initial_intent.value}")
        
        # Determine starting agent based on intent
        agent_mapping = {
            "GREETING": None,  # No agent needed
            "QUESTION": "researcher",
            "EXPLORATION": "researcher", 
            "CREATION": "coder",
            "MODIFICATION": "coder",
            "VALIDATION": "analyzer",
            "REFACTORING": "planner"
        }
        
        current_agent_name = agent_mapping.get(initial_intent.value, "researcher")
        
        if not current_agent_name:
            # Conversational task, handle directly
            return await self.intelligent_router._handle_conversational(user_request, initial_reasoning)
        
        iteration = 0
        current_message = user_request
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"[MULTI-AGENT] Iteration {iteration}/{self.max_iterations}, Agent: {current_agent_name}")
            
            # Get agent
            agent = self._get_agent(current_agent_name)
            if not agent:
                logger.error(f"[MULTI-AGENT] Unknown agent: {current_agent_name}")
                break
            
            # Emit detailed status - show what agent is about to do
            if self.status_emitter:
                try:
                    self.status_emitter.emit_status(
                        stage="executing",
                        message=f"🤖 **{current_agent_name.capitalize()}** is working",
                        details={
                            "type": "agent_start",
                            "agent": current_agent_name,
                            "iteration": iteration,
                            "max_iterations": self.max_iterations,
                            "task": current_message[:200],
                            "conversation_so_far": len(self.agent_conversation)
                        }
                    )
                except Exception as e:
                    logger.error(f"[MULTI-AGENT] Failed to emit agent_start status: {e}", exc_info=True)
            
            # Execute agent task
            task = {
                "description": current_message,
                "project_path": project_path,
                "multi_agent_context": {
                    "conversation_history": self.agent_conversation,
                    "user_goal": user_request
                }
            }
            
            try:
                result = await agent.execute(task, context=context)
            except Exception as e:
                logger.error(f"[MULTI-AGENT] Agent execution failed: {e}", exc_info=True)
                result = {
                    "success": False,
                    "error": str(e)
                }
            
            # Record in conversation
            conversation_entry = {
                "iteration": iteration,
                "agent": current_agent_name,
                "action": current_message,
                "result": result,
                "success": result.get("success", False)
            }
            self.agent_conversation.append(conversation_entry)
            
            logger.info(f"[MULTI-AGENT] Agent '{current_agent_name}' completed: success={result.get('success')}")
            
            # Emit status with agent result
            if self.status_emitter:
                try:
                    result_summary = self._summarize_result(result, current_agent_name)
                    self.status_emitter.emit_status(
                        stage="executing",
                        message=f"✅ **{current_agent_name.capitalize()}** completed: {result_summary}",
                        details={
                            "type": "agent_complete",
                            "agent": current_agent_name,
                            "iteration": iteration,
                            "success": result.get("success", False),
                            "result_summary": result_summary,
                            "full_result": result
                        }
                    )
                except Exception as e:
                    logger.error(f"[MULTI-AGENT] Failed to emit agent_complete status: {e}", exc_info=True)
            
            # Decide next step using AI
            next_decision = await self.decide_next_step(
                user_goal=user_request,
                conversation_history=self.agent_conversation,
                last_agent=current_agent_name,
                last_result=result
            )
            
            next_step = next_decision["next_step"]
            logger.info(f"[MULTI-AGENT] Next step decision: {next_step.value}")
            logger.info(f"[MULTI-AGENT] Reasoning: {next_decision['reasoning']}")
            
            # Emit routing decision to UI
            if self.status_emitter:
                try:
                    self._emit_routing_decision(next_step, next_decision, current_agent_name, iteration)
                except Exception as e:
                    logger.error(f"[MULTI-AGENT] Failed to emit routing decision: {e}", exc_info=True)
            
            if next_step == NextStepDecision.TASK_COMPLETE:
                logger.info("[MULTI-AGENT] Workflow complete!")
                return {
                    "success": True,
                    "result": result,
                    "conversation_history": self.agent_conversation,
                    "iterations": iteration,
                    "final_agent": current_agent_name
                }
            
            elif next_step == NextStepDecision.NEEDS_USER_INPUT:
                logger.info("[MULTI-AGENT] Needs user input, stopping")
                return {
                    "success": False,
                    "needs_user_input": True,
                    "message": next_decision.get("reasoning"),
                    "conversation_history": self.agent_conversation
                }
            
            elif next_step == NextStepDecision.SWITCH_AGENT:
                # Switch to different agent
                next_agent_name = next_decision.get("next_agent")
                if not next_agent_name:
                    logger.warning("[MULTI-AGENT] SWITCH_AGENT but no next_agent specified, completing")
                    break
                
                logger.info(f"[MULTI-AGENT] Switching from {current_agent_name} to {next_agent_name}")
                current_agent_name = next_agent_name
                current_message = next_decision.get("message_to_agent", user_request)
            
            elif next_step == NextStepDecision.CONTINUE_SAME_AGENT:
                # Same agent continues
                logger.info(f"[MULTI-AGENT] {current_agent_name} continues")
                current_message = next_decision.get("message_to_agent", "Continue with the task")
            
            else:
                logger.warning(f"[MULTI-AGENT] Unknown next_step: {next_step}, completing")
                break
        
        # Max iterations reached
        logger.warning(f"[MULTI-AGENT] Max iterations ({self.max_iterations}) reached")
        
        if self.status_emitter:
            self.status_emitter.emit_status(
                stage="executing",
                message=f"⚠️ Max iterations reached ({self.max_iterations})",
                details={
                    "type": "workflow_warning",
                    "warning": "Max iterations reached",
                    "iterations": iteration
                }
            )
        
        return {
            "success": True,
            "warning": "Max iterations reached",
            "conversation_history": self.agent_conversation,
            "iterations": iteration
        }
    
    def _summarize_result(self, result: Dict[str, Any], agent_name: str) -> str:
        """
        Create a human-readable summary of an agent's result.
        
        Args:
            result: Agent result dict
            agent_name: Name of the agent
            
        Returns:
            Human-readable summary string
        """
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            return f"Failed - {error[:100]}"
        
        # Agent-specific summaries
        if agent_name == "researcher":
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                findings = result_data.get("findings", "")
                files_read = result_data.get("files_read", [])
                if files_read:
                    return f"Explored {len(files_read)} files"
                elif findings:
                    return f"Found information: {findings[:100]}..."
            return "Research completed"
        
        elif agent_name == "coder":
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                files_created = result_data.get("files_created", [])
                files_modified = result_data.get("files_modified", [])
                if files_created:
                    return f"Created {len(files_created)} file(s): {', '.join(files_created[:3])}"
                elif files_modified:
                    return f"Modified {len(files_modified)} file(s): {', '.join(files_modified[:3])}"
            return "Code changes completed"
        
        elif agent_name == "analyzer":
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                validation = result_data.get("validation", {})
                design_quality = result_data.get("design_quality", {})
                if design_quality:
                    score = design_quality.get("quality_score", 0)
                    return f"Design quality: {score}/100"
                elif validation:
                    if validation.get("valid"):
                        return "Validation passed ✓"
                    else:
                        errors = validation.get("errors", [])
                        return f"Found {len(errors)} issue(s)"
            return "Analysis completed"
        
        elif agent_name == "planner":
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                tasks = result_data.get("tasks", [])
                if tasks:
                    return f"Created plan with {len(tasks)} task(s)"
            return "Plan created"
        
        # Default
        return "Task completed"
    
    def _emit_routing_decision(
        self,
        next_step: NextStepDecision,
        decision: Dict[str, Any],
        current_agent: str,
        iteration: int
    ):
        """
        Emit routing decision to UI for visibility.
        
        Args:
            next_step: NextStepDecision enum (or string)
            decision: Routing decision dict
            current_agent: Current agent name
            iteration: Current iteration number
        """
        reasoning = decision.get("reasoning", "")
        next_agent = decision.get("next_agent")
        
        # Safely convert next_step to enum if it's a string
        if isinstance(next_step, str):
            try:
                next_step = NextStepDecision[next_step.upper()]
            except (KeyError, AttributeError):
                logger.warning(f"[MULTI-AGENT] Unknown next_step string: {next_step}")
                # Default to TASK_COMPLETE if unknown
                next_step = NextStepDecision.TASK_COMPLETE
        
        # Create user-friendly message based on decision type
        if next_step == NextStepDecision.TASK_COMPLETE:
            emoji = "🎉"
            message = f"{emoji} **Goal Achieved!** {reasoning[:200]}"
        elif next_step == NextStepDecision.SWITCH_AGENT:
            emoji = "🔄"
            message = f"{emoji} **Switching**: {current_agent} → {next_agent}\n💡 {reasoning[:200]}"
        elif next_step == NextStepDecision.CONTINUE_SAME_AGENT:
            emoji = "🔁"
            message = f"{emoji} **{current_agent.capitalize()} continues**\n💡 {reasoning[:200]}"
        elif next_step == NextStepDecision.NEEDS_USER_INPUT:
            emoji = "❓"
            message = f"{emoji} **Needs your input**: {reasoning[:200]}"
        else:
            emoji = "🤔"
            message = f"{emoji} **Decision**: {reasoning[:200]}"
        
        # Convert enum to string for JSON serialization
        next_step_str = next_step.value if hasattr(next_step, 'value') else str(next_step)
        
        self.status_emitter.emit_status(
            stage="executing",
            message=message,
            details={
                "type": "routing_decision",
                "next_step": next_step_str,
                "next_agent": next_agent,
                "current_agent": current_agent,
                "reasoning": reasoning,
                "iteration": iteration,
                "confidence": decision.get("confidence", 0.8)
            }
        )