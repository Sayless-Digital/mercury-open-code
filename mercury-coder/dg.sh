#!/bin/bash

# VS Code Sync Diagnostic Script
# Checks for common sync corruption issues

echo "🔍 VS Code Sync Diagnostic"
echo "=========================="
echo ""

# Check sync directories
echo "📁 Sync Directories:"
if [ -d "$HOME/.config/Code/User/globalStorage" ]; then
    SIZE=$(du -sh "$HOME/.config/Code/User/globalStorage" 2>/dev/null | cut -f1)
    echo "   globalStorage: $SIZE (exists)"
else
    echo "   globalStorage: (not found)"
fi

if [ -d "$HOME/.config/Code/User/workspaceStorage" ]; then
    SIZE=$(du -sh "$HOME/.config/Code/User/workspaceStorage" 2>/dev/null | cut -f1)
    echo "   workspaceStorage: $SIZE (exists)"
else
    echo "   workspaceStorage: (not found)"
fi

# Check extensions
echo ""
echo "📦 Extensions:"
if [ -d "$HOME/.vscode/extensions" ]; then
    COUNT=$(find "$HOME/.vscode/extensions" -maxdepth 1 -type d | wc -l)
    SIZE=$(du -sh "$HOME/.vscode/extensions" 2>/dev/null | cut -f1)
    echo "   Extensions directory: $SIZE ($COUNT items)"
else
    echo "   Extensions directory: (not found)"
fi

# Check cache
echo ""
echo "🗑️  Cache:"
if [ -d "$HOME/.cache/Code" ]; then
    SIZE=$(du -sh "$HOME/.cache/Code" 2>/dev/null | cut -f1)
    echo "   Code cache: $SIZE (exists)"
else
    echo "   Code cache: (not found)"
fi

# Check file watchers
echo ""
echo "👀 File Watchers:"
if [ -f /proc/sys/fs/inotify/max_user_watches ]; then
    WATCHES=$(cat /proc/sys/fs/inotify/max_user_watches)
    INSTANCES=$(cat /proc/sys/fs/inotify/max_user_instances 2>/dev/null || echo "N/A")
    echo "   max_user_watches: $WATCHES"
    echo "   max_user_instances: $INSTANCES"
    
    if [ "$WATCHES" -lt 524288 ]; then
        echo "   ⚠️  Warning: Low watch limit may cause sync issues"
    fi
else
    echo "   inotify: (not available)"
fi

# Check running processes
echo ""
echo "🔄 Running Processes:"
CODE_PROCS=$(pgrep -f "code" 2>/dev/null | wc -l)
CODE_SERVER_PROCS=$(pgrep -f "code-server" 2>/dev/null | wc -l)
echo "   code processes: $CODE_PROCS"
echo "   code-server processes: $CODE_SERVER_PROCS"

if [ "$CODE_PROCS" -gt 5 ] || [ "$CODE_SERVER_PROCS" -gt 5 ]; then
    echo "   ⚠️  Warning: Many processes may indicate stale instances"
fi

# Check for the specific error file
echo ""
echo "📄 Problem File Check:"
PROJECT_DIR="/home/mercury/Documents/Projects/Mercury Coder"
if [ -f "$PROJECT_DIR/src/components/AgentPanel.vue" ]; then
    SIZE=$(ls -lh "$PROJECT_DIR/src/components/AgentPanel.vue" | awk '{print $5}')
    LINES=$(wc -l < "$PROJECT_DIR/src/components/AgentPanel.vue" 2>/dev/null || echo "?")
    echo "   AgentPanel.vue: $SIZE ($LINES lines)"
    
    # Check if file is actually large
    ACTUAL_SIZE=$(stat -f%z "$PROJECT_DIR/src/components/AgentPanel.vue" 2>/dev/null || \
                  stat -c%s "$PROJECT_DIR/src/components/AgentPanel.vue" 2>/dev/null || \
                  echo "0")
    if [ "$ACTUAL_SIZE" -gt 52428800 ]; then  # 50MB in bytes
        echo "   ⚠️  File is actually > 50MB - may need investigation"
    else
        echo "   ✓ File size is normal - sync corruption confirmed"
    fi
else
    echo "   AgentPanel.vue: (not found)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Run ./fix_vscode_sync.sh to fix these issues"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"




























