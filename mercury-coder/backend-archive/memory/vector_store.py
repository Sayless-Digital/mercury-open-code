"""
Vector store for semantic search using Chroma and sentence-transformers.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger("mercury.memory.vector")

try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    VECTOR_AVAILABLE = True
except (ImportError, Exception) as e:
    VECTOR_AVAILABLE = False
    logger.warning(f"Chroma or sentence-transformers not available: {e}. Vector search disabled.")


class VectorStore:
    """Vector database for semantic search."""
    
    def __init__(self, db_path: Optional[str] = None):
        if not VECTOR_AVAILABLE:
            self.enabled = False
            logger.warning("Vector store disabled - dependencies not installed")
            return
        
        self.enabled = True
        
        if db_path is None:
            # Default to backend directory
            backend_dir = Path(__file__).parent.parent
            vector_dir = backend_dir / "vector_db"
            vector_dir.mkdir(exist_ok=True)
            db_path = str(vector_dir)
        
        try:
            # Initialize Chroma client
            self.client = chromadb.PersistentClient(
                path=db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Initialize embedding model
            # Using a lightweight, general-purpose model
            # Can be upgraded to code-specific models later
            model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
            logger.info(f"Loading embedding model: {model_name}")
            self.encoder = SentenceTransformer(model_name)
            logger.info("Embedding model loaded successfully")
            
            # Get or create collection for memories
            self.memory_collection = self.client.get_or_create_collection(
                name="agent_memories",
                metadata={"hnsw:space": "cosine"}
            )
            
            # Get or create collection for task summaries
            self.task_collection = self.client.get_or_create_collection(
                name="task_summaries",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("Vector store initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """Check if vector store is enabled."""
        return self.enabled and VECTOR_AVAILABLE
    
    def add_memory(
        self,
        memory_id: str,
        text: str,
        metadata: Dict[str, Any]
    ):
        """Add a memory to the vector store."""
        if not self.is_enabled():
            return
        
        try:
            # Generate embedding
            embedding = self.encoder.encode(text).tolist()
            
            # Add to collection
            self.memory_collection.add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata],
                ids=[memory_id]
            )
        except Exception as e:
            logger.error(f"Failed to add memory to vector store: {e}")
    
    def add_task_summary(
        self,
        task_id: str,
        text: str,
        metadata: Dict[str, Any]
    ):
        """Add a task summary to the vector store."""
        if not self.is_enabled():
            return
        
        try:
            # Generate embedding
            embedding = self.encoder.encode(text).tolist()
            
            # Add to collection
            self.task_collection.add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata],
                ids=[task_id]
            )
        except Exception as e:
            logger.error(f"Failed to add task summary to vector store: {e}")
    
    def search_memories(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> List[Dict]:
        """Search memories using semantic similarity."""
        if not self.is_enabled():
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.encoder.encode(query).tolist()
            
            # Search
            results = self.memory_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
            
            # Format results
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    def search_task_summaries(
        self,
        query: str,
        n_results: int = 3,
        where: Optional[Dict] = None
    ) -> List[Dict]:
        """Search task summaries using semantic similarity."""
        if not self.is_enabled():
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.encoder.encode(query).tolist()
            
            # Search
            results = self.task_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
            
            # Format results
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Failed to search task summaries: {e}")
            return []
    
    def delete_memory(self, memory_id: str):
        """Delete a memory from the vector store."""
        if not self.is_enabled():
            return
        
        try:
            self.memory_collection.delete(ids=[memory_id])
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
    
    def delete_task_summary(self, task_id: str):
        """Delete a task summary from the vector store."""
        if not self.is_enabled():
            return
        
        try:
            self.task_collection.delete(ids=[task_id])
        except Exception as e:
            logger.error(f"Failed to delete task summary: {e}")

