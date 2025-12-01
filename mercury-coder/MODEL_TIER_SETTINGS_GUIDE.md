# Model Tier Settings - User Guide

## Overview

You can now configure exactly which models to use for each tier (Fast/Smart/Genius) and assign tasks to specific tiers through the Settings UI.

## How to Configure

### Step 1: Open Settings

1. Click on the Settings icon in the app
2. Navigate to the **Models** tab
3. Enable **"Smart Model Selection"** toggle

### Step 2: Configure Models for Each Tier

You'll see three dropdown menus to select models:

**⚡ Fast Model** (Default: Claude 3.5 Haiku)
- Used for: Routing decisions, simple searches
- Recommended: `claude-3-5-haiku` or `claude-3-haiku`
- Purpose: Speed and cost optimization

**🧠 Smart Model** (Default: Claude Sonnet 4.5)
- Used for: Code generation, analysis, planning
- Recommended: `claude-sonnet-4` or `claude-sonnet-3.5`
- Purpose: Quality code and analysis

**🎓 Genius Model** (Default: Claude Opus 4)
- Used for: Complex refactoring, architecture
- Recommended: `claude-opus-4` or `claude-opus-3`
- Purpose: Maximum intelligence for complex tasks

### Step 3: Assign Tiers to Tasks

Below the model configuration, you'll see task assignments:

- **Routing Decisions**: Which agent should act next?
  - Recommended: ⚡ Fast
  
- **Code Generation**: Writing and modifying code
  - Recommended: 🧠 Smart
  
- **Research & Search**: Exploring codebase
  - Recommended: ⚡ Fast
  
- **Code Analysis**: Validating quality
  - Recommended: 🧠 Smart
  
- **Task Planning**: Breaking down tasks
  - Recommended: 🧠 Smart

## Recommended Configurations

### Maximum Cost Savings (73% savings)
```
Fast Model:  Claude 3 Haiku
Smart Model: Claude Sonnet 3.5
Genius Model: Claude Opus 3

Routing:    ⚡ Fast
Coding:     🧠 Smart
Research:   ⚡ Fast
Analysis:   🧠 Smart
Planning:   🧠 Smart
```

### Balanced (55% savings, Latest models)
```
Fast Model:  Claude 3.5 Haiku ⭐ Recommended
Smart Model: Claude Sonnet 4.5 ⭐ Recommended
Genius Model: Claude Opus 4

Routing:    ⚡ Fast
Coding:     🧠 Smart
Research:   ⚡ Fast
Analysis:   🧠 Smart
Planning:   🧠 Smart
```

### Maximum Quality (Lower savings)
```
Fast Model:  Claude 3.5 Haiku
Smart Model: Claude Sonnet 4.5
Genius Model: Claude Opus 4

Routing:    🧠 Smart
Coding:     🎓 Genius
Research:   🧠 Smart
Analysis:   🎓 Genius
Planning:   🎓 Genius
```

## How It Works

1. **You select models**: Choose which specific Claude model to use for each tier
2. **You assign tasks to tiers**: Decide if each task type should use Fast, Smart, or Genius
3. **System uses your choices**: The backend automatically uses your configured models

## Example Workflow

Let's say you configure:
- Fast Model = Claude 3.5 Haiku
- Smart Model = Claude Sonnet 4.5
- Routing = Fast tier
- Coding = Smart tier

When you ask the agent to "create a landing page":

1. **Routing decision** → Uses Claude 3.5 Haiku (fast & cheap)
2. **Creates files** → Uses Claude Sonnet 4.5 (quality code)
3. **Routing decision** → Uses Claude 3.5 Haiku again
4. **Analysis** → Uses Claude Sonnet 4.5 (quality check)

## Cost Impact

### Example: 50 Tasks Workflow

**Before (all Sonnet 4.5):**
- 30 routing calls: $0.090
- 10 research tasks: $0.300
- 10 coding tasks: $0.300
- **Total: $0.690**

**After (with Fast/Smart split):**
- 30 routing calls (Haiku 3.5): $0.024 💰
- 10 research tasks (Haiku 3.5): $0.080 💰
- 10 coding tasks (Sonnet 4.5): $0.300
- **Total: $0.404** (41% savings!)

## Tips

1. **Use Fast for routing** - It's 3-5x faster and routing is simple
2. **Use Smart for coding** - Quality matters for code generation
3. **Use Fast for research** - File exploration is straightforward
4. **Test your configuration** - Try a small task and see the results
5. **Monitor costs** - Check if your settings are working as expected

## Settings Persistence

All your model tier settings are automatically saved to localStorage and will persist across sessions. No need to reconfigure every time!

## Troubleshooting

**Models not appearing in dropdowns?**
- Ensure you've selected the correct AWS region
- Check that models are available in your Bedrock account

**Settings not saving?**
- Check browser console for errors
- Verify localStorage permissions

**Want to reset to defaults?**
- Simply select the recommended models for each tier
- Or toggle Smart Model Selection off and back on

## Advanced: Model IDs

If you need to know the exact model IDs being used:

- Fast (Haiku 3.5): `us.anthropic.claude-3-5-haiku-20241022-v1:0`
- Smart (Sonnet 4.5): `us.anthropic.claude-sonnet-4-20250514-v1:0`
- Genius (Opus 4): `us.anthropic.claude-opus-4-20250514-v1:0`

These are stored in your settings and used by the backend automatically!