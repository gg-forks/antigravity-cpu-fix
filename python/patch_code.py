#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import shutil
import sys

if len(sys.argv) < 2:
    print("❌ Error: Missing Argument. Usage: patch_code.py <AG_SRC>")
    sys.exit(1)

ag_dir = sys.argv[1]

with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "version.txt")) as f:
    VERSION = f.read().strip()

# Detect layout
possible_paths = ["resources/app/out/jetskiAgent/main.js", "out/jetskiAgent/main.js"]

target_rel_path = None
for p in possible_paths:
    if os.path.exists(os.path.join(ag_dir, p)):
        target_rel_path = p
        break

if not target_rel_path:
    # Default to standard if neither found (will fail later but keeps logic simple)
    target_rel_path = "resources/app/out/jetskiAgent/main.js"

# The primary entry point - jetskiAgent/main.js
target_files = [target_rel_path]

# Path to archive for verification (relative to this script)
script_dir = os.path.dirname(os.path.abspath(__file__))
archive_base = os.path.join(script_dir, f"../archive/ag-{VERSION}/src")
archive_base = os.path.normpath(archive_base)
archive_main_js = os.path.join(archive_base, "resources/app/out/jetskiAgent/main.js")
archive_product_json = os.path.join(archive_base, "resources/app/product.json")

# Clean, effective patch based on original intent
# Direct function replacement without conditional checks or IIFE wrapper
polyfill = b"""// Antigravity CPU Fix v1.2 - UI throttling (based on README spec)
// Store originals before patching
const __raf = globalThis.requestAnimationFrame;
const __st = globalThis.setTimeout;
const __si = globalThis.setInterval;

// Throttle requestAnimationFrame to ~1 FPS (1000ms) for UI updates
if (__raf) globalThis.requestAnimationFrame = function(callback) {
    return __st(callback, 1000);
};

// Throttle setTimeout: 0-200ms -> 1200ms; 200-1000ms -> 1500ms
if (__st) globalThis.setTimeout = function(callback, ms, ...args) {
    if (typeof ms === 'number') {
        if (ms < 200) ms = 1200;
        else if (ms < 1000) ms = 1500;
    }
    return __st(callback, ms, ...args);
};

// Throttle setInterval: <1000ms -> 1200-1500ms
if (__si) globalThis.setInterval = function(callback, ms, ...args) {
    if (typeof ms === 'number' && ms < 1000) {
        ms = ms < 200 ? 1200 : 1500;
    }
    return __si(callback, ms, ...args);
};

// Optional: Selective fetch blocking for telemetry only
const __fetch = globalThis.fetch;
if (__fetch) globalThis.fetch = function(url, options) {
    if (typeof url === 'string') {
        // Only block telemetry/analytics, not general API calls
        if (url.includes('/telemetry') || url.includes('/analytics')) {
            return Promise.reject(new Error('Telemetry blocked'));
        }
    }
    return __fetch.call(this, url, options);
};
"""


def get_file_hash(file_path, algo="sha256"):
    """Calculate hash of a file."""
    h = hashlib.new(algo)
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def verify_checksum(target_path, archive_path, product_json_path):
    """Verify that target file matches archive checksum."""

    # First check if archive file exists
    if not os.path.exists(archive_path):
        print(f"⚠️  Archive file not found: {archive_path}")
        return False

    # Get hash of archive file
    archive_hash = get_file_hash(archive_path, "sha256")

    # Get hash of target file
    if not os.path.exists(target_path):
        print(f"⚠️  Target file not found: {target_path}")
        return False
    target_hash = get_file_hash(target_path, "sha256")

    # Compare hashes
    if archive_hash == target_hash:
        print(f"✓ Checksum verified: {os.path.basename(target_path)} matches archive")
        return True
    else:
        print(f"❌ Checksum mismatch for {os.path.basename(target_path)}:")
        print(f"  Archive: {archive_hash}")
        print(f"  Target:  {target_hash}")

        # Check product.json for expected checksum
        if os.path.exists(product_json_path):
            try:
                with open(product_json_path, "r") as f:
                    product_data = json.load(f)

                checksums = product_data.get("checksums", {})
                # Look for main.js checksum key
                target_key = None
                for key in checksums.keys():
                    if key.endswith("jetskiAgent/main.js"):
                        target_key = key
                        break

                if target_key:
                    expected_checksum = checksums[target_key]
                    print(f"  Expected (product.json): {expected_checksum}")

                    # Try to match format (could be base64 or hex)
                    if len(expected_checksum) == 64:  # SHA256 hex
                        if target_hash == expected_checksum:
                            print("✓ Target matches product.json checksum")
                            return True
                    elif len(expected_checksum) == 44:  # SHA256 base64 with padding
                        # Convert target hash to base64 for comparison
                        target_b64 = base64.b64encode(
                            bytes.fromhex(target_hash)
                        ).decode()
                        if target_b64 == expected_checksum:
                            print("✓ Target matches product.json checksum (base64)")
                            return True
            except Exception as e:
                print(f"⚠️  Could not read product.json: {e}")

        return False


for rel_path in target_files:
    file_path = os.path.join(ag_dir, rel_path)
    # For archive, we always expect the standard structure or need to map it.
    # Since archive is fixed structure (resources/app...), we need to be careful.
    # If target is "out/...", archive is still "resources/app/out/...".

    # Map relative path to archive path
    if rel_path.startswith("resources/app/"):
        archive_rel_path = rel_path
    elif rel_path.startswith("out/"):
        archive_rel_path = os.path.join("resources/app", rel_path)
    else:
        archive_rel_path = rel_path

    archive_file_path = os.path.join(archive_base, archive_rel_path)

    if not os.path.exists(file_path):
        print(f"⚠️  Skipping: {rel_path} (Not found)")
        continue

    with open(file_path, "rb") as f:
        content = f.read()

    if b"Antigravity CPU Fix" in content:
        print(f"ℹ️  Already Patched: {rel_path}")
        continue

    # Verify checksum before patching
    print(f"🔍 Verifying checksum for {rel_path}...")
    checksum_ok = verify_checksum(file_path, archive_file_path, archive_product_json)
    if not checksum_ok:
        print(f"⚠️  WARNING: {rel_path} does not match expected checksum")
        print(
            "   The file may have been modified, is from a different version, or already patched."
        )
        print(f"   Expected clean version: {VERSION}")
        print("   Proceeding to patch anyway, but results may be unpredictable.")

    # Backup Logic
    backup_path = file_path + ".bak"
    if not os.path.exists(backup_path):
        try:
            shutil.copy2(file_path, backup_path)
            print(f"📦 Created backup: {rel_path}.bak")
        except Exception as e:
            print(f"❌ Error creating backup for {rel_path}: {e}")
            # Decide if we want to proceed or stop. Proceeding for now but warning.

    original_hash = hashlib.md5(content).hexdigest()

    content = polyfill + b"\n" + content
    new_hash = hashlib.md5(content).hexdigest()

    try:
        with open(file_path, "wb") as f:
            f.write(content)
        print(f"✅ Patched: {rel_path}")
        print(f"  New Hash: {new_hash}")
    except Exception as e:
        print(f"❌ Error writing {rel_path}: {e}")
