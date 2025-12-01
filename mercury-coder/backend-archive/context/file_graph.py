"""
File Graph - Tracks file relationships, imports, dependencies, and component boundaries.
Builds a graph of the codebase structure for top-tier AI agent context awareness.
"""

import os
import re
import logging
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("mercury.context.file_graph")


@dataclass
class FileNode:
    """Represents a file in the graph."""
    path: str
    imports: Set[str] = field(default_factory=set)  # Files this imports
    imported_by: Set[str] = field(default_factory=set)  # Files that import this
    exports: Set[str] = field(default_factory=set)  # Symbols exported
    components: List[Dict[str, Any]] = field(default_factory=list)  # React/Vue components
    classes: List[str] = field(default_factory=list)  # Class names
    functions: List[str] = field(default_factory=list)  # Function names
    api_endpoints: List[str] = field(default_factory=list)  # API endpoints used
    naming_conventions: Dict[str, Any] = field(default_factory=dict)  # Naming patterns


@dataclass
class ComponentBoundary:
    """Represents a component boundary (React, Vue, etc.)."""
    name: str
    type: str  # 'react', 'vue', 'class', 'function'
    file_path: str
    line_start: int
    line_end: int
    props: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


class FileGraph:
    """
    Builds and maintains a graph of file relationships in the codebase.
    
    Tracks:
    - Import/dependency relationships
    - Component boundaries (React, Vue, etc.)
    - API endpoints used
    - Naming conventions
    - Code patterns
    """
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize file graph.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or os.getcwd()
        self.project_root = os.path.abspath(self.project_root)
        self.nodes: Dict[str, FileNode] = {}  # path -> FileNode
        self.component_boundaries: Dict[str, List[ComponentBoundary]] = defaultdict(list)
    
    def _normalize_path(self, file_path: str) -> str:
        """Normalize file path relative to project root."""
        if os.path.isabs(file_path):
            try:
                return os.path.relpath(file_path, self.project_root)
            except ValueError:
                return file_path
        return file_path
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.vue': 'vue',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
        }
        return lang_map.get(ext)
    
    def _parse_python_imports(self, content: str, file_path: str) -> Set[str]:
        """Parse Python imports from file content."""
        imports = set()
        
        # Match import statements
        import_patterns = [
            r'^import\s+([a-zA-Z0-9_.]+)',
            r'^from\s+([a-zA-Z0-9_.]+)\s+import',
        ]
        
        for line in content.split('\n'):
            for pattern in import_patterns:
                match = re.match(pattern, line.strip())
                if match:
                    module = match.group(1)
                    # Try to resolve to file path
                    resolved = self._resolve_python_import(module, file_path)
                    if resolved:
                        imports.add(resolved)
        
        return imports
    
    def _parse_javascript_imports(self, content: str, file_path: str) -> Set[str]:
        """Parse JavaScript/TypeScript imports from file content."""
        imports = set()
        
        # Match ES6 imports: import ... from '...'
        es6_pattern = r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
        # Match require: require('...')
        require_pattern = r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
        
        for pattern in [es6_pattern, require_pattern]:
            matches = re.finditer(pattern, content)
            for match in matches:
                module = match.group(1)
                # Skip node_modules and built-ins
                if not module.startswith('.') and '/' not in module:
                    continue
                resolved = self._resolve_javascript_import(module, file_path)
                if resolved:
                    imports.add(resolved)
        
        return imports
    
    def _resolve_python_import(self, module: str, from_file: str) -> Optional[str]:
        """Resolve Python import to file path."""
        # Simple resolution - look for .py files
        # In practice, would need to handle packages, __init__.py, etc.
        module_parts = module.split('.')
        
        # Try relative to current file
        from_dir = os.path.dirname(from_file)
        if from_dir:
            potential_path = os.path.join(from_dir, *module_parts) + '.py'
            if os.path.exists(os.path.join(self.project_root, potential_path)):
                return self._normalize_path(potential_path)
        
        # Try from project root
        potential_path = os.path.join(*module_parts) + '.py'
        full_path = os.path.join(self.project_root, potential_path)
        if os.path.exists(full_path):
            return self._normalize_path(full_path)
        
        return None
    
    def _resolve_javascript_import(self, module: str, from_file: str) -> Optional[str]:
        """Resolve JavaScript import to file path."""
        from_dir = os.path.dirname(from_file)
        
        # Handle relative imports
        if module.startswith('.'):
            # Relative import
            if module.startswith('./'):
                module = module[2:]
            elif module.startswith('../'):
                # Go up directories
                parts = module.split('../')
                for _ in parts[:-1]:
                    from_dir = os.path.dirname(from_dir)
                module = parts[-1]
            
            # Try with .js, .jsx, .ts, .tsx extensions
            for ext in ['', '.js', '.jsx', '.ts', '.tsx']:
                potential_path = os.path.join(from_dir, module + ext)
                full_path = os.path.join(self.project_root, potential_path)
                if os.path.exists(full_path):
                    return self._normalize_path(potential_path)
        
        return None
    
    def _extract_react_components(self, content: str, file_path: str) -> List[ComponentBoundary]:
        """Extract React components from file."""
        components = []
        
        # Match function components: function ComponentName() or const ComponentName = () =>
        function_component_pattern = r'(?:function|const)\s+([A-Z][a-zA-Z0-9_]*)\s*[=:]?\s*(?:\(|=>)'
        # Match class components: class ComponentName extends
        class_component_pattern = r'class\s+([A-Z][a-zA-Z0-9_]*)\s+extends\s+React\.Component'
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check function components
            match = re.search(function_component_pattern, line)
            if match:
                component_name = match.group(1)
                # Find component end (simplified - would need proper parsing)
                end_line = self._find_component_end(lines, i - 1)
                components.append(ComponentBoundary(
                    name=component_name,
                    type='react',
                    file_path=file_path,
                    line_start=i,
                    line_end=end_line
                ))
            
            # Check class components
            match = re.search(class_component_pattern, line)
            if match:
                component_name = match.group(1)
                end_line = self._find_class_end(lines, i - 1)
                components.append(ComponentBoundary(
                    name=component_name,
                    type='react',
                    file_path=file_path,
                    line_start=i,
                    line_end=end_line
                ))
        
        return components
    
    def _extract_vue_components(self, content: str, file_path: str) -> List[ComponentBoundary]:
        """Extract Vue components from file."""
        components = []
        
        # Vue single file components have <script> tags
        script_match = re.search(r'<script[^>]*>', content)
        if script_match:
            # Try to find component name
            name_match = re.search(r'name\s*:\s*["\']([^"\']+)["\']', content)
            component_name = name_match.group(1) if name_match else os.path.basename(file_path)
            
            components.append(ComponentBoundary(
                name=component_name,
                type='vue',
                file_path=file_path,
                line_start=1,
                line_end=len(content.split('\n'))
            ))
        
        return components
    
    def _extract_python_classes(self, content: str) -> List[str]:
        """Extract Python class names."""
        classes = []
        class_pattern = r'^class\s+([a-zA-Z0-9_]+)'
        
        for line in content.split('\n'):
            match = re.match(class_pattern, line.strip())
            if match:
                classes.append(match.group(1))
        
        return classes
    
    def _extract_python_functions(self, content: str) -> List[str]:
        """Extract Python function names."""
        functions = []
        function_pattern = r'^def\s+([a-zA-Z0-9_]+)'
        
        for line in content.split('\n'):
            match = re.match(function_pattern, line.strip())
            if match:
                functions.append(match.group(1))
        
        return functions
    
    def _extract_api_endpoints(self, content: str) -> List[str]:
        """Extract API endpoints used in code."""
        endpoints = []
        
        # Match common API patterns
        patterns = [
            r'["\'](https?://[^"\']+)["\']',  # HTTP URLs
            r'fetch\s*\(\s*["\']([^"\']+)["\']',  # fetch calls
            r'axios\.(get|post|put|delete)\s*\(\s*["\']([^"\']+)["\']',  # axios calls
            r'@app\.(get|post|put|delete)\s*\(["\']([^"\']+)["\']',  # Flask/FastAPI routes
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                endpoint = match.group(1) if len(match.groups()) == 1 else match.group(2)
                if endpoint and endpoint not in endpoints:
                    endpoints.append(endpoint)
        
        return endpoints
    
    def _extract_naming_conventions(self, content: str, language: str) -> Dict[str, Any]:
        """Extract naming conventions from code."""
        conventions = {
            "function_naming": [],
            "class_naming": [],
            "variable_naming": []
        }
        
        if language == 'python':
            # Python: functions use snake_case, classes use PascalCase
            function_pattern = r'def\s+([a-z_][a-z0-9_]*)'
            class_pattern = r'class\s+([A-Z][a-zA-Z0-9_]*)'
            
            for line in content.split('\n'):
                func_match = re.search(function_pattern, line)
                if func_match:
                    conventions["function_naming"].append(func_match.group(1))
                
                class_match = re.search(class_pattern, line)
                if class_match:
                    conventions["class_naming"].append(class_match.group(1))
        
        elif language in ['javascript', 'typescript']:
            # JS: functions use camelCase, classes use PascalCase
            function_pattern = r'(?:function|const|let|var)\s+([a-z][a-zA-Z0-9]*)\s*[=:]?\s*(?:\(|=>)'
            class_pattern = r'class\s+([A-Z][a-zA-Z0-9]*)'
            
            for line in content.split('\n'):
                func_match = re.search(function_pattern, line)
                if func_match:
                    conventions["function_naming"].append(func_match.group(1))
                
                class_match = re.search(class_pattern, line)
                if class_match:
                    conventions["class_naming"].append(class_match.group(1))
        
        return conventions
    
    def _find_component_end(self, lines: List[str], start_idx: int) -> int:
        """Find the end of a component (simplified)."""
        brace_count = 0
        in_string = False
        string_char = None
        
        for i in range(start_idx, len(lines)):
            line = lines[i]
            for char in line:
                if char in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return i + 1
        
        return len(lines)
    
    def _find_class_end(self, lines: List[str], start_idx: int) -> int:
        """Find the end of a class (simplified)."""
        indent_level = None
        
        for i in range(start_idx, len(lines)):
            line = lines[i]
            if indent_level is None and line.strip():
                indent_level = len(line) - len(line.lstrip())
            
            if indent_level is not None:
                if line.strip() and not line.startswith(' ' * indent_level) and not line.startswith('\t' * indent_level):
                    if i > start_idx:
                        return i
        
        return len(lines)
    
    def add_file(self, file_path: str, content: Optional[str] = None) -> FileNode:
        """
        Add or update a file in the graph.
        
        Args:
            file_path: Path to file
            content: File content (read from disk if not provided)
            
        Returns:
            FileNode for the file
        """
        normalized_path = self._normalize_path(file_path)
        
        # Read content if not provided
        if content is None:
            full_path = os.path.join(self.project_root, normalized_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    logger.warning(f"Could not read file {file_path}: {e}")
                    content = ""
            else:
                content = ""
        
        # Get or create node
        if normalized_path not in self.nodes:
            self.nodes[normalized_path] = FileNode(path=normalized_path)
        
        node = self.nodes[normalized_path]
        language = self._detect_language(normalized_path)
        
        # Parse imports
        if language == 'python':
            node.imports = self._parse_python_imports(content, normalized_path)
        elif language in ['javascript', 'typescript']:
            node.imports = self._parse_javascript_imports(content, normalized_path)
        
        # Update reverse imports (imported_by)
        for imported_file in node.imports:
            if imported_file not in self.nodes:
                self.nodes[imported_file] = FileNode(path=imported_file)
            self.nodes[imported_file].imported_by.add(normalized_path)
        
        # Extract components
        if language in ['javascript', 'typescript']:
            components = self._extract_react_components(content, normalized_path)
            self.component_boundaries[normalized_path].extend(components)
            node.components = [{"name": c.name, "type": c.type} for c in components]
        elif language == 'vue':
            components = self._extract_vue_components(content, normalized_path)
            self.component_boundaries[normalized_path].extend(components)
            node.components = [{"name": c.name, "type": c.type} for c in components]
        
        # Extract classes and functions
        if language == 'python':
            node.classes = self._extract_python_classes(content)
            node.functions = self._extract_python_functions(content)
        
        # Extract API endpoints
        node.api_endpoints = self._extract_api_endpoints(content)
        
        # Extract naming conventions
        if language:
            node.naming_conventions = self._extract_naming_conventions(content, language)
        
        return node
    
    def get_file_dependencies(self, file_path: str) -> Dict[str, Any]:
        """
        Get files that import/use a given file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dict with dependencies information
        """
        normalized_path = self._normalize_path(file_path)
        node = self.nodes.get(normalized_path)
        
        if not node:
            return {
                "file_path": file_path,
                "dependencies": [],
                "imported_by": []
            }
        
        return {
            "file_path": file_path,
            "dependencies": list(node.imports),
            "imported_by": list(node.imported_by),
            "exports": list(node.exports)
        }
    
    def find_related_files(self, file_path: str, max_depth: int = 2) -> List[str]:
        """
        Find files related by imports/components.
        
        Args:
            file_path: Starting file path
            max_depth: Maximum depth to traverse
            
        Returns:
            List of related file paths
        """
        normalized_path = self._normalize_path(file_path)
        related = set()
        visited = set()
        
        def traverse(current_path: str, depth: int):
            if depth > max_depth or current_path in visited:
                return
            
            visited.add(current_path)
            node = self.nodes.get(current_path)
            if not node:
                return
            
            # Add direct imports and files that import this
            related.update(node.imports)
            related.update(node.imported_by)
            
            # Recursively traverse
            if depth < max_depth:
                for imported in node.imports:
                    traverse(imported, depth + 1)
                for importer in node.imported_by:
                    traverse(importer, depth + 1)
        
        traverse(normalized_path, 0)
        related.discard(normalized_path)  # Remove self
        return list(related)
    
    def get_component_boundaries(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Get component structure for a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            List of component boundaries
        """
        normalized_path = self._normalize_path(file_path)
        components = self.component_boundaries.get(normalized_path, [])
        
        return [
            {
                "name": c.name,
                "type": c.type,
                "file_path": c.file_path,
                "line_start": c.line_start,
                "line_end": c.line_end,
                "props": c.props,
                "dependencies": c.dependencies
            }
            for c in components
        ]
    
    def find_similar_patterns(self, pattern_type: str, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find code with similar patterns.
        
        Args:
            pattern_type: Type of pattern to match ('naming', 'structure', 'api_usage')
            file_path: Optional file to compare against
            
        Returns:
            List of similar patterns
        """
        # Simplified pattern matching
        # In practice, would use more sophisticated similarity algorithms
        
        if file_path:
            normalized_path = self._normalize_path(file_path)
            node = self.nodes.get(normalized_path)
            if not node:
                return []
        
        similar = []
        
        # Find files with similar naming conventions
        if pattern_type == 'naming' and file_path:
            target_conventions = node.naming_conventions
            for path, other_node in self.nodes.items():
                if path != normalized_path:
                    other_conventions = other_node.naming_conventions
                    # Simple similarity check
                    if target_conventions.get("function_naming") and other_conventions.get("function_naming"):
                        similar.append({
                            "file_path": path,
                            "similarity": "naming_convention",
                            "details": other_conventions
                        })
        
        return similar
    
    def build_graph(self, project_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Build graph for entire project.
        
        Args:
            project_path: Project root path (uses self.project_root if None)
            
        Returns:
            Dict with build statistics
        """
        if project_path:
            self.project_root = os.path.abspath(project_path)
        
        files_processed = 0
        errors = 0
        
        # Walk project directory
        for root, dirs, files in os.walk(self.project_root):
            # Skip common ignored directories
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.next'}]
            
            for file in files:
                if file.startswith('.'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.project_root)
                
                # Only process code files
                language = self._detect_language(rel_path)
                if not language:
                    continue
                
                try:
                    self.add_file(rel_path)
                    files_processed += 1
                except Exception as e:
                    logger.warning(f"Error processing {rel_path}: {e}")
                    errors += 1
        
        return {
            "files_processed": files_processed,
            "errors": errors,
            "nodes": len(self.nodes),
            "relationships": sum(len(n.imports) for n in self.nodes.values())
        }












