"""
Workflow Cache - thread-safe cache management for proactive search results.
"""

import logging
import threading
import hashlib
from typing import Dict, Optional, Any

from ..utils.cache import LRUCacheWithTTL

logger = logging.getLogger("mercury.agents.orchestration.workflow_cache")


class WorkflowCache:
    """
    Thread-safe cache for proactive search results with LRU and TTL.
    
    Manages cache operations for workflow execution, ensuring thread safety
    and preventing memory leaks through size limits and TTL.
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        """
        Initialize workflow cache.
        
        Args:
            max_size: Maximum number of cache entries (LRU eviction)
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self._cache = LRUCacheWithTTL(max_size=max_size, ttl_seconds=ttl_seconds)
        self._lock = threading.RLock()
    
    
    async def get_proactive_context_async(
        self,
        proactive_search_manager: Optional[Any],
        task_description: str,
        project_path: Optional[str]
    ) -> str:
        """
        Get proactive search context with caching (async version).
        
        Args:
            proactive_search_manager: ProactiveSearchManager instance
            task_description: Task description to search for
            project_path: Project path
            
        Returns:
            Proactive context string
        """
        if not proactive_search_manager:
            return ""
        
        # Create collision-resistant cache key using full SHA256 hash
        cache_input = f"{task_description}:{project_path or ''}:{id(task_description)}"
        cache_key = hashlib.sha256(cache_input.encode()).hexdigest()
        
        # Thread-safe cache access
        with self._lock:
            # Check cache first
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Get context and cache it (outside lock to avoid blocking during I/O)
        try:
            context = await proactive_search_manager.get_context_for_task(
                task_description,
                project_path
            )
            # Thread-safe cache write
            with self._lock:
                self._cache.set(cache_key, context)
            return context
        except Exception as e:
            logger.debug(f"Proactive search failed: {e}")
            # Thread-safe cache write for empty result
            with self._lock:
                self._cache.set(cache_key, "")
            return ""
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert cache to dictionary (for passing to agents).
        
        Returns:
            Dictionary representation of cache
        """
        with self._lock:
            return self._cache.to_dict()
    
    def __len__(self) -> int:
        """Get number of cache entries."""
        with self._lock:
            return len(self._cache)
    
    def _hash_key(self, key: str) -> str:
        """
        Hash a cache key for consistent storage.
        
        Args:
            key: Original cache key string
            
        Returns:
            Hashed cache key
        """
        return hashlib.sha256(key.encode()).hexdigest()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache by key (dictionary-like interface).
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        hashed_key = self._hash_key(key)
        with self._lock:
            value = self._cache.get(hashed_key)
            return value if value is not None else default
    
    def __setitem__(self, key: str, value: Any) -> None:
        """
        Set value in cache by key (dictionary-like interface).
        
        Args:
            key: Cache key
            value: Value to cache
        """
        hashed_key = self._hash_key(key)
        with self._lock:
            self._cache.set(hashed_key, value)
    
    def __getitem__(self, key: str) -> Any:
        """
        Get value from cache by key (dictionary-like interface).
        
        Args:
            key: Cache key
            
        Returns:
            Cached value
            
        Raises:
            KeyError: If key not found
        """
        hashed_key = self._hash_key(key)
        with self._lock:
            value = self._cache.get(hashed_key)
            if value is None:
                raise KeyError(key)
            return value

