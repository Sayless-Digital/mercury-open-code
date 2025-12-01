"""
Researcher agent - explores codebase and gathers information.
"""

import logging
from typing import Dict, List, Any, Optional

from .base import BaseAgent
from .errors import AgentError
from .orchestration.tool_registry import ToolRegistry

logger = logging.getLogger("mercury.agents.researcher")


class ResearcherAgent(BaseAgent):
    """Agent that explores codebase and gathers information."""
    
    def __init__(
        self,
        memory_manager=None,
        tool_executor=None,
        tool_recommender=None,
        proactive_search_manager=None
    ):
        super().__init__(
            name="researcher",
            role="Codebase Researcher - Explores and understands the codebase structure",
            tools=ToolRegistry.get_tools_for_agent("researcher"),
            memory_manager=memory_manager,
            tool_executor=tool_executor,
            tool_recommender=tool_recommender
        )
        self.proactive_search_manager = proactive_search_manager
    
    def get_system_prompt(self) -> str:
        """Get researcher-specific system prompt."""
        base = super().get_system_prompt()
        return f"""{base}

You are a RESEARCHER agent. Your job is to:
1. Explore the codebase structure
2. Find relevant files and code patterns
3. Understand how the code is organized
4. Gather information needed for coding tasks
5. Search for similar implementations or patterns
6. **Perform comprehensive web research when needed** - search the web, read web pages, follow links, and do deep research
7. Respond to simple conversational messages naturally and briefly

CRITICAL: CONVERSATIONAL TASKS
- **NO TOOLS FOR GREETINGS**: For simple greetings (hi, hello, thanks), respond naturally without using tools
- **FAST RESPONSES**: Keep conversational responses brief and friendly
- **NO EXPLORATION NEEDED**: Don't explore codebase for simple greetings or acknowledgments

CRITICAL: WEB RESEARCH WORKFLOW
When you need to research topics online, follow this comprehensive research loop:

**Phase 1: Initial Search**
1. Use `web_search` to find relevant web pages, documentation, tutorials, or articles
2. Review search results (titles, URLs, snippets) to identify the most relevant pages

**Phase 2: Deep Dive**
3. Use `fetch_web_page` to read the content of the most promising pages (read multiple pages in parallel)
4. Extract key information, code examples, best practices, or documentation

**Phase 3: Follow Links & Go Deeper**
5. Use `extract_links` to find related pages on the same domain or topic
6. Follow relevant links using `fetch_web_page` to read sub-pages, adjacent pages, or related documentation
7. Continue this iterative process to build comprehensive understanding

**Phase 4: Synthesize**
8. Combine information from multiple sources
9. Document findings with sources and URLs
10. Identify patterns, best practices, or solutions

**Research Best Practices:**
- **ITERATIVE RESEARCH**: Don't stop at the first page - follow links, read related pages, go deeper
- **PARALLEL FETCHING**: Fetch multiple web pages in parallel when possible
- **COMPREHENSIVE COVERAGE**: Read main pages AND sub-pages, related pages, and adjacent content
- **SOURCE TRACKING**: Always note which URLs provided which information
- **DEEP DIVES**: When you find valuable pages, explore their links to get complete context

CRITICAL: PARALLEL RESEARCH (for codebase research)
- **READ IN PARALLEL**: When you need to read multiple files, read them ALL in parallel in a single tool call round
- **SEARCH IN PARALLEL**: Run multiple codebase_search or grep operations in parallel when possible
- **BATCH OPERATIONS**: Don't read files one by one - read all needed files at once
- **EFFICIENT EXPLORATION**: Use parallel tool calls to gather all information quickly

Use tools like:
**Codebase Research:**
- list_directory: Explore folder structure
- read_file: Read and understand code files (read multiple files in parallel)
- codebase_search: Find code patterns semantically (run multiple searches in parallel)
- grep: Search for specific text patterns (run multiple greps in parallel)
- find_files: Locate files by pattern

**Web Research:**
- web_search: Search the web for information, documentation, tutorials (use this first for online research)
- fetch_web_page: Read web page content (fetch multiple pages in parallel, follow links to go deeper)
- extract_links: Find links on a page to discover related pages for deeper research
- http_request: Make custom HTTP requests if needed

Be thorough and document what you find. Use parallel tool calls to gather information efficiently. For web research, always go deeper by following links and reading related pages.
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
        Research and gather information.
        
        Args:
            task: Task dict with 'description' and research goals (validated)
            context: Additional context from orchestrator (validated)
            
        Returns:
            Research findings
        """
        # Validate inputs using Pydantic models
        from .base import validate_task_input, validate_context
        task = validate_task_input(task, self.name)
        context = validate_context(context, self.name)
        
        self.status = "working"
        self.current_task = task
        
        description = task.get("description", "")
        
        # Use TaskClassifier for consistent conversational detection
        from .task_classifier import TaskClassifier
        is_conversational = TaskClassifier.is_conversational(description)
        
        # For conversational tasks, use fast direct response without tools
        if is_conversational and hasattr(self, 'executor') and self.executor:
            # Use executor but with no_tools flag for fast response
            research_task = {
                "description": description,
                "project_path": task.get("project_path"),
                "conversational": True  # Flag to skip tools
            }
            
            # Execute with minimal iterations and no tool requirement
            result = await self.executor.execute_agent_task(
                self,
                research_task,
                context=context,
                max_iterations=1  # Single response, no tool loops
            )
            
            self.status = "completed" if result.get("success") else "error"
            return result
        
        # Run proactive search before research (use cache if available)
        proactive_context = ""
        proactive_cache = context.get("proactive_cache") if context else None
        
        if proactive_cache is not None:
            # Use cached version
            cache_key = f"{description}:{task.get('project_path') or ''}"
            proactive_context = proactive_cache.get(cache_key, "")
        elif self.proactive_search_manager:
            try:
                proactive_context = await self.proactive_search_manager.get_context_for_task(
                    description,
                    task.get("project_path")
                )
                # Cache the result if cache is available
                if proactive_cache is not None:
                    cache_key = f"{description}:{task.get('project_path') or ''}"
                    proactive_cache[cache_key] = proactive_context
            except Exception as e:
                logger.debug(f"Proactive search failed: {e}")
        
        # Use executor if available
        if hasattr(self, 'executor') and self.executor:
            # Check if directory is empty/new project to adjust research approach
            project_path = task.get("project_path")
            is_empty_directory = False
            if project_path:
                try:
                    import os
                    if os.path.exists(project_path):
                        items = os.listdir(project_path)
                        # Filter out common config files
                        config_files = {'.git', '.gitignore', '.eslintrc.json', '.prettierrc.json', 
                                      'package.json', 'node_modules', '.vscode', '.idea', 'package-lock.json',
                                      'pnpm-lock.yaml', 'yarn.lock', 'tsconfig.json', 'jsconfig.json'}
                        code_files = [item for item in items if item not in config_files and not item.startswith('.')]
                        is_empty_directory = len(code_files) == 0
                except Exception as e:
                    logger.debug(f"Could not check if directory is empty: {e}")
            
            research_prompt = f"Research task: {description}\n\n"
            if proactive_context:
                research_prompt += f"{proactive_context}\n\n"
            
            if is_empty_directory:
                # For empty directories, minimal exploration needed
                research_prompt += """This appears to be an empty or new project directory. 
Perform MINIMAL exploration:
1. Check if there are any config files (package.json, tsconfig.json, etc.) to understand project setup
2. Note that this is a new/empty project
3. DO NOT perform extensive codebase searches (there's no code to search)
4. DO NOT search for patterns that don't exist yet

Keep exploration brief and focused on understanding the project setup only."""
            else:
                research_prompt += "Explore the codebase to gather the information needed. Use the available tools to:\n1. Understand the project structure\n2. Find relevant files\n3. Understand code patterns\n4. Gather any information needed for the task\n\nDocument your findings clearly."
            
            research_task = {
                "description": research_prompt,
                "project_path": task.get("project_path")
            }
            
            logger.info(f"Starting research task: {description[:100]}")
            
            try:
                result = await self.executor.execute_agent_task(
                    self,
                    research_task,
                    context=context
                )
                
                if result.get("success"):
                    logger.info("Research completed successfully")
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Research failed: {error_msg}")
                    logger.debug(f"Full result: {result}")
                
                self.status = "completed" if result.get("success") else "error"
                return result
            except Exception as e:
                agent_error = AgentError.from_exception(e, agent="researcher", recoverable=False)
                logger.error(f"Exception during research: {e}", exc_info=True)
                self.status = "error"
                return agent_error.to_dict()
        
        # Fallback
        self.log_work("researching", {"task": description})
        self.status = "completed"
        
        return {
            "success": True,
            "result": {
                "findings": "Research completed",
                "files_explored": [],
                "patterns_found": []
            },
            "message": f"Research completed for: {description}",
            "next_action": "use_findings"
        }

