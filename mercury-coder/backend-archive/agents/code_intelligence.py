"""
Code Intelligence Service - Analyzes code structure for planning.
Provides AST-based analysis to help planners understand code structure and dependencies.
"""

import logging
import os
from typing import Dict, List, Any, Optional, Set
from tools.ast_tools import ASTTools

logger = logging.getLogger("mercury.agents.code_intelligence")


class CodeIntelligence:
    """
    Analyzes code structure for planning.
    
    Features:
    - Extract function/class signatures
    - Find all call sites for a function
    - Detect interface boundaries
    - Predict impact of changes
    - Return structured analysis for planner
    """
    
    def __init__(self, ast_tools: Optional[ASTTools] = None):
        """
        Initialize code intelligence service.
        
        Args:
            ast_tools: ASTTools instance (creates new one if not provided)
        """
        self.ast_tools = ast_tools or ASTTools()
    
    def analyze_file_structure(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze file structure to extract functions, classes, and interfaces.
        
        Args:
            file_path: Path to file
            content: File content (read if not provided)
            
        Returns:
            Dict with structure analysis
        """
        parse_result = self.ast_tools.parse_ast(file_path, content)
        
        if not parse_result.get("success"):
            return {
                "success": False,
                "error": parse_result.get("error"),
                "file_path": file_path
            }
        
        ast_data = parse_result.get("ast", {})
        
        return {
            "success": True,
            "file_path": file_path,
            "language": parse_result.get("language"),
            "classes": ast_data.get("classes", []),
            "functions": ast_data.get("functions", []),
            "imports": ast_data.get("imports", []),
            "variables": ast_data.get("variables", [])
        }
    
    def find_function_call_sites(
        self,
        file_path: str,
        function_name: str,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find all call sites for a function in a file.
        
        Args:
            file_path: Path to file
            function_name: Name of function to find
            content: File content (read if not provided)
            
        Returns:
            Dict with call sites found
        """
        language = self.ast_tools._detect_language(file_path)
        
        if language != 'python':
            return {
                "success": False,
                "error": f"Call site detection only supported for Python, got {language}"
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
            import ast
            tree = ast.parse(content, filename=file_path)
            
            call_sites = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check if this is a call to the function
                    if isinstance(node.func, ast.Name) and node.func.id == function_name:
                        call_sites.append({
                            "line": node.lineno,
                            "column": node.col_offset,
                            "type": "direct_call"
                        })
                    elif isinstance(node.func, ast.Attribute) and node.func.attr == function_name:
                        call_sites.append({
                            "line": node.lineno,
                            "column": node.col_offset,
                            "type": "method_call",
                            "object": self._ast_node_to_string(node.func.value)
                        })
            
            return {
                "success": True,
                "file_path": file_path,
                "function_name": function_name,
                "call_sites": call_sites,
                "count": len(call_sites)
            }
            
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e.msg} at line {e.lineno}"
            }
        except Exception as e:
            logger.error(f"Error finding call sites: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Error finding call sites: {str(e)}"
            }
    
    def _ast_node_to_string(self, node) -> str:
        """Convert AST node to string representation."""
        import ast
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._ast_node_to_string(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        else:
            return ast.dump(node)
    
    def detect_interface_boundaries(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect interface boundaries (public vs private, exports, etc.).
        
        Args:
            file_path: Path to file
            content: File content (read if not provided)
            
        Returns:
            Dict with interface boundaries
        """
        structure = self.analyze_file_structure(file_path, content)
        
        if not structure.get("success"):
            return structure
        
        public_functions = []
        private_functions = []
        public_classes = []
        private_classes = []
        
        # Python convention: names starting with _ are private
        for func in structure.get("functions", []):
            if func.get("name", "").startswith('_'):
                private_functions.append(func)
            else:
                public_functions.append(func)
        
        for cls in structure.get("classes", []):
            if cls.get("name", "").startswith('_'):
                private_classes.append(cls)
            else:
                public_classes.append(cls)
        
        return {
            "success": True,
            "file_path": file_path,
            "public_interface": {
                "functions": public_functions,
                "classes": public_classes
            },
            "private_implementation": {
                "functions": private_functions,
                "classes": private_classes
            },
            "exports": public_functions + public_classes  # What this file exports
        }
    
    def predict_change_impact(
        self,
        file_path: str,
        target_symbol: str,
        change_type: str = "modify",
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Predict the impact of changing a symbol.
        
        Args:
            file_path: Path to file
            target_symbol: Symbol to change (function/class name)
            change_type: Type of change ("modify", "rename", "delete")
            content: File content (read if not provided)
            
        Returns:
            Dict with impact analysis
        """
        structure = self.analyze_file_structure(file_path, content)
        
        if not structure.get("success"):
            return {
                "success": False,
                "error": structure.get("error")
            }
        
        impact = {
            "target_symbol": target_symbol,
            "change_type": change_type,
            "file_path": file_path,
            "affected_functions": [],
            "affected_classes": [],
            "call_sites": [],
            "breaking_changes": [],
            "risk_level": "low"
        }
        
        # Find if it's a function or class
        is_function = any(f.get("name") == target_symbol for f in structure.get("functions", []))
        is_class = any(c.get("name") == target_symbol for c in structure.get("classes", []))
        
        if not is_function and not is_class:
            return {
                "success": False,
                "error": f"Symbol '{target_symbol}' not found in file"
            }
        
        # Find call sites if it's a function
        if is_function:
            call_sites_result = self.find_function_call_sites(file_path, target_symbol, content)
            if call_sites_result.get("success"):
                impact["call_sites"] = call_sites_result.get("call_sites", [])
        
        # Determine risk level
        if change_type == "delete":
            if impact["call_sites"]:
                impact["risk_level"] = "high"
                impact["breaking_changes"].append({
                    "type": "deletion",
                    "message": f"Deleting {target_symbol} will break {len(impact['call_sites'])} call sites"
                })
            else:
                impact["risk_level"] = "low"
        elif change_type == "rename":
            if impact["call_sites"]:
                impact["risk_level"] = "medium"
                impact["breaking_changes"].append({
                    "type": "rename",
                    "message": f"Renaming {target_symbol} requires updating {len(impact['call_sites'])} call sites"
                })
            else:
                impact["risk_level"] = "low"
        elif change_type == "modify":
            # Modifying signature is riskier than modifying body
            impact["risk_level"] = "medium"
        
        return {
            "success": True,
            "impact": impact
        }
    
    def get_dependencies_from_code(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract actual dependencies from code (not just file graph).
        
        Args:
            file_path: Path to file
            content: File content (read if not provided)
            
        Returns:
            Dict with dependencies
        """
        structure = self.analyze_file_structure(file_path, content)
        
        if not structure.get("success"):
            return structure
        
        imports = structure.get("imports", [])
        
        # Categorize imports
        standard_library = []
        third_party = []
        local = []
        
        for imp in imports:
            module = imp.get("module", "")
            if not module:
                continue
            
            # Heuristic: standard library modules don't have dots (usually)
            # Local imports start with . or are relative
            if module.startswith('.'):
                local.append(imp)
            elif '.' not in module and len(module.split('.')) == 1:
                # Could be standard library or third party - assume standard for now
                standard_library.append(imp)
            else:
                third_party.append(imp)
        
        return {
            "success": True,
            "file_path": file_path,
            "dependencies": {
                "standard_library": standard_library,
                "third_party": third_party,
                "local": local,
                "all": imports
            },
            "import_count": len(imports)
        }

