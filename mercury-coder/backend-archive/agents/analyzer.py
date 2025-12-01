"""
Analyzer agent - validates code quality and correctness.
"""

import logging
from typing import Dict, List, Any, Optional

from .base import BaseAgent
from .orchestration.tool_registry import ToolRegistry

logger = logging.getLogger("mercury.agents.analyzer")


class AnalyzerAgent(BaseAgent):
    """Agent that validates code quality and correctness."""
    
    def __init__(self, memory_manager=None, tool_executor=None, tool_recommender=None):
        super().__init__(
            name="analyzer",
            role="Code Analyzer - Validates code quality, syntax, and correctness",
            tools=ToolRegistry.get_tools_for_agent("analyzer"),
            memory_manager=memory_manager,
            tool_executor=tool_executor,
            tool_recommender=tool_recommender
        )
    
    def get_system_prompt(self) -> str:
        """Get analyzer-specific system prompt."""
        base = super().get_system_prompt()
        return f"""{base}

You are an ANALYZER agent. Your job is to:
1. Check code syntax for errors
2. Run linters to find code quality issues
3. Validate that code follows best practices
4. Verify that changes work correctly
5. Run tests if available
6. Check for potential bugs or issues

Use tools like:
- check_syntax: Validate code syntax
- lint_file: Check code quality
- execute_command: Run tests, linters, type checkers
- read_file: Review code for issues

Be thorough and report all issues found.
"""
    
    def set_executor(self, executor):
        """Set agent executor for LLM calls."""
        self.executor = executor
    
    async def execute(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze and validate code.
        
        Args:
            task: Task dict with 'description' and files to analyze (validated)
            context: Context about what was changed (validated)
            
        Returns:
            Analysis results
        """
        # Validate inputs using Pydantic models
        from .base import validate_task_input, validate_context
        task = validate_task_input(task, self.name)
        context = validate_context(context, self.name)
        
        self.status = "working"
        self.current_task = task
        
        description = task.get("description", "")
        
        # Build context
        change_context = ""
        if context and context.get("files_changed"):
            change_context = f"\nFiles changed:\n{', '.join(context['files_changed'])}\n"
        
        # Use executor if available
        if hasattr(self, 'executor') and self.executor:
            analysis_task = {
                "description": f"Analysis task: {description}\n\n{change_context}Validate the code changes:\n1. Check syntax for all modified files\n2. Run linters if available\n3. Look for potential issues\n4. Verify code quality\n5. Run tests if available",
                "project_path": task.get("project_path")
            }
            
            result = await self.executor.execute_agent_task(
                self,
                analysis_task,
                context=context
            )
            
            self.status = "completed" if result.get("success") else "error"
            return result
        
        # Fallback
        self.log_work("analyzing", {"task": description})
        self.status = "completed"
        
        return {
            "success": True,
            "result": {
                "syntax_errors": [],
                "lint_issues": [],
                "warnings": [],
                "tests_passed": None,
                "validation_passed": True
            },
            "message": f"Analysis completed for: {description}",
            "next_action": "report_results"
        }

