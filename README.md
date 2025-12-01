# Mercury Open Code - Integrated AI Coding Platform

This repository combines **OpenCode** (AI coding agent backend) with **Mercury Coder** (Electron-based IDE frontend) to create a powerful, integrated AI-powered development environment.

## 🏗️ Project Structure

```
mercury-open-code/
├── opencode-backend/      # OpenCode AI agent backend
│   ├── packages/
│   │   ├── opencode/     # Core OpenCode logic
│   │   ├── sdk/          # SDKs (JS/Go)
│   │   ├── desktop/      # Web-based UI
│   │   └── ...
│   ├── package.json
│   └── turbo.json
│
├── mercury-coder/         # Mercury Coder Electron IDE
│   ├── electron/         # Electron main process
│   ├── src/              # Vue.js frontend
│   ├── backend/          # Python FastAPI backend
│   └── package.json
│
├── README.md             # This file
└── INTEGRATION_GUIDE.md  # Integration instructions
```

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+
- **Bun** 1.3+ (install via: `curl -fsSL https://bun.sh/install | bash`)
- **AWS Account** with Bedrock access (optional, for AI features)

### 1. Install Dependencies

```bash
# Install OpenCode backend dependencies
cd opencode-backend
bun install
cd ..

# Install Mercury Coder dependencies
cd mercury-coder
npm install
cd ..
```

### 2. Configure AI Provider (Optional)

The system uses OpenCode's configuration for AI providers:

```bash
# Create OpenCode config (optional - will use defaults if not set)
cd mercury-coder
cp config.json.example config.json
# Edit config.json to set your preferred AI model and provider
```

For AWS Bedrock specifically, see `opencode-backend/AWS_BEDROCK_SETUP.md`

### 3. Run Mercury Coder with Local OpenCode Backend

The easiest way to run the entire integrated system:

```bash
cd mercury-coder

# Using bash script (Linux/Mac):
./start.sh

# OR using Python script (cross-platform):
python3 start.py
```

This will:
1. Install OpenCode backend dependencies (if needed)
2. Start the local OpenCode backend on port 4096
3. Start the Vite dev server on port 5173
4. Launch the Electron desktop app

**Manual Start (Advanced):**

If you prefer to run components separately:

**Terminal 1: OpenCode Backend**
```bash
cd opencode-backend
bun run --cwd packages/opencode --conditions=browser src/index.ts serve --port 4096 --hostname 127.0.0.1 --print-logs
```

**Terminal 2: Mercury Coder Frontend & Electron**
```bash
cd mercury-coder
npm run dev
```

## 🎯 Components

### OpenCode Backend
- **Purpose**: AI coding agent with multi-provider support
- **Tech Stack**: TypeScript, Bun, SolidJS
- **Features**:
  - Multiple AI agents (build, plan, general, explore)
  - Multi-provider support (Anthropic, OpenAI, Google, AWS Bedrock)
  - Tool execution framework
  - Session management
  - WebSocket/SSE streaming

### Mercury Coder
- **Purpose**: Full-featured Electron-based IDE
- **Tech Stack**: Electron, Vue.js, Monaco Editor, Python FastAPI
- **Features**:
  - Monaco code editor (same as VS Code)
  - Integrated terminal (xterm.js)
  - File manager with tree view
  - AI chat assistant
  - Delegate agent panel
  - Project management with SQLite

## 🔌 Integration Status

Mercury Coder is now **fully integrated** with the local OpenCode backend:

✅ **What's Integrated:**
- Mercury Coder uses local `opencode-backend` instead of global installation
- Local SDK linked from `opencode-backend/packages/sdk/js`
- Electron app launches local OpenCode backend automatically
- Startup scripts handle the full stack
- Single unified development environment

🎯 **Benefits:**
- Full control over OpenCode backend source code
- Immediate access to OpenCode features and updates
- No version conflicts with global installations
- Easy debugging and customization
- Multiple AI providers (Anthropic, OpenAI, Google, AWS Bedrock)
- Advanced agent system (general, explore, build, plan)
- Tool execution framework
- WebSocket/SSE streaming support

## 📚 Documentation

- **OpenCode Documentation**: `opencode-backend/README.md`
- **Mercury Coder Documentation**: `mercury-coder/README.md`
- **Integration Guide**: `INTEGRATION_GUIDE.md` (see below)
- **OpenCode API Docs**: https://opencode.ai/docs
- **Contributing**: `opencode-backend/CONTRIBUTING.md`

## 🛠️ Development

### Working on OpenCode Backend
```bash
cd opencode-backend/packages/opencode
bun dev
```

### Working on Mercury Coder
```bash
cd mercury-coder
npm run dev
```

### Running Tests

**OpenCode Tests:**
```bash
cd opencode-backend
bun test
```

**Mercury Coder Tests:**
```bash
cd mercury-coder/backend
pytest
```

## 🔧 Configuration

### OpenCode Configuration
- Location: `opencode-backend/packages/opencode/opencode.json`
- Global config: `~/.config/opencode/`

### Mercury Coder Configuration
- AI model/provider: `mercury-coder/config.json` (follows OpenCode's config schema)
- Database: Stored in Electron userData directory
- Settings: Managed via UI (accessible from Settings panel)

## 🎨 Customization

### Change AI Provider (OpenCode)
Edit `opencode-backend/packages/opencode/opencode.json`:
```json
{
  "model": "anthropic/claude-sonnet-4",
  "provider": {
    "anthropic": {
      "apiKey": "your-key"
    }
  }
}
```

### Change UI Theme (Mercury Coder)
Edit `mercury-coder/src/style.css`

## 🚢 Building for Production

### Build OpenCode
```bash
cd opencode-backend/packages/opencode
bun run build
```

### Build Mercury Coder
```bash
cd mercury-coder
npm run build          # Current platform
npm run build:win      # Windows
npm run build:mac      # macOS
npm run build:linux    # Linux
```

## 🤝 Contributing

See `opencode-backend/CONTRIBUTING.md` for contribution guidelines.

## 📄 License

- **OpenCode**: MIT License (see `opencode-backend/LICENSE`)
- **Mercury Coder**: MIT License (see `mercury-coder/README.md`)

## 🆘 Support

- **OpenCode Discord**: https://discord.gg/opencode
- **Issues**: Create issues in the respective directories
- **Documentation**: https://opencode.ai/docs

## 🎯 Roadmap

- [ ] Complete OpenCode-Mercury Coder integration
- [ ] Unified authentication system
- [ ] Shared configuration management
- [ ] Mobile app support
- [ ] Cloud sync features
- [ ] Team collaboration features

---

**Getting Started**: See `INTEGRATION_GUIDE.md` for step-by-step integration instructions.