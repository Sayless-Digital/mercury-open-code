"""
Tool executor - handles execution of tools called by the agent.
"""

import os
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import fnmatch
import json
import hashlib
import socket
import signal
import sys

# Optional imports with fallback
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False

try:
    from duckduckgo_search import DDGS
    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_AVAILABLE = False

logger = logging.getLogger("mercury.tools")

# Import AST editor for semantic editing
try:
    from .ast_editor import ASTEditor
    AST_EDITOR_AVAILABLE = True
except ImportError:
    AST_EDITOR_AVAILABLE = False
    ASTEditor = None


class ToolExecutor:
    """Executes tools called by the agent."""
    
    def __init__(
        self,
        project_root: Optional[str] = None,
        feedback_loop_manager=None,
        file_graph=None,
        diff_engine=None,
        ast_tools=None,
        code_validator=None
    ):
        """
        Initialize tool executor.
        
        Args:
            project_root: Root directory of the project (for resolving relative paths)
            feedback_loop_manager: FeedbackLoopManager instance for automatic validation
            file_graph: FileGraph instance for dependency queries
            diff_engine: DiffEngine instance for diff computation
            ast_tools: ASTTools instance for static analysis
            code_validator: CodeValidator instance for pre-write validation
        """
        self.project_root = project_root or os.getcwd()
        # Ensure project_root is absolute
        self.project_root = os.path.abspath(self.project_root)
        self.feedback_loop_manager = feedback_loop_manager
        self.file_graph = file_graph
        self.diff_engine = diff_engine
        self.ast_tools = ast_tools
        self.code_validator = code_validator
        
        # Initialize AST editor if available
        if AST_EDITOR_AVAILABLE and ast_tools:
            self.ast_editor = ASTEditor(ast_tools)
        else:
            self.ast_editor = None
        
        # Initialize design quality checker for UI files
        try:
            from .design_quality_checker import DesignQualityChecker
            self.design_quality_checker = DesignQualityChecker()
        except ImportError:
            logger.warning("DesignQualityChecker not available")
            self.design_quality_checker = None
    
    def _resolve_path(self, file_path: str) -> str:
        """Resolve a file path relative to project root or as absolute."""
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(self.project_root, file_path)
    
    def _ensure_safe_path(self, file_path: str) -> str:
        """Ensure the path is within the project root for security."""
        resolved = self._resolve_path(file_path)
        resolved_abs = os.path.abspath(resolved)
        project_abs = os.path.abspath(self.project_root)
        
        # Check if path is within project root using Path objects
        try:
            Path(resolved_abs).relative_to(Path(project_abs))
        except ValueError:
            # Path is outside project root - this is allowed for absolute paths
            # but we should log it
            logger.warning(f"Tool accessing path outside project root: {resolved_abs}")
        
        return resolved_abs
    
    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool and return the result.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Dict with 'success', 'result' or 'error' keys
        """
        try:
            if tool_name == "read_file":
                return self._read_file(arguments)
            elif tool_name == "write_file":
                return self._write_file(arguments)
            elif tool_name == "edit_file":
                return self._edit_file(arguments)
            elif tool_name == "list_directory":
                return self._list_directory(arguments)
            elif tool_name == "execute_command":
                return self._execute_command(arguments)
            elif tool_name == "codebase_search":
                return self._codebase_search(arguments)
            elif tool_name == "grep":
                return self._grep(arguments)
            elif tool_name == "delete_file":
                return self._delete_file(arguments)
            elif tool_name == "delete_directory":
                return self._delete_directory(arguments)
            elif tool_name == "create_directory":
                return self._create_directory(arguments)
            elif tool_name == "move_file":
                return self._move_file(arguments)
            elif tool_name == "copy_file":
                return self._copy_file(arguments)
            elif tool_name == "file_exists":
                return self._file_exists(arguments)
            elif tool_name == "get_file_info":
                return self._get_file_info(arguments)
            elif tool_name == "find_files":
                return self._find_files(arguments)
            elif tool_name == "read_directory_tree":
                return self._read_directory_tree(arguments)
            elif tool_name == "read_env_file":
                return self._read_env_file(arguments)
            elif tool_name == "write_env_file":
                return self._write_env_file(arguments)
            elif tool_name == "search_replace_in_multiple_files":
                return self._search_replace_in_multiple_files(arguments)
            elif tool_name == "git_status":
                return self._git_status(arguments)
            elif tool_name == "git_add":
                return self._git_add(arguments)
            elif tool_name == "git_commit":
                return self._git_commit(arguments)
            elif tool_name == "git_push":
                return self._git_push(arguments)
            elif tool_name == "git_pull":
                return self._git_pull(arguments)
            elif tool_name == "git_branch":
                return self._git_branch(arguments)
            elif tool_name == "git_log":
                return self._git_log(arguments)
            elif tool_name == "git_diff":
                return self._git_diff(arguments)
            elif tool_name == "http_request":
                return self._http_request(arguments)
            elif tool_name == "read_json_file":
                return self._read_json_file(arguments)
            elif tool_name == "write_json_file":
                return self._write_json_file(arguments)
            elif tool_name == "read_yaml_file":
                return self._read_yaml_file(arguments)
            elif tool_name == "write_yaml_file":
                return self._write_yaml_file(arguments)
            elif tool_name == "check_syntax":
                return self._check_syntax(arguments)
            elif tool_name == "lint_file":
                return self._lint_file(arguments)
            elif tool_name == "list_processes":
                return self._list_processes(arguments)
            elif tool_name == "kill_process":
                return self._kill_process(arguments)
            elif tool_name == "check_port":
                return self._check_port(arguments)
            elif tool_name == "read_package_json":
                return self._read_package_json(arguments)
            elif tool_name == "read_requirements_txt":
                return self._read_requirements_txt(arguments)
            elif tool_name == "get_installed_packages":
                return self._get_installed_packages(arguments)
            elif tool_name == "calculate_file_hash":
                return self._calculate_file_hash(arguments)
            elif tool_name == "get_environment_variable":
                return self._get_environment_variable(arguments)
            elif tool_name == "get_file_dependencies":
                return self._get_file_dependencies(arguments)
            elif tool_name == "find_related_files":
                return self._find_related_files(arguments)
            elif tool_name == "get_component_boundaries":
                return self._get_component_boundaries(arguments)
            elif tool_name == "find_similar_patterns":
                return self._find_similar_patterns(arguments)
            elif tool_name == "generate_diff":
                return self._generate_diff(arguments)
            elif tool_name == "parse_ast":
                return self._parse_ast(arguments)
            elif tool_name == "find_references":
                return self._find_references(arguments)
            elif tool_name == "get_type_info":
                return self._get_type_info(arguments)
            elif tool_name == "find_unused_code":
                return self._find_unused_code(arguments)
            elif tool_name == "detect_potential_bugs":
                return self._detect_potential_bugs(arguments)
            elif tool_name == "web_search":
                return self._web_search(arguments)
            elif tool_name == "fetch_web_page":
                return self._fetch_web_page(arguments)
            elif tool_name == "extract_links":
                return self._extract_links(arguments)
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _read_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read a file."""
        file_path = args.get("file_path")
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            with open(resolved_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "content": content,
                    "size": len(content)
                }
            }
        except FileNotFoundError:
            return {"success": False, "error": f"File not found: {file_path}"}
        except Exception as e:
            return {"success": False, "error": f"Error reading file: {str(e)}"}
    
    def _write_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to a file."""
        file_path = args.get("file_path")
        content = args.get("content")
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        if content is None:
            return {"success": False, "error": "content is required"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
            
            # Check if file exists to get original content for validation
            original_content = None
            if os.path.exists(resolved_path):
                try:
                    with open(resolved_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                except Exception:
                    pass
            
            # Validate before writing (pre-write validation)
            validation_result = None
            if self.code_validator:
                try:
                    validation_result = self.code_validator.validate_before_write(
                        resolved_path,
                        content,
                        original_content
                    )
                    
                    # If validation fails, return error without writing
                    if not validation_result.get("valid"):
                        return {
                            "success": False,
                            "error": "Pre-write validation failed",
                            "validation": validation_result,
                            "message": "Code has syntax errors. Please fix them before writing."
                        }
                except Exception as e:
                    logger.warning(f"Pre-write validation error: {e}")
                    # Continue with write if validation fails (non-blocking)
            
            # Check design quality for UI files (HTML, CSS, JS)
            design_quality_result = None
            if self.design_quality_checker:
                try:
                    file_ext = os.path.splitext(resolved_path)[1].lower()
                    if file_ext in ['.html', '.css', '.js', '.jsx', '.tsx', '.vue']:
                        design_quality_result = self.design_quality_checker.check_design_quality(
                            resolved_path,
                            content
                        )
                        
                        # Block writes if design quality is too low (for UI files)
                        if not design_quality_result.get("passed"):
                            quality_score = design_quality_result.get("quality_score", 0)
                            suggestions = design_quality_result.get("suggestions", [])
                            return {
                                "success": False,
                                "error": "Design quality check failed",
                                "design_quality": design_quality_result,
                                "message": f"Design quality too low (score: {quality_score}/100). The UI must be modern, polished, and professional. Suggestions: {'; '.join(suggestions[:3])}"
                            }
                except Exception as e:
                    logger.warning(f"Design quality check error: {e}")
                    # Continue with write if design check fails (non-blocking)
            
            # Write file only if validation passes (or if no validator)
            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Run feedback loop if enabled
            feedback_result = None
            if self.feedback_loop_manager:
                try:
                    import asyncio
                    # Run async feedback loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is already running, create a task
                        feedback_result = asyncio.create_task(
                            self.feedback_loop_manager.run_feedback_loop(
                                file_path,
                                original_content=original_content
                            )
                        )
                    else:
                        feedback_result = loop.run_until_complete(
                            self.feedback_loop_manager.run_feedback_loop(
                                file_path,
                                original_content=original_content
                            )
                        )
                except Exception as e:
                    logger.warning(f"Feedback loop failed: {e}")
            
            result = {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "message": "File written successfully",
                    "size": len(content)
                }
            }
            
            # Add validation information if available
            if validation_result:
                result["result"]["pre_write_validation"] = {
                    "valid": validation_result.get("valid", True),
                    "syntax_valid": validation_result.get("syntax_valid", True),
                    "import_valid": validation_result.get("import_valid", True),
                    "errors": validation_result.get("errors", []),
                    "warnings": validation_result.get("warnings", []),
                    "lint_issues": validation_result.get("lint_issues", [])
                }
            
            # Add design quality information if available
            if design_quality_result:
                result["result"]["design_quality"] = {
                    "quality_score": design_quality_result.get("quality_score", 0),
                    "is_modern": design_quality_result.get("is_modern", False),
                    "is_polished": design_quality_result.get("is_polished", False),
                    "passed": design_quality_result.get("passed", True)
                }
            
            # Add feedback information if available (post-write)
            if feedback_result:
                if hasattr(feedback_result, 'result'):
                    # It's a task, get the result
                    try:
                        feedback_result = feedback_result.result()
                    except Exception:
                        pass
                
                if isinstance(feedback_result, dict):
                    result["result"]["validation"] = {
                        "checked": True,
                        "syntax_valid": feedback_result.get("final_status", {}).get("syntax_valid", True),
                        "errors": feedback_result.get("final_status", {}).get("errors", []),
                        "warnings": feedback_result.get("final_status", {}).get("warnings", []),
                        "attempts": feedback_result.get("attempts", 0)
                    }
            
            return result
        except Exception as e:
            return {"success": False, "error": f"Error writing file: {str(e)}"}
    
    def _determine_edit_strategy(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        current_content: str
    ) -> str:
        """
        Determine the best editing strategy for a file edit.
        
        Args:
            file_path: Path to file
            old_string: Text to replace
            new_string: Replacement text
            current_content: Current file content
            
        Returns:
            Strategy: "ast", "diff", or "string"
        """
        # Check if file is a code file
        ext = os.path.splitext(file_path)[1].lower()
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php'}
        is_code_file = ext in code_extensions
        
        if not is_code_file:
            # For non-code files, use diff or string replacement
            if self.diff_engine:
                return "diff"
            return "string"
        
        # For code files, try AST-based editing if available
        if self.ast_editor and ext == '.py':
            # Check if this looks like a semantic edit (function/class change)
            # Simple heuristic: if old_string contains function/class definition patterns
            if re.search(r'\bdef\s+\w+', old_string) or re.search(r'\bclass\s+\w+', old_string):
                return "ast"
            # Otherwise, try semantic replacement
            return "ast"
        
        # Fall back to diff for code files if AST not available
        if self.diff_engine:
            return "diff"
        
        # Last resort: string replacement
        return "string"
    
    def _edit_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Edit a file using the best available strategy (AST, diff, or string replacement)."""
        file_path = args.get("file_path")
        old_string = args.get("old_string")
        new_string = args.get("new_string")
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        if old_string is None:
            return {"success": False, "error": "old_string is required"}
        if new_string is None:
            return {"success": False, "error": "new_string is required"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            # Read current content
            with open(resolved_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            # Check if old_string exists
            if old_string not in current_content:
                return {
                    "success": False,
                    "error": f"Could not find the exact text to replace in {file_path}. The old_string must match exactly, including whitespace."
                }
            
            # Determine edit strategy
            strategy = self._determine_edit_strategy(resolved_path, old_string, new_string, current_content)
            logger.info(f"Using edit strategy: {strategy} for {file_path}")
            
            new_content = None
            edit_method = None
            previous_method = None
            edit_error = None
            
            # Try strategies in order: AST -> diff -> string
            if strategy == "ast" and self.ast_editor:
                try:
                    # Try AST-based semantic replacement
                    ast_result = self.ast_editor.replace_text_semantic(
                        resolved_path,
                        old_string,
                        new_string,
                        current_content
                    )
                    if ast_result.get("success"):
                        new_content = ast_result.get("new_content")
                        edit_method = "ast_semantic"
                    else:
                        edit_error = ast_result.get("error")
                        previous_method = "ast_semantic"
                        logger.warning(f"AST edit failed: {edit_error}, falling back to diff")
                except Exception as e:
                    edit_error = str(e)
                    previous_method = "ast_semantic"
                    logger.warning(f"AST edit exception: {e}, falling back to diff")
            
            # Fall back to diff-based editing
            if new_content is None and self.diff_engine:
                try:
                    # Compute diff and apply patch
                    minimal = self.diff_engine.compute_minimal_patch(current_content, current_content.replace(old_string, new_string, 1), file_path)
                    patch = minimal.get("patch")
                    if patch:
                        new_content, success = self.diff_engine.apply_patch(current_content, patch)
                        if success:
                            edit_method = "diff_patch"
                        else:
                            if not previous_method:
                                previous_method = "diff_patch"
                            logger.warning("Diff patch application failed, falling back to string replacement")
                    else:
                        if not previous_method:
                            previous_method = "diff_patch"
                        logger.warning("Could not compute diff, falling back to string replacement")
                except Exception as e:
                    if not previous_method:
                        previous_method = "diff_patch"
                    logger.warning(f"Diff edit exception: {e}, falling back to string replacement")
            
            # Fall back to string replacement (last resort)
            if new_content is None:
                new_content = current_content.replace(old_string, new_string, 1)  # Replace first occurrence only
                edit_method = "string_replacement"
                if edit_error and previous_method:
                    logger.warning(f"Using string replacement after {previous_method} failed: {edit_error}")
            
            # Generate diff for display/validation
            diff_result = None
            if self.diff_engine and new_content:
                try:
                    minimal = self.diff_engine.compute_minimal_patch(current_content, new_content, file_path)
                    diff_result = {
                        "unified_diff": self.diff_engine.compute_unified_diff(current_content, new_content, file_path),
                        "minimal_patch": minimal["patch"],
                        "stats": minimal["stats"],
                        "changes": minimal["changes"]
                    }
                except Exception as e:
                    logger.warning(f"Diff generation failed: {e}")
            
            # Validate before writing (pre-write validation)
            validation_result = None
            if self.code_validator:
                try:
                    validation_result = self.code_validator.validate_before_write(
                        resolved_path,
                        new_content,
                        current_content
                    )
                    
                    # If validation fails, return error without writing
                    if not validation_result.get("valid"):
                        return {
                            "success": False,
                            "error": "Pre-write validation failed",
                            "validation": validation_result,
                            "message": "Edited code has syntax errors. Please fix them before applying changes."
                        }
                except Exception as e:
                    logger.warning(f"Pre-write validation error: {e}")
                    # Continue with write if validation fails (non-blocking)
            
            # Check design quality for UI files (HTML, CSS, JS)
            design_quality_result = None
            if self.design_quality_checker:
                try:
                    file_ext = os.path.splitext(resolved_path)[1].lower()
                    if file_ext in ['.html', '.css', '.js', '.jsx', '.tsx', '.vue']:
                        design_quality_result = self.design_quality_checker.check_design_quality(
                            resolved_path,
                            new_content
                        )
                        
                        # Block edits if design quality is too low (for UI files)
                        if not design_quality_result.get("passed"):
                            quality_score = design_quality_result.get("quality_score", 0)
                            suggestions = design_quality_result.get("suggestions", [])
                            return {
                                "success": False,
                                "error": "Design quality check failed",
                                "design_quality": design_quality_result,
                                "message": f"Design quality too low (score: {quality_score}/100). The UI must be modern, polished, and professional. Suggestions: {'; '.join(suggestions[:3])}"
                            }
                except Exception as e:
                    logger.warning(f"Design quality check error: {e}")
                    # Continue with write if design check fails (non-blocking)
            
            # Run feedback loop validation before writing (diff validation) - legacy
            feedback_validation = None
            if self.feedback_loop_manager:
                try:
                    feedback_validation = self.feedback_loop_manager.validate_diff(
                        file_path,
                        current_content,
                        new_content
                    )
                except Exception as e:
                    logger.warning(f"Diff validation failed: {e}")
            
            # Write back only if validation passes (or if no validator)
            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Run feedback loop after edit
            feedback_result = None
            if self.feedback_loop_manager:
                try:
                    import asyncio
                    # Run async feedback loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is already running, create a task
                        feedback_result = asyncio.create_task(
                            self.feedback_loop_manager.run_feedback_loop(
                                file_path,
                                original_content=current_content
                            )
                        )
                    else:
                        feedback_result = loop.run_until_complete(
                            self.feedback_loop_manager.run_feedback_loop(
                                file_path,
                                original_content=current_content
                            )
                        )
                except Exception as e:
                    logger.warning(f"Feedback loop failed: {e}")
            
            result = {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "message": "File edited successfully",
                    "edit_method": edit_method or "unknown"
                }
            }
            
            # Add diff information if available
            if diff_result:
                result["result"]["diff"] = {
                    "unified_diff": diff_result["unified_diff"],
                    "minimal_patch": diff_result["minimal_patch"],
                    "stats": diff_result["stats"],
                    "changes_count": len(diff_result["changes"])
                }
            
            # Add validation information if available
            if validation_result:
                result["result"]["pre_write_validation"] = {
                    "valid": validation_result.get("valid", True),
                    "syntax_valid": validation_result.get("syntax_valid", True),
                    "import_valid": validation_result.get("import_valid", True),
                    "errors": validation_result.get("errors", []),
                    "warnings": validation_result.get("warnings", []),
                    "lint_issues": validation_result.get("lint_issues", [])
                }
            
            # Add design quality information if available
            if design_quality_result:
                result["result"]["design_quality"] = {
                    "quality_score": design_quality_result.get("quality_score", 0),
                    "is_modern": design_quality_result.get("is_modern", False),
                    "is_polished": design_quality_result.get("is_polished", False),
                    "passed": design_quality_result.get("passed", True)
                }
            
            # Add feedback information if available (legacy)
            if feedback_validation:
                result["result"]["diff_validation"] = feedback_validation
            
            # Add warning if string replacement was used (should be last resort)
            if edit_method == "string_replacement":
                result["result"]["warning"] = "Used string replacement (fallback method). Consider using AST or diff-based editing for better results."
            
            if feedback_result:
                if hasattr(feedback_result, 'result'):
                    # It's a task, get the result
                    try:
                        feedback_result = feedback_result.result()
                    except Exception:
                        pass
                
                if isinstance(feedback_result, dict):
                    result["result"]["validation"] = {
                        "checked": True,
                        "syntax_valid": feedback_result.get("final_status", {}).get("syntax_valid", True),
                        "errors": feedback_result.get("final_status", {}).get("errors", []),
                        "warnings": feedback_result.get("final_status", {}).get("warnings", []),
                        "attempts": feedback_result.get("attempts", 0)
                    }
            
            return result
        except FileNotFoundError:
            return {"success": False, "error": f"File not found: {file_path}"}
        except Exception as e:
            return {"success": False, "error": f"Error editing file: {str(e)}"}
    
    def _list_directory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List directory contents."""
        directory_path = args.get("directory_path", ".")
        
        try:
            resolved_path = self._ensure_safe_path(directory_path)
            
            if not os.path.isdir(resolved_path):
                return {"success": False, "error": f"Not a directory: {directory_path}"}
            
            items = []
            for item in sorted(os.listdir(resolved_path)):
                item_path = os.path.join(resolved_path, item)
                items.append({
                    "name": item,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "path": os.path.join(directory_path, item) if directory_path != "." else item
                })
            
            return {
                "success": True,
                "result": {
                    "directory": directory_path,
                    "items": items,
                    "count": len(items)
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error listing directory: {str(e)}"}
    
    def _execute_command(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a shell command."""
        command = args.get("command")
        cwd = args.get("cwd")
        
        if not command:
            return {"success": False, "error": "command is required"}
        
        # Security: Block dangerous commands
        dangerous_patterns = [
            r'rm\s+-rf\s+/',  # rm -rf on root
            r':\s*\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}',  # Fork bomb
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                return {"success": False, "error": "Command blocked for security reasons"}
        
        try:
            # Determine working directory
            work_dir = self.project_root
            if cwd:
                work_dir = self._resolve_path(cwd)
                if not os.path.isdir(work_dir):
                    return {"success": False, "error": f"Working directory not found: {cwd}"}
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                encoding='utf-8',
                errors='replace'
            )
            
            return {
                "success": True,
                "result": {
                    "command": command,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "cwd": work_dir
                }
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out after 5 minutes"}
        except Exception as e:
            return {"success": False, "error": f"Error executing command: {str(e)}"}
    
    def _codebase_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search the codebase using simple text search."""
        query = args.get("query")
        max_results = args.get("max_results", 10)
        
        if not query:
            return {"success": False, "error": "query is required"}
        
        try:
            results = []
            query_lower = query.lower()
            
            # Walk through project directory
            for root, dirs, files in os.walk(self.project_root):
                # Skip common ignored directories
                dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build'}]
                
                for file in files:
                    # Skip binary files and common ignored files
                    if file.startswith('.') or file.endswith(('.pyc', '.pyo', '.so', '.dll', '.exe')):
                        continue
                    
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.project_root)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if query_lower in content.lower():
                                # Find line numbers with matches
                                lines = content.split('\n')
                                matches = []
                                for i, line in enumerate(lines, 1):
                                    if query_lower in line.lower():
                                        matches.append({
                                            "line": i,
                                            "content": line.strip()[:200]  # Truncate long lines
                                        })
                                        if len(matches) >= 5:  # Max 5 matches per file
                                            break
                                
                                if matches:
                                    results.append({
                                        "file_path": rel_path,
                                        "matches": matches,
                                        "match_count": len(matches)
                                    })
                                    
                                    if len(results) >= max_results:
                                        break
                    except Exception:
                        continue
                
                if len(results) >= max_results:
                    break
            
            return {
                "success": True,
                "result": {
                    "query": query,
                    "results": results,
                    "total": len(results)
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error searching codebase: {str(e)}"}
    
    def _grep(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search for regex pattern in files."""
        pattern = args.get("pattern")
        file_path = args.get("file_path")
        
        if not pattern:
            return {"success": False, "error": "pattern is required"}
        
        try:
            # Compile regex
            regex = re.compile(pattern, re.IGNORECASE)
            results = []
            
            # Determine search scope
            if file_path:
                search_path = self._resolve_path(file_path)
                if os.path.isfile(search_path):
                    search_files = [search_path]
                elif os.path.isdir(search_path):
                    search_files = []
                    for root, dirs, files in os.walk(search_path):
                        dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__'}]
                        for f in files:
                            if not f.startswith('.'):
                                search_files.append(os.path.join(root, f))
                else:
                    return {"success": False, "error": f"Path not found: {file_path}"}
            else:
                # Search entire project
                search_files = []
                for root, dirs, files in os.walk(self.project_root):
                    dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', '.venv', 'venv'}]
                    for f in files:
                        if not f.startswith('.') and not f.endswith(('.pyc', '.pyo')):
                            search_files.append(os.path.join(root, f))
            
            # Search files
            for file_path_full in search_files:
                try:
                    with open(file_path_full, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                    matches = []
                    for i, line in enumerate(lines, 1):
                        if regex.search(line):
                            matches.append({
                                "line": i,
                                "content": line.strip()[:200]
                            })
                    
                    if matches:
                        rel_path = os.path.relpath(file_path_full, self.project_root)
                        results.append({
                            "file_path": rel_path,
                            "matches": matches,
                            "match_count": len(matches)
                        })
                except Exception:
                    continue
            
            return {
                "success": True,
                "result": {
                    "pattern": pattern,
                    "results": results,
                    "total": len(results)
                }
            }
        except re.error as e:
            return {"success": False, "error": f"Invalid regex pattern: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Error searching: {str(e)}"}
    
    def _delete_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a file."""
        file_path = args.get("file_path")
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            if not os.path.exists(resolved_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            
            if os.path.isdir(resolved_path):
                return {"success": False, "error": f"Path is a directory, use delete_directory instead: {file_path}"}
            
            os.remove(resolved_path)
            
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "message": "File deleted successfully"
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error deleting file: {str(e)}"}
    
    def _delete_directory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a directory."""
        directory_path = args.get("directory_path")
        recursive = args.get("recursive", True)
        
        if not directory_path:
            return {"success": False, "error": "directory_path is required"}
        
        try:
            resolved_path = self._ensure_safe_path(directory_path)
            
            if not os.path.exists(resolved_path):
                return {"success": False, "error": f"Directory not found: {directory_path}"}
            
            if not os.path.isdir(resolved_path):
                return {"success": False, "error": f"Path is not a directory: {directory_path}"}
            
            if recursive:
                import shutil
                shutil.rmtree(resolved_path)
            else:
                os.rmdir(resolved_path)  # Only works if directory is empty
            
            return {
                "success": True,
                "result": {
                    "directory_path": directory_path,
                    "message": "Directory deleted successfully",
                    "recursive": recursive
                }
            }
        except OSError as e:
            if not recursive and "not empty" in str(e).lower():
                return {"success": False, "error": f"Directory is not empty. Use recursive=true to delete non-empty directories: {directory_path}"}
            return {"success": False, "error": f"Error deleting directory: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Error deleting directory: {str(e)}"}
    
    def _create_directory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a directory."""
        directory_path = args.get("directory_path")
        if not directory_path:
            return {"success": False, "error": "directory_path is required"}
        
        try:
            resolved_path = self._ensure_safe_path(directory_path)
            
            if os.path.exists(resolved_path):
                if os.path.isdir(resolved_path):
                    return {
                        "success": True,
                        "result": {
                            "directory_path": directory_path,
                            "message": "Directory already exists"
                        }
                    }
                else:
                    return {"success": False, "error": f"Path exists but is not a directory: {directory_path}"}
            
            os.makedirs(resolved_path, exist_ok=True)
            
            return {
                "success": True,
                "result": {
                    "directory_path": directory_path,
                    "message": "Directory created successfully"
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error creating directory: {str(e)}"}
    
    def _move_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Move or rename a file or directory."""
        source_path = args.get("source_path")
        destination_path = args.get("destination_path")
        
        if not source_path:
            return {"success": False, "error": "source_path is required"}
        if not destination_path:
            return {"success": False, "error": "destination_path is required"}
        
        try:
            resolved_source = self._ensure_safe_path(source_path)
            resolved_dest = self._ensure_safe_path(destination_path)
            
            if not os.path.exists(resolved_source):
                return {"success": False, "error": f"Source path not found: {source_path}"}
            
            # Create destination directory if it doesn't exist
            dest_dir = os.path.dirname(resolved_dest)
            if dest_dir and not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
            
            import shutil
            shutil.move(resolved_source, resolved_dest)
            
            return {
                "success": True,
                "result": {
                    "source_path": source_path,
                    "destination_path": destination_path,
                    "message": "File or directory moved successfully"
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error moving file: {str(e)}"}
    
    def _copy_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Copy a file or directory."""
        source_path = args.get("source_path")
        destination_path = args.get("destination_path")
        
        if not source_path:
            return {"success": False, "error": "source_path is required"}
        if not destination_path:
            return {"success": False, "error": "destination_path is required"}
        
        try:
            resolved_source = self._ensure_safe_path(source_path)
            resolved_dest = self._ensure_safe_path(destination_path)
            
            if not os.path.exists(resolved_source):
                return {"success": False, "error": f"Source path not found: {source_path}"}
            
            import shutil
            
            if os.path.isdir(resolved_source):
                # Copy directory recursively
                shutil.copytree(resolved_source, resolved_dest, dirs_exist_ok=True)
            else:
                # Copy file
                dest_dir = os.path.dirname(resolved_dest)
                if dest_dir and not os.path.exists(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(resolved_source, resolved_dest)
            
            return {
                "success": True,
                "result": {
                    "source_path": source_path,
                    "destination_path": destination_path,
                    "message": "File or directory copied successfully"
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error copying file: {str(e)}"}
    
    def _file_exists(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a file or directory exists."""
        path = args.get("path")
        if not path:
            return {"success": False, "error": "path is required"}
        
        try:
            resolved_path = self._ensure_safe_path(path)
            exists = os.path.exists(resolved_path)
            
            result = {
                "path": path,
                "exists": exists
            }
            
            if exists:
                result["type"] = "directory" if os.path.isdir(resolved_path) else "file"
            
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {"success": False, "error": f"Error checking path: {str(e)}"}
    
    def _get_file_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get metadata about a file or directory."""
        path = args.get("path")
        if not path:
            return {"success": False, "error": "path is required"}
        
        try:
            resolved_path = self._ensure_safe_path(path)
            
            if not os.path.exists(resolved_path):
                return {"success": False, "error": f"Path not found: {path}"}
            
            stat_info = os.stat(resolved_path)
            is_dir = os.path.isdir(resolved_path)
            
            import time
            from datetime import datetime
            
            result = {
                "path": path,
                "type": "directory" if is_dir else "file",
                "size": stat_info.st_size if not is_dir else None,
                "modified_time": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                "created_time": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                "permissions": oct(stat_info.st_mode)[-3:]  # Last 3 digits for permissions
            }
            
            if is_dir:
                # Count items in directory
                try:
                    result["item_count"] = len(os.listdir(resolved_path))
                except:
                    result["item_count"] = None
            
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {"success": False, "error": f"Error getting file info: {str(e)}"}
    
    def _find_files(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find files by pattern."""
        pattern = args.get("pattern")
        directory_path = args.get("directory_path")
        max_results = args.get("max_results", 50)
        
        if not pattern:
            return {"success": False, "error": "pattern is required"}
        
        try:
            search_path = self.project_root
            if directory_path:
                search_path = self._ensure_safe_path(directory_path)
                if not os.path.isdir(search_path):
                    return {"success": False, "error": f"Not a directory: {directory_path}"}
            
            results = []
            
            for root, dirs, files in os.walk(search_path):
                # Skip common ignored directories
                dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.next'}]
                
                for file in files:
                    if fnmatch.fnmatch(file, pattern) or pattern.lower() in file.lower():
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.project_root)
                        results.append({
                            "file_path": rel_path,
                            "absolute_path": file_path
                        })
                        
                        if len(results) >= max_results:
                            break
                
                if len(results) >= max_results:
                    break
            
            return {
                "success": True,
                "result": {
                    "pattern": pattern,
                    "files": results,
                    "count": len(results)
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error finding files: {str(e)}"}
    
    def _read_directory_tree(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get directory tree structure."""
        directory_path = args.get("directory_path", ".")
        max_depth = args.get("max_depth", 5)
        include_hidden = args.get("include_hidden", False)
        
        try:
            resolved_path = self._ensure_safe_path(directory_path)
            
            if not os.path.isdir(resolved_path):
                return {"success": False, "error": f"Not a directory: {directory_path}"}
            
            def build_tree(path: str, prefix: str = "", depth: int = 0) -> List[str]:
                """Recursively build tree structure."""
                if max_depth >= 0 and depth > max_depth:
                    return []
                
                items = []
                try:
                    entries = sorted(os.listdir(path))
                    if not include_hidden:
                        entries = [e for e in entries if not e.startswith('.')]
                    
                    for i, entry in enumerate(entries):
                        entry_path = os.path.join(path, entry)
                        is_last = i == len(entries) - 1
                        current_prefix = "└── " if is_last else "├── "
                        items.append(prefix + current_prefix + entry)
                        
                        if os.path.isdir(entry_path):
                            # Skip common ignored directories
                            if entry in {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.next'}:
                                continue
                            
                            extension = "    " if is_last else "│   "
                            items.extend(build_tree(entry_path, prefix + extension, depth + 1))
                except PermissionError:
                    pass
                
                return items
            
            tree_lines = build_tree(resolved_path)
            tree_str = "\n".join(tree_lines) if tree_lines else "(empty directory)"
            
            return {
                "success": True,
                "result": {
                    "directory": directory_path,
                    "tree": tree_str,
                    "lines": tree_lines
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error reading directory tree: {str(e)}"}
    
    def _read_env_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read .env file."""
        file_path = args.get("file_path", ".env")
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            if not os.path.exists(resolved_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            
            variables = {}
            with open(resolved_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    # Parse KEY=VALUE format
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        variables[key] = value
            
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "variables": variables,
                    "count": len(variables)
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error reading env file: {str(e)}"}
    
    def _write_env_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Write .env file."""
        file_path = args.get("file_path", ".env")
        variables = args.get("variables", {})
        merge = args.get("merge", True)
        
        if not variables:
            return {"success": False, "error": "variables is required"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            existing_vars = {}
            if merge and os.path.exists(resolved_path):
                # Read existing variables
                with open(resolved_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            existing_vars[key] = value
            
            # Merge with new variables
            existing_vars.update(variables)
            
            # Write to file
            with open(resolved_path, 'w', encoding='utf-8') as f:
                for key, value in sorted(existing_vars.items()):
                    # Escape special characters and wrap in quotes if needed
                    if ' ' in value or '#' in value or '=' in value:
                        value = f'"{value}"'
                    f.write(f"{key}={value}\n")
            
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "variables_written": len(variables),
                    "total_variables": len(existing_vars),
                    "message": "Environment file written successfully"
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error writing env file: {str(e)}"}
    
    def _search_replace_in_multiple_files(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search and replace across multiple files."""
        pattern = args.get("pattern")
        replacement = args.get("replacement")
        file_pattern = args.get("file_pattern")
        use_regex = args.get("use_regex", False)
        
        if not pattern:
            return {"success": False, "error": "pattern is required"}
        if replacement is None:
            return {"success": False, "error": "replacement is required"}
        
        try:
            if use_regex:
                regex = re.compile(pattern)
            else:
                # Escape special regex characters for literal matching
                escaped_pattern = re.escape(pattern)
                regex = re.compile(escaped_pattern)
            
            # Determine search scope
            if file_pattern:
                if os.path.isdir(self._resolve_path(file_pattern)):
                    search_path = self._ensure_safe_path(file_pattern)
                    search_files = []
                    for root, dirs, files in os.walk(search_path):
                        dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__'}]
                        for f in files:
                            search_files.append(os.path.join(root, f))
                else:
                    # Treat as file pattern
                    search_files = []
                    for root, dirs, files in os.walk(self.project_root):
                        dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__'}]
                        for f in files:
                            if fnmatch.fnmatch(f, file_pattern):
                                search_files.append(os.path.join(root, f))
            else:
                # Search entire project
                search_files = []
                for root, dirs, files in os.walk(self.project_root):
                    dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', '.venv', 'venv'}]
                    for f in files:
                        if not f.startswith('.') and not f.endswith(('.pyc', '.pyo')):
                            search_files.append(os.path.join(root, f))
            
            results = []
            total_replacements = 0
            
            for file_path in search_files:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Count matches
                    matches = len(regex.findall(content))
                    if matches > 0:
                        # Perform replacement
                        new_content = regex.sub(replacement, content)
                        
                        # Write back if changed
                        if new_content != content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            
                            rel_path = os.path.relpath(file_path, self.project_root)
                            results.append({
                                "file_path": rel_path,
                                "replacements": matches
                            })
                            total_replacements += matches
                except Exception:
                    continue
            
            return {
                "success": True,
                "result": {
                    "pattern": pattern,
                    "replacement": replacement,
                    "files_modified": len(results),
                    "total_replacements": total_replacements,
                    "details": results
                }
            }
        except re.error as e:
            return {"success": False, "error": f"Invalid regex pattern: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Error in search and replace: {str(e)}"}
    
    def _git_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get git status."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {"success": False, "error": f"Git command failed: {result.stderr}"}
            
            lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            modified = []
            staged = []
            untracked = []
            
            for line in lines:
                if not line:
                    continue
                status = line[:2]
                file_path = line[3:]
                
                if status[0] == ' ' and status[1] != ' ':
                    # Modified but not staged
                    modified.append(file_path)
                elif status[0] != ' ':
                    # Staged
                    staged.append(file_path)
                if status[1] == '?':
                    # Untracked
                    untracked.append(file_path)
            
            # Get current branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
            
            return {
                "success": True,
                "result": {
                    "current_branch": current_branch,
                    "modified": modified,
                    "staged": staged,
                    "untracked": untracked,
                    "has_changes": len(modified) > 0 or len(staged) > 0 or len(untracked) > 0
                }
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git command timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "Git is not installed or not in PATH"}
        except Exception as e:
            return {"success": False, "error": f"Error getting git status: {str(e)}"}
    
    def _git_add(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Stage files for commit."""
        files = args.get("files", [])
        
        if not files:
            return {"success": False, "error": "files is required"}
        
        try:
            result = subprocess.run(
                ["git", "add"] + files,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {"success": False, "error": f"Git add failed: {result.stderr}"}
            
            return {
                "success": True,
                "result": {
                    "files": files,
                    "message": "Files staged successfully"
                }
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git command timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "Git is not installed or not in PATH"}
        except Exception as e:
            return {"success": False, "error": f"Error staging files: {str(e)}"}
    
    def _git_commit(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Commit staged changes."""
        message = args.get("message")
        
        if not message:
            return {"success": False, "error": "message is required"}
        
        try:
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {"success": False, "error": f"Git commit failed: {result.stderr}"}
            
            # Get commit hash
            commit_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            commit_hash = commit_result.stdout.strip() if commit_result.returncode == 0 else None
            
            return {
                "success": True,
                "result": {
                    "message": message,
                    "commit_hash": commit_hash,
                    "output": result.stdout
                }
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git command timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "Git is not installed or not in PATH"}
        except Exception as e:
            return {"success": False, "error": f"Error committing: {str(e)}"}
    
    def _git_push(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Push to remote."""
        remote = args.get("remote", "origin")
        branch = args.get("branch")
        
        try:
            # Get current branch if not specified
            if not branch:
                branch_result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if branch_result.returncode != 0:
                    return {"success": False, "error": "Could not determine current branch"}
                branch = branch_result.stdout.strip()
            
            result = subprocess.run(
                ["git", "push", remote, branch],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return {"success": False, "error": f"Git push failed: {result.stderr}"}
            
            return {
                "success": True,
                "result": {
                    "remote": remote,
                    "branch": branch,
                    "output": result.stdout
                }
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git command timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "Git is not installed or not in PATH"}
        except Exception as e:
            return {"success": False, "error": f"Error pushing: {str(e)}"}
    
    def _git_pull(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Pull from remote."""
        remote = args.get("remote", "origin")
        branch = args.get("branch")
        
        try:
            cmd = ["git", "pull", remote]
            if branch:
                cmd.append(branch)
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return {"success": False, "error": f"Git pull failed: {result.stderr}"}
            
            return {
                "success": True,
                "result": {
                    "remote": remote,
                    "branch": branch or "current",
                    "output": result.stdout
                }
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git command timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "Git is not installed or not in PATH"}
        except Exception as e:
            return {"success": False, "error": f"Error pulling: {str(e)}"}
    
    def _git_branch(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Manage git branches."""
        action = args.get("action")
        branch_name = args.get("branch_name")
        
        if not action:
            return {"success": False, "error": "action is required"}
        
        try:
            if action == "list":
                result = subprocess.run(
                    ["git", "branch", "-a"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    return {"success": False, "error": f"Git branch list failed: {result.stderr}"}
                
                branches = []
                current_branch = None
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('*'):
                        current_branch = line[2:].strip()
                        branches.append({"name": current_branch, "current": True})
                    else:
                        branches.append({"name": line.strip(), "current": False})
                
                return {
                    "success": True,
                    "result": {
                        "branches": branches,
                        "current_branch": current_branch
                    }
                }
            
            elif action == "create":
                if not branch_name:
                    return {"success": False, "error": "branch_name is required for create action"}
                
                result = subprocess.run(
                    ["git", "checkout", "-b", branch_name],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    return {"success": False, "error": f"Git branch create failed: {result.stderr}"}
                
                return {
                    "success": True,
                    "result": {
                        "branch": branch_name,
                        "message": "Branch created and checked out"
                    }
                }
            
            elif action == "switch":
                if not branch_name:
                    return {"success": False, "error": "branch_name is required for switch action"}
                
                result = subprocess.run(
                    ["git", "checkout", branch_name],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    return {"success": False, "error": f"Git branch switch failed: {result.stderr}"}
                
                return {
                    "success": True,
                    "result": {
                        "branch": branch_name,
                        "message": "Switched to branch"
                    }
                }
            
            elif action == "delete":
                if not branch_name:
                    return {"success": False, "error": "branch_name is required for delete action"}
                
                result = subprocess.run(
                    ["git", "branch", "-d", branch_name],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    # Try force delete
                    result = subprocess.run(
                        ["git", "branch", "-D", branch_name],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode != 0:
                        return {"success": False, "error": f"Git branch delete failed: {result.stderr}"}
                
                return {
                    "success": True,
                    "result": {
                        "branch": branch_name,
                        "message": "Branch deleted"
                    }
                }
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git command timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "Git is not installed or not in PATH"}
        except Exception as e:
            return {"success": False, "error": f"Error managing branches: {str(e)}"}
    
    def _git_log(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get git commit history."""
        limit = args.get("limit", 10)
        branch = args.get("branch")
        
        try:
            cmd = ["git", "log", f"--max-count={limit}", "--pretty=format:%H|%an|%ae|%ad|%s", "--date=iso"]
            if branch:
                cmd.append(branch)
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {"success": False, "error": f"Git log failed: {result.stderr}"}
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|', 4)
                if len(parts) == 5:
                    commits.append({
                        "hash": parts[0],
                        "author_name": parts[1],
                        "author_email": parts[2],
                        "date": parts[3],
                        "message": parts[4]
                    })
            
            return {
                "success": True,
                "result": {
                    "commits": commits,
                    "count": len(commits)
                }
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git command timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "Git is not installed or not in PATH"}
        except Exception as e:
            return {"success": False, "error": f"Error getting git log: {str(e)}"}
    
    def _git_diff(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Show git diff."""
        file_path = args.get("file_path")
        staged = args.get("staged", False)
        commit = args.get("commit")
        
        try:
            if commit:
                cmd = ["git", "diff", commit]
            elif staged:
                cmd = ["git", "diff", "--staged"]
            else:
                cmd = ["git", "diff"]
            
            if file_path:
                cmd.append(file_path)
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {"success": False, "error": f"Git diff failed: {result.stderr}"}
            
            return {
                "success": True,
                "result": {
                    "diff": result.stdout,
                    "file_path": file_path,
                    "staged": staged,
                    "commit": commit
                }
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git command timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "Git is not installed or not in PATH"}
        except Exception as e:
            return {"success": False, "error": f"Error getting git diff: {str(e)}"}
    
    def _http_request(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request."""
        url = args.get("url")
        method = args.get("method", "GET")
        headers = args.get("headers", {})
        body = args.get("body")
        timeout = args.get("timeout", 30)
        
        if not url:
            return {"success": False, "error": "url is required"}
        
        if not REQUESTS_AVAILABLE:
            return {"success": False, "error": "requests library is not installed. Install it with: pip install requests"}
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=body,
                timeout=timeout,
                allow_redirects=True
            )
            
            # Try to parse JSON response
            try:
                response_json = response.json()
            except:
                response_json = None
            
            return {
                "success": True,
                "result": {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.text,
                    "json": response_json,
                    "url": response.url
                }
            }
        except requests.exceptions.Timeout:
            return {"success": False, "error": f"Request timed out after {timeout} seconds"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"HTTP request failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Error making HTTP request: {str(e)}"}
    
    def _read_json_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read and parse JSON file."""
        file_path = args.get("file_path")
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            if not os.path.exists(resolved_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            
            with open(resolved_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "data": data
                }
            }
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Error reading JSON file: {str(e)}"}
    
    def _write_json_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Write JSON file."""
        file_path = args.get("file_path")
        data = args.get("data")
        indent = args.get("indent", 2)
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        if data is None:
            return {"success": False, "error": "data is required"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
            
            with open(resolved_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "message": "JSON file written successfully"
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error writing JSON file: {str(e)}"}
    
    def _read_yaml_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read and parse YAML file."""
        file_path = args.get("file_path")
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        if not YAML_AVAILABLE:
            return {"success": False, "error": "PyYAML library is not installed. Install it with: pip install pyyaml"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            if not os.path.exists(resolved_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            
            with open(resolved_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "data": data
                }
            }
        except yaml.YAMLError as e:
            return {"success": False, "error": f"Invalid YAML: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Error reading YAML file: {str(e)}"}
    
    def _write_yaml_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Write YAML file."""
        file_path = args.get("file_path")
        data = args.get("data")
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        if data is None:
            return {"success": False, "error": "data is required"}
        
        if not YAML_AVAILABLE:
            return {"success": False, "error": "PyYAML library is not installed. Install it with: pip install pyyaml"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
            
            with open(resolved_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "message": "YAML file written successfully"
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error writing YAML file: {str(e)}"}
    
    def _check_syntax(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check syntax of a code file."""
        file_path = args.get("file_path")
        language = args.get("language")
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            if not os.path.exists(resolved_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            
            # Infer language from extension if not provided
            if not language:
                ext = os.path.splitext(resolved_path)[1].lower()
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
                    '.php': 'php'
                }
                language = lang_map.get(ext, 'unknown')
            
            errors = []
            
            if language == 'python':
                # Use Python's built-in compiler
                try:
                    with open(resolved_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    compile(code, resolved_path, 'exec')
                except SyntaxError as e:
                    errors.append({
                        "line": e.lineno,
                        "column": e.offset,
                        "message": e.msg,
                        "text": e.text
                    })
            elif language in ['javascript', 'typescript']:
                # Try using node to check syntax
                try:
                    result = subprocess.run(
                        ['node', '--check', resolved_path],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode != 0:
                        errors.append({
                            "message": result.stderr or result.stdout
                        })
                except FileNotFoundError:
                    errors.append({"message": "Node.js not found, cannot check JavaScript/TypeScript syntax"})
            else:
                return {"success": False, "error": f"Syntax checking not supported for language: {language}"}
            
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "language": language,
                    "valid": len(errors) == 0,
                    "errors": errors
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error checking syntax: {str(e)}"}
    
    def _lint_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Lint a code file."""
        file_path = args.get("file_path")
        language = args.get("language")
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            if not os.path.exists(resolved_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            
            # Infer language from extension if not provided
            if not language:
                ext = os.path.splitext(resolved_path)[1].lower()
                lang_map = {
                    '.py': 'python',
                    '.js': 'javascript',
                    '.ts': 'typescript',
                    '.jsx': 'javascript',
                    '.tsx': 'typescript'
                }
                language = lang_map.get(ext, 'unknown')
            
            issues = []
            
            if language == 'python':
                # Try using flake8 or pylint
                for linter in ['flake8', 'pylint']:
                    try:
                        result = subprocess.run(
                            [linter, resolved_path],
                            capture_output=True,
                            text=True,
                            timeout=30,
                            cwd=self.project_root
                        )
                        if result.stdout:
                            for line in result.stdout.strip().split('\n'):
                                if line:
                                    issues.append({"linter": linter, "message": line})
                        break
                    except FileNotFoundError:
                        continue
                if not issues:
                    return {"success": False, "error": "No Python linter found (flake8 or pylint). Install one with: pip install flake8"}
            elif language in ['javascript', 'typescript']:
                # Try using eslint
                try:
                    result = subprocess.run(
                        ['npx', '--yes', 'eslint', resolved_path],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=self.project_root
                    )
                    if result.stdout:
                        for line in result.stdout.strip().split('\n'):
                            if line:
                                issues.append({"linter": "eslint", "message": line})
                except FileNotFoundError:
                    return {"success": False, "error": "npx not found. ESLint requires Node.js and npm."}
            else:
                return {"success": False, "error": f"Linting not supported for language: {language}"}
            
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "language": language,
                    "issues": issues,
                    "issue_count": len(issues)
                }
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Linter timed out"}
        except Exception as e:
            return {"success": False, "error": f"Error linting file: {str(e)}"}
    
    def _list_processes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List running processes."""
        pattern = args.get("pattern")
        
        try:
            if PSUTIL_AVAILABLE:
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
                    try:
                        proc_info = proc.info
                        name = proc_info.get('name', '')
                        cmdline = ' '.join(proc_info.get('cmdline', []))
                        
                        if pattern:
                            if pattern.lower() not in name.lower() and pattern.lower() not in cmdline.lower():
                                continue
                        
                        processes.append({
                            "pid": proc_info.get('pid'),
                            "name": name,
                            "cmdline": cmdline,
                            "cpu_percent": proc_info.get('cpu_percent'),
                            "memory_mb": proc_info.get('memory_info', {}).get('rss', 0) / 1024 / 1024 if proc_info.get('memory_info') else None
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                return {
                    "success": True,
                    "result": {
                        "processes": processes,
                        "count": len(processes)
                    }
                }
            else:
                # Fallback to ps command
                cmd = ['ps', 'aux']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode != 0:
                    return {"success": False, "error": "Failed to list processes"}
                
                processes = []
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        name = parts[10]
                        if pattern and pattern.lower() not in name.lower():
                            continue
                        processes.append({
                            "pid": int(parts[1]),
                            "name": name,
                            "cpu_percent": float(parts[2]),
                            "memory_percent": float(parts[3])
                        })
                
                return {
                    "success": True,
                    "result": {
                        "processes": processes,
                        "count": len(processes)
                    }
                }
        except Exception as e:
            return {"success": False, "error": f"Error listing processes: {str(e)}"}
    
    def _kill_process(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Kill a process."""
        pid = args.get("pid")
        name = args.get("name")
        signal_name = args.get("signal", "SIGTERM")
        
        if not pid and not name:
            return {"success": False, "error": "Either pid or name must be provided"}
        
        try:
            # Map signal names to signal numbers
            signal_map = {
                "SIGTERM": signal.SIGTERM,
                "SIGKILL": signal.SIGKILL,
                "SIGINT": signal.SIGINT
            }
            sig = signal_map.get(signal_name, signal.SIGTERM)
            
            if pid:
                # Kill by PID
                os.kill(pid, sig)
                return {
                    "success": True,
                    "result": {
                        "pid": pid,
                        "signal": signal_name,
                        "message": "Process killed successfully"
                    }
                }
            else:
                # Kill by name
                if PSUTIL_AVAILABLE:
                    killed = []
                    for proc in psutil.process_iter(['pid', 'name']):
                        try:
                            if name.lower() in proc.info.get('name', '').lower():
                                proc.kill()
                                killed.append(proc.info.get('pid'))
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    if killed:
                        return {
                            "success": True,
                            "result": {
                                "name": name,
                                "pids": killed,
                                "message": f"Killed {len(killed)} process(es)"
                            }
                        }
                    else:
                        return {"success": False, "error": f"No processes found matching: {name}"}
                else:
                    # Fallback to pkill
                    result = subprocess.run(
                        ['pkill', '-f', name],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        return {
                            "success": True,
                            "result": {
                                "name": name,
                                "message": "Process killed successfully"
                            }
                        }
                    else:
                        return {"success": False, "error": f"Failed to kill process: {name}"}
        except ProcessLookupError:
            return {"success": False, "error": "Process not found"}
        except PermissionError:
            return {"success": False, "error": "Permission denied. Cannot kill process."}
        except Exception as e:
            return {"success": False, "error": f"Error killing process: {str(e)}"}
    
    def _check_port(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a port is in use."""
        port = args.get("port")
        
        if not port:
            return {"success": False, "error": "port is required"}
        
        if not isinstance(port, int) or port < 1 or port > 65535:
            return {"success": False, "error": "Port must be an integer between 1 and 65535"}
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            in_use = result == 0
            
            process_info = None
            if in_use and PSUTIL_AVAILABLE:
                for conn in psutil.net_connections():
                    if conn.laddr.port == port:
                        try:
                            proc = psutil.Process(conn.pid)
                            process_info = {
                                "pid": conn.pid,
                                "name": proc.name(),
                                "cmdline": ' '.join(proc.cmdline())
                            }
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                        break
            
            return {
                "success": True,
                "result": {
                    "port": port,
                    "in_use": in_use,
                    "process": process_info
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error checking port: {str(e)}"}
    
    def _read_package_json(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read package.json file."""
        file_path = args.get("file_path", "package.json")
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            if not os.path.exists(resolved_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            
            with open(resolved_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "name": data.get("name"),
                    "version": data.get("version"),
                    "dependencies": data.get("dependencies", {}),
                    "devDependencies": data.get("devDependencies", {}),
                    "scripts": data.get("scripts", {}),
                    "full_data": data
                }
            }
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Error reading package.json: {str(e)}"}
    
    def _read_requirements_txt(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read requirements.txt file."""
        file_path = args.get("file_path", "requirements.txt")
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            if not os.path.exists(resolved_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            
            packages = []
            with open(resolved_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    # Parse package spec (name==version, name>=version, etc.)
                    if '==' in line:
                        name, version = line.split('==', 1)
                        packages.append({"name": name.strip(), "version": version.strip(), "spec": line})
                    elif '>=' in line:
                        name, version = line.split('>=', 1)
                        packages.append({"name": name.strip(), "version": version.strip(), "spec": line})
                    else:
                        packages.append({"name": line, "version": None, "spec": line})
            
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "packages": packages,
                    "count": len(packages)
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error reading requirements.txt: {str(e)}"}
    
    def _get_installed_packages(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get installed packages."""
        package_manager = args.get("package_manager")
        
        if not package_manager:
            return {"success": False, "error": "package_manager is required"}
        
        try:
            if package_manager == "npm":
                result = subprocess.run(
                    ['npm', 'list', '--depth=0', '--json'],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    return {"success": False, "error": f"npm command failed: {result.stderr}"}
                
                data = json.loads(result.stdout)
                dependencies = data.get("dependencies", {})
                
                packages = []
                for name, info in dependencies.items():
                    packages.append({
                        "name": name,
                        "version": info.get("version") if isinstance(info, dict) else str(info)
                    })
                
                return {
                    "success": True,
                    "result": {
                        "package_manager": package_manager,
                        "packages": packages,
                        "count": len(packages)
                    }
                }
            
            elif package_manager in ["pip", "pip3"]:
                result = subprocess.run(
                    [package_manager, 'list', '--format=json'],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    return {"success": False, "error": f"{package_manager} command failed: {result.stderr}"}
                
                packages = json.loads(result.stdout)
                
                return {
                    "success": True,
                    "result": {
                        "package_manager": package_manager,
                        "packages": packages,
                        "count": len(packages)
                    }
                }
            
            else:
                return {"success": False, "error": f"Unsupported package manager: {package_manager}"}
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except FileNotFoundError:
            return {"success": False, "error": f"{package_manager} is not installed or not in PATH"}
        except json.JSONDecodeError:
            return {"success": False, "error": "Failed to parse command output"}
        except Exception as e:
            return {"success": False, "error": f"Error getting installed packages: {str(e)}"}
    
    def _calculate_file_hash(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate file hash."""
        file_path = args.get("file_path")
        algorithm = args.get("algorithm", "sha256")
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            if not os.path.exists(resolved_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            
            if os.path.isdir(resolved_path):
                return {"success": False, "error": "Cannot hash directory, only files"}
            
            # Create hash object
            if algorithm == "md5":
                hash_obj = hashlib.md5()
            elif algorithm == "sha256":
                hash_obj = hashlib.sha256()
            elif algorithm == "sha1":
                hash_obj = hashlib.sha1()
            else:
                return {"success": False, "error": f"Unsupported algorithm: {algorithm}"}
            
            # Read file in chunks to handle large files
            with open(resolved_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            
            hash_value = hash_obj.hexdigest()
            
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "algorithm": algorithm,
                    "hash": hash_value
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error calculating file hash: {str(e)}"}
    
    def _get_environment_variable(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get system environment variable."""
        variable_name = args.get("variable_name")
        
        if not variable_name:
            return {"success": False, "error": "variable_name is required"}
        
        try:
            value = os.environ.get(variable_name)
            
            if value is None:
                return {
                    "success": True,
                    "result": {
                        "variable_name": variable_name,
                        "value": None,
                        "exists": False
                    }
                }
            
            return {
                "success": True,
                "result": {
                    "variable_name": variable_name,
                    "value": value,
                    "exists": True
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error getting environment variable: {str(e)}"}
    
    def _get_file_dependencies(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get file dependencies using file graph."""
        file_path = args.get("file_path")
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        if not self.file_graph:
            return {"success": False, "error": "File graph not available"}
        
        try:
            dependencies = self.file_graph.get_file_dependencies(file_path)
            return {
                "success": True,
                "result": dependencies
            }
        except Exception as e:
            return {"success": False, "error": f"Error getting file dependencies: {str(e)}"}
    
    def _find_related_files(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find related files using file graph."""
        file_path = args.get("file_path")
        max_depth = args.get("max_depth", 2)
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        if not self.file_graph:
            return {"success": False, "error": "File graph not available"}
        
        try:
            related = self.file_graph.find_related_files(file_path, max_depth)
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "related_files": related,
                    "count": len(related)
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error finding related files: {str(e)}"}
    
    def _get_component_boundaries(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get component boundaries for a file."""
        file_path = args.get("file_path")
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        if not self.file_graph:
            return {"success": False, "error": "File graph not available"}
        
        try:
            components = self.file_graph.get_component_boundaries(file_path)
            return {
                "success": True,
                "result": {
                    "file_path": file_path,
                    "components": components,
                    "count": len(components)
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error getting component boundaries: {str(e)}"}
    
    def _find_similar_patterns(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find similar code patterns."""
        pattern_type = args.get("pattern_type")
        file_path = args.get("file_path")
        
        if not pattern_type:
            return {"success": False, "error": "pattern_type is required"}
        
        if not self.file_graph:
            return {"success": False, "error": "File graph not available"}
        
        try:
            similar = self.file_graph.find_similar_patterns(pattern_type, file_path)
            return {
                "success": True,
                "result": {
                    "pattern_type": pattern_type,
                    "file_path": file_path,
                    "similar_patterns": similar,
                    "count": len(similar)
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error finding similar patterns: {str(e)}"}
    
    def _generate_diff(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate diff between old and new content."""
        file_path = args.get("file_path", "file")
        old_content = args.get("old_content")
        new_content = args.get("new_content")
        format_type = args.get("format", "unified")
        
        if old_content is None:
            return {"success": False, "error": "old_content is required"}
        if new_content is None:
            return {"success": False, "error": "new_content is required"}
        
        if not self.diff_engine:
            # Fallback to basic diff if diff_engine not available
            import difflib
            old_lines = old_content.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)
            diff = ''.join(difflib.unified_diff(old_lines, new_lines, fromfile=file_path, tofile=file_path))
            return {
                "success": True,
                "result": {
                    "diff": diff,
                    "format": "unified"
                }
            }
        
        try:
            if format_type == "unified":
                diff = self.diff_engine.compute_unified_diff(old_content, new_content, file_path)
                return {
                    "success": True,
                    "result": {
                        "diff": diff,
                        "format": "unified",
                        "file_path": file_path
                    }
                }
            else:  # minimal
                minimal = self.diff_engine.compute_minimal_patch(old_content, new_content, file_path)
                return {
                    "success": True,
                    "result": {
                        "diff": minimal["patch"],
                        "format": "minimal",
                        "file_path": file_path,
                        "changes": minimal["changes"],
                        "stats": minimal["stats"]
                    }
                }
        except Exception as e:
            return {"success": False, "error": f"Error generating diff: {str(e)}"}
    
    def _parse_ast(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Parse file to AST."""
        file_path = args.get("file_path")
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        if not self.ast_tools:
            return {"success": False, "error": "AST tools not available"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            result = self.ast_tools.parse_ast(resolved_path)
            return result
        except Exception as e:
            return {"success": False, "error": f"Error parsing AST: {str(e)}"}
    
    def _find_references(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find references to a symbol."""
        file_path = args.get("file_path")
        symbol = args.get("symbol")
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        if not symbol:
            return {"success": False, "error": "symbol is required"}
        
        if not self.ast_tools:
            return {"success": False, "error": "AST tools not available"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            result = self.ast_tools.find_references(resolved_path, symbol)
            return result
        except Exception as e:
            return {"success": False, "error": f"Error finding references: {str(e)}"}
    
    def _get_type_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get type information for a symbol."""
        file_path = args.get("file_path")
        symbol = args.get("symbol")
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        if not symbol:
            return {"success": False, "error": "symbol is required"}
        
        if not self.ast_tools:
            return {"success": False, "error": "AST tools not available"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            result = self.ast_tools.get_type_info(resolved_path, symbol)
            return result
        except Exception as e:
            return {"success": False, "error": f"Error getting type info: {str(e)}"}
    
    def _find_unused_code(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find unused code (imports, functions, variables)."""
        file_path = args.get("file_path")
        check_type = args.get("check_type", "all")
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        if not self.ast_tools:
            return {"success": False, "error": "AST tools not available"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            
            if check_type in ["imports", "all"]:
                result = self.ast_tools.find_unused_imports(resolved_path)
                if not result.get("success"):
                    return result
                
                unused_imports = result.get("unused_imports", [])
                
                if check_type == "imports":
                    return result
                
                # Also check for unused functions/variables if "all"
                unused_functions = []
                unused_variables = []
                
                if check_type == "all":
                    # Get AST to find functions and variables
                    ast_result = self.ast_tools.parse_ast(resolved_path)
                    if ast_result.get("success"):
                        ast_data = ast_result.get("ast", {})
                        functions = ast_data.get("functions", [])
                        variables = ast_data.get("variables", [])
                        
                        # Simplified check - would need more sophisticated analysis
                        # For now, just return unused imports
                        pass
                
                return {
                    "success": True,
                    "file_path": file_path,
                    "unused_imports": unused_imports,
                    "unused_functions": unused_functions,
                    "unused_variables": unused_variables,
                    "total_unused": len(unused_imports) + len(unused_functions) + len(unused_variables)
                }
            else:
                return {"success": False, "error": f"check_type '{check_type}' not yet fully implemented"}
        except Exception as e:
            return {"success": False, "error": f"Error finding unused code: {str(e)}"}
    
    def _detect_potential_bugs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Detect potential bugs."""
        file_path = args.get("file_path")
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        if not self.ast_tools:
            return {"success": False, "error": "AST tools not available"}
        
        try:
            resolved_path = self._ensure_safe_path(file_path)
            result = self.ast_tools.detect_potential_bugs(resolved_path)
            return result
        except Exception as e:
            return {"success": False, "error": f"Error detecting bugs: {str(e)}"}
    
    def _web_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search the web using DuckDuckGo."""
        query = args.get("query")
        max_results = args.get("max_results", 10)
        
        if not query:
            return {"success": False, "error": "query is required"}
        
        if not DUCKDUCKGO_AVAILABLE:
            return {
                "success": False,
                "error": "duckduckgo-search library is not installed. Install it with: pip install duckduckgo-search"
            }
        
        try:
            # Limit max_results to reasonable value
            max_results = min(max_results, 20)
            
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", "")
                })
            
            return {
                "success": True,
                "result": {
                    "query": query,
                    "results": formatted_results,
                    "count": len(formatted_results)
                }
            }
        except Exception as e:
            logger.error(f"Web search error: {e}", exc_info=True)
            return {"success": False, "error": f"Web search failed: {str(e)}"}
    
    def _fetch_web_page(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch and extract content from a web page."""
        url = args.get("url")
        extract_links = args.get("extract_links", True)
        max_content_length = args.get("max_content_length", 50000)
        
        if not url:
            return {"success": False, "error": "url is required"}
        
        if not REQUESTS_AVAILABLE:
            return {
                "success": False,
                "error": "requests library is not installed. Install it with: pip install requests"
            }
        
        try:
            # Fetch the page
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            html_content = response.text
            content_text = html_content
            links = []
            
            # Extract text and links if BeautifulSoup is available
            if BEAUTIFULSOUP_AVAILABLE:
                try:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style", "meta", "link"]):
                        script.decompose()
                    
                    # Get text content
                    content_text = soup.get_text(separator=' ', strip=True)
                    
                    # Limit content length
                    if len(content_text) > max_content_length:
                        content_text = content_text[:max_content_length] + "... [content truncated]"
                    
                    # Extract links if requested
                    if extract_links:
                        for a_tag in soup.find_all('a', href=True):
                            href = a_tag['href']
                            # Convert relative URLs to absolute
                            if href.startswith('/'):
                                from urllib.parse import urljoin
                                href = urljoin(url, href)
                            elif not href.startswith('http'):
                                continue
                            
                            link_text = a_tag.get_text(strip=True)
                            links.append({
                                "url": href,
                                "text": link_text[:100]  # Limit link text length
                            })
                except Exception as e:
                    logger.warning(f"BeautifulSoup parsing failed: {e}, using raw HTML")
                    # Fall back to raw HTML if parsing fails
            
            return {
                "success": True,
                "result": {
                    "url": response.url,
                    "status_code": response.status_code,
                    "content": content_text,
                    "content_length": len(content_text),
                    "links": links[:50] if extract_links else [],  # Limit to 50 links
                    "links_count": len(links) if extract_links else 0
                }
            }
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to fetch web page: {str(e)}"}
        except Exception as e:
            logger.error(f"Error fetching web page: {e}", exc_info=True)
            return {"success": False, "error": f"Error fetching web page: {str(e)}"}
    
    def _extract_links(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Extract links from a web page."""
        url = args.get("url")
        filter_domain = args.get("filter_domain")
        max_links = args.get("max_links", 50)
        
        if not url:
            return {"success": False, "error": "url is required"}
        
        if not REQUESTS_AVAILABLE:
            return {
                "success": False,
                "error": "requests library is not installed. Install it with: pip install requests"
            }
        
        try:
            # Fetch the page
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            links = []
            
            if BEAUTIFULSOUP_AVAILABLE:
                try:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag['href']
                        # Convert relative URLs to absolute
                        if href.startswith('/'):
                            from urllib.parse import urljoin
                            href = urljoin(url, href)
                        elif not href.startswith('http'):
                            continue
                        
                        # Filter by domain if specified
                        if filter_domain:
                            from urllib.parse import urlparse
                            parsed = urlparse(href)
                            if filter_domain not in parsed.netloc:
                                continue
                        
                        link_text = a_tag.get_text(strip=True)
                        links.append({
                            "url": href,
                            "text": link_text[:100]  # Limit link text length
                        })
                        
                        if len(links) >= max_links:
                            break
                except Exception as e:
                    logger.warning(f"BeautifulSoup parsing failed: {e}")
                    return {"success": False, "error": f"Failed to parse HTML: {str(e)}"}
            else:
                # Fallback: use regex to find links (less reliable)
                import re
                link_pattern = r'href=["\']([^"\']+)["\']'
                matches = re.findall(link_pattern, response.text)
                for match in matches[:max_links]:
                    if match.startswith('/'):
                        from urllib.parse import urljoin
                        match = urljoin(url, match)
                    elif not match.startswith('http'):
                        continue
                    
                    if filter_domain and filter_domain not in match:
                        continue
                    
                    links.append({"url": match, "text": ""})
            
            return {
                "success": True,
                "result": {
                    "url": response.url,
                    "links": links,
                    "count": len(links)
                }
            }
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to fetch web page: {str(e)}"}
        except Exception as e:
            logger.error(f"Error extracting links: {e}", exc_info=True)
            return {"success": False, "error": f"Error extracting links: {str(e)}"}


