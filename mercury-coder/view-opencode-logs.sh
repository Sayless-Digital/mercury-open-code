#!/bin/bash
# Quick script to view OpenCode logs

LOG_DIR="$HOME/.local/share/opencode/log"
LATEST_LOG=$(find "$LOG_DIR" -name "*.log" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)

if [ -z "$LATEST_LOG" ]; then
    echo "No OpenCode log files found in $LOG_DIR"
    exit 1
fi

echo "Viewing latest OpenCode log: $LATEST_LOG"
echo "Press Ctrl+C to exit"
echo ""
echo "=== Last 50 lines ==="
tail -50 "$LATEST_LOG"

echo ""
echo "=== Following log (live updates) ==="
tail -f "$LATEST_LOG"

