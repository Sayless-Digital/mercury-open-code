"""
Follow-Up Detector - detects follow-up requests using semantic similarity.
"""

import logging
from typing import Dict, Optional, Any

logger = logging.getLogger("mercury.agents.orchestration.follow_up_detector")


class FollowUpDetector:
    """
    Detects follow-up requests using semantic similarity and keyword matching.
    
    Uses vector embeddings to detect semantic follow-up instead of fragile
    keyword matching alone.
    """
    
    def __init__(self, memory_manager: Optional[Any] = None):
        """
        Initialize follow-up detector.
        
        Args:
            memory_manager: Optional memory manager with vector store
        """
        self.memory_manager = memory_manager
    
    def detect_follow_up_request(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if this is a follow-up request using semantic similarity.
        
        Uses vector embeddings to detect semantic follow-up instead of fragile keyword matching.
        
        Examples:
        - "write the changes" after research that recommended improvements
        - "implement it" after planning
        - "do it" after recommendations
        
        Args:
            user_request: User's request text
            context: Optional context dict with conversation_history, recent_messages
            
        Returns:
            Dict with follow-up info if detected, None otherwise
        """
        if not context:
            return None
        
        request_lower = user_request.lower().strip()
        
        # Quick check for implementation keywords (still useful for fast path)
        implementation_keywords = ["write", "implement", "create", "build", "apply", "make", "do it"]
        has_implementation_keyword = any(keyword in request_lower for keyword in implementation_keywords)
        
        if not has_implementation_keyword:
            return None
        
        # Use semantic similarity if memory manager and vector store available
        conversation_history = context.get("conversation_history", [])
        recent_messages = context.get("recent_messages", [])
        
        if self.memory_manager and self.memory_manager.vector_store and conversation_history:
            try:
                # Get recent conversation messages (last 3)
                recent_contexts = []
                for msg in reversed((recent_messages or []) + conversation_history[-3:]):
                    content = ""
                    if isinstance(msg, dict):
                        content = msg.get("content", "")
                        if isinstance(content, list):
                            content = " ".join([str(c) for c in content if isinstance(c, str)])
                    else:
                        content = str(msg)
                    if content:
                        recent_contexts.append(content[:500])  # Limit length
                
                if recent_contexts:
                    # Use vector store to find similar messages
                    # Check if recent messages are semantically similar to implementation requests
                    similar = self.memory_manager.vector_store.search_similar(
                        query=user_request,
                        limit=3
                    )
                    
                    # Also check if recent messages contain recommendations/research findings
                    recent_text = " ".join(recent_contexts).lower()
                    has_recommendations = any(term in recent_text for term in [
                        "recommendation", "improvement", "enhancement", "finding",
                        "should", "consider", "add", "implement", "suggest"
                    ])
                    
                    # If we found similar context or recommendations, it's likely a follow-up
                    if similar or has_recommendations:
                        return {
                            "needs_implementation": True,
                            "reason": "Follow-up request detected via semantic similarity",
                            "previous_findings": recent_contexts[:2]
                        }
            except Exception as e:
                logger.debug(f"Semantic follow-up detection failed: {e}, falling back to keyword detection")
        
        # Fallback to keyword-based detection if semantic similarity unavailable
        follow_up_keywords = [
            "write", "implement", "do it", "make the changes", "apply", 
            "go ahead", "proceed", "execute", "create", "build", "finish"
        ]
        
        is_follow_up = any(keyword in request_lower for keyword in follow_up_keywords)
        
        if is_follow_up and conversation_history:
            # Check for previous research/recommendations in conversation
            recent_text = " ".join([
                str(msg.get("content", "") if isinstance(msg, dict) else msg)
                for msg in conversation_history[-3:]
            ]).lower()
            
            has_previous_research = any(term in recent_text for term in [
                "recommendation", "improvement", "enhancement", "finding",
                "should", "consider", "add", "implement", "suggest"
            ])
            
            if has_previous_research:
                return {
                    "needs_implementation": True,
                    "reason": "Follow-up request after research with recommendations",
                    "previous_findings": []
                }
        
        return None

