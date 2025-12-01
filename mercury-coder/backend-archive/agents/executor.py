"""
Agent executor - connects agents to LLM and tool execution.
"""

import logging
import json
from typing import Dict, List, Any, Optional
import asyncio

from .base import BaseAgent
from .task import Task, TaskStatus
from .task_classifier import TaskClassifier
from .loop_detector import LoopDetector
from .errors import AgentError
from .tool_conflict_detector import group_tools_by_conflicts

logger = logging.getLogger("mercury.agents.executor")


class AgentExecutor:
    """Executes agent tasks using LLM and tools."""
    
    def __init__(
        self,
        model_id: str,
        invoke_bedrock_model,
        tool_executor,
        all_tools: List[Dict[str, Any]],
        tool_callback: Optional[callable] = None,
        feedback_loop_manager=None
    ):
        """
        Initialize agent executor.
        
        Args:
            model_id: Bedrock model ID
            invoke_bedrock_model: Function to invoke Bedrock model
            tool_executor: Tool executor instance
            all_tools: All available tool definitions
            tool_callback: Optional callback to notify about tool executions
            feedback_loop_manager: FeedbackLoopManager instance for automatic refinement
        """
        self.model_id = model_id
        self.invoke_bedrock_model = invoke_bedrock_model
        self.tool_executor = tool_executor
        self.all_tools = all_tools
        self.tool_callback = tool_callback
        self.feedback_loop_manager = feedback_loop_manager
    
    async def execute_agent_task(
        self,
        agent: BaseAgent,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        max_iterations: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,  # Structured outputs support
        model_id: Optional[str] = None  # NEW: Override model for this specific task
    ) -> Dict[str, Any]:
        """
        Execute an agent task using LLM and tools.
        
        Args:
            agent: Agent instance
            task: Task dictionary
            context: Additional context
            max_iterations: Maximum tool execution iterations (None = auto-detect from complexity)
            response_format: Optional response format for structured outputs
            model_id: Optional model ID to use (overrides default)
            
        Returns:
            Task result
        """
        # Use provided model_id or fall back to default
        execution_model_id = model_id or self.model_id
        # Determine max_iterations from task complexity if not provided
        if max_iterations is None:
            max_iterations = TaskClassifier.get_max_iterations(task)
        
        # Get agent's available tools (enhanced with semantic recommendations)
        task_description = task.get("description", "")
        available_tools = agent.get_enhanced_tools(self.all_tools, task_description)
        
        # Build system prompt
        system_prompt = agent.get_system_prompt()
        
        # Add enhanced context from memory/RAG/vector search/conversation history
        context_str = agent.get_context_for_task(
            task_description,
            task.get("project_path"),
            limit=8,  # Get more context
            session_id=context.get("session_id") if context else None
        )
        if context_str:
            system_prompt += f"\n\n{context_str}\n"
        
        # Add tool descriptions with recommendations if tool_recommender available
        if hasattr(agent, 'tool_recommender') and agent.tool_recommender:
            try:
                tool_descriptions = agent.tool_recommender.get_tool_descriptions_for_prompt(
                    recommended_tools=agent.tool_recommender.recommend_tools(
                        query=task_description,
                        limit=5,
                        use_vector_search=True
                    ) if task_description else None,
                    include_all=False  # Only include recommended tools in descriptions
                )
                if tool_descriptions:
                    system_prompt += f"\n{tool_descriptions}\n"
            except Exception as e:
                logger.debug(f"Could not add tool descriptions: {e}")
        
        # Build initial message
        task_description = task.get("description", "")
        context_info = ""
        if context:
            if context.get("research_findings"):
                context_info += f"\nResearch Findings:\n{context['research_findings']}\n"
            completed_tasks = context.get('completed_tasks', [])
            if completed_tasks:
                # Convert to strings in case they're integers
                completed_tasks_str = [str(task_id) for task_id in completed_tasks]
                context_info += f"\nCompleted Tasks: {', '.join(completed_tasks_str)}\n"
        
        # Check if this is a conversational task (no tools needed)
        # Use TaskClassifier for consistent detection, but also respect explicit flag
        is_conversational = task.get("conversational", False) or TaskClassifier.is_conversational(task_description)
        
        if is_conversational:
            # Simple conversational response - no tools, direct answer
            user_message = task_description
            # Don't provide tools for conversational tasks
            available_tools = []
        else:
            user_message = f"""Task: {task_description}

{context_info}

Please accomplish this task using the available tools. Be thorough and complete.
"""
        
        messages = [{"role": "user", "content": user_message}]
        
        # Execute with tool calling
        iteration = 0
        tool_call_history = []  # Track tool calls to detect loops
        loop_detector = LoopDetector(window_size=5)  # Pattern-based loop detection
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"[EXECUTOR] Iteration {iteration}/{max_iterations} for task: {task_description[:50]}...")
            
            # Call LLM with retry logic
            max_retries = 3
            retry_count = 0
            response = None
            
            while retry_count < max_retries:
                try:
                    response = await self.invoke_bedrock_model(
                        model_id=execution_model_id,
                        system_prompt=system_prompt,
                        messages=messages,
                        max_tokens=8192,
                        tools=available_tools,
                        enable_thinking=True,  # Enable thinking mode for better reasoning
                        response_format=response_format  # Pass through structured output format
                    )
                    # Success - break out of retry loop
                    break
                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)
                    error_type = type(e).__name__
                    logger.warning(f"LLM call failed (attempt {retry_count}/{max_retries}): {error_type}: {error_msg}")
                    
                    if retry_count >= max_retries:
                        # All retries exhausted
                        error_msg_full = f"LLM call failed after {max_retries} attempts: {error_type}: {error_msg}"
                        logger.error(error_msg_full)
                        agent_error = AgentError(
                            message=error_msg_full,
                            agent="executor",
                            recoverable=False
                        )
                        return agent_error.to_dict()
                    
                    # Exponential backoff: wait 1s, 2s, 4s
                    wait_time = 2 ** (retry_count - 1)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
            
            if response is None:
                agent_error = AgentError(
                    message="Failed to get response from LLM after retries",
                    agent="executor",
                    recoverable=False
                )
                return agent_error.to_dict()
            
            # Validate response
            if not response:
                logger.error("LLM returned None response")
                agent_error = AgentError(
                    message="Empty response from LLM",
                    agent="executor",
                    recoverable=False
                )
                return agent_error.to_dict()
            
            # Extract content and tool calls
            content = response.get("content", [])
            if not content:
                # Check if there's an error in the response
                if "error" in response:
                    error_msg = response.get("error", "Unknown LLM error")
                    logger.error(f"LLM returned error: {error_msg}")
                    agent_error = AgentError(
                        message=error_msg,
                        agent="executor",
                        recoverable=False
                    )
                    return agent_error.to_dict()
                # Empty content - might be a timeout or incomplete response
                logger.warning("LLM returned empty content")
                agent_error = AgentError(
                    message="LLM returned empty content",
                    agent="executor",
                    recoverable=False
                )
                return agent_error.to_dict()
            
            tool_calls = []
            text_parts = []
            
            for block in content:
                if block.get("type") == "tool_use":
                    tool_calls.append(block)
                elif block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            
            # If we have text response and no tools, we're done
            if text_parts and not tool_calls:
                final_text = "".join(text_parts)
                
                # Early stopping: If we've written files and LLM says we're done, stop immediately
                has_written_files = any(
                    any(tc in ["write_file", "edit_file"] for tc in tc_round.get("tools", []))
                    for tc_round in tool_call_history
                )
                
                # Check if LLM explicitly says task is complete
                completion_indicators = [
                    "completed", "done", "finished", "ready", "created successfully",
                    "task complete", "all done", "successfully created"
                ]
                text_lower = final_text.lower()
                is_complete = any(indicator in text_lower for indicator in completion_indicators)
                
                if has_written_files and (is_complete or iteration >= 2):
                    logger.info(f"[EXECUTOR] Early stopping: Files written and task appears complete after {iteration} iterations")
                    return {
                        "success": True,
                        "result": {"message": final_text},
                        "message": final_text,
                        "early_stop": True
                    }
                
                return {
                    "success": True,
                    "result": {"message": final_text},
                    "message": final_text
                }
            
            # Execute tools
            if tool_calls:
                # Detect loops using pattern-based detection
                loop_detected = loop_detector.add_action(tool_calls)
                
                if loop_detected:
                    logger.error(f"[EXECUTOR] Loop detected! Repetitive pattern in tool calls. Stopping.")
                    # Try to extract any useful information from the last response
                    if text_parts:
                        final_text = "".join(text_parts)
                        return {
                            "success": True,
                            "result": {"message": final_text},
                            "message": final_text,
                            "warning": "Loop detected but task may be complete"
                        }
                    agent_error = AgentError(
                        message="Loop detected: repetitive pattern in tool calls",
                        agent="executor",
                        recoverable=True
                    )
                    error_dict = agent_error.to_dict()
                    error_dict["result"] = {"message": "Task stuck in loop making repetitive tool calls"}
                    return error_dict
                
                # Track tool calls
                tool_call_history.append({
                    "iteration": iteration,
                    "tools": [tc.get("name") for tc in tool_calls]
                })
                
                # Early stopping: Check if task is complete
                # For creation tasks, if files were written successfully, we're likely done
                write_tools = [tc for tc in tool_calls if tc.get("name") in ["write_file", "edit_file"]]
                if write_tools:
                    # Check if this is a creation task
                    description_lower = task_description.lower()
                    is_creation_task = any(keyword in description_lower for keyword in [
                        "create", "write", "make", "build", "add", "new file", "new files"
                    ])
                    
                    # If we've written files and it's a creation task, check if we should stop early
                    if is_creation_task and iteration >= 2:
                        # After writing files, if we have 2+ iterations, we're likely done
                        logger.info(f"[EXECUTOR] Files written in creation task after {iteration} iterations. Checking if task is complete...")
                        # Continue to next iteration to see if LLM confirms completion
                        # But we'll stop early if LLM says it's done
                
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": content
                })
                
                # Group tools by conflicts using dynamic detection
                # This considers actual file paths and relationships, not just tool names
                file_graph = getattr(agent, 'file_graph', None) if hasattr(agent, 'file_graph') else None
                parallel_calls, sequential_calls = group_tools_by_conflicts(tool_calls, file_graph)
                
                tool_results = []
                
                # Execute parallel tools concurrently
                if parallel_calls:
                    logger.info(f"[EXECUTOR] Executing {len(parallel_calls)} tools in parallel")
                    
                    async def execute_tool_async(tool_call):
                        tool_name = tool_call.get("name")
                        tool_input = tool_call.get("input", {})
                        tool_id = tool_call.get("id")
                        
                        # Notify about tool execution start (single callback per tool)
                        if self.tool_callback:
                            try:
                                self.tool_callback({
                                    "type": "tool_progress",
                                    "tool_use_id": tool_id,
                                    "name": tool_name,
                                    "input": tool_input,
                                    "status": "started"
                                })
                            except Exception as e:
                                logger.warning(f"Tool callback error: {e}")
                        
                        try:
                            # Run tool in thread pool to avoid blocking
                            result = await asyncio.to_thread(
                                self.tool_executor.execute,
                                tool_name,
                                tool_input
                            )
                            
                            logger.info(f"[EXECUTOR] Parallel tool {tool_name} completed")
                            
                            # Notify about tool completion (single callback)
                            if self.tool_callback:
                                try:
                                    self.tool_callback({
                                        "type": "tool_progress",
                                        "tool_use_id": tool_id,
                                        "name": tool_name,
                                        "input": tool_input,
                                        "result": result,
                                        "status": "completed" if result.get("success") else "error"
                                    })
                                except Exception as e:
                                    logger.warning(f"Tool callback error: {e}")
                            
                            return {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": json.dumps(result)
                            }
                        except Exception as e:
                            logger.error(f"Parallel tool execution error: {e}", exc_info=True)
                            error_result = {"success": False, "error": str(e)}
                            
                            # Notify about tool execution error (single callback)
                            if self.tool_callback:
                                try:
                                    self.tool_callback({
                                        "type": "tool_progress",
                                        "tool_use_id": tool_id,
                                        "name": tool_name,
                                        "input": tool_input,
                                        "result": error_result,
                                        "status": "error"
                                    })
                                except Exception as e:
                                    logger.warning(f"Tool callback error: {e}")
                            
                            return {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": json.dumps(error_result)
                            }
                    
                    # Execute all parallel tools concurrently
                    parallel_results = await asyncio.gather(*[
                        execute_tool_async(tc) for tc in parallel_calls
                    ])
                    tool_results.extend(parallel_results)
                
                # Execute sequential tools one by one (to avoid conflicts)
                if sequential_calls:
                    logger.info(f"[EXECUTOR] Executing {len(sequential_calls)} tools sequentially")
                    
                    for tool_call in sequential_calls:
                        tool_name = tool_call.get("name")
                        tool_input = tool_call.get("input", {})
                        tool_id = tool_call.get("id")
                        
                        logger.info(f"[EXECUTOR] Executing sequential tool: {tool_name}")
                        
                        # Notify about tool execution start (single callback per tool)
                        if self.tool_callback:
                            try:
                                self.tool_callback({
                                    "type": "tool_progress",
                                    "tool_use_id": tool_id,
                                    "name": tool_name,
                                    "input": tool_input,
                                    "status": "started"
                                })
                            except Exception as e:
                                logger.warning(f"Tool callback error: {e}")
                        
                        try:
                            result = self.tool_executor.execute(tool_name, tool_input)
                            # Check if the tool result indicates completion
                            if isinstance(result, dict) and result.get("success") and tool_name in ["read_file", "codebase_search"]:
                                # For read/search operations, check if we have enough info
                                result_content = str(result.get("content", "") or result.get("result", ""))
                                if len(result_content) > 1000:  # Substantial content retrieved
                                    logger.info(f"[EXECUTOR] Tool {tool_name} returned substantial content ({len(result_content)} chars)")
                        except Exception as e:
                            logger.error(f"Tool execution error: {e}", exc_info=True)
                            result = {"success": False, "error": str(e)}
                        
                        # Notify about tool execution completion (single callback)
                        if self.tool_callback:
                            try:
                                self.tool_callback({
                                    "type": "tool_progress",
                                    "tool_use_id": tool_id,
                                    "name": tool_name,
                                    "input": tool_input,
                                    "result": result,
                                    "status": "completed" if result.get("success") else "error"
                                })
                            except Exception as e:
                                logger.warning(f"Tool callback error: {e}")
                        
                        # Add result
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result)
                        })
                        
                        # Check if this was a write/edit operation and trigger feedback loop if needed
                        # Run feedback loop asynchronously (non-blocking) with timeout
                        # Only run for complex tasks or when explicitly needed - skip for simple file creation
                        description_lower = task_description.lower()
                        is_simple_creation = any(keyword in description_lower for keyword in [
                            "create", "write", "make", "build", "add"
                        ]) and any(keyword in description_lower for keyword in [
                            "file", "files", "page", "script", "html", "css", "javascript", "js"
                        ]) and len(task_description.split()) <= 8
                        
                        # Only run feedback loop for complex tasks or when there are obvious errors
                        should_run_feedback = not is_simple_creation or not result.get("success")
                        
                        if self.feedback_loop_manager and self.feedback_loop_manager.enabled and tool_name in ["write_file", "edit_file"] and should_run_feedback:
                            if result.get("success"):
                                file_path = tool_input.get("file_path") or tool_input.get("path", "")
                                if file_path:
                                    # Run feedback loop asynchronously (non-blocking) with shorter timeout
                                    async def run_feedback_loop():
                                        """Run feedback loop with timeout."""
                                        try:
                                            # Set shorter timeout for feedback loop operations (3 seconds instead of 5)
                                            check_result = await asyncio.wait_for(
                                                self.feedback_loop_manager.check_file(file_path),
                                                timeout=3.0
                                            )
                                            errors = check_result.get("errors", [])
                                            
                                            # Only refine if there are critical errors (syntax errors, not just warnings)
                                            critical_errors = [e for e in errors if "syntax" in str(e).lower() or "error" in str(e).lower()]
                                            
                                            if critical_errors:
                                                refinement_result = await asyncio.wait_for(
                                                    self.feedback_loop_manager.refine_file(
                                                        file_path,
                                                        errors=critical_errors
                                                    ),
                                                    timeout=3.0
                                                )
                                            else:
                                                refinement_result = {
                                                    "needs_refinement": False,
                                                    "errors": [],
                                                    "suggestions": []
                                                }
                                            
                                            # If refinement found critical issues, add to tool result
                                            if refinement_result.get("needs_refinement") or critical_errors:
                                                errors = refinement_result.get("errors", critical_errors)
                                                suggestions = refinement_result.get("suggestions", [])
                                                
                                                if errors or suggestions:
                                                    logger.info(f"[EXECUTOR] Feedback loop detected critical issues in {file_path}")
                                                    
                                                    # Add refinement context to tool result
                                                    if tool_results:
                                                        error_summary = "; ".join([e.get("message", str(e))[:100] for e in errors[:2]])  # Limit to 2 errors
                                                        suggestion_summary = "; ".join([s.get("message", str(s))[:100] for s in suggestions[:2]])  # Limit to 2 suggestions
                                                        
                                                        refinement_context = {
                                                            "needs_refinement": True,
                                                            "errors": error_summary,
                                                            "suggestions": suggestion_summary,
                                                            "file_path": file_path
                                                        }
                                                        
                                                        # Update tool result with refinement info
                                                        current_content = tool_results[-1].get("content", "{}")
                                                        try:
                                                            content_dict = json.loads(current_content) if isinstance(current_content, str) else current_content
                                                        except:
                                                            content_dict = {"result": current_content}
                                                        
                                                        content_dict["refinement"] = refinement_context
                                                        tool_results[-1]["content"] = json.dumps(content_dict)
                                                        
                                                        # Add refinement message to help LLM understand (only for critical errors)
                                                        if critical_errors:
                                                            messages.append({
                                                                "role": "user",
                                                                "content": f"CRITICAL: The file {file_path} has syntax errors that must be fixed:\n{error_summary}\n\nPlease fix these errors immediately."
                                                            })
                                        except asyncio.TimeoutError:
                                            logger.debug(f"Feedback loop timeout for {file_path}")
                                        except Exception as e:
                                            logger.debug(f"Feedback loop refinement check failed: {e}")
                                    
                                    # Run feedback loop asynchronously (fire and forget)
                                    asyncio.create_task(run_feedback_loop())
                
                # Add tool results as single user message (Claude API format)
                # All tool results must be batched in one message with array of tool_result objects
                if tool_results:
                    messages.append({
                        "role": "user",
                        "content": tool_results  # Array of {"type": "tool_result", "tool_use_id": "...", "content": "..."}
                    })
                
                # Detect if agent is over-analyzing without writing files
                # Check if we've done multiple read/list operations without any write operations
                read_ops = sum(1 for tc in tool_call_history if any(
                    tool_name in ["read_file", "list_directory", "file_exists", "codebase_search", "grep", "web_search", "fetch_web_page"]
                    for tool_name in tc.get("tools", [])
                ))
                write_ops = sum(1 for tc in tool_call_history if any(
                    tool_name in ["write_file", "edit_file"]
                    for tool_name in tc.get("tools", [])
                ))
                
                # If this looks like a creation task and we've read a lot without writing
                description_lower = task_description.lower()
                is_creation_task = any(keyword in description_lower for keyword in [
                    "create", "write", "make", "build", "add", "new file", "new files",
                    "landing page", "html", "css", "javascript", "script", "do a", "do "
                ])
                
                # AGGRESSIVE: Force execution on first iteration for creation tasks
                if is_creation_task and iteration == 1 and write_ops == 0:
                    logger.warning(f"[EXECUTOR] Creation task detected. Forcing immediate file writing on iteration 1.")
                    messages.append({
                        "role": "user",
                        "content": "STOP! You are doing a FILE CREATION task. Your VERY NEXT tool call MUST be write_file to create the files. Do NOT research, do NOT analyze, do NOT check if files exist. Just write the files NOW with your first tool call!"
                    })
                elif is_creation_task and read_ops >= 2 and write_ops == 0 and iteration >= 2:
                    logger.error(f"[EXECUTOR] Agent still analyzing after 2 iterations! FORCING file write.")
                    messages.append({
                        "role": "user",
                        "content": "CRITICAL ERROR: You are WASTING TIME analyzing. This is a creation task - you have done {read_ops} read operations and ZERO write operations. STOP ANALYZING IMMEDIATELY. Your NEXT tool call MUST be write_file. Write the files NOW or the task will fail!"
                    })
                
                # Early stopping: If files were written successfully and we're past iteration 2, prompt for completion
                has_written_files = any(
                    any(tc in ["write_file", "edit_file"] for tc in tc_round.get("tools", []))
                    for tc_round in tool_call_history
                )
                
                if has_written_files and iteration >= 2:
                    # Check if we've done enough - prompt for completion check
                    logger.info(f"[EXECUTOR] Files written after {iteration} iterations. Prompting for completion check.")
                    messages.append({
                        "role": "user",
                        "content": "You have written the files. Please confirm if the task is complete. If yes, provide a brief summary and stop. If no, explain what else is needed."
                    })
                
                # If we're getting close to max iterations, encourage completion
                elif iteration >= max_iterations - 1:
                    logger.warning(f"[EXECUTOR] Approaching max iterations ({iteration}/{max_iterations}). Adding completion prompt.")
                    messages.append({
                        "role": "user",
                        "content": "You are at the maximum number of iterations. Please provide a final summary of what you've accomplished and complete the task now."
                    })
            else:
                # No tools, just text - we're done
                final_text = "".join(text_parts)
                return {
                    "success": True,
                    "result": {"message": final_text},
                    "message": final_text
                }
        
        # Max iterations reached
        logger.error(f"[EXECUTOR] Max iterations ({max_iterations}) reached for task: {task_description[:50]}...")
        logger.error(f"[EXECUTOR] Tool call history: {len(tool_call_history)} tool call rounds")
        
        # Try to extract any useful information from the last response
        if text_parts:
            final_text = "".join(text_parts)
            logger.warning(f"[EXECUTOR] Returning partial result with text content")
            return {
                "success": True,
                "result": {"message": final_text},
                "message": final_text,
                "warning": "Max iterations reached but some work may be complete"
            }
        
        agent_error = AgentError(
            message=f"Maximum iterations ({max_iterations}) reached. Tool calls made: {len(tool_call_history)} rounds.",
            agent="executor",
            recoverable=True
        )
        return agent_error.to_dict()

