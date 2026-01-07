# Antigravity CPU Fix

**TL;DR:** Antigravity wastes insane CPU because the agent panel repaints at 60 FPS even when idle — that's 3,000+ function calls/second for nothing! This fix slows it to 1 refresh/second (still usable) and cuts LSP background load. CPU drops from 80%+ to ~20% idle. Backups auto; undo easy.

Antigravity feels slow because the agent panel constantly does small background tasks — it redraws and measures parts of the UI many times per second, which eats CPU even when you're not interacting with it. Also, every open project can launch a language server that uses CPU in the background, so multiple projects multiply the load. This patch reduces that constant background work so the app becomes responsive again; backups are automatic and rollback is a single copy.

## What this does (plain English)
- Slows the agent UI so it stops hammering the CPU:
  - `requestAnimationFrame` → `setTimeout(..., 1000)` (~1 FPS)
  - `setTimeout`: 0–200ms → 1200ms; 200–1000ms → 1500ms
  - `setInterval` <1000ms → 1200–1500ms
  - **Removed aggressive fetch blocking** that was interfering with chat functionality
- Lowers background LSP churn:
  - Watch/search excludes for node_modules, .git, venv, dist/build, caches
  - TS server uses fs events + dynamic polling; memory cap 2048
  - Python: no indexing, no auto-import completions, workspace diagnostics
- Launcher adds devtools port 9223 and auto-repatch after updates.

## Quick start

### Install
1. **Analyze Environment** (Dry Run):
