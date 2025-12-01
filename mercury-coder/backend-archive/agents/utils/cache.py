"""
LRU Cache with TTL implementation for agent caches.
"""

import threading
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict


class LRUCacheWithTTL:
    """
    Thread-safe LRU cache with TTL (Time To Live) support.
    
    Features:
    - Maximum size limit (LRU eviction)
    - TTL expiration
    - Thread-safe operations
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: Optional[int] = None):
        """
        Initialize LRU cache with TTL.
        
        Args:
            max_size: Maximum number of items in cache
            ttl_seconds: Time to live in seconds (None = no expiration)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Tuple[Any, datetime]] = OrderedDict()
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            value, timestamp = self._cache[key]
            
            # Check TTL
            if self.ttl_seconds is not None:
                age = (datetime.now() - timestamp).total_seconds()
                if age > self.ttl_seconds:
                    # Expired - remove it
                    del self._cache[key]
                    return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            # Remove if exists (will be re-added at end)
            if key in self._cache:
                del self._cache[key]
            
            # Add new entry
            self._cache[key] = (value, datetime.now())
            
            # Evict oldest if over limit
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)  # Remove oldest (first item)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in cache (and is not expired)."""
        return self.get(key) is not None
    
    def __getitem__(self, key: str) -> Any:
        """Dict-like access: cache[key]."""
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Dict-like assignment: cache[key] = value."""
        self.set(key, value)
    
    def __delitem__(self, key: str) -> None:
        """Dict-like deletion: del cache[key]."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            else:
                raise KeyError(key)
    
    def __len__(self) -> int:
        """Get number of items in cache."""
        with self._lock:
            # Clean expired entries first
            if self.ttl_seconds is not None:
                now = datetime.now()
                expired_keys = [
                    key for key, (_, timestamp) in self._cache.items()
                    if (now - timestamp).total_seconds() > self.ttl_seconds
                ]
                for key in expired_keys:
                    del self._cache[key]
            return len(self._cache)
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        if self.ttl_seconds is None:
            return 0
        
        with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, (_, timestamp) in self._cache.items()
                if (now - timestamp).total_seconds() > self.ttl_seconds
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

