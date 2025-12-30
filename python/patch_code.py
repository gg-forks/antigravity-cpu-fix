#!/usr/bin/env python3
import hashlib
import os
import re
import sys

# 1. Validation
if len(sys.argv) < 2:
    print("❌ Error: Missing Argument. Usage: patch_code.py <AG_DIR>")
    sys.exit(1)

base_dir = sys.argv[1]
file_path = os.path.join(base_dir, "resources/app/out/jetskiAgent/main.js")
print(f"Targeting: {file_path}")

try:
    with open(file_path, "rb") as f:
        content = f.read()
except FileNotFoundError:
    print(f"❌ Critical: Could not find main.js at {file_path}")
    sys.exit(1)

original_hash = hashlib.md5(content).hexdigest()

# --- STRATEGY: Runtime Hijack ---
# Injecting into globalThis ensures aliases like 'iur' or 'aur'
# still use our throttled versions.
polyfill = b"""{
  const _f = globalThis.fetch;
  if (_f) {
    globalThis.fetch = (u, o) => {
      if (typeof u === "string" && u.includes("antigravity")) {
        return Promise.reject(new TypeError("Blocked by Antigravity Patch"));
      }
      return _f(u, o);
    };
  }
  const _si = globalThis.setInterval;
  globalThis.setInterval = (fn, ms, ...args) => {
    if (typeof ms === 'number' && ms < 1000) ms = 1200;
    return _si(fn, ms, ...args);
  };
  globalThis.queueMicrotask = (fn) => setTimeout(fn, 1200);
  globalThis.requestAnimationFrame = (fn) => setTimeout(fn, 1200);
}
const __slowMo = (fn) => setTimeout(fn, 1200);
"""

# Check unique string to prevent stacking
if b"Blocked by Antigravity Patch" not in content:
    content = polyfill + b"\n" + content
    print("✓ Injected Runtime Hijack Polyfill")

# 5. Write changes
new_hash = hashlib.md5(content).hexdigest()

if new_hash != original_hash:
    try:
        with open(file_path, "wb") as f:
            f.write(content)
        print("✓ Patched successfully")
        print(f"  New Hash: {new_hash}")
    except Exception as e:
        print(f"❌ Error writing file: {e}")
        sys.exit(1)
else:
    print("⚠️  No changes made (Already patched or search string found)")
