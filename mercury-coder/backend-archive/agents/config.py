"""
Agent configuration - standardized configuration for agent initialization.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Any


@dataclass
class AgentConfig:
    """
    Standardized configuration for agent initialization.
    
    This ensures all agents are initialized consistently with the same
    dependencies and capabilities.
    """
    memory_manager: Optional[Any] = None
    tool_executor: Optional[Any] = None
    tool_recommender: Optional[Any] = None
    file_graph: Optional[Any] = None
    pattern_matcher: Optional[Any] = None
    proactive_search_manager: Optional[Any] = None
    feedback_loop_manager: Optional[Any] = None
    
    def get_common_params(self) -> Dict[str, Any]:
        """Get common parameters for all agents."""
        return {
            "memory_manager": self.memory_manager,
            "tool_executor": self.tool_executor,
            "tool_recommender": self.tool_recommender,
        }
    
    def get_planner_params(self) -> Dict[str, Any]:
        """Get parameters specific to PlannerAgent."""
        params = self.get_common_params()
        params.update({
            "file_graph": self.file_graph,
            "pattern_matcher": self.pattern_matcher,
            "proactive_search_manager": self.proactive_search_manager,
        })
        return params
    
    def get_researcher_params(self) -> Dict[str, Any]:
        """Get parameters specific to ResearcherAgent."""
        params = self.get_common_params()
        params.update({
            "proactive_search_manager": self.proactive_search_manager,
        })
        return params
    
    def get_coder_params(self) -> Dict[str, Any]:
        """Get parameters specific to CoderAgent."""
        params = self.get_common_params()
        params.update({
            "proactive_search_manager": self.proactive_search_manager,
        })
        return params
    
    def get_analyzer_params(self) -> Dict[str, Any]:
        """Get parameters specific to AnalyzerAgent."""
        # Analyzer doesn't need proactive_search_manager currently
        return self.get_common_params()


# Configuration constants
class AgentConstants:
    """Configuration constants for agent behavior."""
    MAX_TASK_RETRIES = 3
    RETRY_DELAY_SECONDS = 1.0
    CONTEXT_RETRIEVAL_LIMIT_DEFAULT = 5
    CONTEXT_RETRIEVAL_LIMIT_ENHANCED = 8
    MAX_ITERATIONS_SIMPLE = 3
    MAX_ITERATIONS_MODERATE = 5
    MAX_ITERATIONS_COMPLEX = 8
    MAX_ITERATIONS_VERY_COMPLEX = 12
    LOOP_DETECTOR_WINDOW_SIZE = 5
    FEEDBACK_LOOP_MAX_RETRIES = 3
    PROACTIVE_CACHE_TTL_SECONDS = 3600

