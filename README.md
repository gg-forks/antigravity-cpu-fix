# Antigravity CPU Fix

**TL;DR:** Antigravity wastes insane CPU because the agent panel repaints at 60 FPS even when idle — that's 3,000+ function calls/second for nothing! This fix slows it to 1 refresh/second (still usable) and cuts LSP background load. CPU drops from 80%+ to ~20% idle. Backups auto; undo easy.

Antigravity feels slow because the agent panel constantly does small background tasks — it redraws and measures parts of the UI many times per second, which eats CPU even when you're not interacting with it. Also, every open project can launch a language server that uses CPU in the background, so multiple projects multiply the load. This patch reduces that constant background work so the app becomes responsive again; backups are automatic and rollback is a single copy.

## What this does (plain English)
- Slows the agent UI so it stops hammering the CPU:
  - `requestAnimationFrame` → `setTimeout(..., 1000)` (~1 FPS)
  - `setTimeout`: 0–200ms → 1200ms; 200–1000ms → 1500ms
  - `setInterval` <1000ms → 1200–1500ms
  - `queueMicrotask` → `setTimeout(..., 50ms)` (Removed aggressive throttling in recent patch)
- Lowers background LSP churn:
  - Watch/search excludes for node_modules, .git, venv, dist/build, caches
  - TS server uses fs events + dynamic polling; memory cap 2048
  - Python: no indexing, no auto-import completions, workspace diagnostics
- Launcher adds devtools port 9223 and auto-repatch after updates.

## Quick start

### Install
1. **Analyze Environment** (Dry Run):
   ```bash
   make doctor
   ```
2. **Optimize Settings** (Safe, User-space only):
   ```bash
   make 1_optimize_settings
   ```
3. **Patch Code** (Req. Sudo):
   ```bash
   # This will create .bak backups of modified files
   sudo make 2_patch_code
   ```
4. **Update Integrity** (Req. Sudo):
   ```bash
   sudo make 3_update_integrity
   ```

### Rollback
If you need to restore original files:
```bash
sudo make rollback
```

## What to expect
- Agent panel updates ~1s by design.
- Renderer CPU should drop; total CPU still scales with how many workspaces/LSPs you keep open.

## Backup Strategy
- **In-place backups**: The patch scripts create `.bak` files next to the original files (e.g., `main.js.bak`).
- **Archive folder**: Contains the original version 1.104.0 source files for reference and rollback.
- **Rollback**: Use `make rollback` for instructions, or manually copy from `archive/ag-1.104.0/`.

## Files you need
- `make` — Use the Makefile targets to run tools.
- `archive/` — Contains original version 1.104.0 files for reference and rollback.

## Limits
- Antigravity updates overwrite bundled JS; rerun the patch.
- Multiple projects still spawn multiple LSPs; that load is per workspace.
- Everything is local and backed up; undo is copying the backups back.

## Verify files
Scripts only modify Antigravity's local files and your settings; no network calls or data collection.
