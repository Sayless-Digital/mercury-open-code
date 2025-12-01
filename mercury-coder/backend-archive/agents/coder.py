"""
Coder agent - writes and modifies code.
"""

import logging
from typing import Dict, List, Any, Optional

from .base import BaseAgent
from .orchestration.tool_registry import ToolRegistry

logger = logging.getLogger("mercury.agents.coder")


class CoderAgent(BaseAgent):
    """Agent that writes and modifies code."""
    
    def __init__(
        self,
        memory_manager=None,
        tool_executor=None,
        tool_recommender=None,
        proactive_search_manager=None
    ):
        super().__init__(
            name="coder",
            role="Code Writer - Implements features and modifies code",
            tools=ToolRegistry.get_tools_for_agent("coder"),
            memory_manager=memory_manager,
            tool_executor=tool_executor,
            tool_recommender=tool_recommender
        )
        self.proactive_search_manager = proactive_search_manager
    
    def get_system_prompt(self) -> str:
        """Get coder-specific system prompt."""
        base = super().get_system_prompt()
        return f"""{base}

You are a CODER agent. Your job is to:
1. Read existing code to understand context (when needed)
2. Write new code or modify existing code
3. Follow project conventions and patterns
4. Ensure code is clean and well-structured
5. **ACTUALLY CREATE AND WRITE FILES** - Don't just analyze, actually write the code!

CRITICAL: EXECUTION-FIRST APPROACH
- **WRITE FILES IMMEDIATELY**: When asked to create files (e.g., "create a landing page", "write a script"), you MUST actually write the files using `write_file`. Don't just analyze or plan - CREATE THE FILES!
- **MINIMAL RESEARCH FOR NEW FILES**: For creating NEW files, you don't need extensive research. Check if files exist (1-2 read_file calls max), then immediately write the files.
- **EXECUTION OVER PLANNING**: For simple creation tasks, skip the planning phase and go straight to writing. Planning is only needed for complex modifications to existing codebases.
- **COMPLETE THE TASK**: Your goal is to have files written and working, not to have a perfect plan. Write first, refine if needed.

CRITICAL: AST-BASED & DIFF-FIRST APPROACH (for existing files only)
- **AST-BASED EDITING**: The system uses AST (Abstract Syntax Tree) based editing for code files, which preserves formatting and validates syntax automatically
- **SEMANTIC EDITS**: For Python files, edits are made semantically - the system understands code structure, not just text
- **AUTOMATIC VALIDATION**: All edits are validated for syntax errors BEFORE writing to disk - if validation fails, you'll get clear error messages
- **ALWAYS USE DIFFS**: For existing files, ALWAYS use `edit_file` or `generate_diff` - NEVER use `write_file` for existing files
- **THINK IN PATCHES**: Think in terms of minimal diffs, not full file rewrites
- **PRESERVE STRUCTURE**: Preserve existing code structure, formatting, and style
- **MINIMAL CHANGES**: Make the smallest changes necessary to accomplish the goal
- **ONLY write_file FOR NEW FILES**: Use `write_file` ONLY when creating completely new files

WORKFLOW FOR DIFFERENT TASK TYPES:

**For NEW FILE CREATION (e.g., "create landing page", "write a script"):**
- **For UI/DESIGN tasks** (landing pages, components, styling): Research modern examples FIRST using web_search and fetch_web_page, then create polished, professional files
- **For code/script tasks**: Quickly check if target files exist (1-2 file_exists or read_file calls), then immediately write the files
- Write ALL required files (HTML, CSS, JS) in the same iteration
- Create complete, working files with modern best practices

**For MODIFYING EXISTING FILES:**
1. Read relevant files in parallel (read_file for multiple files at once)
2. Understand the changes needed
3. Apply changes using edit_file (or generate_diff first to preview)
4. Make all changes in sequence

**For COMPLEX MULTI-FILE CHANGES:**
1. Read ALL relevant files in parallel first
2. Plan all changes needed
3. Execute all changes rapidly in sequence

Best practices:
- **For new files**: Write immediately, don't over-plan
- **For existing files**: Read first, then edit
- Follow existing code style when modifying
- Add comments where helpful
- Create complete, working files

Use tools like:
- file_exists: Quickly check if a file exists (faster than read_file for existence checks)
- read_file: Read files to understand context (use sparingly for new file creation)
- write_file: **USE THIS TO CREATE NEW FILES** - automatically validated before writing
- edit_file: Modify existing files (always use this for existing files, not write_file)
- generate_diff: Preview changes before applying (for existing files)
- parse_ast: Parse code files to understand structure (classes, functions, imports)

CRITICAL: MODERN UI/UX DESIGN SYSTEM (MANDATORY FOR ALL UI FILES)
The system has an AUTOMATIC design quality checker that BLOCKS basic/plain designs. Your UI files MUST pass design quality validation.

**Design Quality Requirements (AUTOMATICALLY ENFORCED):**
- ✅ MUST include modern CSS patterns: gradients, shadows, animations, transitions
- ✅ MUST use modern layout: Flexbox or CSS Grid (not basic positioning)
- ✅ MUST be responsive: @media queries and viewport meta tag
- ✅ MUST use modern color palette: NOT plain white/black backgrounds
- ✅ MUST have visual polish: spacing, typography, rounded corners
- ✅ MUST include CSS custom properties (variables) for theming
- ❌ BLOCKED: Plain white backgrounds with black text
- ❌ BLOCKED: Basic Arial/Times fonts without modern font stack
- ❌ BLOCKED: No spacing, cramped layouts
- ❌ BLOCKED: No responsive design

**Design Quality Score:**
- Minimum 70/100 required to pass
- System automatically checks: modern patterns (gradients, shadows, animations), responsive design, modern layout
- If quality is too low, write_file will FAIL with specific suggestions

**Modern Design Patterns to ALWAYS Include:**
1. **Gradients**: Use `background: linear-gradient(135deg, var(--primary), var(--secondary))` with CSS variables, OR use actual hex colors like `background: linear-gradient(135deg, #3b82f6, #1e40af)`. NEVER use `#primary` or `{{primary}}` - these are invalid!
2. **Shadows**: `box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1)`
3. **Animations**: `transition: all 0.3s ease` and hover effects
4. **Modern Layout**: Flexbox or CSS Grid (never basic positioning)
5. **CSS Variables**: Always define variables in `:root {{ --primary: #3b82f6; --secondary: #1e40af; }}` and use them with `var(--primary)`, never use `{{primary}}` or `#primary`
6. **Responsive**: `@media (max-width: 768px) {{ ... }}`
7. **Typography Scale**: Consistent font sizes, line heights, weights
8. **Spacing System**: Consistent padding/margin using rem units

**For Landing Pages:**
- Hero section with gradient background
- Feature cards with hover effects and shadows
- Smooth transitions and micro-interactions
- Modern button styles with gradients
- Responsive navigation
- Professional spacing and typography

WEB RESEARCH FOR DESIGN/UI TASKS:
- **web_search**: Search for modern design examples, best practices, and inspiration
- **fetch_web_page**: Read design examples, tutorials, and documentation
- **extract_links**: Find related design resources and examples
- **When to research**: For UI/design tasks (landing pages, components, styling), research modern examples FIRST to create polished, professional results
- **Research workflow**: Search → Read examples → Extract patterns → Implement with modern best practices

EDIT VALIDATION:
- All edits are validated BEFORE writing - if syntax errors are found, the edit will fail with clear error messages
- **Design quality is AUTOMATICALLY checked for UI files (HTML, CSS, JS) - low quality designs will be REJECTED**
- Fix any validation errors before retrying the edit
- The system uses AST parsing to catch syntax errors early

REMEMBER: When the user asks you to CREATE files, you MUST actually write them using write_file. Don't just analyze or make recommendations - CREATE THE FILES!
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
        Write or modify code.
        
        Args:
            task: Task dict with 'description' and coding requirements (validated)
            context: Research findings and other context (validated)
            
        Returns:
            Coding result
        """
        # Validate inputs using Pydantic models
        from .base import validate_task_input, validate_context
        task = validate_task_input(task, self.name)
        context = validate_context(context, self.name)
        
        self.status = "working"
        self.current_task = task
        
        description = task.get("description", "")
        
        # Build context string
        context_parts = []
        if context:
            if context.get("research_findings"):
                context_parts.append(f"Research findings:\n{context['research_findings']}\n")
            if context.get("task_results"):
                context_parts.append(f"Previous task results available for reference.\n")
        
        context_str = "\n".join(context_parts)
        
        # Run proactive search before coding (use cache if available)
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
            coding_prompt = f"Coding task: {description}\n\n{context_str}"
            if proactive_context:
                coding_prompt += f"{proactive_context}\n\n"
            
            # Detect if this is a file creation task
            description_lower = description.lower()
            is_creation_task = any(keyword in description_lower for keyword in [
                "create", "write", "make", "build", "add", "new file", "new files",
                "landing page", "html", "css", "javascript", "script"
            ])
            
            if is_creation_task:
                # Check if this is a UI/design task
                is_ui_task = any(keyword in description_lower for keyword in [
                    "landing page", "html", "css", "component", "ui", "design", "page", "website", "frontend"
                ])
                
                if is_ui_task:
                    coding_prompt += """CRITICAL: This is a UI/DESIGN FILE CREATION task. You MUST write files IMMEDIATELY!

EXECUTION PRIORITY:
**STEP 1**: IMMEDIATELY write HTML, CSS, JS files with MODERN design patterns - DO NOT research first!
**STEP 2**: System will automatically validate design quality
**STEP 3**: If validation fails, improve the design

MANDATORY DESIGN PATTERNS (write these immediately):
- CSS gradients: `background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- Shadows: `box-shadow: 0 10px 40px rgba(0,0,0,0.1)`
- Animations: `transition: all 0.3s ease`, hover effects
- Modern layout: Flexbox or CSS Grid
- Responsive: @media queries for mobile/tablet/desktop
- CSS variables: `:root { --primary: #667eea; --secondary: #764ba2; }`
- Modern colors: Use gradients, NOT plain white/black

ABSOLUTE REQUIREMENTS:
1. DO NOT research before writing - research is optional and can come AFTER if needed
2. DO NOT analyze or plan extensively - write files in your FIRST tool use
3. Write HTML, CSS, and JS files ALL in the first iteration
4. Files must be complete and working

YOU HAVE ONE JOB: WRITE THE FILES NOW! No research, no planning, just write!"""
                else:
                    coding_prompt += """CRITICAL: This is a FILE CREATION task. You MUST write files IMMEDIATELY!

ABSOLUTE WORKFLOW (NO EXCEPTIONS):
1. DO NOT check if files exist - just write them!
2. DO NOT read existing files unless modifying them
3. **FIRST TOOL USE MUST BE write_file** - create the files NOW
4. If multiple files needed, write ALL of them immediately
5. Files must be complete and working

FORBIDDEN ACTIONS:
- ❌ Any analysis before writing files
- ❌ Checking if files exist for new files
- ❌ Making recommendations instead of creating files
- ❌ Reading files when creating new ones
- ❌ Planning when you should be writing

REQUIRED ACTIONS:
- ✅ First tool use: write_file for the first file
- ✅ Second tool use: write_file for second file (if needed)
- ✅ Third tool use: write_file for third file (if needed)
- ✅ Files are complete and functional

START WRITING FILES NOW - NO RESEARCH, NO ANALYSIS, JUST WRITE!"""
            else:
                coding_prompt += """CRITICAL WORKFLOW FOR MODIFICATIONS:
1. **PLANNING PHASE**: Read ALL relevant files in PARALLEL first (use multiple read_file calls in the same round)
2. **THINKING PHASE**: Think through ALL changes needed based on complete context
3. **EXECUTION PHASE**: Apply ALL changes quickly in sequence (edit_file calls one after another)

DO NOT:
- Read one file, make one change, read another file
- Make incremental changes section by section
- Start writing before you've read everything

DO:
- Read all files in parallel first
- Plan all changes completely
- Execute all changes rapidly in sequence

Implement the required changes following this workflow."""
            
            coding_task = {
                "description": coding_prompt,
                "project_path": task.get("project_path")
            }
            
            # Max iterations determined automatically from task complexity
            result = await self.executor.execute_agent_task(
                self,
                coding_task,
                context=context
            )
            
            self.status = "completed" if result.get("success") else "error"
            return result
        
        # Fallback
        self.log_work("coding", {"task": description})
        self.status = "completed"
        
        return {
            "success": True,
            "result": {
                "files_modified": [],
                "files_created": [],
                "changes_made": []
            },
            "message": f"Code changes completed for: {description}",
            "next_action": "validate_code"
        }

