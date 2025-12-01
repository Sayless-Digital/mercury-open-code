"""
Feedback Loop Manager - Automatic error detection and refinement system.
Implements run → inspect → refine loop for top-tier AI agent behavior.
"""

import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger("mercury.agents.feedback_loop")


class FeedbackLoopManager:
    """
    Manages automatic feedback loop: run → inspect → refine.
    
    After every file write/edit:
    1. Check syntax
    2. Run linters
    3. Capture compiler output
    4. Detect errors
    5. Auto-refine if needed
    6. Retry until clean or max attempts
    """
    
    def __init__(
        self,
        tool_executor=None,
        max_retries: int = 3,
        enabled: bool = True
    ):
        """
        Initialize feedback loop manager.
        
        Args:
            tool_executor: Tool executor instance for running checks
            max_retries: Maximum refinement attempts (default: 3)
            enabled: Whether feedback loop is enabled (default: True)
        """
        self.tool_executor = tool_executor
        self.max_retries = max_retries
        self.enabled = enabled
        self.refinement_history: List[Dict[str, Any]] = []
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.vue': 'javascript',  # Vue files are JS
        }
        return lang_map.get(ext)
    
    async def check_file(
        self,
        file_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check a file for errors (syntax, linting, etc.).
        
        Args:
            file_path: Path to file to check
            language: Programming language (auto-detected if not provided)
            
        Returns:
            Dict with:
            - success: bool
            - errors: List of errors found
            - warnings: List of warnings
            - syntax_valid: bool
            - lint_issues: List of lint issues
        """
        if not self.enabled or not self.tool_executor:
            return {
                "success": True,
                "errors": [],
                "warnings": [],
                "syntax_valid": True,
                "lint_issues": []
            }
        
        # Detect language if not provided
        if not language:
            language = self._detect_language(file_path)
        
        if not language:
            logger.warning(f"Could not detect language for {file_path}")
            return {
                "success": True,
                "errors": [],
                "warnings": [],
                "syntax_valid": True,
                "lint_issues": []
            }
        
        errors = []
        warnings = []
        lint_issues = []
        syntax_valid = True
        
        # 1. Check syntax
        try:
            syntax_result = self.tool_executor.execute("check_syntax", {
                "file_path": file_path,
                "language": language
            })
            
            if syntax_result.get("success"):
                syntax_data = syntax_result.get("result", {})
                syntax_valid = syntax_data.get("valid", True)
                syntax_errors = syntax_data.get("errors", [])
                
                if syntax_errors:
                    errors.extend(syntax_errors)
                    syntax_valid = False
            else:
                # Syntax check failed - might be a tool issue, not a syntax issue
                logger.warning(f"Syntax check tool failed: {syntax_result.get('error')}")
                # Set syntax_valid to False on tool failure to be safe
                syntax_valid = False
        except Exception as e:
            logger.error(f"Error checking syntax: {e}")
            # Set error state on exception
            syntax_valid = False
            errors.append({"message": f"Syntax check exception: {str(e)}", "type": "exception"})
        
        # 2. Run linter
        try:
            lint_result = self.tool_executor.execute("lint_file", {
                "file_path": file_path,
                "language": language
            })
            
            if lint_result.get("success"):
                lint_data = lint_result.get("result", {})
                issues = lint_data.get("issues", [])
                lint_issues.extend(issues)
                
                # Separate errors and warnings from lint issues
                for issue in issues:
                    message = issue.get("message", "")
                    if "error" in message.lower() or "fatal" in message.lower():
                        errors.append(issue)
                    else:
                        warnings.append(issue)
        except Exception as e:
            logger.debug(f"Linter not available or failed: {e}")
        
        return {
            "success": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "syntax_valid": syntax_valid,
            "lint_issues": lint_issues,
            "language": language
        }
    
    async def refine_file(
        self,
        file_path: str,
        errors: List[Dict[str, Any]],
        language: Optional[str] = None,
        original_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Attempt to automatically refine a file based on errors.
        
        Args:
            file_path: Path to file to refine
            errors: List of errors found
            language: Programming language
            original_content: Original file content (for comparison)
            
        Returns:
            Dict with:
            - success: bool
            - refined: bool (whether refinement was attempted)
            - message: str
            - suggestions: List of suggested fixes
        """
        if not errors:
            return {
                "success": True,
                "refined": False,
                "message": "No errors to refine",
                "suggestions": []
            }
        
        # For now, return suggestions rather than auto-fixing
        # Auto-fixing would require LLM integration which is handled at agent level
        suggestions = []
        
        for error in errors:
            error_msg = error.get("message", "")
            line = error.get("line")
            
            suggestion = {
                "error": error_msg,
                "line": line,
                "type": "syntax" if "syntax" in error_msg.lower() else "lint",
                "suggestion": self._generate_suggestion(error, language)
            }
            suggestions.append(suggestion)
        
        return {
            "success": True,
            "refined": False,  # Not auto-refining, just suggesting
            "message": f"Found {len(suggestions)} issues that need attention",
            "suggestions": suggestions
        }
    
    def _generate_suggestion(self, error: Dict[str, Any], language: Optional[str]) -> str:
        """Generate a suggestion for fixing an error."""
        error_msg = error.get("message", "").lower()
        line = error.get("line")
        
        # Common error patterns and suggestions
        if "unexpected" in error_msg or "syntax" in error_msg:
            return f"Check syntax around line {line}. Look for missing brackets, quotes, or semicolons."
        elif "undefined" in error_msg or "not defined" in error_msg:
            return f"Variable or function may not be defined. Check imports and variable declarations."
        elif "unused" in error_msg:
            return f"Remove unused import or variable."
        elif "import" in error_msg:
            return f"Check import statement - module may not be found or path is incorrect."
        else:
            return f"Review error message and fix accordingly: {error.get('message', '')}"
    
    async def run_feedback_loop(
        self,
        file_path: str,
        language: Optional[str] = None,
        original_content: Optional[str] = None,
        max_attempts: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run complete feedback loop: check → refine → recheck.
        
        Args:
            file_path: Path to file to check
            language: Programming language
            original_content: Original content (for diff validation)
            max_attempts: Maximum refinement attempts (uses self.max_retries if None)
            
        Returns:
            Dict with:
            - success: bool
            - attempts: int (number of attempts made)
            - final_status: Dict (final check result)
            - refinement_history: List of refinement attempts
        """
        if not self.enabled:
            return {
                "success": True,
                "attempts": 0,
                "final_status": {"success": True},
                "refinement_history": []
            }
        
        max_attempts = max_attempts or self.max_retries
        attempts = 0
        refinement_history = []
        
        while attempts < max_attempts:
            attempts += 1
            
            # Check file
            check_result = await self.check_file(file_path, language)
            
            if check_result.get("success"):
                # No errors found - we're done
                return {
                    "success": True,
                    "attempts": attempts,
                    "final_status": check_result,
                    "refinement_history": refinement_history
                }
            
            # Errors found - attempt refinement
            errors = check_result.get("errors", [])
            refine_result = await self.refine_file(
                file_path,
                errors,
                language,
                original_content
            )
            
            refinement_history.append({
                "attempt": attempts,
                "check_result": check_result,
                "refine_result": refine_result,
                "timestamp": datetime.now().isoformat()
            })
            
            # If refinement didn't actually fix anything (just suggested),
            # we break to avoid infinite loop
            if not refine_result.get("refined"):
                # Refinement was just suggestions, not actual fixes
                # Break and return current status
                break
        
        # Store in history
        self.refinement_history.append({
            "file_path": file_path,
            "attempts": attempts,
            "final_status": check_result,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": check_result.get("success", False),
            "attempts": attempts,
            "final_status": check_result,
            "refinement_history": refinement_history
        }
    
    def validate_diff(
        self,
        file_path: str,
        old_content: str,
        new_content: str
    ) -> Dict[str, Any]:
        """
        Validate a diff before applying.
        
        Args:
            file_path: Path to file
            old_content: Original content
            new_content: New content
            
        Returns:
            Dict with:
            - valid: bool
            - diff_too_large: bool (if > 50% of file changed)
            - potential_conflicts: List of potential conflicts
        """
        if not old_content:
            # New file - always valid
            return {
                "valid": True,
                "diff_too_large": False,
                "potential_conflicts": []
            }
        
        old_lines = old_content.split('\n')
        new_lines = new_content.split('\n')
        
        # Calculate diff size
        total_lines = len(old_lines)
        changed_lines = sum(1 for o, n in zip(old_lines, new_lines) if o != n)
        
        # If more than 50% changed, suggest full rewrite
        diff_too_large = (changed_lines / total_lines) > 0.5 if total_lines > 0 else False
        
        # Check for potential conflicts (concurrent edits)
        # This is a simple heuristic - in practice would need more sophisticated conflict detection
        potential_conflicts = []
        
        # If file was modified externally, there might be conflicts
        # This would require file modification time tracking
        
        return {
            "valid": True,
            "diff_too_large": diff_too_large,
            "potential_conflicts": potential_conflicts,
            "changed_lines": changed_lines,
            "total_lines": total_lines,
            "change_percentage": (changed_lines / total_lines * 100) if total_lines > 0 else 0
        }


