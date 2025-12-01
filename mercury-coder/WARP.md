# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Mercury Coder is an AI-powered code editor built with Electron, Vue.js, and Amazon Bedrock (Claude). It features a delegate agent system for autonomous coding tasks with multi-agent orchestration.

## Common Development Commands

### Setup
```bash
# Install Node.js dependencies
npm install

# Install Python dependencies
cd backend
pip install -r requirements.txt
cd ..

# Configure AWS Bedrock
cp backend/.env.example backend/.env
# Edit backend/.env with your BEDROCK_API_KEY
```

### Running the Application

#### Development Mode (Linux/macOS)
```bash
./start.sh
# This script:
# - Checks and kills existing processes on ports 8000, 5173
# - Starts Python backend (port 8000)
# - Starts Vite dev server (port 5173)
# - Launches Electron desktop app
# Press Ctrl+C to stop all services
```

#### Manual Development Mode
```bash
# Terminal 1: Start Python backend
cd backend
python3 main.py

# Terminal 2: Start Electron app with Vite
npm run dev
```

### Testing

```bash
# Run backend tests
cd backend
pytest

# Run tests with the helper script
python3 run_tests.py

# Run agent demo (end-to-end test)
python3 scripts/run_agent_demo.py \
  --goal "Summarize the repo layout" \
  --project-path /absolute/path/to/project
```

### Building

```bash
# Build for current platform
npm run build

# Platform-specific builds
npm run build:win      # Windows
npm run build:mac      # macOS
npm run build:linux    # Linux
```

### Rebuilding Native Modules

If you encounter native module errors (better-sqlite3, node-pty):
```bash
npm run postinstall
# or manually:
npx electron-rebuild -f -w better-sqlite3 node-pty
```

## Architecture Overview

### Three-Tier Architecture

**1. Electron Main Process** (`electron/`)
- `main.js`: Window management, IPC handlers, backend HTTP proxying
- `preload.js`: Context bridge for secure renderer-to-main communication
- `database.js`: SQLite database for project management

**2. Vue.js Renderer Process** (`src/`)
- **Components**: Monaco editor, file manager, terminal (xterm.js), chat panel
- **Stores** (Pinia): project, editor, chat, settings, memory, models
- **Composables**: Reusable UI logic (keyboard shortcuts, menu actions, theme, window controls)

**3. Python FastAPI Backend** (`backend/`)
- `main.py`: REST API and SSE streaming endpoints
- Multi-agent orchestration system
- Amazon Bedrock integration
- Context indexing and memory management

### Multi-Agent System

The backend uses a sophisticated multi-agent architecture:

```
OrchestratorAgent (Coordinator)
├── PlannerAgent - Creates execution plans
├── ResearcherAgent - Code exploration and analysis
├── CoderAgent - Code generation and modification
└── AnalyzerAgent - Validation and quality checks
```

**Supporting Components:**
- `AgentExecutor`: LLM invocation + tool execution loop
- `TaskRouter`: Routes simple tasks directly to specialized agents
- `StatusEmitter`: Streams workflow status updates to UI
- `FeedbackLoopManager`: Auto-refinement with retries
- `ProactiveSearchManager`: Pre-task context gathering
- `LoopDetector`: Prevents infinite loops
- `ToolConflictDetector`: Manages parallel tool execution

### Key Backend Modules

**`agents/`** - Multi-agent orchestration system
- `orchestrator.py`: Main workflow coordinator (1163 lines - complex!)
- `planner.py`, `researcher.py`, `coder.py`, `analyzer.py`: Specialized agents
- `executor.py`: LLM + tool execution loop with retry logic
- `task_classifier.py`: Classifies task complexity
- `orchestration/`: WorkflowManager, TaskRouter, StatusEmitter, FollowUpDetector

**`tools/`** - Tool system for agent actions
- `definitions.py`: Tool definitions for Claude's native tool calling
- `executor.py`: Tool execution engine
- `ast_tools.py`, `ast_editor.py`: AST-based code manipulation
- `diff_engine.py`: Code diff generation
- `code_validator.py`: Syntax and import validation

**`context/`** - Code context management
- `indexer.py`: Project indexing (supports up to 4000 files)
- `file_graph.py`: Dependency graph for files
- `pattern_matcher.py`: Pattern-based code search

**`memory/`** - Agent memory system
- `manager.py`: Hybrid search (vector + keyword) over memories
- `vector_store.py`: ChromaDB for semantic search
- `database.py`: SQLite for structured storage
- `history_summarizer.py`: Conversation summarization

### API Endpoints

**Chat Endpoints:**
- `POST /api/chat/stream` - SSE streaming chat with Claude
- `POST /api/chat/conversation` - Store conversation message
- `GET /api/chat/conversations/{project_path}` - Get conversation history

**Agent Endpoints:**
- `POST /api/agent/run` - Launch autonomous agent task
- `GET /api/agent/tasks` - List recent tasks
- `GET /api/agent/tasks/{task_id}` - Get task details
- `POST /api/agent/context/index` - Index project files
- `POST /api/agent/context/search` - Search indexed context

**Memory Endpoints:**
- `POST /api/memory/store` - Store agent memory
- `GET /api/memory/search` - Search memories
- `GET /api/memory/tasks/{project_path}` - Get task summaries

## Development Notes

### Project Structure
```
mercury-coder/
├── electron/          # Main process, preload, database
├── src/               # Vue.js frontend
│   ├── components/   # UI components
│   ├── stores/       # Pinia state management
│   ├── composables/  # Reusable composition functions
│   └── utils/        # Helper utilities
├── backend/          # Python FastAPI backend
│   ├── agents/       # Multi-agent system
│   ├── tools/        # Agent tools
│   ├── context/      # Context indexing
│   ├── memory/       # Memory system
│   └── tests/        # Backend tests
└── scripts/          # Helper scripts
```

### Configuration Files
- `backend/.env`: AWS Bedrock API configuration (not in git)
- `backend/.env.example`: Template for API configuration
- `package.json`: Node.js dependencies and build scripts
- `vite.config.js`: Vite dev server configuration (port 5173)
- `electron/database.js`: SQLite database path in Electron userData

### Agent Workflow

When you index a project and run an agent task:

1. **Indexing**: `ProjectIndexer` scans files, builds search index, creates file dependency graph
2. **Task Launch**: User provides goal → `OrchestratorAgent` starts workflow
3. **Planning**: `PlannerAgent` creates structured plan with tasks
4. **Execution**: Orchestrator routes tasks to specialized agents
5. **Monitoring**: Status updates stream via SSE to UI
6. **Memory**: Results stored in vector + keyword database for future tasks

### Key Design Patterns

- **Strategy Pattern**: Different agents for different task types
- **Observer Pattern**: StatusEmitter broadcasts workflow updates
- **Factory Pattern**: AgentConfig standardizes agent initialization
- **Hybrid Search**: Combines vector (semantic) and keyword search for memory retrieval

### Known Issues & Warnings

From `AGENT_ARCHITECTURE_REVIEW.md`:
- `orchestrator.py` is very large (1163 lines) - be careful when modifying
- Thread safety issues exist in `_proactive_cache` - avoid concurrent access
- Error handling is inconsistent across agents - use `AgentError.to_dict()` format
- Context is passed as `Dict[str, Any]` - no type safety, validate carefully
- Memory caches can grow unbounded in long sessions

### When Adding New Features

**New Frontend Components**: Add to `src/components/`, use Pinia stores for state
**New Backend APIs**: Add endpoints to `backend/main.py`, follow existing patterns
**New Agent Tools**: Add to `backend/tools/definitions.py`, implement in `ToolExecutor`
**New IPC Handlers**: Add to `electron/main.js`, expose in `preload.js`

### Debugging

**Backend Logs**: Check `backend.log` and `backend/debug_tools.log`
**Frontend Logs**: Check `frontend.log` and browser console
**Electron Logs**: Check `electron.log`
**Enable DevTools**: Uncomment line ~194 in `electron/main.js`

### Model Configuration

Default model: `anthropic.claude-3-sonnet-20240229-v1:0`

Change in `backend/.env`:
- `anthropic.claude-3-opus-20240229-v1:0` - Most capable
- `anthropic.claude-3-haiku-20240307-v1:0` - Fastest

The backend automatically tries inference profiles and converse API for newer models (Claude Sonnet 4.5+).

### Port Requirements

- **8000**: Python FastAPI backend
- **5173**: Vite dev server
- Make sure these ports are available before running

The `start.sh` script automatically checks and kills existing processes on these ports.
