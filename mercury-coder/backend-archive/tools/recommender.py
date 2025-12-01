"""
Tool recommendation system using RAG (Retrieval Augmented Generation).
Helps the agent find the right tools for a given task using semantic search.
"""

import logging
from typing import List, Dict, Any, Optional
from .definitions import TOOL_DEFINITIONS

logger = logging.getLogger("mercury.tools.recommender")


class ToolRecommender:
    """Recommends tools based on user queries using semantic search."""
    
    def __init__(self, vector_store=None):
        """
        Initialize tool recommender.
        
        Args:
            vector_store: Optional vector store for semantic search (from memory system)
        """
        self.tools = TOOL_DEFINITIONS
        self.vector_store = vector_store
        
        # Build tool index with descriptions and use cases
        self._build_tool_index()
    
    def _build_tool_index(self):
        """Build searchable index of tools with descriptions and use cases."""
        self.tool_index = []
        
        # Tool categories and use cases
        tool_use_cases = {
            "read_file": [
                "read a file", "examine code", "check configuration", "view file contents",
                "look at a file", "open file", "see what's in a file"
            ],
            "write_file": [
                "create a file", "write code", "save file", "create new file",
                "write content", "generate file"
            ],
            "edit_file": [
                "modify file", "change code", "update file", "edit code",
                "make changes", "fix code", "update a file"
            ],
            "delete_file": [
                "delete file", "remove file", "clean up", "delete a file"
            ],
            "list_directory": [
                "list files", "see directory", "explore folder", "browse directory",
                "what files are here", "show files"
            ],
            "create_directory": [
                "create folder", "make directory", "create new folder", "mkdir"
            ],
            "delete_directory": [
                "delete folder", "remove directory", "delete folder"
            ],
            "move_file": [
                "move file", "rename file", "reorganize", "move a file"
            ],
            "copy_file": [
                "copy file", "duplicate", "backup file"
            ],
            "file_exists": [
                "check if file exists", "file exists", "does file exist"
            ],
            "get_file_info": [
                "file info", "file metadata", "file size", "file details"
            ],
            "find_files": [
                "find files", "search for files", "locate files", "find all .py files"
            ],
            "read_directory_tree": [
                "directory tree", "folder structure", "project structure", "file tree"
            ],
            "read_env_file": [
                "read .env", "environment variables", "env file", "config"
            ],
            "write_env_file": [
                "write .env", "set environment variables", "update env"
            ],
            "read_json_file": [
                "read json", "parse json", "read package.json", "read config json"
            ],
            "write_json_file": [
                "write json", "create json", "update json", "modify json"
            ],
            "read_yaml_file": [
                "read yaml", "parse yaml", "read docker-compose", "yaml config"
            ],
            "write_yaml_file": [
                "write yaml", "create yaml", "update yaml"
            ],
            "execute_command": [
                "run command", "execute command", "run script", "run npm install",
                "run test", "execute shell command", "run terminal command"
            ],
            "codebase_search": [
                "search code", "find code", "search codebase", "find function",
                "find class", "search for code pattern"
            ],
            "grep": [
                "grep", "search text", "find text", "search pattern", "regex search"
            ],
            "search_replace_in_multiple_files": [
                "replace in multiple files", "batch replace", "find and replace",
                "replace across files"
            ],
            "check_syntax": [
                "check syntax", "validate syntax", "syntax error", "syntax check"
            ],
            "lint_file": [
                "lint code", "check code quality", "lint file", "code linting"
            ],
            "http_request": [
                "make http request", "api call", "fetch url", "http get", "http post",
                "test api", "call endpoint", "web request"
            ],
            "list_processes": [
                "list processes", "running processes", "show processes", "ps"
            ],
            "kill_process": [
                "kill process", "stop process", "terminate process", "kill pid"
            ],
            "check_port": [
                "check port", "port in use", "is port available", "port check"
            ],
            "read_package_json": [
                "read package.json", "npm dependencies", "package info"
            ],
            "read_requirements_txt": [
                "read requirements", "python packages", "pip packages"
            ],
            "get_installed_packages": [
                "installed packages", "npm list", "pip list", "what packages installed"
            ],
            "calculate_file_hash": [
                "file hash", "checksum", "file integrity", "md5", "sha256"
            ],
            "get_environment_variable": [
                "get env var", "environment variable", "system variable"
            ],
            "git_status": [
                "git status", "check git status", "what changed", "git changes"
            ],
            "git_add": [
                "git add", "stage files", "git stage", "add to git"
            ],
            "git_commit": [
                "git commit", "commit changes", "save commit"
            ],
            "git_push": [
                "git push", "push to remote", "upload commits"
            ],
            "git_pull": [
                "git pull", "pull changes", "update from remote"
            ],
            "git_branch": [
                "git branch", "create branch", "switch branch", "list branches"
            ],
            "git_log": [
                "git log", "commit history", "git history", "see commits"
            ],
            "git_diff": [
                "git diff", "see changes", "what changed", "view diff"
            ]
        }
        
        # Build index entries
        for tool in self.tools:
            tool_name = tool["name"]
            description = tool.get("description", "")
            use_cases = tool_use_cases.get(tool_name, [])
            
            # Create searchable text
            search_text = f"{tool_name} {description} {' '.join(use_cases)}"
            
            self.tool_index.append({
                "tool": tool,
                "name": tool_name,
                "description": description,
                "use_cases": use_cases,
                "search_text": search_text
            })
    
    def recommend_tools(
        self,
        query: str,
        limit: int = 5,
        use_vector_search: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Recommend tools based on user query.
        
        Args:
            query: User's query or task description
            limit: Maximum number of tools to return
            use_vector_search: Whether to use vector search (if available)
            
        Returns:
            List of recommended tools with relevance scores
        """
        query_lower = query.lower()
        
        # Score tools based on keyword matching
        scored_tools = []
        
        for entry in self.tool_index:
            score = 0.0
            tool_name = entry["name"]
            description = entry["description"].lower()
            use_cases = [uc.lower() for uc in entry["use_cases"]]
            search_text = entry["search_text"].lower()
            
            # Exact tool name match (highest priority)
            if tool_name.lower() in query_lower:
                score += 100.0
            
            # Description keywords
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 3:  # Ignore short words
                    if word in description:
                        score += 5.0
                    if word in search_text:
                        score += 2.0
            
            # Use case matching
            for use_case in use_cases:
                if use_case in query_lower:
                    score += 10.0
                # Partial match
                for word in query_lower.split():
                    if word in use_case and len(word) > 3:
                        score += 3.0
            
            # Category matching
            if any(keyword in query_lower for keyword in ["file", "read", "write", "edit"]):
                if "file" in tool_name:
                    score += 5.0
            
            if any(keyword in query_lower for keyword in ["git", "commit", "push", "branch"]):
                if "git" in tool_name:
                    score += 10.0
            
            if any(keyword in query_lower for keyword in ["http", "api", "request", "url"]):
                if "http" in tool_name:
                    score += 10.0
            
            if any(keyword in query_lower for keyword in ["process", "kill", "port"]):
                if any(kw in tool_name for kw in ["process", "port"]):
                    score += 8.0
            
            if score > 0:
                scored_tools.append({
                    "tool": entry["tool"],
                    "name": tool_name,
                    "description": entry["description"],
                    "score": score,
                    "relevance": "high" if score > 20 else "medium" if score > 10 else "low"
                })
        
        # Sort by score (descending)
        scored_tools.sort(key=lambda x: x["score"], reverse=True)
        
        # Use vector search if available and enabled
        if use_vector_search and self.vector_store and self.vector_store.is_enabled():
            try:
                # Search for tool usage examples in memory
                vector_results = self.vector_store.search(
                    query=query,
                    limit=limit * 2  # Get more results for re-ranking
                )
                
                # Boost tools that appear in vector search results
                tool_names_in_memory = set()
                for result in vector_results:
                    # Extract tool names from memory content
                    content = result.get("content", "").lower()
                    for entry in self.tool_index:
                        if entry["name"] in content:
                            tool_names_in_memory.add(entry["name"])
                
                # Boost scores for tools found in memory
                for tool_entry in scored_tools:
                    if tool_entry["name"] in tool_names_in_memory:
                        tool_entry["score"] += 15.0
                        tool_entry["relevance"] = "high"
                
                # Re-sort after boosting
                scored_tools.sort(key=lambda x: x["score"], reverse=True)
            except Exception as e:
                logger.warning(f"Vector search failed, using keyword search only: {e}")
        
        return scored_tools[:limit]
    
    def get_tool_descriptions_for_prompt(
        self,
        recommended_tools: Optional[List[Dict[str, Any]]] = None,
        include_all: bool = False
    ) -> str:
        """
        Generate tool descriptions section for system prompt.
        
        Args:
            recommended_tools: List of recommended tools (if None, includes all)
            include_all: If True, include all tools regardless of recommendations
            
        Returns:
            Formatted string with tool descriptions
        """
        if include_all:
            tools_to_include = self.tools
        elif recommended_tools:
            tools_to_include = [entry["tool"] for entry in recommended_tools]
        else:
            tools_to_include = self.tools
        
        # Group tools by category
        categories = {
            "File Operations": ["read_file", "write_file", "edit_file", "delete_file", "copy_file", "move_file"],
            "Directory Operations": ["list_directory", "create_directory", "delete_directory", "read_directory_tree", "find_files"],
            "File System Queries": ["file_exists", "get_file_info", "calculate_file_hash"],
            "Configuration Files": ["read_json_file", "write_json_file", "read_yaml_file", "write_yaml_file", "read_env_file", "write_env_file"],
            "Code Search & Analysis": ["codebase_search", "grep", "check_syntax", "lint_file", "search_replace_in_multiple_files"],
            "Package Management": ["read_package_json", "read_requirements_txt", "get_installed_packages"],
            "System Operations": ["execute_command", "list_processes", "kill_process", "check_port", "get_environment_variable"],
            "HTTP/API": ["http_request"],
            "Git Operations": ["git_status", "git_add", "git_commit", "git_push", "git_pull", "git_branch", "git_log", "git_diff"]
        }
        
        sections = []
        sections.append("## AVAILABLE TOOLS\n")
        sections.append("You have access to the following tools. Use them proactively to accomplish tasks.\n")
        
        for category, tool_names in categories.items():
            category_tools = [t for t in tools_to_include if t["name"] in tool_names]
            if category_tools:
                sections.append(f"### {category}\n")
                for tool in category_tools:
                    name = tool["name"]
                    desc = tool.get("description", "")
                    sections.append(f"- **{name}**: {desc}\n")
                sections.append("")
        
        # Add usage guidelines
        sections.append("### Tool Usage Guidelines\n")
        sections.append("1. **Read before writing**: Use `read_file` to understand existing code before modifying it\n")
        sections.append("2. **Explore the codebase**: Use `list_directory` and `codebase_search` to understand project structure\n")
        sections.append("3. **Check syntax**: Use `check_syntax` and `lint_file` before committing changes\n")
        sections.append("4. **Use Git**: Use git tools to commit and push your changes\n")
        sections.append("5. **Test APIs**: Use `http_request` to test endpoints and verify functionality\n")
        sections.append("6. **Batch operations**: Use `search_replace_in_multiple_files` for making the same change across files\n")
        sections.append("7. **Package management**: Check `read_package_json` or `read_requirements_txt` to understand dependencies\n")
        
        return "\n".join(sections)
    
    def get_recommended_tools_context(
        self,
        query: str,
        limit: int = 3
    ) -> str:
        """
        Get context string about recommended tools for a query.
        
        Args:
            query: User's query
            limit: Number of tools to recommend
            
        Returns:
            Formatted context string
        """
        recommended = self.recommend_tools(query, limit=limit)
        
        if not recommended:
            return ""
        
        context_parts = ["## RECOMMENDED TOOLS FOR THIS TASK\n"]
        context_parts.append("Based on your request, these tools are most relevant:\n")
        
        for i, entry in enumerate(recommended, 1):
            name = entry["name"]
            desc = entry["description"]
            relevance = entry["relevance"]
            context_parts.append(f"{i}. **{name}** ({relevance} relevance): {desc}\n")
        
        return "\n".join(context_parts)


