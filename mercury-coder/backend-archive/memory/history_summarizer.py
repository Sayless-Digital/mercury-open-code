"""
Conversation history summarization to save tokens while preserving context.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger("mercury.memory.history")


class HistorySummarizer:
    """Summarize conversation history to save tokens."""
    
    def __init__(self, max_messages: int = 20, summary_threshold: int = 30):
        """
        Initialize history summarizer.
        
        Args:
            max_messages: Maximum messages to keep in full detail
            summary_threshold: Number of messages before summarizing old ones
        """
        self.max_messages = max_messages
        self.summary_threshold = summary_threshold
    
    def should_summarize(self, message_count: int) -> bool:
        """Check if history should be summarized."""
        return message_count > self.summary_threshold
    
    def summarize_conversation(
        self,
        messages: List[Dict],
        keep_recent: int = 10
    ) -> List[Dict]:
        """
        Summarize old messages, keep recent ones intact.
        
        Args:
            messages: Full message history
            keep_recent: Number of recent messages to keep as-is
        
        Returns:
            Summarized messages with recent messages intact
        """
        if len(messages) <= self.max_messages:
            return messages
        
        # Keep recent messages
        recent = messages[-keep_recent:]
        old = messages[:-keep_recent]
        
        # Summarize old messages
        summary = self._create_summary(old)
        
        # Combine: summary + recent
        return [summary] + recent
    
    def _create_summary(self, messages: List[Dict]) -> Dict:
        """Create summary of old messages."""
        # Extract key information
        user_goals = []
        assistant_responses = []
        key_decisions = []
        topics_discussed = []
        
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            
            if role == "user":
                # Extract user goals and questions
                if isinstance(content, str) and len(content) > 20:
                    # Clean up content
                    clean_content = content.strip()
                    if clean_content:
                        user_goals.append(clean_content[:150])  # Truncate long messages
            
            elif role == "assistant":
                # Extract key responses
                if isinstance(content, str) and len(content) > 50:
                    # Look for code blocks, solutions, decisions
                    if "```" in content or "solution" in content.lower() or "here's" in content.lower():
                        assistant_responses.append(content[:200])
        
        # Extract topics from messages
        all_text = " ".join([
            msg.get("content", "") if isinstance(msg.get("content"), str) else ""
            for msg in messages
        ])
        
        # Simple topic extraction (can be enhanced)
        topics = self._extract_topics(all_text)
        
        # Create summary message
        summary_parts = ["## Summary of Previous Conversation\n"]
        
        if user_goals:
            summary_parts.append(f"**User Goals/Questions ({len(user_goals)}):**")
            for i, goal in enumerate(user_goals[:5], 1):  # Top 5 goals
                summary_parts.append(f"{i}. {goal}...")
            summary_parts.append("")
        
        if topics:
            summary_parts.append(f"**Topics Discussed:** {', '.join(topics[:5])}")
            summary_parts.append("")
        
        if assistant_responses:
            summary_parts.append(f"**Key Responses ({len(assistant_responses)}):**")
            summary_parts.append("Assistant provided solutions, code examples, and guidance.")
            summary_parts.append("")
        
        summary_parts.append(
            f"**Context:** This is a summary of {len(messages)} previous messages. "
            "Full details may be available in memory/RAG system if needed."
        )
        
        summary_text = "\n".join(summary_parts)
        
        return {
            "role": "system",
            "content": summary_text,
            "metadata": {
                "type": "summary",
                "original_message_count": len(messages),
                "summarized_at": datetime.now().isoformat()
            }
        }
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract main topics from conversation text."""
        # Simple keyword-based topic extraction
        # Can be enhanced with NLP later
        
        topics_keywords = {
            "typescript": ["typescript", "ts", "typed"],
            "javascript": ["javascript", "js", "node"],
            "react": ["react", "component", "jsx"],
            "css": ["css", "styling", "styles"],
            "api": ["api", "endpoint", "request"],
            "database": ["database", "db", "sql", "query"],
            "testing": ["test", "testing", "spec"],
            "deployment": ["deploy", "production", "server"],
            "bug": ["bug", "error", "fix", "issue"],
            "feature": ["feature", "add", "implement", "create"]
        }
        
        text_lower = text.lower()
        found_topics = []
        
        for topic, keywords in topics_keywords.items():
            if any(kw in text_lower for kw in keywords):
                found_topics.append(topic)
        
        return found_topics[:10]  # Return top 10 topics
    
    def estimate_tokens(self, messages: List[Dict]) -> int:
        """
        Rough token estimation (4 characters ≈ 1 token).
        More accurate methods can be added later.
        """
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                # Handle message format with blocks
                for block in content:
                    if isinstance(block, dict):
                        text = block.get("text", "")
                        if isinstance(text, str):
                            total_chars += len(text)
        
        # Rough estimate: 4 chars per token
        return total_chars // 4
    
    def optimize_for_tokens(
        self,
        messages: List[Dict],
        max_tokens: int = 8000,
        keep_recent: int = 10
    ) -> List[Dict]:
        """
        Optimize message history to fit within token budget.
        
        Args:
            messages: Full message history
            max_tokens: Maximum tokens allowed
            keep_recent: Number of recent messages to always keep
        
        Returns:
            Optimized message list
        """
        # Always keep recent messages
        recent = messages[-keep_recent:] if len(messages) > keep_recent else messages
        old = messages[:-keep_recent] if len(messages) > keep_recent else []
        
        # Estimate tokens for recent messages
        recent_tokens = self.estimate_tokens(recent)
        
        if recent_tokens >= max_tokens:
            # Even recent messages are too long, truncate them
            logger.warning(f"Recent messages exceed token limit ({recent_tokens} > {max_tokens})")
            return self._truncate_messages(recent, max_tokens)
        
        # Calculate available tokens for old messages
        available_tokens = max_tokens - recent_tokens
        
        if not old:
            # No old messages, return as-is
            return recent
        
        # Estimate tokens for old messages
        old_tokens = self.estimate_tokens(old)
        
        if old_tokens <= available_tokens:
            # Old messages fit, return all
            return old + recent
        
        # Old messages don't fit, summarize them
        summary = self._create_summary(old)
        summary_tokens = self.estimate_tokens([summary])
        
        if summary_tokens <= available_tokens:
            # Summary fits, use it
            return [summary] + recent
        else:
            # Even summary is too long, truncate it
            logger.warning("Summary exceeds token limit, truncating")
            return [self._truncate_message(summary, available_tokens)] + recent
    
    def _truncate_messages(self, messages: List[Dict], max_tokens: int) -> List[Dict]:
        """Truncate messages to fit token budget."""
        truncated = []
        remaining_tokens = max_tokens
        
        # Process messages in reverse (keep most recent)
        for msg in reversed(messages):
            msg_tokens = self.estimate_tokens([msg])
            
            if msg_tokens <= remaining_tokens:
                truncated.insert(0, msg)
                remaining_tokens -= msg_tokens
            else:
                # Truncate this message
                truncated_msg = self._truncate_message(msg, remaining_tokens)
                truncated.insert(0, truncated_msg)
                break
        
        return truncated
    
    def _truncate_message(self, message: Dict, max_tokens: int) -> Dict:
        """Truncate a single message to fit token budget."""
        content = message.get("content", "")
        
        if isinstance(content, str):
            # Rough truncation: 4 chars per token
            max_chars = max_tokens * 4
            if len(content) > max_chars:
                truncated_content = content[:max_chars] + "\n\n[Message truncated due to token limit]"
                return {**message, "content": truncated_content}
        
        return message







