"""
AST Tools - Parse code to AST and perform static analysis.
Provides AST parsing, reference finding, type information, and unused code detection.
"""

import ast
import re
import logging
import os
from typing import Dict, List, Any, Optional, Set, Tuple

logger = logging.getLogger("mercury.tools.ast_tools")


class ASTTools:
    """
    Provides AST parsing and static analysis utilities.
    
    Supports:
    - Python (using built-in ast module)
    - JavaScript/TypeScript (basic parsing, would need tree-sitter for full support)
    """
    
    def __init__(self):
        """Initialize AST tools."""
        pass
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
        }
        return lang_map.get(ext)
    
    def parse_ast(self, file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse code to AST.
        
        Args:
            file_path: Path to file
            content: File content (read from disk if not provided)
            
        Returns:
            Dict with AST information
        """
        language = self._detect_language(file_path)
        
        if not language:
            return {
                "success": False,
                "error": f"Language not supported for AST parsing: {file_path}"
            }
        
        # Read content if not provided
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Could not read file: {str(e)}"
                }
        
        if language == 'python':
            return self._parse_python_ast(file_path, content)
        elif language in ['javascript', 'typescript']:
            return self._parse_javascript_ast(file_path, content)
        else:
            return {
                "success": False,
                "error": f"AST parsing not yet implemented for {language}"
            }
    
    def _parse_python_ast(self, file_path: str, content: str) -> Dict[str, Any]:
        """Parse Python code to AST."""
        try:
            tree = ast.parse(content, filename=file_path)
            
            # Extract information from AST
            classes = []
            functions = []
            imports = []
            variables = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "bases": [self._ast_node_to_string(base) for base in node.bases],
                        "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    })
                elif isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "decorators": [self._ast_node_to_string(d) for d in node.decorator_list]
                    })
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            "module": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                            "type": "import"
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append({
                            "module": module,
                            "name": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                            "type": "from_import"
                        })
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            variables.append({
                                "name": target.id,
                                "line": node.lineno
                            })
            
            return {
                "success": True,
                "language": "python",
                "file_path": file_path,
                "ast": {
                    "classes": classes,
                    "functions": functions,
                    "imports": imports,
                    "variables": variables
                }
            }
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e.msg} at line {e.lineno}",
                "syntax_error": {
                    "message": e.msg,
                    "line": e.lineno,
                    "offset": e.offset
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error parsing AST: {str(e)}"
            }
    
    def _parse_javascript_ast(self, file_path: str, content: str) -> Dict[str, Any]:
        """Parse JavaScript/TypeScript code to AST (simplified)."""
        # Simplified JavaScript parsing using regex
        # For production, would use tree-sitter or @babel/parser
        
        classes = []
        functions = []
        imports = []
        variables = []
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Match class declarations
            class_match = re.search(r'class\s+([a-zA-Z0-9_]+)', line)
            if class_match:
                classes.append({
                    "name": class_match.group(1),
                    "line": i
                })
            
            # Match function declarations
            function_patterns = [
                r'function\s+([a-zA-Z0-9_]+)\s*\(',
                r'const\s+([a-zA-Z0-9_]+)\s*=\s*(?:\(|function)',
                r'let\s+([a-zA-Z0-9_]+)\s*=\s*(?:\(|function)',
                r'var\s+([a-zA-Z0-9_]+)\s*=\s*(?:\(|function)'
            ]
            for pattern in function_patterns:
                func_match = re.search(pattern, line)
                if func_match:
                    functions.append({
                        "name": func_match.group(1),
                        "line": i
                    })
                    break
            
            # Match imports
            import_match = re.search(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", line)
            if import_match:
                imports.append({
                    "module": import_match.group(1),
                    "line": i,
                    "type": "es6_import"
                })
            
            require_match = re.search(r"require\s*\(\s*['\"]([^'\"]+)['\"]", line)
            if require_match:
                imports.append({
                    "module": require_match.group(1),
                    "line": i,
                    "type": "require"
                })
        
        return {
            "success": True,
            "language": "javascript",
            "file_path": file_path,
            "ast": {
                "classes": classes,
                "functions": functions,
                "imports": imports,
                "variables": variables
            },
            "note": "Simplified parsing - for full AST use tree-sitter"
        }
    
    def _ast_node_to_string(self, node: ast.AST) -> str:
        """Convert AST node to string representation."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._ast_node_to_string(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        else:
            return ast.dump(node)
    
    def find_references(self, file_path: str, symbol: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Find all references to a symbol in a file.
        
        Args:
            file_path: Path to file
            symbol: Symbol name to find
            content: File content (read if not provided)
            
        Returns:
            Dict with references found
        """
        language = self._detect_language(file_path)
        
        if not language:
            return {
                "success": False,
                "error": f"Language not supported: {file_path}"
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
        
        references = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Simple pattern matching for symbol references
            # For Python, would use AST visitor
            # For JS, would use proper parser
            
            if language == 'python':
                # Use regex to find symbol references
                pattern = r'\b' + re.escape(symbol) + r'\b'
                if re.search(pattern, line):
                    references.append({
                        "line": i,
                        "content": line.strip(),
                        "type": "reference"
                    })
            else:
                # JavaScript/TypeScript
                pattern = r'\b' + re.escape(symbol) + r'\b'
                if re.search(pattern, line):
                    references.append({
                        "line": i,
                        "content": line.strip(),
                        "type": "reference"
                    })
        
        return {
            "success": True,
            "symbol": symbol,
            "file_path": file_path,
            "references": references,
            "count": len(references)
        }
    
    def get_type_info(self, file_path: str, symbol: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Get type information for a symbol.
        
        Args:
            file_path: Path to file
            symbol: Symbol name
            content: File content
            
        Returns:
            Dict with type information
        """
        language = self._detect_language(file_path)
        
        if language == 'python':
            return self._get_python_type_info(file_path, symbol, content)
        else:
            return {
                "success": False,
                "error": f"Type information not yet implemented for {language}"
            }
    
    def _get_python_type_info(self, file_path: str, symbol: str, content: Optional[str]) -> Dict[str, Any]:
        """Get Python type information."""
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
            
            type_info = {
                "symbol": symbol,
                "type": None,
                "line": None,
                "definition": None
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == symbol:
                    type_info["type"] = "function"
                    type_info["line"] = node.lineno
                    type_info["definition"] = {
                        "args": [arg.arg for arg in node.args.args],
                        "returns": self._ast_node_to_string(node.returns) if node.returns else None
                    }
                    break
                elif isinstance(node, ast.ClassDef) and node.name == symbol:
                    type_info["type"] = "class"
                    type_info["line"] = node.lineno
                    type_info["definition"] = {
                        "bases": [self._ast_node_to_string(base) for base in node.bases]
                    }
                    break
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == symbol:
                            type_info["type"] = "variable"
                            type_info["line"] = node.lineno
                            # Try to infer type from value
                            if isinstance(node.value, ast.Constant):
                                type_info["definition"] = {
                                    "value_type": type(node.value.value).__name__
                                }
                            break
            
            return {
                "success": True,
                "type_info": type_info
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting type info: {str(e)}"
            }
    
    def find_unused_imports(self, file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Find unused imports in a file.
        
        Args:
            file_path: Path to file
            content: File content
            
        Returns:
            Dict with unused imports
        """
        language = self._detect_language(file_path)
        
        if not language:
            return {
                "success": False,
                "error": f"Language not supported: {file_path}"
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
        
        if language == 'python':
            return self._find_unused_python_imports(file_path, content)
        elif language in ['javascript', 'typescript']:
            return self._find_unused_javascript_imports(file_path, content)
        else:
            return {
                "success": False,
                "error": f"Unused import detection not yet implemented for {language}"
            }
    
    def _find_unused_python_imports(self, file_path: str, content: str) -> Dict[str, Any]:
        """Find unused Python imports."""
        try:
            tree = ast.parse(content, filename=file_path)
            
            imported_names = set()
            used_names = set()
            
            # Collect imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name.split('.')[0]
                        imported_names.add(name)
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        imported_names.add(name)
            
            # Collect used names
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
            
            # Find unused
            unused = imported_names - used_names
            
            unused_imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name.split('.')[0]
                        if name in unused:
                            unused_imports.append({
                                "name": name,
                                "module": alias.name,
                                "line": node.lineno,
                                "type": "import"
                            })
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        if name in unused:
                            unused_imports.append({
                                "name": name,
                                "module": node.module or "",
                                "line": node.lineno,
                                "type": "from_import"
                            })
            
            return {
                "success": True,
                "file_path": file_path,
                "unused_imports": unused_imports,
                "count": len(unused_imports)
            }
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e.msg} at line {e.lineno}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error finding unused imports: {str(e)}"
            }
    
    def _find_unused_javascript_imports(self, file_path: str, content: str) -> Dict[str, Any]:
        """Find unused JavaScript imports (simplified)."""
        # Simplified detection using regex
        # For production, would use proper AST parser
        
        imported_names = set()
        used_names = set()
        
        lines = content.split('\n')
        
        # Collect imports
        for i, line in enumerate(lines, 1):
            # ES6 imports: import { name1, name2 } from 'module'
            import_match = re.search(r'import\s+{([^}]+)}\s+from', line)
            if import_match:
                names = [n.strip() for n in import_match.group(1).split(',')]
                imported_names.update(names)
            
            # Default import: import name from 'module'
            default_import = re.search(r'import\s+(\w+)\s+from', line)
            if default_import:
                imported_names.add(default_import.group(1))
        
        # Collect used names (simplified - just check if name appears)
        for name in imported_names:
            # Check if name is used (not in import statements)
            pattern = r'\b' + re.escape(name) + r'\b'
            for i, line in enumerate(lines, 1):
                if i > 1:  # Skip first line (likely import)
                    if re.search(pattern, line) and 'import' not in line:
                        used_names.add(name)
                        break
        
        unused = imported_names - used_names
        
        unused_imports = []
        for i, line in enumerate(lines, 1):
            if 'import' in line:
                for name in unused:
                    if re.search(r'\b' + re.escape(name) + r'\b', line):
                        unused_imports.append({
                            "name": name,
                            "line": i,
                            "type": "es6_import"
                        })
        
        return {
            "success": True,
            "file_path": file_path,
            "unused_imports": unused_imports,
            "count": len(unused_imports),
            "note": "Simplified detection - may have false positives"
        }
    
    def detect_dead_code(self, file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Detect dead/unreachable code.
        
        Args:
            file_path: Path to file
            content: File content
            
        Returns:
            Dict with dead code detected
        """
        # Simplified dead code detection
        # In practice, would need more sophisticated analysis
        
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Could not read file: {str(e)}"
                }
        
        language = self._detect_language(file_path)
        
        if language == 'python':
            return self._detect_python_dead_code(file_path, content)
        else:
            return {
                "success": False,
                "error": f"Dead code detection not yet implemented for {language}"
            }
    
    def _detect_python_dead_code(self, file_path: str, content: str) -> Dict[str, Any]:
        """Detect dead code in Python (simplified)."""
        try:
            tree = ast.parse(content, filename=file_path)
            
            dead_code = []
            
            # Find functions that are never called
            functions = {}
            function_calls = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions[node.name] = {
                        "line": node.lineno,
                        "is_private": node.name.startswith('_')
                    }
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        function_calls.add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        function_calls.add(node.func.attr)
            
            # Check for unused functions (not private, not called)
            for func_name, func_info in functions.items():
                if not func_info["is_private"] and func_name not in function_calls:
                    dead_code.append({
                        "type": "unused_function",
                        "name": func_name,
                        "line": func_info["line"]
                    })
            
            return {
                "success": True,
                "file_path": file_path,
                "dead_code": dead_code,
                "count": len(dead_code)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error detecting dead code: {str(e)}"
            }
    
    def detect_potential_bugs(self, file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Detect potential bugs using static analysis.
        
        Args:
            file_path: Path to file
            content: File content
            
        Returns:
            Dict with potential bugs
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
        
        language = self._detect_language(file_path)
        
        if language == 'python':
            return self._detect_python_bugs(file_path, content)
        else:
            return {
                "success": False,
                "error": f"Bug detection not yet implemented for {language}"
            }
    
    def _detect_python_bugs(self, file_path: str, content: str) -> Dict[str, Any]:
        """Detect potential bugs in Python code."""
        bugs = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for common issues
            stripped = line.strip()
            
            # Bare except clauses
            if re.match(r'^\s*except\s*:', stripped):
                bugs.append({
                    "type": "bare_except",
                    "line": i,
                    "message": "Bare except clause catches all exceptions, including SystemExit and KeyboardInterrupt",
                    "severity": "warning"
                })
            
            # Comparison with None using == instead of is
            if re.search(r'==\s+None', line) or re.search(r'!=\s+None', line):
                bugs.append({
                    "type": "none_comparison",
                    "line": i,
                    "message": "Use 'is None' or 'is not None' instead of '== None' or '!= None'",
                    "severity": "info"
                })
            
            # Mutable default arguments
            if re.search(r'def\s+\w+\s*\([^)]*=\s*[\[\{]', line):
                bugs.append({
                    "type": "mutable_default",
                    "line": i,
                    "message": "Mutable default arguments can lead to unexpected behavior",
                    "severity": "warning"
                })
        
        return {
            "success": True,
            "file_path": file_path,
            "potential_bugs": bugs,
            "count": len(bugs)
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
    
    def apply_ast_edit(
        self,
        file_path: str,
        edit_type: str,
        edit_params: Dict[str, Any],
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply an AST-based edit to code.
        
        Args:
            file_path: Path to file
            edit_type: Type of edit ('replace_function', 'replace_text', 'add_import', etc.)
            edit_params: Parameters for the edit
            content: File content (read if not provided)
            
        Returns:
            Dict with edited content and metadata
        """
        language = self._detect_language(file_path)
        
        if language != 'python':
            return {
                "success": False,
                "error": f"AST editing only supported for Python, got {language}"
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
            
            if edit_type == 'replace_function':
                function_name = edit_params.get('function_name')
                new_body = edit_params.get('new_body')
                
                if not function_name or not new_body:
                    return {
                        "success": False,
                        "error": "replace_function requires 'function_name' and 'new_body'"
                    }
                
                # Find function
                function_node = None
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == function_name:
                        function_node = node
                        break
                
                if function_node is None:
                    return {
                        "success": False,
                        "error": f"Function '{function_name}' not found"
                    }
                
                # Parse new body
                try:
                    new_body_ast = ast.parse(new_body, mode='exec')
                except SyntaxError as e:
                    return {
                        "success": False,
                        "error": f"Syntax error in new body: {e.msg} at line {e.lineno}"
                    }
                
                # Replace function body (simplified - would need AST manipulation library for full support)
                # For now, use string-based replacement with validation
                lines = content.splitlines(keepends=True)
                func_start = function_node.lineno - 1
                
                # Find function end
                func_indent = len(lines[func_start]) - len(lines[func_start].lstrip())
                func_end = len(lines)
                
                for i in range(func_start + 1, len(lines)):
                    line = lines[i]
                    stripped = line.lstrip()
                    if not stripped or stripped.startswith('#'):
                        continue
                    indent = len(line) - len(stripped)
                    if indent <= func_indent and (stripped.startswith('def ') or stripped.startswith('class ')):
                        func_end = i
                        break
                
                # Extract signature
                sig_line = lines[func_start]
                colon_pos = sig_line.find(':')
                if colon_pos == -1:
                    return {
                        "success": False,
                        "error": "Could not find function signature"
                    }
                
                signature = sig_line[:colon_pos + 1].rstrip()
                body_indent = ' ' * (func_indent + 4)
                new_func = signature + '\n'
                for line in new_body.splitlines():
                    new_func += body_indent + line + '\n'
                
                new_content = ''.join(lines[:func_start] + [new_func] + lines[func_end:])
                
                # Validate
                validation = self.validate_syntax(file_path, new_content)
                if not validation.get("valid"):
                    return {
                        "success": False,
                        "error": "Edit resulted in syntax errors",
                        "validation": validation
                    }
                
                return {
                    "success": True,
                    "new_content": new_content,
                    "old_content": content,
                    "edit_type": edit_type,
                    "validation": validation
                }
            
            elif edit_type == 'replace_text':
                old_text = edit_params.get('old_text')
                new_text = edit_params.get('new_text')
                
                if not old_text or not new_text:
                    return {
                        "success": False,
                        "error": "replace_text requires 'old_text' and 'new_text'"
                    }
                
                if old_text not in content:
                    return {
                        "success": False,
                        "error": "old_text not found in content"
                    }
                
                new_content = content.replace(old_text, new_text, 1)
                
                # Validate
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
                    "edit_type": edit_type,
                    "validation": validation
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown edit type: {edit_type}"
                }
                
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error in original file: {e.msg} at line {e.lineno}"
            }
        except Exception as e:
            logger.error(f"Error applying AST edit: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Error applying AST edit: {str(e)}"
            }


