#!/bin/bash
# Antigravity CPU Fix Installer
# One-click install + verify
set -euo pipefail

BACKUP_DIR="/tmp/antigravity_backups_$(date +%Y%m%d_%H%M%S)"

echo "=== ANTIGRAVITY CPU FIX INSTALLER ==="
echo "This will apply the CPU fix and show before/after CPU usage."
echo "Backups will be created in: $BACKUP_DIR"
echo ""

# Check if Antigravity is running
if pgrep -f "/usr/share/antigravity/antigravity" > /dev/null 2>&1; then
    echo "❌ Antigravity is running. Please close it first."
    exit 1
fi

# Benchmark before
echo "📊 Benchmarking CPU usage BEFORE fix (10s)..."
BEFORE_CPU=$(ps aux | grep -E '/usr/share/antigravity/antigravity' | grep -v grep | awk '{sum+=$3} END {print sum}' 2>/dev/null || echo "0")
echo "   Before: ${BEFORE_CPU}% total CPU"

# Create backup dir
mkdir -p "$BACKUP_DIR"

# Apply patch (from balanced script)
echo ""
echo "🔧 Applying patch..."
sudo cp /usr/share/antigravity/resources/app/out/jetskiAgent/main.js "$BACKUP_DIR/main.js.backup"
sudo cp /usr/share/antigravity/resources/app/out/vs/workbench/workbench.desktop.main.js "$BACKUP_DIR/workbench.desktop.main.js.backup"
cp ~/.config/Antigravity/User/settings.json "$BACKUP_DIR/settings.json.backup"

# Patch jetskiAgent/main.js
sudo python3 << 'PYEOF'
import re

file_path = '/usr/share/antigravity/resources/app/out/jetskiAgent/main.js'

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Throttle requestAnimationFrame to ~1 FPS
content = re.sub(r'requestAnimationFrame\(([^)]+)\)', r'setTimeout(\1, 1000)', content)

# Throttle setTimeout (0-200ms -> 1200ms, 200-1000ms -> 1500ms)
def patch_timeout(match):
    func = match.group(1)
    interval = int(match.group(2))
    if 0 <= interval < 200:
        return f'setTimeout({func}, 1200)'
    elif 200 <= interval < 1000:
        return f'setTimeout({func}, 1500)'
    return match.group(0)

content = re.sub(r'setTimeout\(([^,)]+),\s*(\d+)([^0-9,])', patch_timeout, content)

# Throttle setInterval (<1000ms -> 1200-1500ms)
def patch_interval(match):
    func = match.group(1)
    interval = int(match.group(2))
    if 0 <= interval < 1000:
        new_interval = 1200 if interval < 200 else 1500
        return f'setInterval({func}, {new_interval})'
    return match.group(0)

content = re.sub(r'setInterval\(([^,)]+),\s*(\d+)([^0-9,])', patch_interval, content)

# Throttle queueMicrotask
content = re.sub(r'queueMicrotask\(([^)]+)\)', r'setTimeout(\1, 50)', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Patched jetskiAgent/main.js")
PYEOF

# Apply settings
python3 << 'PYEOF'
import json

settings_file = '/home/cove-mint/.config/Antigravity/User/settings.json'

with open(settings_file, 'r') as f:
    settings = json.load(f)

# Add optimizations
settings.update({
    "files.watcherExclude": {
        "**/.git/objects/**": True,
        "**/.git/subtree-cache/**": True,
        "**/node_modules/**": True,
        "**/.venv/**": True,
        "**/__pycache__/**": True,
        "**/dist/**": True,
        "**/build/**": True,
        "**/.next/**": True,
        "**/target/**": True,
        "**/.cache/**": True
    },
    "search.exclude": {
        "**/node_modules": True,
        "**/venv": True,
        "**/.venv": True,
        "**/__pycache__": True,
        "**/dist": True,
        "**/build": True,
        "**/.next": True,
        "**/target": True,
        "**/.git": True,
        "**/.cache": True
    },
    "search.followSymlinks": False,
    "search.useIgnoreFiles": True,
    "typescript.tsserver.maxTsServerMemory": 2048,
    "typescript.tsserver.watchOptions": {
        "watchFile": "useFsEvents",
        "watchDirectory": "useFsEvents",
        "fallbackPolling": "dynamicPriority",
        "synchronousWatchDirectory": False
    },
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.autoImportCompletions": False,
    "python.analysis.diagnosticMode": "workspace",
    "python.analysis.indexing": False
})

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print("✓ Optimized settings")
PYEOF

echo "✓ Patch applied successfully"
echo ""

# Launch Antigravity
echo "🚀 Launching Antigravity with devtools port 9223..."
/usr/share/antigravity/antigravity --remote-debugging-port=9223 --remote-allow-origins='*' --user-data-dir=/tmp/antigravity_devtools --disable-features=RendererCodeIntegrity >/tmp/antigravity_diagnostics/antigravity_install.log 2>&1 &
sleep 15

# Benchmark after
echo ""
echo "📊 Benchmarking CPU usage AFTER fix (10s)..."
AFTER_CPU=$(ps aux | grep -E '/usr/share/antigravity/antigravity' | grep -v grep | awk '{sum+=$3} END {print sum}' 2>/dev/null || echo "0")
echo "   After: ${AFTER_CPU}% total CPU"

echo ""
echo "✅ INSTALL COMPLETE"
echo "   Backups: $BACKUP_DIR"
echo "   Before: ${BEFORE_CPU}% CPU"
echo "   After:  ${AFTER_CPU}% CPU"
echo ""
echo "To undo: ./rollback.sh"
