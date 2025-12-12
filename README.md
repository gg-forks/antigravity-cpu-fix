# Antigravity CPU Fix (Balanced)

Make Antigravity’s agent UI stop burning CPU, with safe rollbacks and lean LSP settings. This is the balanced version (keeps the agent usable, ~1s cadence), not the ultra-aggressive 5s throttles. Backups are automatic.

## Quick Start (layman)
```bash
git clone https://github.com/sgpascoe/antigravity-cpu-fix.git
cd antigravity-cpu-fix
chmod +x fix-antigravity-balanced.sh auto-repatch-and-launch.sh

# Apply the balanced patch once (backups auto-created)
sudo ./fix-antigravity-balanced.sh

# Launch Antigravity with auto-repatch + devtools port (9223)
./auto-repatch-and-launch.sh
```

## Rollback (simple)
Backups live in `/tmp/antigravity_backups_YYYYMMDD_HHMMSS/`.
```bash
TS=<your backup timestamp>
sudo cp /tmp/antigravity_backups_$TS/main.js.backup /usr/share/antigravity/resources/app/out/jetskiAgent/main.js
sudo cp /tmp/antigravity_backups_$TS/workbench.desktop.main.js.backup /usr/share/antigravity/resources/app/out/vs/workbench/workbench.desktop.main.js
cp /tmp/antigravity_backups_$TS/settings.json.backup ~/.config/Antigravity/User/settings.json
```
Or reinstall Antigravity if you prefer.

## What it changes (balanced patch)
- `jetskiAgent/main.js` (agent renderer):
  - `requestAnimationFrame` → `setTimeout(..., 1000)` (1 FPS)
  - `setTimeout`: 0–200ms → 1200ms; 200–1000ms → 1500ms
  - `setInterval` <1000ms → 1200–1500ms
  - `queueMicrotask` → `setTimeout(..., 50ms)`
- Settings (`~/.config/Antigravity/User/settings.json`):
  - Watch/search excludes for node_modules, .git, venv, dist/build, caches
  - TS server watch opts: `useFsEvents`, dynamic polling, async dir watch; `maxTsServerMemory: 2048`
  - Python analysis: no indexing, no auto-import completions, workspace diagnostics
- Optional launcher flags:
  - `--remote-debugging-port=9223 --remote-allow-origins=* --user-data-dir=/tmp/antigravity_devtools --disable-features=RendererCodeIntegrity`

## Why this helps
- Root cause: jetski agent UI was repainting/reflowing continuously (Preact DOM reconciliation + layout reads). Throttling those loops cuts renderer CPU.
- Remaining load scales with the number of workspaces (multiple LSP/tsserver processes). The settings tweaks lower their overhead but don’t eliminate per-workspace cost.

## Requirements
- Linux, Antigravity at `/usr/share/antigravity/`, `sudo`, `python3`.

## Monitoring
```bash
ps aux | grep antigravity | grep -v grep | awk '{sum+=$3} END {print "Total CPU: " sum"%"}'
```
Expected idle after patch: renderer low; total CPU depends on how many workspaces/LSPs you run.

## Limitations
- Updates overwrite bundled JS; rerun the patch or use `auto-repatch-and-launch.sh`.
- Multi-workspace setups still spawn multiple LSPs; close unneeded windows to reduce load.
- UI cadence ~1s in the agent panel (by design for this balanced mode).

## Files you care about
- `fix-antigravity-balanced.sh` — apply patch once (backups auto)
- `auto-repatch-and-launch.sh` — reapply after updates + launch with devtools port
- `fix-antigravity.sh` — original scripted flow (kept for completeness)
- `archive/` — deep-dive docs and legacy variants (not needed for basic use)
