#!/bin/bash
# Antigravity CPU Fix Rollback
# Undo the patch and restore backups
set -euo pipefail

BACKUP_DIR=""
if [ -d "/tmp/antigravity_backups_"* ]; then
    # Find the latest backup
    BACKUP_DIR=$(ls -td /tmp/antigravity_backups_* | head -1)
fi

echo "=== ANTIGRAVITY CPU FIX ROLLBACK ==="
if [ -z "$BACKUP_DIR" ]; then
    echo "❌ No backup directory found in /tmp/"
    echo "   (Backups are in /tmp/antigravity_backups_YYYYMMDD_HHMMSS/)"
    exit 1
fi

echo "Using backup: $BACKUP_DIR"
echo ""

# Check if Antigravity is running
if pgrep -f "/usr/share/antigravity/antigravity" > /dev/null 2>&1; then
    echo "⚠️  Antigravity is running. Closing it..."
    pkill -f "/usr/share/antigravity/antigravity" 2>/dev/null || true
    sleep 3
fi

# Restore files
echo "🔄 Restoring files..."
if [ -f "$BACKUP_DIR/main.js.backup" ]; then
    sudo cp "$BACKUP_DIR/main.js.backup" /usr/share/antigravity/resources/app/out/jetskiAgent/main.js
    echo "✓ Restored jetskiAgent/main.js"
fi

if [ -f "$BACKUP_DIR/workbench.desktop.main.js.backup" ]; then
    sudo cp "$BACKUP_DIR/workbench.desktop.main.js.backup" /usr/share/antigravity/resources/app/out/vs/workbench/workbench.desktop.main.js
    echo "✓ Restored workbench.desktop.main.js"
fi

if [ -f "$BACKUP_DIR/settings.json.backup" ]; then
    cp "$BACKUP_DIR/settings.json.backup" ~/.config/Antigravity/User/settings.json
    echo "✓ Restored settings.json"
fi

echo ""
echo "✅ ROLLBACK COMPLETE"
echo "You can now launch Antigravity normally."
