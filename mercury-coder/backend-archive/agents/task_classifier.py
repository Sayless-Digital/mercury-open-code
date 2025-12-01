"""
Task classification utility - centralizes task complexity and type detection.
"""

from enum import Enum
from typing import Dict, Any, Optional


class TaskType(Enum):
    """Task type classification."""
    CONVERSATIONAL = "conversational"  # Simple greetings, acknowledgments
    SIMPLE = "simple"  # Single action, no workflow needed
    MODERATE = "moderate"  # Requires some planning
    COMPLEX = "complex"  # Requires full workflow
    VERY_COMPLEX = "very_complex"  # Large refactors, multi-file changes


class TaskComplexity(Enum):
    """Task complexity levels for iteration limits."""
    TRIVIAL = 1  # Simple response, no tools
    SIMPLE = 3  # Few tool calls
    MODERATE = 5  # Default
    COMPLEX = 8  # Multi-step with many files
    VERY_COMPLEX = 12  # Large refactors


class TaskClassifier:
    """Centralized task classification logic."""
    
    # Consistent thresholds
    SIMPLE_WORD_THRESHOLD = 5  # Tasks with <= 5 words are likely simple
    VERY_SHORT_THRESHOLD = 3  # Tasks with <= 3 words are likely conversational
    
    # Keywords that suggest complexity
    COMPLEX_KEYWORDS = [
        "implement", "create", "add", "build", "refactor", "restructure",
        "feature", "functionality", "system", "architecture", "multiple",
        "several", "all", "entire", "complete", "full"
    ]
    
    # Keywords that suggest simplicity
    SIMPLE_KEYWORDS = [
        "read", "show", "display", "what", "explain", "tell", "how",
        "where", "find", "search", "grep", "list"
    ]
    
    # Conversational indicators
    CONVERSATIONAL_INDICATORS = [
        "hi", "hello", "hey", "hiya", "greetings", "sup", "yo", "howdy",
        "thanks", "thank you", "ty", "ok", "okay", "yes", "no", "np",
        "cool", "nice", "sure", "alright", "got it", "understood"
    ]
    
    # Code-related keywords that prevent conversational classification
    CODE_KEYWORDS = [
        "file", "code", "function", "class", "read", "write", "edit",
        "search", "find", "explore", "implement", "create"
    ]
    
    @classmethod
    def classify(cls, task_description: str) -> TaskType:
        """
        Classify a task by its description.
        
        Args:
            task_description: The task description text
            
        Returns:
            TaskType enum value
        """
        if not task_description:
            return TaskType.SIMPLE
        
        description_lower = task_description.lower().strip()
        words = description_lower.split()
        
        # Check for conversational tasks (very short with conversational indicators)
        if len(words) <= cls.VERY_SHORT_THRESHOLD:
            greetings = cls.CONVERSATIONAL_INDICATORS[:8]  # First 8 are greetings
            acknowledgments = cls.CONVERSATIONAL_INDICATORS[8:]  # Rest are acknowledgments
            questions = ["what", "how", "who", "when", "where", "why"]
            
            if any(word in greetings or word in acknowledgments for word in words):
                return TaskType.CONVERSATIONAL
            
            # Simple questions without code-related keywords
            if any(word in questions for word in words[:2]) and not any(
                word in cls.CODE_KEYWORDS for word in words
            ):
                return TaskType.CONVERSATIONAL
        
        # Check for conversational tasks (short with conversational indicators, no code keywords)
        if len(words) <= cls.SIMPLE_WORD_THRESHOLD:
            if any(indicator in description_lower for indicator in cls.CONVERSATIONAL_INDICATORS):
                if not any(keyword in description_lower for keyword in cls.CODE_KEYWORDS):
                    return TaskType.CONVERSATIONAL
        
        # Count complex vs simple indicators
        complex_count = sum(1 for keyword in cls.COMPLEX_KEYWORDS if keyword in description_lower)
        simple_count = sum(1 for keyword in cls.SIMPLE_KEYWORDS if keyword in description_lower)
        
        # Check for simple "create X" patterns first (before marking as complex)
        # Simple creation tasks like "create a landing page" or "do a landing page" don't need full workflow
        simple_action_verbs = ["read", "write", "edit", "delete", "create", "show", "do", "make"]
        has_simple_action = any(verb in description_lower.split()[:3] for verb in simple_action_verbs)
        
        # If it's a short "create X" task (3-5 words), treat as simple/moderate
        # Examples: "create a landing page", "create login form", "add button"
        if has_simple_action and len(words) <= 5:
            # Check if it's truly simple (single object to create) vs complex (multiple things)
            # Simple: "create landing page", "add button", "create form"
            # Complex: "create landing page with multiple sections and forms"
            if any(complex_word in description_lower for complex_word in ["multiple", "several", "all", "entire", "complete", "full", "system", "architecture"]):
                # Has complexity indicators, keep as complex
                pass
            elif complex_count == 1 and "create" in description_lower:
                # Simple "create X" task - treat as moderate (needs some planning but not full workflow)
                return TaskType.MODERATE
            elif simple_count > 0 and complex_count == 0:
                return TaskType.SIMPLE
        
        # Very complex: multiple complex keywords
        if complex_count >= 2:
            return TaskType.VERY_COMPLEX
        
        # Complex: has complex keywords (but not simple "create X" patterns)
        if complex_count >= 1:
            return TaskType.COMPLEX
        
        # Simple: has simple keywords and no complex ones
        if simple_count > 0 and complex_count == 0:
            # Check if it's a single action verb (likely simple)
            if has_simple_action:
                return TaskType.SIMPLE
            
            # Short messages without complex keywords
            if len(words) <= cls.SIMPLE_WORD_THRESHOLD:
                return TaskType.SIMPLE
        
        # Moderate: default for unclear cases
        return TaskType.MODERATE
    
    @classmethod
    def is_conversational(cls, task_description: str) -> bool:
        """
        Check if task is conversational (simple response, no tools needed).
        
        Args:
            task_description: The task description text
            
        Returns:
            True if conversational, False otherwise
        """
        task_type = cls.classify(task_description)
        return task_type == TaskType.CONVERSATIONAL
    
    @classmethod
    def should_use_full_workflow(cls, task_description: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine if task requires full workflow (explore → plan → execute → validate).
        
        Args:
            task_description: The task description text
            context: Optional context dict with project info (e.g., {"is_empty_directory": bool})
            
        Returns:
            True if full workflow needed, False for direct execution
        """
        task_type = cls.classify(task_description)
        description_lower = task_description.lower().strip()
        words = description_lower.split()
        
        # Simple file creation tasks should skip full workflow
        # Examples: "create landing page", "write HTML file", "create script.js", "do a landing page"
        is_file_creation = any(keyword in description_lower for keyword in [
            "create", "write", "make", "build", "add", "do a", "do "
        ]) and any(keyword in description_lower for keyword in [
            "file", "files", "page", "script", "html", "css", "javascript", "js", "landing page", "website", "site", "component"
        ])
        
        # Check if it's a short, simple creation task
        # Allow up to 12 words for simple file creation (e.g., "create a landing page with css, js and html only")
        is_short_task = len(words) <= 12
        has_complex_indicators = any(word in description_lower for word in [
            "multiple", "several", "all", "entire", "complete", "full", "system", "architecture", 
            "refactor", "restructure", "implement feature", "add functionality"
        ])
        
        # Simple file creation tasks don't need full workflow
        if is_file_creation and is_short_task and not has_complex_indicators:
            return False
        
        # Check if directory is empty/new project - simple creation tasks don't need full workflow
        if context:
            is_empty = context.get("is_empty_directory", False)
            is_new_project = context.get("is_new_project", False)
            
            # For empty/new projects, simple "create X" tasks can skip full workflow
            if (is_empty or is_new_project) and task_type == TaskType.MODERATE:
                # Simple creation patterns in empty directories
                if len(words) <= 6 and any(verb in description_lower.split()[:3] for verb in ["create", "add", "build", "do", "make"]):
                    # Don't need full exploration for empty directories
                    return False
        
        # Only complex and very_complex tasks need full workflow
        return task_type in [TaskType.COMPLEX, TaskType.VERY_COMPLEX]
    
    @classmethod
    def estimate_complexity(cls, task: Dict[str, Any]) -> TaskComplexity:
        """
        Estimate task complexity for iteration limits.
        
        Args:
            task: Task dictionary with description and other fields
            
        Returns:
            TaskComplexity enum value
        """
        description = task.get("description", "")
        task_type = cls.classify(description)
        
        # Map task type to complexity
        if task_type == TaskType.CONVERSATIONAL:
            return TaskComplexity.TRIVIAL
        elif task_type == TaskType.SIMPLE:
            return TaskComplexity.SIMPLE
        elif task_type == TaskType.MODERATE:
            return TaskComplexity.MODERATE
        elif task_type == TaskType.COMPLEX:
            return TaskComplexity.COMPLEX
        else:  # VERY_COMPLEX
            return TaskComplexity.VERY_COMPLEX
    
    @classmethod
    def get_max_iterations(cls, task: Dict[str, Any]) -> int:
        """
        Get maximum iterations for a task based on complexity.
        
        Args:
            task: Task dictionary
            
        Returns:
            Maximum number of iterations
        """
        complexity = cls.estimate_complexity(task)
        description = task.get("description", "").lower()
        
        # For simple file creation tasks, reduce iterations to force faster execution
        # This prevents over-analysis and encourages immediate file writing
        is_simple_creation = any(keyword in description for keyword in [
            "create", "write", "make", "build", "add", "do"
        ]) and any(keyword in description for keyword in [
            "file", "files", "page", "script", "html", "css", "javascript", "js", "landing page", "website", "site"
        ])
        
        # Check if it's a short, simple creation task (not complex multi-file refactoring)
        words = description.split()
        is_short_task = len(words) <= 6
        has_complex_indicators = any(word in description for word in [
            "multiple", "several", "all", "entire", "complete", "full", "system", "architecture", "refactor"
        ])
        
        if is_simple_creation and is_short_task and not has_complex_indicators:
            # Simple file creation - limit to 2-3 iterations to FORCE immediate execution
            # Iteration 1: Should write files immediately
            # Iteration 2: Confirm completion
            # This prevents the agent from wasting time analyzing
            return min(complexity.value, 3)
        
        return complexity.value


