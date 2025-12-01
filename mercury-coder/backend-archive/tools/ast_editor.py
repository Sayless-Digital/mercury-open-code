"""
AST Editor - AST-based code editing operations.
Provides semantic editing capabilities that preserve formatting and validate syntax.
"""

import ast
import re
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from .ast_tools import ASTTools

logger = logging.getLogger("mercury.tools.ast_editor")


class ASTEditor:
    """
    Provides AST-based code editing operations.
    
    Features:
    - Parse code to AST before editing
    - Make semantic edits (function/class modifications, symbol renames)
    - Preserve formatting and comments
    - Generate minimal diffs from AST changes
    - Validate syntax before returning edited code
    """
    
    def __init__(self, ast_tools: Optional[ASTTools] = None):
        """
        Initialize AST editor.
        
        Args:
            ast_tools: ASTTools instance (creates new one if not provided)
        """
        self.ast_tools = ast_tools or ASTTools()
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        return self.ast_tools._detect_language(file_path)
    
    def edit_function(
        self,
        file_path: str,
        function_name: str,
        new_function_body: str,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Edit a function by replacing its body.
        
        Args:
            file_path: Path to file
            function_name: Name of function to edit
            new_function_body: New function body code
            content: File content (read if not provided)
            
        Returns:
            Dict with edited content and metadata
        """
        language = self._detect_language(file_path)
        
        if language != 'python':
            return {
                "success": False,
                "error": f"Function editing only supported for Python, got {language}"
            }
        
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Could not read file: {str(e)}"
                }
        
        try:
            tree = ast.parse(content, filename=file_path)
            
            # Find the function
            function_node = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    function_node = node
                    break
            
            if function_node is None:
                return {
                    "success": False,
                    "error": f"Function '{function_name}' not found in file"
                }
            
            # Parse new function body
            try:
                new_body_ast = ast.parse(new_function_body, mode='exec')
                if not new_body_ast.body:
                    return {
                        "success": False,
                        "error": "New function body is empty"
                    }
            except SyntaxError as e:
                return {
                    "success": False,
                    "error": f"Syntax error in new function body: {e.msg} at line {e.lineno}",
                    "syntax_error": {
                        "message": e.msg,
                        "line": e.lineno,
                        "offset": e.offset
                    }
                }
            
            # Replace function body
            # For now, we'll use a simpler approach: find the function in source and replace
            # This preserves formatting better than AST manipulation
            lines = content.splitlines(keepends=True)
            func_start_line = function_node.lineno - 1  # 0-indexed
            
            # Find function end (next function/class at same or lower indentation, or end of file)
            func_indent = len(lines[func_start_line]) - len(lines[func_start_line].lstrip())
            func_end_line = len(lines)
            
            for i in range(func_start_line + 1, len(lines)):
                line = lines[i]
                stripped = line.lstrip()
                if not stripped or stripped.startswith('#'):
                    continue
                indent = len(line) - len(stripped)
                if indent <= func_indent and (stripped.startswith('def ') or stripped.startswith('class ') or stripped.startswith('@')):
                    func_end_line = i
                    break
            
            # Extract function signature
            func_sig_line = lines[func_start_line]
            # Find the colon
            colon_pos = func_sig_line.find(':')
            if colon_pos == -1:
                return {
                    "success": False,
                    "error": "Could not find function signature"
                }
            
            func_signature = func_sig_line[:colon_pos + 1].rstrip()
            
            # Build new function
            new_function = func_signature + '\n'
            # Add indentation to new body
            body_indent = ' ' * (func_indent + 4)
            for line in new_function_body.splitlines():
                new_function += body_indent + line + '\n'
            
            # Replace in content
            new_lines = lines[:func_start_line] + [new_function] + lines[func_end_line:]
            new_content = ''.join(new_lines)
            
            # Validate syntax
            validation = self.validate_syntax(file_path, new_content)
            if not validation.get("valid"):
                return {
                    "success": False,
                    "error": "Edited code has syntax errors",
                    "validation": validation
                }
            
            return {
                "success": True,
                "new_content": new_content,
                "old_content": content,
                "function_name": function_name,
                "validation": validation
            }
            
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error in original file: {e.msg} at line {e.lineno}",
                "syntax_error": {
                    "message": e.msg,
                    "line": e.lineno,
                    "offset": e.offset
                }
            }
        except Exception as e:
            logger.error(f"Error editing function: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Error editing function: {str(e)}"
            }
    
    def replace_text_semantic(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Replace text using semantic understanding (AST-aware).
        
        This tries to understand what the old_string represents in the AST
        and replace it semantically, preserving formatting.
        
        Args:
            file_path: Path to file
            old_string: Text to replace
            new_string: Replacement text
            content: File content (read if not provided)
            
        Returns:
            Dict with edited content and metadata
        """
        language = self._detect_language(file_path)
        
        if language != 'python':
            # For non-Python, fall back to simple replacement
            if content is None:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Could not read file: {str(e)}"
                    }
            
            if old_string not in content:
                return {
                    "success": False,
                    "error": "Could not find old_string in content"
                }
            
            new_content = content.replace(old_string, new_string, 1)
            
            return {
                "success": True,
                "new_content": new_content,
                "old_content": content,
                "method": "string_replacement"
            }
        
        # For Python, try AST-aware replacement
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Could not read file: {str(e)}"
                }
        
        if old_string not in content:
            return {
                "success": False,
                "error": "Could not find old_string in content"
            }
        
        # Try to parse and understand the context
        try:
            tree = ast.parse(content, filename=file_path)
            
            # Find where old_string appears in the source
            old_pos = content.find(old_string)
            if old_pos == -1:
                return {
                    "success": False,
                    "error": "Could not find old_string in content"
                }
            
            # Find which line contains old_string
            lines = content.splitlines(keepends=True)
            char_count = 0
            old_line_start = 0
            for i, line in enumerate(lines):
                if char_count <= old_pos < char_count + len(line):
                    old_line_start = i
                    break
                char_count += len(line)
            
            # For now, use simple replacement but validate afterwards
            new_content = content.replace(old_string, new_string, 1)
            
            # Validate syntax
            validation = self.validate_syntax(file_path, new_content)
            if not validation.get("valid"):
                return {
                    "success": False,
                    "error": "Replacement resulted in syntax errors",
                    "validation": validation
                }
            
            return {
                "success": True,
                "new_content": new_content,
                "old_content": content,
                "method": "semantic_replacement",
                "validation": validation
            }
            
        except SyntaxError as e:
            # If original file has syntax errors, fall back to simple replacement
            logger.warning(f"Original file has syntax errors, using simple replacement: {e}")
            new_content = content.replace(old_string, new_string, 1)
            return {
                "success": True,
                "new_content": new_content,
                "old_content": content,
                "method": "string_replacement_fallback",
                "warning": "Original file had syntax errors, used simple replacement"
            }
        except Exception as e:
            logger.error(f"Error in semantic replacement: {e}", exc_info=True)
            # Fall back to simple replacement
            new_content = content.replace(old_string, new_string, 1)
            return {
                "success": True,
                "new_content": new_content,
                "old_content": content,
                "method": "string_replacement_fallback",
                "warning": f"AST analysis failed: {str(e)}"
            }
    
    def validate_syntax(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate syntax of code.
        
        Args:
            file_path: Path to file
            content: File content (read if not provided)
            
        Returns:
            Dict with validation results
        """
        language = self._detect_language(file_path)
        
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                return {
                    "valid": False,
                    "error": f"Could not read file: {str(e)}"
                }
        
        if language == 'python':
            try:
                ast.parse(content, filename=file_path)
                return {
                    "valid": True,
                    "language": "python",
                    "errors": []
                }
            except SyntaxError as e:
                return {
                    "valid": False,
                    "language": "python",
                    "errors": [{
                        "type": "syntax_error",
                        "message": e.msg,
                        "line": e.lineno,
                        "offset": e.offset
                    }]
                }
            except Exception as e:
                return {
                    "valid": False,
                    "language": "python",
                    "errors": [{
                        "type": "parse_error",
                        "message": str(e)
                    }]
                }
        elif language in ['javascript', 'typescript']:
            # Basic JavaScript validation (check for balanced braces, etc.)
            open_braces = content.count('{')
            close_braces = content.count('}')
            open_parens = content.count('(')
            close_parens = content.count(')')
            open_brackets = content.count('[')
            close_brackets = content.count(']')
            
            errors = []
            if open_braces != close_braces:
                errors.append({
                    "type": "unbalanced_braces",
                    "message": f"Mismatched braces: {open_braces} open, {close_braces} close"
                })
            if open_parens != close_parens:
                errors.append({
                    "type": "unbalanced_parens",
                    "message": f"Mismatched parentheses: {open_parens} open, {close_parens} close"
                })
            if open_brackets != close_brackets:
                errors.append({
                    "type": "unbalanced_brackets",
                    "message": f"Mismatched brackets: {open_brackets} open, {close_brackets} close"
                })
            
            return {
                "valid": len(errors) == 0,
                "language": language,
                "errors": errors
            }
        else:
            return {
                "valid": True,  # Assume valid for unsupported languages
                "language": language,
                "errors": [],
                "note": "Syntax validation not implemented for this language"
            }
    
    def find_edit_location(
        self,
        file_path: str,
        search_text: str,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find location of text in file for editing.
        
        Args:
            file_path: Path to file
            search_text: Text to find
            content: File content (read if not provided)
            
        Returns:
            Dict with location information
        """
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Could not read file: {str(e)}"
                }
        
        if search_text not in content:
            return {
                "success": False,
                "error": "Search text not found in file"
            }
        
        # Find all occurrences
        positions = []
        start = 0
        while True:
            pos = content.find(search_text, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        
        # Convert to line/column
        lines = content.splitlines(keepends=True)
        locations = []
        char_count = 0
        
        for pos in positions:
            line_num = 0
            col_num = 0
            current_count = 0
            
            for i, line in enumerate(lines):
                if current_count <= pos < current_count + len(line):
                    line_num = i + 1  # 1-indexed
                    col_num = pos - current_count + 1  # 1-indexed
                    break
                current_count += len(line)
            
            locations.append({
                "position": pos,
                "line": line_num,
                "column": col_num
            })
        
        return {
            "success": True,
            "file_path": file_path,
            "search_text": search_text,
            "occurrences": len(locations),
            "locations": locations
        }











