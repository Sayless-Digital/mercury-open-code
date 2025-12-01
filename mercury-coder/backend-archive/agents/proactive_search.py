"""
Proactive Search Manager - Automatically searches codebase before tasks.
Implements "I've seen this before" functionality for top-tier AI agents.
"""

import logging
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .utils import extract_file_references
from .utils.cache import LRUCacheWithTTL

logger = logging.getLogger("mercury.agents.proactive_search")


class ProactiveSearchManager:
    """
    Automatically searches codebase before tasks to find:
    - Similar functions/patterns
    - Related implementations
    - API usage examples
    - Caches results for performance
    """
    
    def __init__(
        self,
        tool_executor=None,
        memory_manager=None,
        file_graph=None,
        cache_ttl_seconds: int = 3600  # 1 hour cache
    ):
        """
        Initialize proactive search manager.
        
        Args:
            tool_executor: Tool executor for running searches
            memory_manager: Memory manager for semantic search
            file_graph: File graph for dependency-based search
            cache_ttl_seconds: Cache TTL in seconds
        """
        self.tool_executor = tool_executor
        self.memory_manager = memory_manager
        self.file_graph = file_graph
        self.cache_ttl = cache_ttl_seconds
        # Use LRU cache with size limit (max 200 entries) and TTL
        self.search_cache = LRUCacheWithTTL(max_size=200, ttl_seconds=cache_ttl_seconds)
    
    def _get_cache_key(self, query: str, search_type: str) -> str:
        """Generate cache key for query."""
        return f"{search_type}:{query.lower().strip()}"
    
    # _is_cache_valid method removed - LRU cache handles TTL automatically
    
    async def search_before_task(
        self,
        task_description: str,
        task_type: str = "code",  # "code", "research", "plan"
        project_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Automatically search codebase before a task.
        
        Args:
            task_description: Description of the task
            task_type: Type of task (code, research, plan)
            project_path: Project path for filtering
            
        Returns:
            Dict with search results and context
        """
        search_results = {
            "similar_functions": [],
            "related_implementations": [],
            "api_examples": [],
            "patterns": []
        }
        
        # 1. Search for similar functions/patterns
        similar = await self._search_similar_functions(task_description, project_path)
        search_results["similar_functions"] = similar
        
        # 2. Search for related implementations
        related = await self._search_related_implementations(task_description, project_path)
        search_results["related_implementations"] = related
        
        # 3. Search for API usage examples
        api_examples = await self._search_api_examples(task_description, project_path)
        search_results["api_examples"] = api_examples
        
        # 4. Search for code patterns
        patterns = await self._search_patterns(task_description, project_path)
        search_results["patterns"] = patterns
        
        return search_results
    
    async def _search_similar_functions(
        self,
        query: str,
        project_path: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Search for similar functions."""
        cache_key = self._get_cache_key(query, "similar_functions")
        
        # Check cache (LRU cache handles TTL automatically)
        cached = self.search_cache.get(cache_key)
        if cached is not None:
            # cached is a dict with "results" and "timestamp"
            if isinstance(cached, dict):
                return cached.get("results", [])
            return cached if isinstance(cached, list) else []
        
        results = []
        
        if self.tool_executor:
            try:
                # Use codebase_search to find similar functions
                search_result = self.tool_executor.execute("codebase_search", {
                    "query": query,
                    "max_results": 5
                })
                
                if search_result.get("success"):
                    search_data = search_result.get("result", {})
                    matches = search_data.get("results", [])
                    
                    for match in matches:
                        results.append({
                            "file_path": match.get("file_path"),
                            "matches": match.get("matches", []),
                            "relevance": "high"  # Simplified
                        })
            except Exception as e:
                logger.debug(f"Similar functions search failed: {e}")
        
        # Thread-safe cache write
        with self._cache_lock:
            self.search_cache[cache_key] = {
                "results": results,
                "timestamp": datetime.now()
            }
        
        return results
    
    async def _search_related_implementations(
        self,
        query: str,
        project_path: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Search for related implementations."""
        cache_key = self._get_cache_key(query, "related_implementations")
        
        # Check cache (LRU cache handles TTL automatically)
        cached = self.search_cache.get(cache_key)
        if cached is not None:
            # cached is a dict with "results" and "timestamp"
            if isinstance(cached, dict):
                return cached.get("results", [])
            return cached if isinstance(cached, list) else []
        
        results = []
        
        # Use memory manager for semantic search
        if self.memory_manager:
            try:
                memory_context = self.memory_manager.get_context_for_query(query, project_path, limit=3)
                if memory_context:
                    # Extract task summaries
                    if "Similar Past Tasks:" in memory_context:
                        results.append({
                            "type": "memory",
                            "content": memory_context,
                            "relevance": "high"
                        })
            except Exception as e:
                logger.debug(f"Memory search failed: {e}")
        
        # Use file graph to find related files
        if self.file_graph:
            try:
                # Try to extract file references from query
                file_refs = self._extract_file_references(query)
                if file_refs:
                    for file_ref in file_refs[:2]:
                        related = self.file_graph.find_related_files(file_ref, max_depth=2)
                        if related:
                            results.append({
                                "type": "file_graph",
                                "file_path": file_ref,
                                "related_files": related[:5],
                                "relevance": "medium"
                            })
            except Exception as e:
                logger.debug(f"File graph search failed: {e}")
        
        # Cache results (LRU cache is thread-safe)
        self.search_cache.set(cache_key, {
            "results": results,
            "timestamp": datetime.now()
        })
        
        return results
    
    async def _search_api_examples(
        self,
        query: str,
        project_path: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Search for API usage examples."""
        cache_key = self._get_cache_key(query, "api_examples")
        
        # Check cache (LRU cache handles TTL automatically)
        cached = self.search_cache.get(cache_key)
        if cached is not None:
            # cached is a dict with "results" and "timestamp"
            if isinstance(cached, dict):
                return cached.get("results", [])
            return cached if isinstance(cached, list) else []
        
        results = []
        
        # Search for API-related keywords
        api_keywords = ["api", "endpoint", "http", "fetch", "axios", "request", "url"]
        has_api_keywords = any(keyword in query.lower() for keyword in api_keywords)
        
        if has_api_keywords and self.tool_executor:
            try:
                # Search for API usage patterns
                search_result = self.tool_executor.execute("grep", {
                    "pattern": r"(fetch|axios|http|request)\(|@app\.(get|post|put|delete)",
                    "file_path": project_path
                })
                
                if search_result.get("success"):
                    search_data = search_result.get("result", {})
                    matches = search_data.get("results", [])
                    
                    for match in matches[:5]:
                        results.append({
                            "file_path": match.get("file_path"),
                            "matches": match.get("matches", []),
                            "type": "api_usage"
                        })
            except Exception as e:
                logger.debug(f"API examples search failed: {e}")
        
        # Cache results (LRU cache is thread-safe)
        self.search_cache.set(cache_key, {
            "results": results,
            "timestamp": datetime.now()
        })
        
        return results
    
    async def _search_patterns(
        self,
        query: str,
        project_path: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Search for code patterns."""
        cache_key = self._get_cache_key(query, "patterns")
        
        # Check cache (LRU cache handles TTL automatically)
        cached = self.search_cache.get(cache_key)
        if cached is not None:
            # cached is a dict with "results" and "timestamp"
            if isinstance(cached, dict):
                return cached.get("results", [])
            return cached if isinstance(cached, list) else []
        
        results = []
        
        # Use memory manager to find similar patterns
        if self.memory_manager:
            try:
                # Search for code patterns in memory
                memory_context = self.memory_manager.get_context_for_query(query, project_path, limit=2)
                if memory_context and "Relevant Memories:" in memory_context:
                    # Extract pattern information
                    results.append({
                        "type": "memory_pattern",
                        "content": memory_context,
                        "relevance": "medium"
                    })
            except Exception as e:
                logger.debug(f"Pattern search failed: {e}")
        
        # Cache results (LRU cache is thread-safe)
        self.search_cache.set(cache_key, {
            "results": results,
            "timestamp": datetime.now()
        })
        
        return results
    
    def _extract_file_references(self, text: str) -> List[str]:
        """Extract file references from text using shared utility."""
        return extract_file_references(text)
    
    async def get_context_for_task(
        self,
        task_description: str,
        project_path: Optional[str] = None
    ) -> str:
        """
        Get proactive search context for a task.
        
        Fully async method that waits for search to complete before returning context.
        
        Args:
            task_description: Task description
            project_path: Project path
            
        Returns:
            Formatted context string
        """
        try:
            # Run proactive search and wait for results
            results = await self.search_before_task(task_description, "code", project_path)
        except Exception as e:
            logger.debug(f"Proactive search failed: {e}")
            results = {
                "similar_functions": [],
                "related_implementations": [],
                "api_examples": [],
                "patterns": []
            }
        
        # Format results
        context_parts = []
        
        if results.get("similar_functions"):
            context_parts.append("## Similar Functions Found:")
            for func in results["similar_functions"][:3]:
                file_path = func.get("file_path", "unknown")
                context_parts.append(f"- {file_path}")
        
        if results.get("related_implementations"):
            context_parts.append("\n## Related Implementations:")
            for impl in results["related_implementations"][:2]:
                if impl.get("type") == "file_graph":
                    context_parts.append(f"- Related files: {', '.join(impl.get('related_files', [])[:3])}")
        
        if results.get("api_examples"):
            context_parts.append("\n## API Usage Examples:")
            for example in results["api_examples"][:2]:
                context_parts.append(f"- {example.get('file_path', 'unknown')}")
        
        return "\n".join(context_parts) if context_parts else ""


