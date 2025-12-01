"""
Pattern Matcher - Extracts and matches code patterns.
Implements "I've seen this before" functionality for top-tier AI agents.
"""

import logging
import re
import hashlib
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("mercury.context.pattern_matcher")


@dataclass
class CodePattern:
    """Represents a code pattern."""
    pattern_id: str
    description: str
    pattern_type: str  # 'function', 'class', 'api_usage', 'structure'
    file_path: str
    code_snippet: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    success_count: int = 0
    last_used: Optional[datetime] = None


class PatternMatcher:
    """
    Extracts and matches code patterns across the codebase.
    
    Features:
    - Extract patterns from files
    - Match similar patterns
    - Learn from successful patterns
    - Store patterns in vector store
    - Provide "I've seen this before" functionality
    """
    
    def __init__(self, memory_manager=None, vector_store=None):
        """
        Initialize pattern matcher.
        
        Args:
            memory_manager: Memory manager for semantic search
            vector_store: Vector store for pattern embeddings
        """
        self.memory_manager = memory_manager
        self.vector_store = vector_store
        self.patterns: Dict[str, CodePattern] = {}  # pattern_id -> CodePattern
        self.pattern_index: Dict[str, List[str]] = {}  # pattern_type -> [pattern_ids]
    
    def _generate_pattern_id(self, code_snippet: str, file_path: str) -> str:
        """Generate unique pattern ID."""
        content = f"{file_path}:{code_snippet[:200]}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def extract_pattern(
        self,
        file_path: str,
        code_snippet: str,
        pattern_type: str = "function",
        description: Optional[str] = None
    ) -> CodePattern:
        """
        Extract a pattern from code.
        
        Args:
            file_path: Path to file
            code_snippet: Code snippet containing the pattern
            pattern_type: Type of pattern (function, class, api_usage, structure)
            description: Optional description of the pattern
            
        Returns:
            CodePattern object
        """
        pattern_id = self._generate_pattern_id(code_snippet, file_path)
        
        if pattern_id in self.patterns:
            # Update existing pattern
            pattern = self.patterns[pattern_id]
            pattern.success_count += 1
            pattern.last_used = datetime.now()
            return pattern
        
        # Create new pattern
        pattern = CodePattern(
            pattern_id=pattern_id,
            description=description or f"{pattern_type} pattern from {file_path}",
            pattern_type=pattern_type,
            file_path=file_path,
            code_snippet=code_snippet,
            success_count=1,
            last_used=datetime.now()
        )
        
        self.patterns[pattern_id] = pattern
        
        # Index by type
        if pattern_type not in self.pattern_index:
            self.pattern_index[pattern_type] = []
        if pattern_id not in self.pattern_index[pattern_type]:
            self.pattern_index[pattern_type].append(pattern_id)
        
        # Store in vector store if available
        if self.vector_store:
            try:
                self.vector_store.add(
                    ids=[pattern_id],
                    documents=[code_snippet],
                    metadatas=[{
                        "pattern_type": pattern_type,
                        "file_path": file_path,
                        "description": pattern.description
                    }]
                )
            except Exception as e:
                logger.debug(f"Failed to store pattern in vector store: {e}")
        
        return pattern
    
    def find_similar_patterns(
        self,
        query: str,
        project_path: Optional[str] = None,
        pattern_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar patterns to a query.
        
        Args:
            query: Query string describing what to find
            project_path: Optional project path for filtering
            pattern_type: Optional pattern type filter
            limit: Maximum number of results
            
        Returns:
            List of similar patterns
        """
        results = []
        
        # 1. Search in vector store if available
        if self.vector_store:
            try:
                vector_results = self.vector_store.query(
                    query_texts=[query],
                    n_results=limit
                )
                
                if vector_results and "ids" in vector_results:
                    for i, pattern_id in enumerate(vector_results["ids"][0][:limit]):
                        if pattern_id in self.patterns:
                            pattern = self.patterns[pattern_id]
                            results.append({
                                "pattern_id": pattern.pattern_id,
                                "description": pattern.description,
                                "pattern_type": pattern.pattern_type,
                                "file_path": pattern.file_path,
                                "code_snippet": pattern.code_snippet[:200],
                                "similarity": "high",  # From vector search
                                "success_count": pattern.success_count
                            })
            except Exception as e:
                logger.debug(f"Vector store search failed: {e}")
        
        # 2. Search in memory if available
        if self.memory_manager and len(results) < limit:
            try:
                memory_context = self.memory_manager.get_context_for_query(query, project_path, limit=3)
                if memory_context and "Relevant Memories:" in memory_context:
                    # Extract pattern information from memory
                    results.append({
                        "pattern_id": "memory_pattern",
                        "description": "Pattern from memory",
                        "pattern_type": "memory",
                        "file_path": "memory",
                        "code_snippet": memory_context[:300],
                        "similarity": "medium",
                        "source": "memory"
                    })
            except Exception as e:
                logger.debug(f"Memory search failed: {e}")
        
        # 3. Simple keyword matching as fallback
        if len(results) < limit:
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            for pattern_id, pattern in self.patterns.items():
                if pattern_type and pattern.pattern_type != pattern_type:
                    continue
                
                # Simple keyword matching
                pattern_text = (pattern.description + " " + pattern.code_snippet).lower()
                pattern_words = set(pattern_text.split())
                
                # Calculate simple similarity (word overlap)
                overlap = len(query_words & pattern_words)
                if overlap > 0:
                    similarity_score = overlap / max(len(query_words), len(pattern_words))
                    
                    if similarity_score > 0.2:  # Threshold
                        results.append({
                            "pattern_id": pattern.pattern_id,
                            "description": pattern.description,
                            "pattern_type": pattern.pattern_type,
                            "file_path": pattern.file_path,
                            "code_snippet": pattern.code_snippet[:200],
                            "similarity": "medium",
                            "similarity_score": similarity_score,
                            "success_count": pattern.success_count
                        })
        
        # Sort by success count and similarity
        results.sort(key=lambda x: (x.get("success_count", 0), x.get("similarity_score", 0)), reverse=True)
        
        return results[:limit]
    
    def match_pattern(
        self,
        code_snippet: str,
        pattern_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Match code snippet against known patterns.
        
        Args:
            code_snippet: Code to match
            pattern_type: Optional pattern type filter
            
        Returns:
            List of matching patterns
        """
        matches = []
        
        # Extract features from code snippet
        snippet_lower = code_snippet.lower()
        snippet_words = set(snippet_lower.split())
        
        for pattern_id, pattern in self.patterns.items():
            if pattern_type and pattern.pattern_type != pattern_type:
                continue
            
            # Compare code snippets
            pattern_lower = pattern.code_snippet.lower()
            pattern_words = set(pattern_lower.split())
            
            # Calculate similarity
            overlap = len(snippet_words & pattern_words)
            total_words = len(snippet_words | pattern_words)
            
            if total_words > 0:
                similarity = overlap / total_words
                
                if similarity > 0.3:  # Threshold
                    matches.append({
                        "pattern_id": pattern.pattern_id,
                        "description": pattern.description,
                        "pattern_type": pattern.pattern_type,
                        "file_path": pattern.file_path,
                        "similarity": similarity,
                        "success_count": pattern.success_count
                    })
        
        # Sort by similarity
        matches.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        
        return matches
    
    def learn_from_success(
        self,
        pattern_id: str,
        success: bool = True
    ):
        """
        Learn from pattern usage success.
        
        Args:
            pattern_id: Pattern ID
            success: Whether the pattern usage was successful
        """
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            if success:
                pattern.success_count += 1
            pattern.last_used = datetime.now()
    
    def get_pattern(self, pattern_id: str) -> Optional[CodePattern]:
        """Get pattern by ID."""
        return self.patterns.get(pattern_id)
    
    def get_patterns_by_type(self, pattern_type: str) -> List[CodePattern]:
        """Get all patterns of a specific type."""
        pattern_ids = self.pattern_index.get(pattern_type, [])
        return [self.patterns[pid] for pid in pattern_ids if pid in self.patterns]
    
    def extract_patterns_from_file(
        self,
        file_path: str,
        content: str
    ) -> List[CodePattern]:
        """
        Extract patterns from a file.
        
        Args:
            file_path: Path to file
            content: File content
            
        Returns:
            List of extracted patterns
        """
        patterns = []
        
        # Detect language
        ext = file_path.split('.')[-1].lower() if '.' in file_path else ''
        
        if ext == 'py':
            # Extract Python functions and classes
            function_pattern = r'def\s+([a-zA-Z0-9_]+)\s*\([^)]*\):'
            class_pattern = r'class\s+([a-zA-Z0-9_]+)'
            
            for match in re.finditer(function_pattern, content):
                func_name = match.group(1)
                # Extract function body (simplified)
                start = match.end()
                # Find function end (simplified - would need proper parsing)
                end = content.find('\n\n', start)
                if end == -1:
                    end = min(start + 500, len(content))
                
                code_snippet = content[match.start():end]
                pattern = self.extract_pattern(
                    file_path,
                    code_snippet,
                    "function",
                    f"Function: {func_name}"
                )
                patterns.append(pattern)
            
            for match in re.finditer(class_pattern, content):
                class_name = match.group(1)
                # Extract class body (simplified)
                start = match.end()
                end = content.find('\n\n', start)
                if end == -1:
                    end = min(start + 1000, len(content))
                
                code_snippet = content[match.start():end]
                pattern = self.extract_pattern(
                    file_path,
                    code_snippet,
                    "class",
                    f"Class: {class_name}"
                )
                patterns.append(pattern)
        
        elif ext in ['js', 'ts', 'jsx', 'tsx']:
            # Extract JavaScript functions and classes
            function_pattern = r'(?:function|const|let|var)\s+([a-zA-Z0-9_]+)\s*[=:]?\s*(?:\(|=>)'
            class_pattern = r'class\s+([a-zA-Z0-9_]+)'
            
            for match in re.finditer(function_pattern, content):
                func_name = match.group(1)
                start = match.start()
                end = min(start + 500, len(content))
                code_snippet = content[start:end]
                pattern = self.extract_pattern(
                    file_path,
                    code_snippet,
                    "function",
                    f"Function: {func_name}"
                )
                patterns.append(pattern)
            
            for match in re.finditer(class_pattern, content):
                class_name = match.group(1)
                start = match.start()
                end = min(start + 1000, len(content))
                code_snippet = content[start:end]
                pattern = self.extract_pattern(
                    file_path,
                    code_snippet,
                    "class",
                    f"Class: {class_name}"
                )
                patterns.append(pattern)
        
        return patterns












