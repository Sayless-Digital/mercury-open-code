# Intelligent AI-Powered Task Routing

## Problem: Static Keyword Matching

**Before:** The system used static keyword matching to route tasks:
- "create" → route to coder
- "show" → route to researcher  
- "do" → not recognized, defaults to researcher ❌

**Issue:** 
- "do a landing page" was routed to **researcher** (wrong!)
- Researcher explored and made recommendations but **never created files**
- No semantic understanding of intent

## Solution: AI Semantic Router

**After:** The system uses an AI decision layer that understands semantic intent:
- "do a landing page" → AI understands this means CREATE → routes to **coder** ✅
- "show me the code" → AI understands this means EXPLORE → routes to **researcher** ✅
- "hi" → AI understands this is GREETING → fast conversational response ✅

## How It Works

### 1. Intent Analysis (AI-Powered)
The [`IntelligentRouter`](intelligent_router.py) uses an LLM to analyze requests:

```python
# User says: "do a landing page design"
routing, intent, reasoning = await intelligent_router.analyze_intent(
    user_request="do a landing page design",
    context={"is_empty_directory": True}
)

# AI Response:
# routing = RouteDecision.CODER_DIRECT
# intent = IntentType.CREATION
# reasoning = "User wants to CREATE new files, route to coder"
```

### 2. Semantic Understanding

The AI understands these intent types:
- **GREETING**: "hi", "hello", "thanks" → Fast response
- **QUESTION**: "what is X?", "how does Y work?" → Researcher
- **EXPLORATION**: "show me", "find", "search" → Researcher  
- **CREATION**: "create", "make", "build", "**do** [something]" → **Coder**
- **MODIFICATION**: "edit", "change", "update" → Coder
- **VALIDATION**: "test", "check", "validate" → Analyzer
- **REFACTORING**: Large changes → Full workflow

### 3. Intelligent Routing Decisions

```python
RouteDecision.CONVERSATIONAL     # Fast response, no tools
RouteDecision.CODER_DIRECT       # Route to coder agent ✅
RouteDecision.RESEARCHER_ONLY    # Route to researcher
RouteDecision.ANALYZER_DIRECT    # Route to analyzer
RouteDecision.FULL_WORKFLOW      # Full explore→plan→execute→validate
```

## Examples

### Example 1: "do a landing page"
**Before (Keyword Matching):**
```
"do" not in keywords → Default to researcher → Only explores, no files created ❌
```

**After (AI Router):**
```
AI: "User wants to CREATE landing page" 
→ Intent: CREATION
→ Route: CODER_DIRECT  
→ Coder creates HTML/CSS/JS files ✅
```

### Example 2: "show me the authentication code"
**Before:**
```
"show" in keywords → Route to researcher ✅ (works, but static)
```

**After:**
```
AI: "User wants to EXPLORE existing code"
→ Intent: EXPLORATION
→ Route: RESEARCHER_ONLY ✅ (semantic understanding)
```

### Example 3: "hi there"
**Before:**
```
Short message → Conversational check → Fast response ✅
```

**After:**
```
AI: "Simple GREETING"
→ Intent: GREETING
→ Route: CONVERSATIONAL ✅ (faster, more intelligent)
```

## Benefits

1. **Semantic Understanding**: Understands intent, not just keywords
2. **Flexible**: Handles variations ("do", "make", "create" all recognized as CREATION)
3. **Context-Aware**: Considers project state (empty directory vs existing code)
4. **Self-Improving**: Can analyze conversation history for better decisions
5. **Fallback Safety**: Falls back to heuristics if AI fails

## Integration

The intelligent router is integrated in [`orchestrator.py`](../orchestrator.py):

```python
# In execute_workflow():
if not use_full_workflow:
    # Use intelligent router for semantic routing
    route_result = await self.intelligent_router.route_task(
        user_request, project_path, session_id, context
    )
    
    # Check if router determined full workflow is needed
    if route_result.get("needs_full_workflow"):
        use_full_workflow = True
    else:
        return route_result  # Task handled by intelligent router
```

## Performance

- **Caching**: Identical requests are cached for fast repeated routing
- **Fast Fallback**: If AI fails, uses simple heuristics
- **Parallel Analysis**: Routing decision made in parallel with other operations

## Future Enhancements

1. **Learning**: Train on successful routing decisions
2. **Multi-Agent**: Route to multiple agents in sequence/parallel
3. **Confidence-Based**: Use full workflow if confidence is low
4. **Context Memory**: Remember user preferences for routing

## Testing

See [`test_intelligent_router.py`](../../tests/test_intelligent_router.py) for examples.