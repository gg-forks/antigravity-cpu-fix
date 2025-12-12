# Antigravity CPU Fix

Antigravity feels slow because the agent panel constantly does small background tasks — it redraws and measures parts of the UI many times per second, which eats CPU even when you're not interacting with it. Also, every open project can launch a language server that uses CPU in the background, so multiple projects multiply the load. This patch reduces that constant background work so the app becomes responsive again; backups are automatic and rollback is a single copy.

## What this does (plain English)
- Slows the agent UI so it stops hammering the CPU:
  - `requestAnimationFrame` → `setTimeout(..., 1000)` (~1 FPS)
  - `setTimeout`: 0–200ms → 1200ms; 200–1000ms → 1500ms
  - `setInterval` <1000ms → 1200–1500ms
  - `queueMicrotask` → `setTimeout(..., 50ms)`
- Lowers background LSP churn:
  - Watch/search excludes for node_modules, .git, venv, dist/build, caches
  - TS server uses fs events + dynamic polling; memory cap 2048
  - Python: no indexing, no auto-import completions, workspace diagnostics
- Launcher adds devtools port 9223 and auto-repatch after updates.

## Quick start
```bash
git clone https://github.com/sgpascoe/antigravity-cpu-fix.git
cd antigravity-cpu-fix
chmod +x fix-antigravity-balanced.sh auto-repatch-and-launch.sh

# Apply (backups auto-created)
sudo ./fix-antigravity-balanced.sh

# Launch with auto-repatch + devtools port 9223
./auto-repatch-and-launch.sh
```

## Rollback
Backups: `/tmp/antigravity_backups_YYYYMMDD_HHMMSS/`
```bash
TS=<timestamp>
sudo cp /tmp/antigravity_backups_$TS/main.js.backup /usr/share/antigravity/resources/app/out/jetskiAgent/main.js
sudo cp /tmp/antigravity_backups_$TS/workbench.desktop.main.js.backup /usr/share/antigravity/resources/app/out/vs/workbench/workbench.desktop.main.js
cp /tmp/antigravity_backups_$TS/settings.json.backup ~/.config/Antigravity/User/settings.json
```
Or reinstall Antigravity.

## What to expect
- Agent panel updates ~1s by design.
- Renderer CPU should drop; total CPU still scales with how many workspaces/LSPs you keep open.

## Monitor
```bash
ps aux | grep antigravity | grep -v grep | awk '{sum+=$3} END {print "Total CPU: " sum"%"}'
```

## Files you need
- `fix-antigravity-balanced.sh` — apply once (auto backups)
- `auto-repatch-and-launch.sh` — reapply after updates and launch with devtools port
- `archive/` — everything else (old variants, monitor script, deep dive)

## Limits
- Antigravity updates overwrite bundled JS; rerun the patch or use the launcher.
- Multiple projects still spawn multiple LSPs; that load is per workspace.
- Everything is local and backed up; undo is copying the backups back.
