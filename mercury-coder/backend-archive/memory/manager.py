"""
Memory manager for retrieving and storing agent memories.
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from .database import MemoryDatabase
from .vector_store import VectorStore
from .history_summarizer import HistorySummarizer

logger = logging.getLogger("mercury.memory")


class MemoryManager:
    """Manages agent memory retrieval and storage."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db = MemoryDatabase(db_path)
        self.vector_store = VectorStore()
        self.history_summarizer = HistorySummarizer(max_messages=20, summary_threshold=30)
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for search."""
        # Simple keyword extraction
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could',
            'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
        
        # Extract words
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter and get unique
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        
        # Return top keywords
        from collections import Counter
        return [word for word, count in Counter(keywords).most_common(10)]
    
    def get_context_for_query(
        self,
        query: str,
        project_path: Optional[str] = None,
        limit: int = 5
    ) -> str:
        """
        Get relevant context from memory for a query.
        Uses hybrid search: vector (semantic) + keyword search.
        Returns formatted context string to include in prompt.
        """
        context_parts = []
        
        # Hybrid search: combine vector and keyword results
        vector_memories = []
        keyword_memories = []
        
        # 1. Vector search (semantic) - if available
        if self.vector_store.is_enabled():
            where_clause = None
            if project_path:
                where_clause = {"project_path": project_path}
            
            vector_results = self.vector_store.search_memories(
                query=query,
                n_results=limit,
                where=where_clause
            )
            
            # Get full memory details from database using IDs
            for result in vector_results:
                memory_id = result.get('id')
                if memory_id:
                    # Try to get from database
                    # Note: We'll need to store memory_id in the database
                    vector_memories.append({
                        'id': memory_id,
                        'content': result.get('document', ''),
                        'metadata': result.get('metadata', {}),
                        'distance': result.get('distance', 1.0),
                        'source': 'vector'
                    })
        
        # 2. Keyword search (fallback or complement)
        keyword_memories = self.db.search_memories(
            project_path=project_path,
            query=query,
            limit=limit
        )
        
        # Merge and deduplicate results
        # Prioritize vector results (better semantic match)
        all_memories = []
        seen_ids = set()
        
        # Add vector results first (better quality)
        for mem in vector_memories:
            mem_id = mem.get('id', '')
            if mem_id and mem_id not in seen_ids:
                all_memories.append(mem)
                seen_ids.add(mem_id)
        
        # Add keyword results (fill gaps)
        for mem in keyword_memories:
            mem_id = str(mem.get('id', ''))
            if mem_id not in seen_ids:
                mem['source'] = 'keyword'
                all_memories.append(mem)
                seen_ids.add(mem_id)
        
        # Format memories for context
        if all_memories:
            context_parts.append("## Relevant Memories:")
            for mem in all_memories[:3]:  # Top 3 memories
                title = mem.get("title") or mem.get("metadata", {}).get("title", "Memory")
                content = mem.get("content", "")[:200]  # Truncate
                source = mem.get("source", "keyword")
                context_parts.append(f"- **{title}** ({source}): {content}...")
            context_parts.append("")
        
        # 3. Search task summaries (hybrid)
        vector_tasks = []
        keyword_tasks = []
        
        if self.vector_store.is_enabled():
            where_clause = None
            if project_path:
                where_clause = {"project_path": project_path}
            
            vector_task_results = self.vector_store.search_task_summaries(
                query=query,
                n_results=2,
                where=where_clause
            )
            
            for result in vector_task_results:
                vector_tasks.append({
                    'id': result.get('id'),
                    'document': result.get('document', ''),
                    'metadata': result.get('metadata', {}),
                    'source': 'vector'
                })
        
        keyword_tasks = self.db.get_relevant_task_summaries(
            project_path=project_path,
            query=query,
            limit=2
        )
        
        # Merge task summaries
        all_tasks = []
        seen_task_ids = set()
        
        for task in vector_tasks:
            task_id = task.get('id', '')
            if task_id and task_id not in seen_task_ids:
                all_tasks.append(task)
                seen_task_ids.add(task_id)
        
        for task in keyword_tasks:
            task_id = str(task.get('id', ''))
            if task_id not in seen_task_ids:
                task['source'] = 'keyword'
                all_tasks.append(task)
                seen_task_ids.add(task_id)
        
        if all_tasks:
            context_parts.append("## Similar Past Tasks:")
            for task in all_tasks[:2]:  # Top 2 tasks
                if 'task_goal' in task:
                    goal = task.get("task_goal", "")[:100]
                    summary_text = task.get("summary", "")[:150]
                    source = task.get("source", "keyword")
                    context_parts.append(f"- **{goal}** ({source}): {summary_text}...")
                elif 'metadata' in task:
                    goal = task.get("metadata", {}).get("task_goal", "")[:100]
                    summary_text = task.get("document", "")[:150]
                    source = task.get("source", "vector")
                    context_parts.append(f"- **{goal}** ({source}): {summary_text}...")
            context_parts.append("")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def get_recent_conversation(
        self,
        project_path: Optional[str],
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get recent conversation messages."""
        return self.db.get_recent_conversation(
            project_path=project_path,
            session_id=session_id,
            limit=limit
        )
    
    def get_optimized_conversation_history(
        self,
        project_path: Optional[str],
        session_id: Optional[str] = None,
        max_tokens: int = 8000,
        keep_recent: int = 10
    ) -> List[Dict]:
        """
        Get conversation history optimized for token budget.
        Summarizes old messages, keeps recent ones intact.
        
        Returns:
            List of messages in Claude API format (role + content)
        """
        # Get all recent messages
        all_messages = self.db.get_recent_conversation(
            project_path=project_path,
            session_id=session_id,
            limit=100  # Get more to summarize
        )
        
        if not all_messages:
            return []
        
        # Convert to Claude API format
        claude_messages = []
        for msg in all_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Convert to Claude format
            claude_messages.append({
                "role": role,
                "content": content
            })
        
        # Optimize for token budget
        optimized = self.history_summarizer.optimize_for_tokens(
            claude_messages,
            max_tokens=max_tokens,
            keep_recent=keep_recent
        )
        
        return optimized
    
    def save_message(
        self,
        project_path: Optional[str],
        session_id: str,
        message_index: int,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """Save a chat message."""
        self.db.save_message(
            project_path=project_path,
            session_id=session_id,
            message_index=message_index,
            role=role,
            content=content,
            metadata=metadata
        )
    
    def extract_memories(
        self,
        user_message: str,
        assistant_response: str,
        project_path: Optional[str] = None
    ) -> List[Dict]:
        """
        Extract important information to remember from conversation.
        Returns list of memories to save.
        """
        memories = []
        
        # Extract user preferences (simple heuristics)
        preference_keywords = ['prefer', 'like', 'always', 'never', 'usually', 'typically']
        if any(kw in user_message.lower() for kw in preference_keywords):
            memories.append({
                "type": "user_preference",
                "title": "User Preference",
                "content": f"User said: {user_message[:200]}",
                "importance": 0.7
            })
        
        # Extract code patterns (if response contains code)
        if "```" in assistant_response or "function" in assistant_response.lower():
            # Extract code blocks
            code_blocks = re.findall(r'```[\w]*\n(.*?)```', assistant_response, re.DOTALL)
            if code_blocks:
                memories.append({
                    "type": "code_pattern",
                    "title": "Code Pattern",
                    "content": f"Code pattern used: {code_blocks[0][:300]}",
                    "importance": 0.8
                })
        
        # Extract solutions (if response solves a problem)
        solution_keywords = ['solution', 'fix', 'resolved', 'working', 'correct']
        if any(kw in assistant_response.lower() for kw in solution_keywords):
            memories.append({
                "type": "solution",
                "title": "Solution",
                "content": f"Solution for: {user_message[:100]}\n{assistant_response[:200]}",
                "importance": 0.9
            })
        
        return memories
    
    def save_tool_usage(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_result: Dict[str, Any],
        user_query: str,
        project_path: Optional[str] = None,
        success: bool = True
    ):
        """
        Save tool usage pattern to memory for learning.
        
        Args:
            tool_name: Name of the tool used
            tool_input: Input parameters passed to the tool
            tool_result: Result returned by the tool
            user_query: Original user query that led to this tool usage
            project_path: Project path (optional)
            success: Whether the tool usage was successful
        """
        try:
            # Create a memory entry for tool usage
            if success and tool_result.get("success"):
                # Extract key information
                content_parts = [
                    f"Tool: {tool_name}",
                    f"User query: {user_query[:200]}",
                    f"Input: {json.dumps(tool_input)[:200]}",
                ]
                
                # Add result summary if available
                result_summary = tool_result.get("result", {})
                if isinstance(result_summary, dict):
                    # Extract key result info
                    if "file_path" in result_summary:
                        content_parts.append(f"File: {result_summary['file_path']}")
                    if "message" in result_summary:
                        content_parts.append(f"Result: {result_summary['message']}")
                
                content = " | ".join(content_parts)
                
                # Save as code_pattern memory type (tool usage patterns)
                memory = {
                    "type": "code_pattern",  # Reuse code_pattern for tool patterns
                    "title": f"Tool Usage: {tool_name}",
                    "content": content,
                    "keywords": json.dumps([tool_name, user_query[:50]]),
                    "importance": 0.6,
                    "project_path": project_path
                }
                
                # Save to database
                self.db.save_memory(**memory)
                
                # Also add to vector store for semantic search
                if self.vector_store and self.vector_store.is_enabled():
                    try:
                        self.vector_store.add_document(
                            text=f"{tool_name} {user_query} {content}",
                            metadata={
                                "type": "tool_usage",
                                "tool_name": tool_name,
                                "project_path": project_path or ""
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to add tool usage to vector store: {e}")
        except Exception as e:
            logger.warning(f"Failed to save tool usage: {e}")
    
    def save_conversation(
        self,
        project_path: Optional[str],
        session_id: str,
        user_message: str,
        assistant_response: str,
        metadata: Optional[Dict] = None
    ):
        """Save a conversation exchange."""
        # Get current message index
        recent = self.get_recent_conversation(project_path, session_id, limit=1)
        message_index = len(recent) if recent else 0
        
        # Save user message
        self.save_message(
            project_path=project_path,
            session_id=session_id,
            message_index=message_index,
            role="user",
            content=user_message,
            metadata=metadata
        )
        
        # Save assistant response
        self.save_message(
            project_path=project_path,
            session_id=session_id,
            message_index=message_index + 1,
            role="assistant",
            content=assistant_response,
            metadata=metadata
        )
        
        # Extract and save important memories
        memories = self.extract_memories(user_message, assistant_response, project_path)
        for mem in memories:
            keywords = self.extract_keywords(f"{user_message} {assistant_response}")
            memory_id = self.db.save_memory(
                project_path=project_path,
                memory_type=mem["type"],
                content=mem["content"],
                title=mem["title"],
                keywords=keywords,
                importance=mem["importance"]
            )
            
            # Also add to vector store
            if self.vector_store.is_enabled():
                # Create text for embedding (title + content)
                embedding_text = f"{mem.get('title', '')} {mem.get('content', '')}"
                self.vector_store.add_memory(
                    memory_id=str(memory_id),
                    text=embedding_text,
                    metadata={
                        "project_path": project_path or "",
                        "memory_type": mem["type"],
                        "title": mem.get("title", ""),
                        "importance": mem["importance"]
                    }
                )
    
    def save_task_summary(
        self,
        project_path: Optional[str],
        task_goal: str,
        summary: str,
        key_points: Optional[List[str]] = None,
        files_modified: Optional[List[str]] = None,
        success: bool = True
    ):
        """Save a task summary."""
        # Save to database
        self.db.save_task_summary(
            project_path=project_path,
            task_goal=task_goal,
            summary=summary,
            key_points=key_points,
            files_modified=files_modified,
            success=success
        )
        
        # Also add to vector store
        if self.vector_store.is_enabled():
            # Create text for embedding
            embedding_text = f"{task_goal} {summary}"
            if key_points:
                embedding_text += " " + " ".join(key_points)
            
            # Generate task ID
            import hashlib
            task_id = hashlib.sha256(embedding_text.encode()).hexdigest()[:16]
            
            self.vector_store.add_task_summary(
                task_id=task_id,
                text=embedding_text,
                metadata={
                    "project_path": project_path or "",
                    "task_goal": task_goal,
                    "success": success,
                    "files_modified": json.dumps(files_modified) if files_modified else ""
                }
            )

