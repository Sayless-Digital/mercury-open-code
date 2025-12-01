# Model Selector Integration Guide

## The Problem

Currently, the system uses the **same model** for everything:
- Simple routing decisions ("which agent next?")
- Complex code generation
- Simple summaries
- Deep architectural analysis

**Result:** Slow and expensive! Smart models cost ~10-50x more than fast models.

## The Solution: Tiered Models

Use **fast models** for simple tasks, **smart models** for complex work:

| Task Type | Complexity | Model | Why |
|-----------|-----------|-------|-----|
| **Routing** | Simple | 🏃 Fast (Haiku) | Just deciding "which agent?" |
| **Summaries** | Simple | 🏃 Fast (Haiku) | "Created 3 files" |
| **Conversation** | Simple | 🏃 Fast (Haiku) | "Hi, how can I help?" |
| **Simple Research** | Simple | 🏃 Fast (Haiku) | "Find main.py" |
| **Coding** | Moderate | 🧠 Smart (Sonnet) | Needs intelligence |
| **Analysis** | Moderate | 🧠 Smart (Sonnet) | Quality checks |
| **Planning** | Moderate | 🧠 Smart (Sonnet) | Task breakdown |
| **Refactoring** | Complex | 🎓 Genius (Opus) | Multi-file changes |

## Cost Savings

**Example Workflow:** "create a landing page"

Without tiering (all Smart):
```
5 routing decisions × $3.00 = $15.00
2 coding tasks × $3.00 = $6.00
2 analysis tasks × $3.00 = $6.00
1 research task × $3.00 = $3.00
Total: ~$30.00 per 1M tokens
```

With tiering:
```
5 routing decisions × $0.25 = $1.25  (Fast)
2 coding tasks × $3.00 = $6.00       (Smart)
2 analysis tasks × $3.00 = $6.00     (Smart)
1 research task × $0.25 = $0.25      (Fast)
Total: ~$13.50 per 1M tokens
```

**Savings: 55% cost reduction + 3-5x faster routing!**

## Implementation

### 1. Import ModelSelector

```python
from .model_selector import ModelSelector, TaskComplexity
```

### 2. Initialize in MultiAgentOrchestrator

```python
class MultiAgentOrchestrator:
    def __init__(self, ...):
        # ... existing code ...
        
        # Initialize model selector
        self.model_selector = ModelSelector(default_provider="anthropic")
```

### 3. Use in Routing Decisions

```python
async def decide_next_step(self, ...):
    # Use FAST model for routing (simple classification)
    routing_model = self.model_selector.select_model_for_routing()
    
    response = await self.invoke_bedrock_model(
        model_id=routing_model,  # Fast model!
        system_prompt=system_prompt,
        messages=messages,
        max_tokens=512
    )
```

### 4. Use in Agent Execution

```python
async def execute_collaborative_workflow(self, ...):
    # ... in the agent execution loop ...
    
    # Select appropriate model based on agent type
    if current_agent_name == "researcher":
        model = self.model_selector.select_model_for_research(TaskComplexity.SIMPLE)
    elif current_agent_name == "coder":
        model = self.model_selector.select_model_for_coding(TaskComplexity.MODERATE)
    elif current_agent_name == "analyzer":
        model = self.model_selector.select_model_for_analysis(TaskComplexity.MODERATE)
    elif current_agent_name == "planner":
        model = self.model_selector.select_model_for_planning()
    else:
        model = self.model_id  # Default smart model
    
    # Execute with selected model
    result = await agent.execute(task, context=context, model_id=model)
```

### 5. Agent Base Class Support

Update agents to accept model_id parameter:

```python
class BaseAgent:
    async def execute(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None  # NEW: Allow model override
    ) -> Dict[str, Any]:
        # Use provided model or default
        model_to_use = model_id or self.default_model_id
        
        # Execute with selected model
        result = await self.executor.execute_agent_task(
            self,
            task,
            context=context,
            model_id=model_to_use  # Pass through
        )
        return result
```

## Model Configuration

### Default Models (in model_selector.py)

```python
MODEL_MAP = {
    ModelTier.FAST: {
        "anthropic": "us.anthropic.claude-3-haiku-20240307-v1:0",
        "openai": "gpt-3.5-turbo"
    },
    ModelTier.SMART: {
        "anthropic": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "openai": "gpt-4o"
    },
    ModelTier.GENIUS: {
        "anthropic": "us.anthropic.claude-opus-4-20250514-v1:0",
        "openai": "gpt-4-turbo"
    }
}
```

### Customize for Your Needs

```python
# Example: Force all routing to use Haiku
selector = ModelSelector(default_provider="anthropic")

# Override specific selections
routing_model = "us.anthropic.claude-3-haiku-20240307-v1:0"
coding_model = "us.anthropic.claude-sonnet-4-20250514-v1:0"
```

## Task Complexity Detection

The system can auto-detect complexity:

```python
from .task_classifier import TaskClassifier

# Classify task complexity
task_description = "refactor authentication system"
task_type = TaskClassifier.classify(task_description)

# Map to model complexity
if task_type == TaskType.VERY_COMPLEX:
    complexity = TaskComplexity.VERY_COMPLEX
    model = selector.select_model_for_coding(complexity)  # Genius model
```

## Monitoring

Track model usage and costs:

```python
class MultiAgentOrchestrator:
    def __init__(self, ...):
        self.model_usage_stats = {
            "fast": 0,
            "smart": 0,
            "genius": 0
        }
    
    def _track_model_usage(self, model_id: str):
        if "haiku" in model_id.lower():
            self.model_usage_stats["fast"] += 1
        elif "opus" in model_id.lower():
            self.model_usage_stats["genius"] += 1
        else:
            self.model_usage_stats["smart"] += 1
    
    def get_cost_estimate(self):
        """Estimate cost based on usage."""
        return self.model_selector.estimate_cost_savings({
            "routing": self.model_usage_stats["fast"],
            "coding": self.model_usage_stats["smart"],
            "research": self.model_usage_stats["fast"],
            "analysis": self.model_usage_stats["smart"]
        })
```

## Testing

Test model selection:

```python
selector = ModelSelector()

# Test routing (should use fast)
routing_model = selector.select_model_for_routing()
assert "haiku" in routing_model.lower()

# Test coding (should use smart)
coding_model = selector.select_model_for_coding(TaskComplexity.MODERATE)
assert "sonnet" in coding_model.lower()

# Test complex refactoring (should use genius)
refactor_model = selector.select_model_for_coding(TaskComplexity.VERY_COMPLEX)
assert "opus" in refactor_model.lower() or "sonnet" in refactor_model.lower()
```

## Benefits Summary

✅ **55-70% cost reduction** for typical workflows
✅ **3-5x faster routing** decisions  
✅ **Same quality** for complex tasks (still use smart models)
✅ **Intelligent selection** based on task complexity
✅ **Configurable** - adjust tiers per your needs

## Recommended Rollout

1. **Phase 1**: Add model selector to routing decisions only
   - Immediate 30-40% speed improvement
   - Lowest risk

2. **Phase 2**: Add to conversational responses and summaries
   - Additional 10-15% cost savings
   - Better UX (faster responses)

3. **Phase 3**: Add to research tasks
   - Another 10-15% savings
   - Most research is simple searches

4. **Phase 4**: Dynamic selection for coding based on complexity
   - Optimal performance/cost balance
   - Requires complexity detection

## Future Enhancements

- **Learning**: Track which models work best for which tasks
- **Adaptive**: Automatically adjust tier based on results
- **User Preferences**: Let users choose speed vs quality
- **Cost Limits**: Auto-downgrade to fast models when approaching limits