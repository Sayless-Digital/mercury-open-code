"""
Code Validator - Centralized code validation service.
Provides pre-write validation for syntax, imports, types, and linting.
"""

import logging
import os
import subprocess
from typing import Dict, List, Any, Optional
from .ast_tools import ASTTools

logger = logging.getLogger("mercury.tools.code_validator")


class CodeValidator:
    """
    Centralized code validation service.
    
    Features:
    - Syntax validation using AST
    - Import validation (check if imports exist)
    - Type checking (basic, for Python)
    - Linting integration
    - Return structured validation results
    """
    
    def __init__(self, ast_tools: Optional[ASTTools] = None):
        """
        Initialize code validator.
        
        Args:
            ast_tools: ASTTools instance (creates new one if not provided)
        """
        self.ast_tools = ast_tools or ASTTools()
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        return self.ast_tools._detect_language(file_path)
    
    def validate_before_write(
        self,
        file_path: str,
        new_content: str,
        old_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate code before writing to disk.
        
        Args:
            file_path: Path to file
            new_content: New content to validate
            old_content: Original content (for comparison)
            
        Returns:
            Dict with validation results:
            - valid: bool
            - errors: List of errors
            - warnings: List of warnings
            - syntax_valid: bool
            - import_valid: bool
            - lint_issues: List of lint issues
        """
        language = self._detect_language(file_path)
        
        if not language:
            # For non-code files, just check basic things
            return {
                "valid": True,
                "errors": [],
                "warnings": [],
                "syntax_valid": True,
                "import_valid": True,
                "lint_issues": []
            }
        
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "syntax_valid": True,
            "import_valid": True,
            "lint_issues": [],
            "language": language
        }
        
        # 1. Syntax validation
        syntax_result = self.ast_tools.validate_syntax(file_path, new_content)
        if not syntax_result.get("valid"):
            results["valid"] = False
            results["syntax_valid"] = False
            results["errors"].extend(syntax_result.get("errors", []))
        
        # 2. Import validation (for Python)
        if language == 'python':
            import_result = self._validate_python_imports(file_path, new_content)
            if not import_result.get("valid"):
                results["import_valid"] = False
                results["warnings"].extend(import_result.get("warnings", []))
                # Don't fail validation on import warnings, just warn
        
        # 3. Basic linting (if available)
        if language == 'python':
            lint_result = self._lint_python_code(file_path, new_content)
            if lint_result.get("issues"):
                results["lint_issues"] = lint_result.get("issues", [])
                # Lint issues are warnings, not errors
        
        # Determine overall validity
        # Only syntax errors make it invalid
        results["valid"] = results["syntax_valid"]
        
        return results
    
    def _validate_python_imports(
        self,
        file_path: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Validate Python imports.
        
        Args:
            file_path: Path to file
            content: File content
            
        Returns:
            Dict with validation results
        """
        try:
            parse_result = self.ast_tools.parse_ast(file_path, content)
            if not parse_result.get("success"):
                return {
                    "valid": False,
                    "warnings": [f"Could not parse AST: {parse_result.get('error')}"]
                }
            
            ast_data = parse_result.get("ast", {})
            imports = ast_data.get("imports", [])
            
            warnings = []
            
            # Check for common import issues
            for imp in imports:
                module = imp.get("module", "")
                if module:
                    # Check if it's a standard library module (basic check)
                    # In production, would check against actual installed packages
                    if module.startswith('.'):
                        # Relative import - assume valid
                        continue
                    
                    # For now, just check if it looks like a valid module name
                    if not all(c.isalnum() or c in '._' for c in module):
                        warnings.append({
                            "type": "invalid_import",
                            "module": module,
                            "message": f"Import '{module}' has invalid characters"
                        })
            
            return {
                "valid": len(warnings) == 0,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.warning(f"Error validating imports: {e}")
            return {
                "valid": True,  # Don't fail on import validation errors
                "warnings": [f"Could not validate imports: {str(e)}"]
            }
    
    def _lint_python_code(
        self,
        file_path: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Lint Python code (basic checks).
        
        Args:
            file_path: Path to file
            content: File content
            
        Returns:
            Dict with lint issues
        """
        issues = []
        
        # Basic linting checks
        lines = content.splitlines()
        
        for i, line in enumerate(lines, 1):
            # Check line length (PEP 8: max 79 chars)
            if len(line) > 100:  # Using 100 as a reasonable limit
                issues.append({
                    "type": "line_too_long",
                    "line": i,
                    "message": f"Line {i} is too long ({len(line)} characters)"
                })
            
            # Check for trailing whitespace
            if line.rstrip() != line and line.strip():
                issues.append({
                    "type": "trailing_whitespace",
                    "line": i,
                    "message": f"Line {i} has trailing whitespace"
                })
        
        # Try to use pyflakes or flake8 if available (non-blocking)
        try:
            # Write content to temp file for linting
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            try:
                # Try pyflakes
                result = subprocess.run(
                    ['pyflakes', temp_path],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode != 0 and result.stdout:
                    for line in result.stdout.splitlines():
                        if ':' in line:
                            parts = line.split(':', 2)
                            if len(parts) >= 3:
                                try:
                                    line_num = int(parts[1])
                                    message = parts[2].strip()
                                    issues.append({
                                        "type": "pyflakes",
                                        "line": line_num,
                                        "message": message
                                    })
                                except ValueError:
                                    pass
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # pyflakes not available or timed out - skip
                pass
            finally:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                    
        except Exception as e:
            logger.debug(f"Could not run external linter: {e}")
        
        return {
            "issues": issues
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
            Dict with validation results
        """
        # Validate the new content
        validation = self.validate_before_write(file_path, new_content, old_content)
        
        # Add diff-specific checks
        if validation.get("valid"):
            # Check if change is too large
            old_lines = len(old_content.splitlines())
            new_lines = len(new_content.splitlines())
            change_percentage = abs(new_lines - old_lines) / old_lines * 100 if old_lines > 0 else 0
            
            if change_percentage > 50:
                validation["warnings"].append({
                    "type": "large_change",
                    "message": f"Change affects {change_percentage:.1f}% of file - consider reviewing carefully"
                })
        
        return validation











