# Mercury Coder

An AI-powered code editor built with Electron, Vue.js, and Amazon Bedrock. Similar to Cursor and Kite Code, but powered by AWS Bedrock.

## Features

- 🎨 **Custom Frameless Window** - Beautiful custom title bar with window controls
- 📁 **File Manager** - Navigate your project files with a tree view
- 💻 **Monaco Editor** - Professional code editor (same as VS Code)
- 🖥️ **Integrated Terminal** - Built-in terminal using xterm.js
- 🤖 **AI Chat Assistant** - Powered by Amazon Bedrock (Claude)
- 🧠 **Delegate Agent Panel** - Launch autonomous coding runs, monitor plans, search indexed context, and review tool logs directly in the UI
- 💾 **Project Management** - SQLite database to track and manage projects
- 🌙 **Dark Theme** - Modern dark UI optimized for coding

## Architecture

```
┌─────────────────────────────────────────┐
│  Electron Main Process                  │
│  ├── Window Management                  │
│  ├── SQLite Database                    │
│  └── Python Backend Process             │
└─────────────────────────────────────────┘
              ↕ IPC
┌─────────────────────────────────────────┐
│  Vue.js Renderer Process                │
│  ├── Monaco Editor                      │
│  ├── File Manager                       │
│  ├── Terminal (xterm.js)                │
│  └── AI Chat Window                     │
└─────────────────────────────────────────┘
              ↕ HTTP
┌─────────────────────────────────────────┐
│  Python FastAPI Backend                 │
│  └── Amazon Bedrock Integration         │
└─────────────────────────────────────────┘
```

## Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.8+
- **AWS Account** with Bedrock access
- **AWS Credentials** configured

## Setup

### 1. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Install Python dependencies
cd backend
pip install -r requirements.txt
```

### 2. Configure AWS Bedrock

1. Copy the example environment file:
```bash
cp backend/.env.example backend/.env
```

2. Edit `backend/.env` with your AWS credentials:
```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
PORT=8000
```

3. Make sure you have access to the Bedrock model in your AWS account. You may need to request access in the AWS Console.

### 3. Run the Application

**Development Mode:**
```bash
# Terminal 1: Start Python backend
cd backend
python main.py

# Terminal 2: Start Electron app
npm run dev
```

The app will automatically:
- Start the Vue.js dev server on port 5173
- Launch Electron when the dev server is ready
- Connect to the Python backend on port 8000

## Delegate Agent Workflow

1. **Index your project**: Open a project in the app and click *Index Project* inside the Delegate Agent panel (right column). This builds a searchable snapshot via the new FastAPI `/api/agent/context/*` endpoints.
2. **Launch a task**: Describe a goal (e.g., “add unit tests for the context indexer”) and press *Run Agent*. The panel streams plan output, tool usage, and status updates coming from `/api/agent/run`.
3. **Search indexed context**: Use the inline search box to instantly retrieve snippets from the indexed files—perfect for grounding prompts before launching a run.
4. **Monitor tasks**: Recent runs are listed with timestamps and status chips. Selecting a task reveals the generated plan plus the structured event log recorded by the orchestrator.
5. **Optional CLI demo**: The helper script `scripts/run_agent_demo.py` can trigger agent runs outside the UI:
   ```bash
   python scripts/run_agent_demo.py \
     --goal "Summarize the repo layout" \
     --project-path /absolute/path/to/project
   ```

## Building for Production

```bash
# Build for your platform
npm run build          # Builds for current platform
npm run build:win      # Windows
npm run build:mac      # macOS
npm run build:linux    # Linux
```

## Project Structure

```
mercury-coder/
├── electron/          # Electron main process
│   ├── main.js       # Main entry point
│   ├── preload.js    # Preload script
│   └── database.js   # SQLite database class
├── src/              # Vue.js frontend
│   ├── components/   # Vue components
│   ├── stores/       # Pinia stores
│   └── composables/  # Vue composables
├── backend/          # Python FastAPI backend
│   ├── main.py      # FastAPI server
│   └── requirements.txt
└── package.json
```

## Usage

1. **Open a Project**: Click "Open Project" on the welcome screen to select a folder
2. **Navigate Files**: Use the file manager on the left to browse your project
3. **Edit Code**: Click files to open them in the Monaco editor
4. **Chat with AI**: Use the chat window on the right to ask questions about your code
5. **Terminal**: Use the integrated terminal at the bottom for commands

## Configuration

### Changing the Bedrock Model

Edit `backend/.env` and set `BEDROCK_MODEL_ID` to your preferred model:
- `anthropic.claude-3-sonnet-20240229-v1:0` (default)
- `anthropic.claude-3-opus-20240229-v1:0`
- `anthropic.claude-3-haiku-20240307-v1:0`
- Or any other Bedrock model ID

### Customizing the UI

Edit `src/style.css` to change theme colors and styling.

## Development

### Adding New Features

- **Frontend Components**: Add to `src/components/`
- **Backend APIs**: Add endpoints to `backend/main.py`
- **IPC Handlers**: Add to `electron/main.js` and expose in `preload.js`

### Debugging

- **Electron DevTools**: Uncomment the line in `electron/main.js` to enable DevTools
- **Backend Logs**: Check the terminal where you run `python main.py`
- **Database**: Database file is stored in Electron's userData directory

### Testing

- Backend unit tests cover the delegate toolset and context indexer. Run them with:
  ```bash
  cd backend
  pytest
  ```
- Use `scripts/run_agent_demo.py` to run an end-to-end agent task against a live backend.

## Troubleshooting

### Backend Not Starting
- Make sure Python 3.8+ is installed
- Check that all dependencies are installed: `pip install -r backend/requirements.txt`
- Verify the backend port (8000) is not in use

### AWS Bedrock Errors
- Verify AWS credentials are correct
- Check that you have access to Bedrock in the AWS Console
- Ensure the model ID is correct and you have access to it

### Build Issues
- Make sure all dependencies are installed
- Check Node.js version (18+)
- Try deleting `node_modules` and reinstalling

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.






