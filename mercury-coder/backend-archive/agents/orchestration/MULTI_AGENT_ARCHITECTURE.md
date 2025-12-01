# Multi-Agent Collaborative Architecture

## Revolutionary Change: Agents That Talk To Each Other

### Before (Old System)
```
User → Router → Agent → Done
         ↓
   Single routing decision
   Agent works in isolation
   No agent-to-agent communication
```

**Problem:** Agents couldn't collaborate. If a task needed multiple specialties, it was routed once to a single agent who had to do everything alone.

### After (New System)
```
User → Router → Agent 1 → Router → Agent 2 → Router → Agent 3 → Done
         ↓          ↓          ↓          ↓          ↓
    Continuous AI routing after EVERY agent action
    Agents communicate and collaborate dynamically
    Workflow adapts based on results
```

**Solution:** AI router runs **after every agent completes work**, deciding dynamically who should act next!

## How It Works

### 1. Initial Routing
```python
User: "create a landing page"
   ↓
AI Router analyzes: "CREATION task" → Routes to Coder
```

### 2. First Agent Acts
```python
Coder: Creates HTML/CSS/JS files
   ↓
Returns: {files_created: ["index.html", "styles.css", "script.js"]}
```

### 3. AI Router Decides Next Step
```python
AI Router analyzes: 
  - Goal: "create landing page"
  - Done: Files created
  - Question: "Should we validate the quality?"
  ↓
Decision: SWITCH_AGENT → Analyzer
```

### 4. Second Agent Acts
```python
Analyzer: Validates design quality
   ↓
Returns: {design_score: 45, issues: ["No gradients", "Plain colors"]}
```

### 5. AI Router Decides Again
```python
AI Router analyzes:
  - Goal: "create landing page"
  - Done: Files created, but quality too low
  - Question: "What now?"
  ↓
Decision: SWITCH_AGENT → Coder (with message: "Improve design - add gradients, modern colors")
```

### 6. Third Agent Acts
```python
Coder: Improves files with modern design
   ↓
Returns: {files_modified: ["styles.css"], improvements: ["Added gradients", "Modern colors"]}
```

### 7. AI Router Decides Final Step
```python
AI Router analyzes:
  - Goal: "create landing page"  
  - Done: Files created AND validated
  - Question: "Are we done?"
  ↓
Decision: TASK_COMPLETE ✅
```

## Key Components

### 1. MultiAgentOrchestrator
**File:** [`multi_agent_orchestrator.py`](multi_agent_orchestrator.py)

**Purpose:** Orchestrates the agent-to-agent conversation loop.

**Key Method:** `execute_collaborative_workflow()`
- Routes to initial agent
- Agent performs work
- Routes to next agent (or same agent, or completion)
- Repeat until goal achieved

**Features:**
- Max iterations limit (default: 15)
- Full conversation history tracking
- Dynamic agent switching
- User input detection (when blocked)

### 2. AI Routing After Every Action
**Method:** `decide_next_step()`

**Input:**
- User's original goal
- Conversation history (last 5 agent actions)
- Last agent's result

**Output:**
- `next_step`: What happens next?
  - `CONTINUE_SAME_AGENT`: Current agent continues
  - `SWITCH_AGENT`: Different agent takes over
  - `TASK_COMPLETE`: Goal achieved
  - `NEEDS_USER_INPUT`: Blocked, needs user
- `next_agent`: Which agent should act (if switching)
- `reasoning`: Why this decision makes sense
- `message_to_agent`: Specific instructions for next agent

**Example Decision:**
```json
{
  "next_step": "SWITCH_AGENT",
  "next_agent": "coder",
  "reasoning": "Validation found design quality issues. Coder should improve the styling.",
  "message_to_agent": "Improve styles.css - add CSS gradients, shadows, and modern colors. Current design score is 45/100.",
  "confidence": 0.95
}
```

### 3. Agent Conversation History
Each agent action is recorded:
```python
{
  "iteration": 3,
  "agent": "coder",
  "action": "Improve styling with modern design patterns",
  "result": {...},
  "success": True
}
```

This history is used for routing decisions, ensuring context is maintained across agent switches.

## Example Workflows

### Example 1: Simple Task (1 Agent)
```
User: "search for authentication code"
  ↓
Router: EXPLORATION → Researcher
  ↓
Researcher: Searches codebase, finds auth files
  ↓
Router: TASK_COMPLETE ✅
```

### Example 2: Moderate Task (2 Agents)
```
User: "create a config file"
  ↓
Router: CREATION → Coder
  ↓
Coder: Creates config.json
  ↓
Router: SWITCH_AGENT → Analyzer
  ↓
Analyzer: Validates JSON syntax
  ↓
Router: TASK_COMPLETE ✅
```

### Example 3: Complex Task (Multiple Agents, Iterations)
```
User: "refactor the authentication system"
  ↓
Router: COMPLEX → Planner
  ↓
Planner: Creates refactoring plan (5 steps)
  ↓
Router: SWITCH_AGENT → Researcher
  ↓
Researcher: Analyzes current auth code
  ↓
Router: SWITCH_AGENT → Coder
  ↓
Coder: Refactors auth module
  ↓
Router: SWITCH_AGENT → Analyzer
  ↓
Analyzer: Tests changes, finds issues
  ↓
Router: SWITCH_AGENT → Coder (with issues to fix)
  ↓
Coder: Fixes issues
  ↓
Router: SWITCH_AGENT → Analyzer
  ↓
Analyzer: Validates - all good
  ↓
Router: TASK_COMPLETE ✅
```

## Benefits

### 1. **True Collaboration**
Agents work together like a real dev team:
- Researcher finds info
- Coder implements
- Analyzer validates
- Coder iterates
- Until goal achieved

### 2. **Dynamic Adaptation**
Workflow adapts based on results:
- If validation fails → route back to coder
- If coder needs info → route to researcher
- If task is complex → route to planner first

### 3. **Intelligent Specialization**
Each agent focuses on what they do best:
- Researcher: Information gathering
- Coder: Code creation/modification
- Analyzer: Quality validation
- Planner: Task breakdown

### 4. **Iterative Refinement**
Natural feedback loops:
```
Coder → Analyzer → (issues found) → Coder → Analyzer → ✅
```

### 5. **Context Preservation**
Full conversation history ensures:
- Agents know what others have done
- No repeated work
- Builds on previous results

## Configuration

In [`orchestrator.py`](../orchestrator.py):

```python
self.multi_agent_orchestrator = MultiAgentOrchestrator(
    intelligent_router=self.intelligent_router,
    researcher=self.researcher,
    coder=self.coder,
    analyzer=self.analyzer,
    planner=self.planner,
    invoke_bedrock_model=invoke_bedrock_model,
    model_id=model_id,
    status_emitter=self.status_emitter,
    max_iterations=15  # Adjust based on needs
)
```

**max_iterations:** Maximum agent-to-agent interactions before forcing completion. Prevents infinite loops.

## Testing

Test the multi-agent workflow:

```bash
# Simple task (1-2 agents)
User: "find the main entry point"

# Moderate task (2-3 agents)  
User: "create a landing page"

# Complex task (3+ agents, iterations)
User: "refactor and improve the auth system"
```

## Monitoring

Watch for these log messages:

```
[MULTI-AGENT] Starting collaborative workflow
[MULTI-AGENT] Iteration 1/15, Agent: coder
[MULTI-AGENT] Agent 'coder' completed: success=True
[MULTI-AGENT] Next step decision: SWITCH_AGENT
[MULTI-AGENT] Reasoning: Files created, now validate
[MULTI-AGENT] Switching from coder to analyzer
[MULTI-AGENT] Iteration 2/15, Agent: analyzer
...
[MULTI-AGENT] Workflow complete!
```

## Future Enhancements

1. **Parallel Agent Execution**: Multiple agents work simultaneously
2. **Agent Memory**: Agents remember past interactions across sessions
3. **Learning**: System learns which agent combinations work best
4. **Agent Proposals**: Agents can suggest "I think we should bring in the analyzer"
5. **Sub-Workflows**: Agents can spawn their own multi-agent workflows

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    User Request                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Multi-Agent Orchestrator                    │
│  ┌────────────────────────────────────────────────────┐ │
│  │         AI Router (Semantic Intent Analysis)        │ │
│  └──────┬─────────────────────────────────────────────┘ │
│         │                                                │
│         ▼                                                │
│  ┌──────────────────┐                                   │
│  │  Decide Agent    │                                   │
│  └──────┬───────────┘                                   │
│         │                                                │
│         ▼                                                │
│  ┌─────────────────────────────────────────────┐       │
│  │  Agent Executes (Researcher/Coder/Analyzer) │       │
│  └──────┬──────────────────────────────────────┘       │
│         │                                                │
│         ▼                                                │
│  ┌─────────────────────────────────────────────┐       │
│  │  AI Router (Decide Next Step)               │       │
│  │  - Continue same agent?                     │       │
│  │  - Switch to different agent?               │       │
│  │  - Task complete?                           │       │
│  └──────┬──────────────────────────────────────┘       │
│         │                                                │
│         ▼                                                │
│  ┌──────────────┐                                       │
│  │  Next Agent  │ ◄────────┐                           │
│  └──────┬───────┘          │                           │
│         │                   │                           │
│         └───────────────────┘ (Loop until complete)    │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Final Result + Conversation History         │
└─────────────────────────────────────────────────────────┘
```

## Comparison: Old vs New

| Aspect | Old System | New System |
|--------|-----------|------------|
| **Routing** | Once at start | After every action |
| **Agent Communication** | None | Full conversation history |
| **Adaptation** | Static | Dynamic based on results |
| **Specialization** | One agent does everything | Agents collaborate on their specialties |
| **Quality Loop** | Manual | Automatic (analyzer → coder → analyzer) |
| **Complex Tasks** | Single agent struggles | Multiple agents collaborate |

## Summary

The **Multi-Agent Collaborative Architecture** transforms your system from isolated agents to a **true dev team** that communicates and collaborates:

✅ **AI routing after every action**
✅ **Agents talk to each other dynamically**
✅ **Workflow adapts based on results**
✅ **Automatic quality refinement loops**
✅ **True specialization and collaboration**

This is the future of AI agent systems!