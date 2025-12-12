# Antigravity CPU Fix

**TL;DR:** Antigravity wastes insane CPU because the agent panel repaints at 60 FPS even when idle — that's 3,000+ function calls/second for nothing! This fix slows it to 1 refresh/second (still usable) and cuts LSP background load. CPU drops from 80%+ to ~20% idle. Backups auto; undo easy.

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
chmod +x install.sh rollback.sh

# One-click install + verify (shows before/after CPU)
sudo ./install.sh

# To undo: ./rollback.sh
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
- `install.sh` — one-click install + verify (shows before/after CPU)
- `rollback.sh` — undo the patch
- `archive/` — everything else (old variants, monitor script, deep dive)

## Limits
- Antigravity updates overwrite bundled JS; rerun the patch or use the launcher.
- Multiple projects still spawn multiple LSPs; that load is per workspace.
- Everything is local and backed up; undo is copying the backups back.

## Verify files
Check integrity before running:
```bash
# install.sh
sha256sum install.sh  # 6db0c5c62b6e7900345e9f6b061acf32b960b9394f44c9ba93e5457e6aa4337e
# rollback.sh
sha256sum rollback.sh  # 114c7d00b9f08edffc23e488c81a450df2a2e54fa3d67d65eb2e36315ba59a7e
```
Scripts only modify Antigravity's local files and your settings; no network calls or data collection.
