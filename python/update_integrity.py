#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import shutil
import sys

# 1. Setup
if len(sys.argv) < 2:
    print("❌ Error: Missing Argument. Usage: update_integrity.py <AG_SRC>")
    sys.exit(1)

base_dir = sys.argv[1]

VERSION = "1.107.0"

# Detect layout for product.json
possible_product_paths = [
    os.path.join(base_dir, "resources/app/product.json"),
    os.path.join(base_dir, "product.json"),
]
product_json_path = None
for p in possible_product_paths:
    if os.path.exists(p):
        product_json_path = p
        break
if not product_json_path:
    product_json_path = possible_product_paths[0]  # Default

# Detect layout for main.js
possible_main_paths = [
    os.path.join(base_dir, "resources/app/out/jetskiAgent/main.js"),
    os.path.join(base_dir, "out/jetskiAgent/main.js"),
]
file_path = None
for p in possible_main_paths:
    if os.path.exists(p):
        file_path = p
        break
if not file_path:
    file_path = possible_main_paths[0]  # Default

target_suffix = "jetskiAgent/main.js"

# Path to archive for reference
archive_base = f"archive/ag-{VERSION}/src"
archive_main_js = os.path.join(archive_base, "resources/app/out/jetskiAgent/main.js")
archive_product_json = os.path.join(archive_base, "resources/app/product.json")


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


# Backup Logic
backup_path = product_json_path + ".bak"
if not os.path.exists(backup_path):
    try:
        shutil.copy2(product_json_path, backup_path)
        print("📦 Created backup: product.json.bak")
    except Exception as e:
        print(f"❌ Error creating backup for product.json: {e}")

# Read existing data
with open(product_json_path, "r") as f:
    data = json.load(f)

checksums = data.get("checksums", {})

# 2. Find Key
target_key = None
if "out/jetskiAgent/main.js" in checksums:
    target_key = "out/jetskiAgent/main.js"
else:
    for key in checksums.keys():
        if key.endswith(target_suffix):
            target_key = key
            break

# 3. Update Logic
needs_save = False

if target_key:
    print(f"ℹ️  Found checksum key: {target_key}")
    old_hash = checksums[target_key]

    # Detect hash format
    algo, encoding = detect_hash_format(old_hash)
    print(f"  Detected format: {algo}, {encoding}")

    # Calculate new hash
    try:
        new_hash = get_file_hash(file_path, algo, encoding)
    except FileNotFoundError:
        print(f"❌ Error: Could not read target file: {file_path}")
        sys.exit(1)

    # Compare with archive hash for verification
    if os.path.exists(archive_main_js):
        archive_hash = get_file_hash(archive_main_js, algo, encoding)
        print(f"  Archive hash: {archive_hash}")

        # If patched file doesn't match archive, that's expected
        if new_hash != archive_hash:
            print("  ✓ File is patched (differs from archive)")
        else:
            print("  ⚠️  File matches archive (may not be patched)")

    # Compare with old hash
    if new_hash != old_hash:
        checksums[target_key] = new_hash
        data["checksums"] = checksums
        needs_save = True
        print(f"✓ Checksum mismatch detected. Updating (Format: {encoding})")
        print(f"  Old: {old_hash}")
        print(f"  New: {new_hash}")
    else:
        print("✓ Checksum verified and up-to-date. No changes needed.")

else:
    print("⚠️  Specific checksum key not found.")
    # Only nuke if checksums actually exist
    if "checksums" in data and data["checksums"]:
        print("☢️  NUCLEAR OPTION: Removing ALL checksums to force valid state.")
        del data["checksums"]
        needs_save = True
        print("✓ Integrity check disabled entirely.")
    else:
        print("ℹ️  Checksums already empty or missing.")

# 4. Write (Only if changed)
if needs_save:
    try:
        with open(product_json_path, "w") as f:
            json.dump(data, f, indent=2)
        print("💾 product.json updated successfully.")
    except Exception as e:
        print(f"❌ Error writing product.json: {e}")
        sys.exit(1)
