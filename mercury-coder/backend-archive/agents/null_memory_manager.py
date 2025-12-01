"""
Null Memory Manager - Null Object Pattern for graceful degradation.
"""

from typing import Dict, List, Any, Optional


class NullMemoryManager:
    """
    Null Object implementation of MemoryManager.
    
    Returns empty/default values for all methods to allow graceful degradation
    when memory manager is not available.
    """
    
    def get_context_for_query(
        self,
        query: str,
        project_path: Optional[str] = None,
        limit: int = 5
    ) -> str:
        """Return empty context."""
        return ""
    
    def get_optimized_conversation_history(
        self,
        project_path: Optional[str] = None,
        session_id: Optional[str] = None,
        max_tokens: int = 2000,
        keep_recent: int = 5
    ) -> List[Dict[str, Any]]:
        """Return empty conversation history."""
        return []
    
    def add_message(
        self,
        role: str,
        content: str,
        project_path: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """No-op - do nothing."""
        pass
    
    def search_similar(
        self,
        query: str,
        project_path: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Return empty results."""
        return []
    
    @property
    def vector_store(self):
        """Return None for vector store."""
        return None












