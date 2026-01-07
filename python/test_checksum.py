#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import sys


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


def test_checksums():
    """Test that archive files match expected checksums."""
    print("=== Antigravity Checksum Verification Test ===\n")

    # Test main.js
    archive_main_js = "archive/ag-1.104.0/src/resources/app/out/jetskiAgent/main.js"
    archive_product_json = "archive/ag-1.104.0/src/resources/app/product.json"

    if not os.path.exists(archive_main_js):
        print(f"❌ Archive main.js not found: {archive_main_js}")
        return False

    if not os.path.exists(archive_product_json):
        print(f"❌ Archive product.json not found: {archive_product_json}")
        return False

    # Read product.json to get expected checksums
    with open(archive_product_json, "r") as f:
        product_data = json.load(f)

    checksums = product_data.get("checksums", {})

    # Find main.js checksum key
    target_key = None
    for key in checksums.keys():
        if key.endswith("jetskiAgent/main.js"):
            target_key = key
            break

    if not target_key:
        print("❌ Could not find main.js checksum key in product.json")
        # Try to list available keys
        print(f"  Available keys: {list(checksums.keys())}")
        return False

    expected_checksum = checksums[target_key]
    print(f"Found checksum key: {target_key}")
    print(f"Expected checksum: {expected_checksum}")

    # Detect hash format
    if len(expected_checksum) == 32:
        algo, encoding = "md5", "hex"
    elif len(expected_checksum) == 64:
        algo, encoding = "sha256", "hex"
    elif len(expected_checksum) == 44 and expected_checksum.endswith("="):
        algo, encoding = "sha256", "base64"
    elif len(expected_checksum) == 43:
        algo, encoding = "sha256", "base64_unpadded"
    else:
        print(f"❌ Unknown checksum format: length={len(expected_checksum)}")
        return False

    print(f"Detected format: {algo}, {encoding}")

    # Calculate actual hash
    actual_hash = get_file_hash(archive_main_js, algo, encoding)
    print(f"Actual hash: {actual_hash}")

    # Compare
    if actual_hash == expected_checksum:
        print("\n✅ SUCCESS: Archive main.js matches expected checksum!")
        print(f"   Version: {product_data.get('version', 'unknown')}")
        return True
    else:
        print("\n❌ FAILURE: Archive main.js does NOT match expected checksum!")
        print("   The archive may be corrupted or from a different version.")
        return False


if __name__ == "__main__":
    success = test_checksums()
    sys.exit(0 if success else 1)
