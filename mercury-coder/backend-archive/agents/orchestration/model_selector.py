"""
Model Selector - Intelligently chooses fast vs smart models based on task complexity.

Fast models for:
- Routing decisions (which agent next?)
- Status summaries
- Simple classifications
- Conversational responses

Smart models for:
- Complex code generation
- Multi-file refactoring
- Architectural planning
- Deep analysis
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger("mercury.agents.orchestration.model_selector")


class ModelTier(Enum):
    """Model performance tiers."""
    FAST = "fast"  # Quick, cheap models (Haiku, GPT-3.5-Turbo)
    SMART = "smart"  # Powerful models (Sonnet, GPT-4)
    GENIUS = "genius"  # Most powerful (Opus, GPT-4-Turbo)


class TaskComplexity(Enum):
    """Task complexity levels."""
    TRIVIAL = "trivial"  # Simple yes/no, routing
    SIMPLE = "simple"  # Basic operations
    MODERATE = "moderate"  # Standard coding
    COMPLEX = "complex"  # Multi-file changes
    VERY_COMPLEX = "very_complex"  # Architecture, refactoring


class ModelSelector:
    """
    Intelligently selects which model to use based on task complexity.
    
    This optimizes for both speed and cost:
    - Fast models: Routing, summaries, simple decisions
    - Smart models: Code generation, analysis, planning
    """
    
    # Model mappings (configure based on your setup)
    MODEL_MAP = {
        ModelTier.FAST: {
            "anthropic": "us.anthropic.claude-3-haiku-20240307-v1:0",
            "openai": "gpt-3.5-turbo",
            "default": "us.anthropic.claude-3-haiku-20240307-v1:0"
        },
        ModelTier.SMART: {
            "anthropic": "us.anthropic.claude-sonnet-4-20250514-v1:0",
            "openai": "gpt-4o",
            "default": "us.anthropic.claude-sonnet-4-20250514-v1:0"
        },
        ModelTier.GENIUS: {
            "anthropic": "us.anthropic.claude-opus-4-20250514-v1:0",
            "openai": "gpt-4o",
            "default": "us.anthropic.claude-opus-4-20250514-v1:0"
        }
    }
    
    def __init__(self, default_provider: str = "anthropic"):
        """
        Initialize model selector.
        
        Args:
            default_provider: Default model provider (anthropic, openai)
        """
        self.default_provider = default_provider
    
    def select_model_for_routing(self) -> str:
        """
        Select model for routing decisions.
        
        Routing is simple: "Should we switch agents?" "Is task complete?"
        Use FAST model for speed.
        
        Returns:
            Model ID for routing
        """
        return self._get_model(ModelTier.FAST)
    
    def select_model_for_coding(self, complexity: TaskComplexity = TaskComplexity.MODERATE) -> str:
        """
        Select model for code generation.
        
        Coding needs intelligence but speed varies by complexity.
        
        Args:
            complexity: Task complexity level
            
        Returns:
            Model ID for coding
        """
        if complexity in [TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE]:
            return self._get_model(ModelTier.SMART)  # Smart is fine for simple
        elif complexity == TaskComplexity.MODERATE:
            return self._get_model(ModelTier.SMART)  # Standard coding
        else:
            return self._get_model(ModelTier.GENIUS)  # Complex needs genius
    
    def select_model_for_research(self, complexity: TaskComplexity = TaskComplexity.SIMPLE) -> str:
        """
        Select model for research/exploration.
        
        Research is often simple: "Find auth code" "List files"
        
        Args:
            complexity: Task complexity level
            
        Returns:
            Model ID for research
        """
        if complexity in [TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE]:
            return self._get_model(ModelTier.FAST)  # Fast for simple searches
        else:
            return self._get_model(ModelTier.SMART)  # Smart for complex analysis
    
    def select_model_for_analysis(self, complexity: TaskComplexity = TaskComplexity.MODERATE) -> str:
        """
        Select model for code analysis/validation.
        
        Analysis needs intelligence to spot issues.
        
        Args:
            complexity: Task complexity level
            
        Returns:
            Model ID for analysis
        """
        if complexity == TaskComplexity.SIMPLE:
            return self._get_model(ModelTier.SMART)  # Smart for basic validation
        else:
            return self._get_model(ModelTier.SMART)  # Smart for deeper analysis
    
    def select_model_for_planning(self) -> str:
        """
        Select model for task planning.
        
        Planning needs intelligence to break down tasks properly.
        
        Returns:
            Model ID for planning
        """
        return self._get_model(ModelTier.SMART)  # Smart for planning
    
    def select_model_for_conversation(self) -> str:
        """
        Select model for conversational responses.
        
        Simple greetings don't need smart models.
        
        Returns:
            Model ID for conversation
        """
        return self._get_model(ModelTier.FAST)  # Fast for simple conversation
    
    def select_model_for_task(self, task_type: str, complexity: TaskComplexity = TaskComplexity.MODERATE) -> str:
        """
        Select model based on task type and complexity.
        
        Args:
            task_type: Type of task (routing, coding, research, analysis, planning, conversation)
            complexity: Task complexity level
            
        Returns:
            Model ID for the task
        """
        if task_type == "routing":
            return self.select_model_for_routing()
        elif task_type == "coding":
            return self.select_model_for_coding(complexity)
        elif task_type == "research":
            return self.select_model_for_research(complexity)
        elif task_type == "analysis":
            return self.select_model_for_analysis(complexity)
        elif task_type == "planning":
            return self.select_model_for_planning()
        elif task_type == "conversation":
            return self.select_model_for_conversation()
        else:
            logger.warning(f"Unknown task type: {task_type}, using SMART model")
            return self._get_model(ModelTier.SMART)
    
    def _get_model(self, tier: ModelTier) -> str:
        """
        Get model ID for a tier.
        
        Args:
            tier: Model tier
            
        Returns:
            Model ID
        """
        models = self.MODEL_MAP.get(tier, {})
        return models.get(self.default_provider, models.get("default"))
    
    def estimate_cost_savings(self, task_breakdown: Dict[str, int]) -> Dict[str, Any]:
        """
        Estimate cost savings from using tiered models.
        
        Args:
            task_breakdown: Dict of task_type -> count
            
        Returns:
            Cost estimate comparison
        """
        # Rough cost per 1M tokens (adjust based on actual pricing)
        COSTS = {
            ModelTier.FAST: {"input": 0.25, "output": 1.25},  # Haiku pricing
            ModelTier.SMART: {"input": 3.00, "output": 15.00},  # Sonnet pricing
            ModelTier.GENIUS: {"input": 15.00, "output": 75.00}  # Opus pricing
        }
        
        # Estimate tokens per task type
        TOKENS_PER_TASK = {
            "routing": {"input": 500, "output": 200},  # Small
            "coding": {"input": 2000, "output": 1500},  # Medium
            "research": {"input": 1000, "output": 500},  # Small-medium
            "analysis": {"input": 1500, "output": 800},  # Medium
            "planning": {"input": 1000, "output": 1000},  # Medium
            "conversation": {"input": 200, "output": 150}  # Tiny
        }
        
        # Calculate cost with tiered models
        tiered_cost = 0
        for task_type, count in task_breakdown.items():
            model_id = self.select_model_for_task(task_type)
            # Determine tier from model_id
            if "haiku" in model_id.lower() or "3.5" in model_id:
                tier = ModelTier.FAST
            elif "opus" in model_id.lower():
                tier = ModelTier.GENIUS
            else:
                tier = ModelTier.SMART
            
            tokens = TOKENS_PER_TASK.get(task_type, {"input": 1000, "output": 500})
            input_cost = (tokens["input"] / 1_000_000) * COSTS[tier]["input"] * count
            output_cost = (tokens["output"] / 1_000_000) * COSTS[tier]["output"] * count
            tiered_cost += input_cost + output_cost
        
        # Calculate cost if everything used SMART model
        all_smart_cost = 0
        for task_type, count in task_breakdown.items():
            tokens = TOKENS_PER_TASK.get(task_type, {"input": 1000, "output": 500})
            input_cost = (tokens["input"] / 1_000_000) * COSTS[ModelTier.SMART]["input"] * count
            output_cost = (tokens["output"] / 1_000_000) * COSTS[ModelTier.SMART]["output"] * count
            all_smart_cost += input_cost + output_cost
        
        savings = all_smart_cost - tiered_cost
        savings_percent = (savings / all_smart_cost * 100) if all_smart_cost > 0 else 0
        
        return {
            "tiered_cost": round(tiered_cost, 4),
            "all_smart_cost": round(all_smart_cost, 4),
            "savings": round(savings, 4),
            "savings_percent": round(savings_percent, 1)
        }


# Example usage breakdown
EXAMPLE_WORKFLOW = {
    "routing": 5,  # 5 routing decisions
    "coding": 2,  # 2 coding tasks
    "research": 1,  # 1 research task
    "analysis": 2,  # 2 analysis tasks
}

# Estimated savings: ~40-60% cost reduction for typical workflows!