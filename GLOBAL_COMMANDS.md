# Global Mercury Coder Commands

Mercury Coder can be launched from anywhere in your terminal using global commands.

## 📋 Available Commands

### Primary Command: `mercury`

The main unified command for managing Mercury Coder:

```bash
mercury                # Show help and available commands
mercury start          # Start Mercury Coder (auto-stops if already running)
mercury stop           # Stop Mercury Coder
mercury restart        # Restart Mercury Coder
mercury status         # Check if Mercury Coder is running
mercury logs           # View available log files
```

### Shortcut Commands

Quick access commands for common operations:

```bash
mercury-coder          # Start Mercury Coder (same as mercury start)
mercury-stop           # Stop Mercury Coder (same as mercury stop)
```

## 🚀 Usage Examples

### Starting Mercury Coder

```bash
# Using the unified command
mercury start

# OR using the shortcut
mercury-coder
```

This will:
1. Check if Mercury is already running
2. Auto-stop existing session if running
3. Clean up any old processes
4. Start the local OpenCode backend (port 4096)
5. Start the Vite frontend (port 5173)
6. Launch the Electron desktop app

### Stopping Mercury Coder

```bash
# Using the unified command
mercury stop

# OR using the shortcut
mercury-stop
```

This will:
1. Kill all Mercury Coder processes
2. Free all ports (4096, 5173)
3. Clean up gracefully

### Restarting Mercury Coder

```bash
mercury restart
```

This performs a stop followed by a start.

### Checking Status

```bash
mercury status
```

Shows:
- Whether Mercury Coder is running
- Status of each component (backend, frontend)
- Access URLs

Example output:
```
================================
  Mercury Coder Status
================================

✓ Mercury Coder is running

  ● OpenCode Backend (port 4096)
  ● Frontend (port 5173)

Access:
  Frontend: http://localhost:5173
  Backend:  http://127.0.0.1:4096
```

### Viewing Logs

```bash
mercury logs
```

Shows available log files and how to view them:
- `opencode-backend.log` - OpenCode backend logs
- `frontend.log` - Vite frontend logs
- `electron.log` - Electron main process logs

## 🛠️ Technical Details

### Command Locations

All commands are installed in `/usr/local/bin/`:
- `/usr/local/bin/mercury` - Main unified command (6.3K)
- `/usr/local/bin/mercury-coder` - Start shortcut (1.5K)
- `/usr/local/bin/mercury-stop` - Stop shortcut (1.3K)

### What Gets Started

When you run `mercury start`, the system launches:

1. **OpenCode Backend** (Local)
   - Located in: `opencode-backend/packages/opencode/`
   - Runs via: `bun run --cwd packages/opencode --conditions=browser src/index.ts serve`
   - Port: 4096
   - Protocol: HTTP/WebSocket

2. **Vite Frontend**
   - Located in: `mercury-coder/src/`
   - Runs via: `npm run dev:vite`
   - Port: 5173
   - Hot reload enabled

3. **Electron Desktop App**
   - Main process: `mercury-coder/electron/main.js`
   - Runs via: `npm run dev:electron`
   - Opens the desktop window

### What Gets Stopped

When you run `mercury stop`, the system kills:

1. **Process Patterns**:
   - `mercury-coder`
   - `npm.*dev.*mercury`
   - `electron.*mercury-coder`
   - `node_modules/.bin/vite`
   - `concurrently`
   - `bun.*opencode.*serve`
   - `bun run.*src/index.ts`

2. **Ports**:
   - 4096 (OpenCode backend)
   - 5173 (Vite frontend)
   - 8001 (Whisper, if used)
   - 8000 (Old Python backend, if any)

## 🔧 Installation

These commands are already installed if you followed the setup. If you need to reinstall:

```bash
# The commands are in /usr/local/bin/ and require sudo to modify
# They were created during the integration setup

# To verify installation:
which mercury
which mercury-coder
which mercury-stop

# To update, edit the files directly:
sudo nano /usr/local/bin/mercury
sudo nano /usr/local/bin/mercury-coder
sudo nano /usr/local/bin/mercury-stop

# Make sure they're executable:
sudo chmod +x /usr/local/bin/mercury*
```

## 📝 Configuration

The commands use these paths (edit in the scripts if needed):

```bash
PROJECT_DIR="/home/mercury/Documents/Projects/mercury-open-code/mercury-coder"
```

If you move the project, update this path in:
- `/usr/local/bin/mercury`
- `/usr/local/bin/mercury-coder`

## 🐛 Troubleshooting

### "Command not found"

```bash
# Check if commands are in PATH
echo $PATH | grep /usr/local/bin

# Verify commands exist
ls -lh /usr/local/bin/mercury*

# Make sure they're executable
sudo chmod +x /usr/local/bin/mercury*
```

### "Already running" behavior

As of the latest update, `mercury start` automatically stops any existing session before starting a new one. You no longer need to manually stop first.

```bash
# This now works even if Mercury is already running
mercury start

# But you can still manually stop if needed
mercury stop
sleep 2
mercury start
```

### Ports still in use

```bash
# Manual port cleanup
lsof -ti:4096 | xargs kill -9
lsof -ti:5173 | xargs kill -9

# Then try starting again
mercury start
```

### Check what's actually running

```bash
# Check processes
ps aux | grep mercury
ps aux | grep opencode
ps aux | grep electron

# Check ports
lsof -i :4096
lsof -i :5173
```

## 🎯 Tips

### Quick Start After Boot

Add to your `.bashrc` or `.zshrc`:

```bash
alias mc='mercury start'
alias mcs='mercury status'
alias mcl='mercury logs'
```

### Auto-Start on Login

Create a systemd user service or add to your desktop startup applications:

```bash
# Add to ~/.config/autostart/mercury-coder.desktop
[Desktop Entry]
Type=Application
Name=Mercury Coder
Exec=/usr/local/bin/mercury start
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
```

### Running in Background

The commands already run in the background. Use `mercury status` to check if it's running.

### Viewing Real-Time Logs

```bash
cd /home/mercury/Documents/Projects/mercury-open-code/mercury-coder

# View all logs
tail -f *.log

# View specific log
tail -f opencode-backend.log
```

## 📚 Related Documentation

- [README.md](README.md) - Main project documentation
- [INTEGRATION_NOTES.md](INTEGRATION_NOTES.md) - Integration details
- [mercury-coder/start.sh](mercury-coder/start.sh) - Startup script source

## 🆘 Support

If you encounter issues with the global commands:

1. Check the status: `mercury status`
2. View logs: `mercury logs`
3. Try a clean restart: `mercury stop && sleep 3 && mercury start`
4. Check the troubleshooting section above
5. Review the actual startup script: `mercury-coder/start.sh`

---

**Quick Reference:**
- Start: `mercury start` or `mercury-coder`
- Stop: `mercury stop` or `mercury-stop`
- Status: `mercury status`
- Restart: `mercury restart`
- Help: `mercury`
