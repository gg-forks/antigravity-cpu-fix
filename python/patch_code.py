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


def get_file_hash(file_path, algo="sha256", encoding="hex"):
    """Calculate hash of a file with specified algorithm and encoding."""
    h = hashlib.new(algo)
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)

    if encoding == "base64":
        return base64.b64encode(h.digest()).decode("utf-8")
    elif encoding == "base64_unpadded":
        return base64.b64encode(h.digest()).decode("utf-8").rstrip("=")
    else:  # hex
        return h.hexdigest()


def detect_hash_format(existing_hash):
    """Detect the hash format from an existing checksum."""
    if len(existing_hash) == 32:
        return "md5", "hex"
    elif len(existing_hash) == 64:
        return "sha256", "hex"
    elif len(existing_hash) == 44 and existing_hash.endswith("="):
        return "sha256", "base64"
    elif len(existing_hash) == 43:
        return "sha256", "base64_unpadded"
    else:
        # Default to sha256 hex
        return "sha256", "hex"


def verify_checksum(
    target_path, archive_path, archive_product_json, system_product_json
):
    """Verify that target file matches archive or system checksum."""

    # 1. Direct comparison with archive file
    if os.path.exists(archive_path):
        archive_hash_hex = get_file_hash(archive_path, "sha256", "hex")
        target_hash_hex = get_file_hash(target_path, "sha256", "hex")

        if archive_hash_hex == target_hash_hex:
            print(
                f"✓ Checksum verified: {os.path.basename(target_path)} matches archive file"
            )
            return True

    # 2. Comparison with expected hashes in product.json files
    target_hashes = {}  # algo: {encoding: hash}

    for label, product_json in [
        ("Archive", archive_product_json),
        ("System", system_product_json),
    ]:
        if not os.path.exists(product_json):
            continue

        try:
            with open(product_json, "r") as f:
                product_data = json.load(f)

            checksums = product_data.get("checksums", {})
            target_key = None
            for key in checksums.keys():
                if key.endswith("jetskiAgent/main.js"):
                    target_key = key
                    break

            if target_key:
                expected_hash = checksums[target_key]
                algo, encoding = detect_hash_format(expected_hash)

                # Cache actual hash for target
                cache_key = (algo, encoding)
                if cache_key not in target_hashes:
                    target_hashes[cache_key] = get_file_hash(
                        target_path, algo, encoding
                    )

                if target_hashes[cache_key] == expected_hash:
                    print(
                        f"✓ Checksum verified: {os.path.basename(target_path)} matches {label} product.json ({encoding})"
                    )
                    return True
                else:
                    if label == "Archive":
                        print(
                            f"❌ Checksum mismatch for {os.path.basename(target_path)}:"
                        )
                        print(f"  Archive (expected): {expected_hash}")
                        print(f"  Target  (actual):   {target_hashes[cache_key]}")
        except Exception as e:
            print(f"⚠️  Could not read {label} product.json: {e}")

    return False


for rel_path in target_files:
    file_path = os.path.join(ag_dir, rel_path)
    # Detect system product.json path
    system_product_json = os.path.join(ag_dir, "resources/app/product.json")
    if not os.path.exists(system_product_json):
        system_product_json = os.path.join(ag_dir, "product.json")

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
    checksum_ok = verify_checksum(
        file_path, archive_file_path, archive_product_json, system_product_json
    )
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
            if isinstance(e, PermissionError):
                print(f"❌ Permission Denied: Could not create backup for {rel_path}.")
                print("   Please run with 'sudo'.")
                sys.exit(1)
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
        if isinstance(e, PermissionError):
            print(f"❌ Permission Denied: Could not write {rel_path}.")
            print("   Please run with 'sudo'.")
        else:
            print(f"❌ Error writing {rel_path}: {e}")
        sys.exit(1)
