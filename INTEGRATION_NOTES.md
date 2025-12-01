# Local OpenCode Backend Integration

This document describes how Mercury Coder has been integrated with the local OpenCode backend.

## Changes Made

### 1. Package Configuration

**File: `mercury-coder/package.json`**
- Added local SDK dependency: `"@opencode-ai/sdk": "file:../opencode-backend/packages/sdk/js"`
- This links directly to the local OpenCode SDK instead of using the published npm package

### 2. Electron Main Process

**File: `mercury-coder/electron/main.js`**
- Modified `startOpencodeServer()` function to launch local backend
- Changed from spawning global `opencode` command to running:
  ```bash
  bun run --cwd packages/opencode --conditions=browser src/index.ts serve --port 4096 --hostname 127.0.0.1 --print-logs
  ```
- Backend path resolves to `../../opencode-backend` from electron directory
- Added fallback for `BUN_PATH` environment variable

### 3. Startup Scripts

**Files: `mercury-coder/start.sh` and `mercury-coder/start.py`**

Both scripts now:
1. Check for bun installation
2. Navigate to `opencode-backend` directory
3. Install dependencies if needed (`bun install`)
4. Start OpenCode backend using bun
5. Wait for backend to be ready on port 4096
6. Start Vite frontend on port 5173
7. Launch Electron app
8. Clean up all processes on exit

**Removed:**
- Python FastAPI backend (was on port 8000)
- Python backend dependencies and configuration

**Added:**
- OpenCode backend startup (port 4096)
- Bun dependency check
- Health check for OpenCode backend

### 4. Port Changes

| Service | Old Port | New Port |
|---------|----------|----------|
| Backend | 8000 (Python) | 4096 (OpenCode) |
| Frontend | 5173 | 5173 (unchanged) |
| Electron | N/A | N/A |

## Architecture

```
mercury-open-code/
├── opencode-backend/           # OpenCode source (runs on port 4096)
│   ├── packages/
│   │   ├── opencode/          # Main backend code
│   │   │   └── src/index.ts   # Entry point
│   │   └── sdk/js/            # SDK (linked to mercury-coder)
│   └── package.json
│
└── mercury-coder/              # Frontend IDE
    ├── electron/main.js        # Starts local OpenCode backend
    ├── src/                    # Vue.js frontend (port 5173)
    │   └── composables/
    │       ├── useOpencode.js  # Uses @opencode-ai/sdk
    │       └── ...
    ├── package.json            # Links to local SDK
    ├── start.sh               # Bash startup script
    └── start.py               # Python startup script
```

## Running the System

### Quick Start
```bash
cd mercury-coder
./start.sh          # Linux/Mac
# OR
python3 start.py    # Cross-platform
```

### Manual Start

**Terminal 1: OpenCode Backend**
```bash
cd opencode-backend
bun run --cwd packages/opencode --conditions=browser src/index.ts serve --port 4096 --hostname 127.0.0.1 --print-logs
```

**Terminal 2: Mercury Coder**
```bash
cd mercury-coder
npm run dev
```

## Development Workflow

### Making Changes to OpenCode Backend

1. Edit files in `opencode-backend/packages/opencode/src/`
2. Bun will hot-reload (if using `--watch`)
3. Changes are immediately available to Mercury Coder

### Making Changes to Frontend

1. Edit files in `mercury-coder/src/`
2. Vite will hot-reload
3. Electron will refresh automatically

### Making Changes to SDK

1. Edit files in `opencode-backend/packages/sdk/js/src/`
2. TypeScript will recompile
3. Restart Mercury Coder to pick up changes (or set up watch mode)

## Debugging

### OpenCode Backend Logs
- Location: `mercury-coder/opencode-backend.log`
- Real-time: Add `--print-logs` flag (already included)

### Frontend Logs
- Location: `mercury-coder/frontend.log`
- Browser console: Open DevTools in Electron (Ctrl+Shift+I)

### Electron Logs
- Location: `mercury-coder/electron.log`
- Main process console: Check terminal where electron started

## Configuration

### AI Model/Provider Configuration

Edit `mercury-coder/config.json`:
```json
{
  "model": "amazon-bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0",
  "$schema": "https://opencode.ai/config.json"
}
```

Supported providers:
- `anthropic/*` - Anthropic Claude models
- `openai/*` - OpenAI GPT models
- `google/*` - Google Gemini models
- `amazon-bedrock/*` - AWS Bedrock models

### Provider Credentials

OpenCode looks for credentials in:
1. Environment variables
2. `~/.config/opencode/` directory
3. Local `opencode.json` files

For AWS Bedrock specifically, see `opencode-backend/AWS_BEDROCK_SETUP.md`

## Troubleshooting

### "bun not found"
Install bun:
```bash
curl -fsSL https://bun.sh/install | bash
```

### "Port 4096 already in use"
Kill existing OpenCode process:
```bash
lsof -ti :4096 | xargs kill -9
```

### "Cannot find module '@opencode-ai/sdk'"
Reinstall dependencies:
```bash
cd mercury-coder
rm -rf node_modules
npm install
```

### OpenCode backend won't start
Check logs:
```bash
tail -f mercury-coder/opencode-backend.log
```

Common issues:
- Missing dependencies: Run `cd opencode-backend && bun install`
- Port conflict: Kill process on port 4096
- Invalid configuration: Check `config.json` syntax

## Next Steps

### Possible Enhancements

1. **Hot Reload for SDK Changes**
   - Set up watch mode for SDK builds
   - Auto-restart Electron on SDK changes

2. **Unified Configuration UI**
   - Add provider configuration to Settings panel
   - Manage API keys from UI

3. **Backend Process Management**
   - Add restart button in UI
   - Show backend status indicator
   - Display backend logs in UI

4. **Development Tools**
   - Add OpenCode API explorer
   - Integrate OpenCode debugging tools
   - Add performance monitoring

5. **Testing**
   - Add integration tests
   - Test multiple AI providers
   - Test error handling and recovery

## References

- [OpenCode Documentation](https://opencode.ai/docs)
- [OpenCode GitHub](https://github.com/sst/opencode)
- [Mercury Coder Documentation](mercury-coder/README.md)
- [Integration Guide](mercury-coder/IMPLEMENTATION_GUIDE.md)
