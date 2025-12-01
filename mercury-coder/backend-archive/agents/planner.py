"""
Planner agent - creates detailed task plans from goals.
"""

import logging
import re
import os
from typing import Dict, List, Any, Optional
import json
import uuid

from .base import BaseAgent
from .errors import AgentError
from .utils import extract_file_references
from .orchestration.tool_registry import ToolRegistry
from .code_intelligence import CodeIntelligence

logger = logging.getLogger("mercury.agents.planner")

# Try to import json_repair for better JSON parsing fallback
try:
    from json_repair import repair_json
    JSON_REPAIR_AVAILABLE = True
except ImportError:
    JSON_REPAIR_AVAILABLE = False
    logger.warning("json_repair not available - using standard JSON parsing only")


class PlannerAgent(BaseAgent):
    """Agent that creates detailed task plans."""
    
    def __init__(
        self,
        memory_manager=None,
        tool_executor=None,
        tool_recommender=None,
        file_graph=None,
        pattern_matcher=None,
        proactive_search_manager=None
    ):
        super().__init__(
            name="planner",
            role="Task Planner - Breaks down goals into actionable task lists",
            tools=ToolRegistry.get_tools_for_agent("planner"),  # Tools for understanding codebase
            memory_manager=memory_manager,
            tool_executor=tool_executor,
            tool_recommender=tool_recommender
        )
        self.file_graph = file_graph
        self.pattern_matcher = pattern_matcher
        self.proactive_search_manager = proactive_search_manager
        
        # Initialize code intelligence for AST-based planning
        # Get AST tools from tool executor if available
        ast_tools = None
        if tool_executor and hasattr(tool_executor, 'ast_tools'):
            ast_tools = tool_executor.ast_tools
        self.code_intelligence = CodeIntelligence(ast_tools=ast_tools)
    
    def get_system_prompt(self) -> str:
        """Get planner-specific system prompt."""
        base = super().get_system_prompt()
        return f"""{base}

You are a PLANNER agent. Your job is to:
1. Understand the user's goal or request
2. Break it down into specific, actionable tasks
3. Create a detailed task list with dependencies
4. Assign each task to the appropriate agent (researcher, coder, analyzer)

ENHANCED PLANNING CAPABILITIES:

**Dependency Scanning:**
- Before planning, scan file dependencies to understand what files import/use target files
- Identify files that will be affected by changes
- Map interface boundaries and component relationships
- Detect circular dependencies that could cause issues
- Use get_file_dependencies and find_related_files tools to gather this information

**Error Prediction:**
- Predict potential failure points before they happen
- Identify risky changes that might break existing functionality
- Suggest validation steps to catch errors early
- Include error handling in task plans
- Consider common error patterns: import errors, API errors, database errors, async/await issues

**Interface Mapping:**
- Extract API endpoints used in the codebase
- Map function signatures and their contracts
- Track interface boundaries between components
- Understand how different parts of the system interact
- Use get_component_boundaries to understand component structure

**Pattern Matching:**
- Check for similar past tasks in memory
- Reuse successful patterns from previous implementations
- Learn from past mistakes and avoid repeating them
- Include pattern context in planning to guide implementation
- Use find_similar_patterns to discover related code patterns

When creating a plan:
- Be specific and actionable
- Identify dependencies between tasks AND between files
- Consider what information needs to be gathered first
- Think about validation steps and error handling
- Break large tasks into smaller, manageable pieces
- **CRITICAL**: Only assign tasks to 'researcher', 'coder', or 'analyzer' agents - NEVER assign tasks to 'planner' agent
- For simple conversational tasks (greetings, acknowledgments), assign them to 'researcher' agent
- Include error prediction and validation steps in your plan
- Reference similar patterns when available

Output your plan as a JSON structure with tasks.

IMPORTANT: Return ONLY valid JSON matching the required schema. No markdown code blocks, no explanations before or after.
"""
    
    def get_plan_json_schema(self) -> Dict[str, Any]:
        """Get JSON schema for structured outputs (guarantees valid JSON)."""
        # AWS Bedrock format for structured outputs
        return {
            "type": "json_schema",
            "json_schema": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Unique task identifier"
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Detailed task description"
                                    },
                                    "agent": {
                                        "type": "string",
                                        "enum": ["researcher", "coder", "analyzer"],
                                        "description": "Agent to handle this task"
                                    },
                                    "dependencies": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "List of task IDs this task depends on"
                                    },
                                    "expected_outcome": {
                                        "type": "string",
                                        "description": "What should be achieved by this task"
                                    }
                                },
                                "required": ["id", "description", "agent"]
                            }
                        }
                    },
                    "required": ["tasks"],
                    "additionalProperties": False
                }
            }
        }
    
    def set_executor(self, executor):
        """Set agent executor for LLM calls."""
        self.executor = executor
    
    async def execute(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a plan from a goal, or execute a task if description is provided.
        
        Args:
            task: Task dict with 'goal' key (for planning) or 'description' key (for execution) (validated)
            context: Additional context (validated)
            
        Returns:
            Plan structure with tasks (for planning) or execution result (for tasks)
        """
        # Validate inputs using Pydantic models
        from .base import validate_task_input, validate_context
        task = validate_task_input(task, self.name)
        context = validate_context(context, self.name)
        
        self.status = "working"
        self.current_task = task
        
        # Planner should ONLY handle planning tasks (requires goal field)
        # Reject any execution tasks (description without goal)
        description = task.get("description", "")
        goal = task.get("goal", "")
        
        # If it's an execution task (description but no goal), reject it
        if description and not goal:
            self.status = "error"
            agent_error = AgentError(
                message="Planner requires 'goal' for planning. Use researcher for execution tasks.",
                agent="planner",
                recoverable=False
            )
            return agent_error.to_dict()
        
        # Planning task requires goal
        if not goal:
            self.status = "error"
            agent_error = AgentError(
                message="No goal provided for planning",
                agent="planner",
                recoverable=False
            )
            return agent_error.to_dict()
        
        # Perform dependency scanning, error prediction, interface mapping, and pattern matching
        # Skip heavy analysis for simple creation tasks to speed up planning
        goal_lower = goal.lower()
        is_simple_creation = any(keyword in goal_lower for keyword in [
            "create", "write", "make", "build", "add"
        ]) and any(keyword in goal_lower for keyword in [
            "file", "files", "page", "script", "html", "css", "javascript", "js"
        ]) and len(goal.split()) <= 8
        
        if is_simple_creation:
            # Skip heavy dependency scanning for simple file creation
            planning_context = {
                "dependencies": "",
                "related_files": "",
                "error_predictions": "",
                "interfaces": "",
                "similar_patterns": ""
            }
        else:
            planning_context = self._gather_planning_context(goal, task, context)
        
        # Run proactive search (use cache if available)
        proactive_context = ""
        proactive_cache = context.get("proactive_cache") if context else None
        
        if proactive_cache is not None:
            # Use cached version
            cache_key = f"{goal}:{task.get('project_path') or ''}"
            proactive_context = proactive_cache.get(cache_key, "")
        elif self.proactive_search_manager:
            try:
                proactive_context = await self.proactive_search_manager.get_context_for_task(
                    goal,
                    task.get("project_path")
                )
                # Cache the result if cache is available
                if proactive_cache is not None:
                    cache_key = f"{goal}:{task.get('project_path') or ''}"
                    proactive_cache[cache_key] = proactive_context
            except Exception as e:
                logger.debug(f"Proactive search failed: {e}")
        
        # Use executor if available
        if hasattr(self, 'executor') and self.executor:
            # Build planning prompt with context
            planning_prompt = f"Create a detailed task plan to accomplish: {goal}\n\n"
            
            # Add proactive search context
            if proactive_context:
                planning_prompt += f"{proactive_context}\n\n"
            
            # Add planning context
            if planning_context.get("dependencies"):
                planning_prompt += f"## File Dependencies:\n{planning_context['dependencies']}\n\n"
            if planning_context.get("related_files"):
                planning_prompt += f"## Related Files:\n{planning_context['related_files']}\n\n"
            if planning_context.get("error_predictions"):
                planning_prompt += f"## Potential Issues to Watch For:\n{planning_context['error_predictions']}\n\n"
            if planning_context.get("interfaces"):
                planning_prompt += f"## API Interfaces:\n{planning_context['interfaces']}\n\n"
            if planning_context.get("similar_patterns"):
                planning_prompt += f"## Similar Past Implementations:\n{planning_context['similar_patterns']}\n\n"
            
            # Add previous recommendations if available (for follow-up requests)
            previous_recommendations = task.get("previous_recommendations", "")
            if previous_recommendations:
                planning_prompt += f"\n## Previous Research & Recommendations:\n{previous_recommendations}\n\n"
                planning_prompt += "Based on the above recommendations, create tasks to implement the suggested improvements.\n\n"
            
            # Add exploration findings if available
            exploration_findings = task.get("exploration_findings", {})
            if exploration_findings:
                if isinstance(exploration_findings, dict):
                    findings_text = str(exploration_findings)
                else:
                    findings_text = str(exploration_findings)
                planning_prompt += f"\n## Exploration Findings:\n{findings_text[:1000]}\n\n"
            
            planning_prompt += """Break this down into specific, actionable tasks. For each task, specify:
1. Task description (what needs to be done)
2. Which agent should handle it (researcher, coder, or analyzer)
3. Any dependencies (tasks that must complete first)
4. Expected outcome

CRITICAL AGENT ASSIGNMENT RULES:
- **FILE CREATION TASKS** (create, write, make, build, add files): ALWAYS assign to 'coder' agent
  Examples: "create landing page", "write HTML file", "add CSS file", "create script.js"
  → These should go DIRECTLY to coder, NO research tasks needed first
- **CODE MODIFICATION TASKS** (edit, modify, change, update existing code): Assign to 'coder' agent
- **RESEARCH/EXPLORATION TASKS** (read, find, search, explore, understand): Assign to 'researcher' agent
  → Only create research tasks if you need to understand EXISTING code before modifying it
- **ANALYSIS/VALIDATION TASKS** (check, validate, test, lint, analyze): Assign to 'analyzer' agent
- **SIMPLE CONVERSATIONAL TASKS** (greetings, acknowledgments): Assign to 'researcher' agent

IMPORTANT: 
- NEVER assign tasks to 'planner' agent - only assign to researcher, coder, or analyzer
- For NEW FILE CREATION: Skip research tasks - assign directly to coder. The coder can check if files exist quickly.
- For EXISTING FILE MODIFICATION: You may need 1 research task to understand the code, then assign to coder
- Keep plans SIMPLE: For "create landing page with HTML/CSS/JS", create 1-3 tasks max (all to coder)
- Don't over-plan: If the goal is to create files, the plan should be: "Create the files" → assign to coder

Return your plan as a JSON object with a 'tasks' array, each task having: id, description, agent, dependencies (array), expected_outcome."""
            
            planning_task = {
                "description": planning_prompt,
                "project_path": task.get("project_path")
            }
            
            # Use structured outputs for guaranteed valid JSON
            response_format = self.get_plan_json_schema()
            
            result = await self.executor.execute_agent_task(
                self,
                planning_task,
                context=context,
                response_format=response_format  # Pass structured output format
            )
            
            if result.get("success"):
                # Parse plan from result
                try:
                    # With structured outputs, the response should be valid JSON
                    # But we still need to extract it from the response structure
                    result_data = result.get("result", {})
                    plan_data = None
                    
                    # Strategy 1: Check if result already contains structured data (from structured outputs)
                    if isinstance(result_data, dict) and "tasks" in result_data:
                        plan_data = result_data
                        logger.info(f"✅ Using structured result data directly (from structured outputs)")
                    else:
                        # Strategy 2: Extract from message text (fallback for non-structured responses)
                        message = result.get("message", "")
                        if not message:
                            if isinstance(result_data, str):
                                message = result_data
                            elif isinstance(result_data, dict) and "message" in result_data:
                                message = result_data.get("message", "")
                        
                        if message:
                            # Try to find JSON in the message
                            # First, try simple JSON extraction
                            json_match = re.search(r'\{.*\}', message, re.DOTALL)
                            if json_match:
                                json_str = json_match.group(0)
                                try:
                                    plan_data = json.loads(json_str)
                                    logger.info(f"✅ Parsed JSON from message")
                                except json.JSONDecodeError:
                                    # Try json_repair if available
                                    if JSON_REPAIR_AVAILABLE:
                                        try:
                                            repaired = repair_json(json_str)
                                            plan_data = json.loads(repaired)
                                            logger.info(f"✅ Repaired and parsed JSON using json_repair")
                                        except Exception as e:
                                            logger.warning(f"JSON repair failed: {e}")
                                    else:
                                        logger.warning(f"Failed to parse JSON and json_repair not available")
                            
                            # If still no data, try parsing entire message
                            if plan_data is None:
                                try:
                                    plan_data = json.loads(message.strip())
                                    logger.info(f"✅ Parsed entire message as JSON")
                                except json.JSONDecodeError:
                                    # Try json_repair on full message
                                    if JSON_REPAIR_AVAILABLE:
                                        try:
                                            repaired = repair_json(message.strip())
                                            plan_data = json.loads(repaired)
                                            logger.info(f"✅ Repaired and parsed full message using json_repair")
                                        except Exception as e:
                                            logger.warning(f"JSON repair on full message failed: {e}")
                    
                    # Strategy 3: Check if result contains plan structure directly
                    if plan_data is None:
                        result_result = result.get("result", {})
                        if isinstance(result_result, dict):
                            if "tasks" in result_result or "plan" in result_result:
                                plan_data = result_result.get("plan") or result_result
                                logger.info(f"✅ Using result structure as plan data")
                    
                    if plan_data is None:
                        # Log the actual message for debugging
                        message_str = result.get("message", "")
                        logger.error(f"Failed to extract plan JSON. Message length: {len(message_str) if message_str else 0}, Result keys: {list(result.keys())}, Result type: {type(result.get('result'))}")
                        raise json.JSONDecodeError("Could not extract valid JSON from planner response", message_str or "", 0)
                    
                    plan_id = str(uuid.uuid4())
                    tasks = plan_data.get("tasks", [])
                    
                    self.status = "completed"
                    return {
                        "success": True,
                        "result": {
                            "plan_id": plan_id,
                            "goal": goal,
                            "tasks": tasks
                        },
                        "message": f"Plan created with {len(tasks)} tasks",
                        "next_action": "execute_plan"
                    }
                except (json.JSONDecodeError, KeyError) as e:
                    agent_error = AgentError.from_exception(e, agent="planner", recoverable=False)
                    logger.error(f"Failed to parse plan JSON: {e}", exc_info=True)
                    self.status = "error"
                    error_dict = agent_error.to_dict()
                    error_dict["raw_result"] = result
                    return error_dict
            else:
                self.status = "error"
                return result
        
        # Fallback: return basic structure
        self.log_work("planning", {"goal": goal})
        self.status = "completed"
        
        return {
            "success": True,
            "result": {
                "plan_id": str(uuid.uuid4()),
                "goal": goal,
                "tasks": []
            },
            "message": f"Plan created for: {goal}",
            "next_action": "execute_plan"
        }
    
    def _gather_planning_context(
        self,
        goal: str,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Gather planning context: dependencies, error predictions, interfaces, patterns.
        
        Returns:
            Dict with planning context information
        """
        planning_context = {
            "dependencies": "",
            "related_files": "",
            "error_predictions": "",
            "interfaces": "",
            "similar_patterns": ""
        }
        
        project_path = task.get("project_path")
        
        # 1. Dependency scanning (enhanced with AST analysis)
        if project_path:
            try:
                # Try to identify target files from goal
                target_files = self._extract_file_references(goal)
                
                if target_files:
                    dep_info = []
                    
                    # Use file graph for file-level dependencies
                    if self.file_graph:
                        for file_path in target_files[:3]:  # Limit to 3 files
                            deps = self.file_graph.get_file_dependencies(file_path)
                            if deps.get("dependencies") or deps.get("imported_by"):
                                dep_info.append(f"- {file_path}:")
                                if deps.get("dependencies"):
                                    dep_info.append(f"  Imports: {', '.join(deps['dependencies'][:5])}")
                                if deps.get("imported_by"):
                                    dep_info.append(f"  Imported by: {', '.join(deps['imported_by'][:5])}")
                    
                    # Use code intelligence for code-level dependencies (only for complex tasks)
                    # Skip AST analysis for simple tasks to speed up planning
                    goal_lower = goal.lower()
                    is_complex = any(word in goal_lower for word in [
                        "refactor", "restructure", "modify", "update", "change existing"
                    ])
                    
                    if is_complex:
                        for file_path in target_files[:2]:  # Limit to 2 files for AST analysis
                            try:
                                full_path = os.path.join(project_path, file_path) if project_path else file_path
                                if os.path.exists(full_path):
                                    code_deps = self.code_intelligence.get_dependencies_from_code(full_path)
                                    if code_deps.get("success"):
                                        deps_data = code_deps.get("dependencies", {})
                                        if deps_data.get("all"):
                                            dep_info.append(f"- {file_path} (code-level dependencies):")
                                            for imp in deps_data.get("all", [])[:5]:
                                                module = imp.get("module", "")
                                                name = imp.get("name", "")
                                                if name:
                                                    dep_info.append(f"  {name} from {module}")
                                                else:
                                                    dep_info.append(f"  {module}")
                            except Exception as e:
                                logger.debug(f"Code-level dependency analysis failed for {file_path}: {e}")
                    
                    if dep_info:
                        planning_context["dependencies"] = "\n".join(dep_info)
            except Exception as e:
                logger.debug(f"Dependency scanning failed: {e}")
        
        # 2. Find related files
        if self.file_graph and project_path:
            try:
                target_files = self._extract_file_references(goal)
                if target_files:
                    related = set()
                    for file_path in target_files[:2]:
                        related_files = self.file_graph.find_related_files(file_path, max_depth=2)
                        related.update(related_files[:5])  # Limit results
                    
                    if related:
                        planning_context["related_files"] = "\n".join([f"- {f}" for f in list(related)[:10]])
            except Exception as e:
                logger.debug(f"Related files search failed: {e}")
        
        # 3. Error prediction
        error_predictions = self._predict_errors(goal, task)
        if error_predictions:
            planning_context["error_predictions"] = "\n".join([f"- {pred}" for pred in error_predictions])
        
        # 4. Interface mapping (enhanced with AST analysis)
        if project_path:
            try:
                target_files = self._extract_file_references(goal)
                if target_files:
                    interfaces = []
                    
                    # Use file graph for API endpoints
                    if self.file_graph:
                        for file_path in target_files[:2]:
                            node = self.file_graph.nodes.get(file_path)
                            if node and node.api_endpoints:
                                interfaces.extend([f"- {ep}" for ep in node.api_endpoints[:5]])
                    
                    # Use code intelligence for function/class interfaces (only for complex tasks)
                    # Skip AST analysis for simple tasks to speed up planning
                    goal_lower = goal.lower()
                    is_complex = any(word in goal_lower for word in [
                        "refactor", "restructure", "modify", "update", "change existing"
                    ])
                    
                    if is_complex:
                        for file_path in target_files[:2]:
                            try:
                                full_path = os.path.join(project_path, file_path) if project_path else file_path
                                if os.path.exists(full_path):
                                    boundaries = self.code_intelligence.detect_interface_boundaries(full_path)
                                    if boundaries.get("success"):
                                        public = boundaries.get("public_interface", {})
                                        for func in public.get("functions", [])[:5]:
                                            func_name = func.get("name", "")
                                            args = func.get("args", [])
                                            interfaces.append(f"- {func_name}({', '.join(args)})")
                                        for cls in public.get("classes", [])[:3]:
                                            cls_name = cls.get("name", "")
                                            interfaces.append(f"- class {cls_name}")
                            except Exception as e:
                                logger.debug(f"Interface detection failed for {file_path}: {e}")
                    
                    if interfaces:
                        planning_context["interfaces"] = "\n".join(interfaces)
            except Exception as e:
                logger.debug(f"Interface mapping failed: {e}")
        
        # 5. Pattern matching
        if self.pattern_matcher:
            try:
                similar = self.pattern_matcher.find_similar_patterns(goal, project_path)
                if similar:
                    patterns = [f"- {p.get('description', 'Similar pattern found')}" for p in similar[:3]]
                    planning_context["similar_patterns"] = "\n".join(patterns)
            except Exception as e:
                logger.debug(f"Pattern matching failed: {e}")
        
        # Also check memory for similar past tasks
        if self.memory_manager:
            try:
                memory_context = self.memory_manager.get_context_for_query(goal, project_path, limit=3)
                if memory_context:
                    # Extract similar task summaries
                    if "Similar Past Tasks:" in memory_context:
                        planning_context["similar_patterns"] += "\n" + memory_context.split("Similar Past Tasks:")[1][:500]
            except Exception as e:
                logger.debug(f"Memory pattern search failed: {e}")
        
        return planning_context
    
    def _extract_file_references(self, goal: str) -> List[str]:
        """Extract file references from goal text using shared utility."""
        return extract_file_references(goal)
    
    def _predict_errors(self, goal: str, task: Dict[str, Any]) -> List[str]:
        """Predict potential errors or issues."""
        predictions = []
        goal_lower = goal.lower()
        
        # Common error patterns
        if "import" in goal_lower or "dependency" in goal_lower:
            predictions.append("Import errors: Check if all required modules are available")
        
        if "api" in goal_lower or "endpoint" in goal_lower:
            predictions.append("API errors: Verify endpoint URLs and authentication")
        
        if "database" in goal_lower or "db" in goal_lower:
            predictions.append("Database errors: Check connection and schema compatibility")
        
        if "test" in goal_lower:
            predictions.append("Test failures: Ensure test environment is properly configured")
        
        if "refactor" in goal_lower or "restructure" in goal_lower:
            predictions.append("Breaking changes: Verify all dependent code is updated")
        
        if "async" in goal_lower or "await" in goal_lower:
            predictions.append("Async/await errors: Ensure proper async handling")
        
        return predictions

