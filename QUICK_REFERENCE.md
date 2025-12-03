# Mercury Coder Quick Reference

## 🚀 Starting Mercury

```bash
# Start Mercury (auto-stops if already running)
mercury start

# Or use the shortcut
mercury-coder
```

## 🛑 Stopping Mercury

```bash
# Stop Mercury
mercury stop

# Or use the shortcut
mercury-stop
```

## 🔄 Restarting Mercury

```bash
# Clean restart
mercury restart
```

## 📊 Check Status

```bash
# See what's running
mercury status
```

## 📝 View Logs

```bash
# Show available logs
mercury logs

# View specific logs
cd /home/mercury/Documents/Projects/mercury-open-code/mercury-coder
tail -f opencode-backend.log
tail -f frontend.log
tail -f electron.log

# View all logs
tail -f *.log
```

## 🔧 Troubleshooting

### Mercury won't start
```bash
# Check status
mercury status

# Stop everything
mercury stop

# Wait a moment
sleep 3

# Try again
mercury start
```

### Ports still in use
```bash
# Force kill processes on ports
lsof -ti:4096 | xargs kill -9
lsof -ti:5173 | xargs kill -9
lsof -ti:8001 | xargs kill -9

# Then start
mercury start
```

### Clear all Mercury processes
```bash
# Nuclear option - kill everything
pkill -9 -f "mercury"
pkill -9 -f "opencode"
pkill -9 -f "electron.*mercury"

# Clean up ports
lsof -ti:4096,5173,8001 | xargs kill -9

# Start fresh
mercury start
```

## 📍 Access URLs

- **Frontend UI**: http://localhost:5173
- **Backend API**: http://127.0.0.1:4096
- **Whisper API**: http://127.0.0.1:8001 (if enabled)

## 🗂️ Project Structure

```
mercury-open-code/
├── mercury-coder/              # Main application
│   ├── src/                    # Vue frontend
│   ├── electron/               # Electron main process
│   ├── backend-whisper/        # Speech-to-text service
│   └── start.sh               # Startup script
└── opencode-backend/           # OpenCode backend
    └── packages/opencode/      # Backend source
```

## 💾 Session Management

### How Sessions Work
- Sessions are stored by OpenCode backend
- Each session has a unique ID (e.g., `ses_xxx...`)
- Messages are cached per session for fast switching
- Sessions persist between restarts

### Session Switching
1. Click on a session tab to switch
2. Messages load instantly (cached)
3. Switch as fast as you want - no data loss
4. Send messages and switch - everything persists

## 🎯 Pro Tips

### Quick Aliases
Add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias mc='mercury start'
alias mcs='mercury status'
alias mcl='mercury logs'
alias mck='mercury stop'
```

### Auto-Start on Login
Create `~/.config/autostart/mercury-coder.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Mercury Coder
Exec=/usr/local/bin/mercury start
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
```

### Useful Commands
```bash
# Check if OpenCode is responding
curl http://127.0.0.1:4096/health

# Watch logs in real-time
cd mercury-coder && tail -f *.log

# Count active sessions
ls -l ~/.opencode/sessions/ | wc -l

# See all Mercury processes
ps aux | grep mercury
```

## 🐛 Common Issues

### Issue: Empty chat panel after switching
**Solution**: Already fixed! Messages now cached per session.

### Issue: "Already running" error
**Solution**: Already fixed! `mercury start` now auto-stops existing sessions.

### Issue: Port already in use
**Solution**: 
```bash
mercury stop
sleep 2
mercury start
```

### Issue: Frontend won't connect to backend
**Solution**: Check both are running:
```bash
mercury status
# Both OpenCode Backend and Frontend should show green
```

### Issue: Changes not showing
**Solution**: Hard refresh browser:
- Linux/Windows: `Ctrl + Shift + R`
- Mac: `Cmd + Shift + R`

## 📚 Documentation

- **Main README**: [README.md](README.md)
- **Global Commands**: [GLOBAL_COMMANDS.md](GLOBAL_COMMANDS.md)
- **Today's Changes**: [CHANGES_20251202.md](CHANGES_20251202.md)
- **Integration Notes**: [INTEGRATION_NOTES.md](INTEGRATION_NOTES.md)

## 🆘 Getting Help

1. Check status: `mercury status`
2. View logs: `mercury logs`
3. Try restart: `mercury restart`
4. Check this guide
5. Check detailed documentation

---

**Quick Start**: `mercury start`  
**Quick Stop**: `mercury stop`  
**Quick Status**: `mercury status`  
**Quick Help**: `mercury` (no arguments)
