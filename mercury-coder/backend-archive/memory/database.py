"""
Memory database for storing and retrieving agent memories.
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("mercury.memory")


class MemoryDatabase:
    """SQLite database for agent memory."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to backend directory
            backend_dir = Path(__file__).parent.parent
            db_path = str(backend_dir / "memory.db")
        
        self.db_path = db_path
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Conversations table - stores chat messages
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_path TEXT,
                session_id TEXT,
                message_index INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Memories table - stores important information to remember
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_path TEXT,
                memory_type TEXT NOT NULL,  -- 'user_preference', 'code_pattern', 'solution', 'context'
                title TEXT,
                content TEXT NOT NULL,
                keywords TEXT,  -- JSON array for search
                importance REAL DEFAULT 1.0,  -- 0.0 to 1.0
                usage_count INTEGER DEFAULT 0,
                last_used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Task summaries - stores summaries of completed tasks
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_path TEXT,
                task_goal TEXT NOT NULL,
                summary TEXT NOT NULL,
                key_points TEXT,  -- JSON array
                files_modified TEXT,  -- JSON array
                success BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_project ON conversations(project_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_project ON memories(project_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_type ON memories(memory_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_importance ON memories(importance DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_task_project ON task_summaries(project_path)")
        
        conn.commit()
        conn.close()
    
    def save_message(
        self,
        project_path: Optional[str],
        session_id: str,
        message_index: int,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """Save a chat message to database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO conversations (project_path, session_id, message_index, role, content, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            project_path,
            session_id,
            message_index,
            role,
            content,
            json.dumps(metadata) if metadata else None
        ))
        conn.commit()
        conn.close()
    
    def get_recent_conversation(
        self,
        project_path: Optional[str],
        session_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get recent conversation messages."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        if session_id:
            rows = conn.execute("""
                SELECT * FROM conversations
                WHERE project_path = ? AND session_id = ?
                ORDER BY message_index ASC
                LIMIT ?
            """, (project_path, session_id, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM conversations
                WHERE project_path = ?
                ORDER BY created_at DESC, message_index DESC
                LIMIT ?
            """, (project_path, limit)).fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
    
    def save_memory(
        self,
        project_path: Optional[str],
        memory_type: str,
        content: str,
        title: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        importance: float = 1.0
    ) -> int:
        """Save a memory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            INSERT INTO memories (project_path, memory_type, title, content, keywords, importance)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            project_path,
            memory_type,
            title,
            content,
            json.dumps(keywords) if keywords else None,
            importance
        ))
        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return memory_id
    
    def search_memories(
        self,
        project_path: Optional[str],
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Search memories by keywords and content."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Simple keyword matching (can be upgraded to vector search later)
        query_lower = query.lower()
        conditions = ["(content LIKE ? OR title LIKE ?)"]
        params = [f"%{query_lower}%", f"%{query_lower}%"]
        
        if project_path:
            conditions.append("(project_path = ? OR project_path IS NULL)")
            params.append(project_path)
        
        if memory_types:
            placeholders = ",".join(["?"] * len(memory_types))
            conditions.append(f"memory_type IN ({placeholders})")
            params.extend(memory_types)
        
        params.append(limit)
        
        rows = conn.execute(f"""
            SELECT * FROM memories
            WHERE {' AND '.join(conditions)}
            ORDER BY importance DESC, usage_count DESC, last_used_at DESC
            LIMIT ?
        """, params).fetchall()
        
        # Update usage count
        for row in rows:
            conn.execute("""
                UPDATE memories
                SET usage_count = usage_count + 1,
                    last_used_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (row["id"],))
        
        conn.commit()
        conn.close()
        
        return [dict(row) for row in rows]
    
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
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO task_summaries (project_path, task_goal, summary, key_points, files_modified, success)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            project_path,
            task_goal,
            summary,
            json.dumps(key_points) if key_points else None,
            json.dumps(files_modified) if files_modified else None,
            1 if success else 0
        ))
        conn.commit()
        conn.close()
    
    def get_relevant_task_summaries(
        self,
        project_path: Optional[str],
        query: str,
        limit: int = 3
    ) -> List[Dict]:
        """Get relevant task summaries for a query."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        query_lower = query.lower()
        conditions = ["(task_goal LIKE ? OR summary LIKE ?)"]
        params = [f"%{query_lower}%", f"%{query_lower}%"]
        
        if project_path:
            conditions.append("(project_path = ? OR project_path IS NULL)")
            params.append(project_path)
        
        params.append(limit)
        
        rows = conn.execute(f"""
            SELECT * FROM task_summaries
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at DESC
            LIMIT ?
        """, params).fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]







