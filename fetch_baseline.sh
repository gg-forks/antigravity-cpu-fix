#!/bin/bash
set -e

VERSION="${1:-1.107.0}"
ORIG_DIR="$PWD"
ARCHIVE_APP="${ORIG_DIR}/archive/ag-${VERSION}/src/resources/app"
ARCHIVE_MAIN="${ARCHIVE_APP}/out/jetskiAgent"

# Create target directories
mkdir -p "${ARCHIVE_MAIN}"

echo "Fetching pristine baseline for Internal Version: ${VERSION}..."

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

# Get current installed package version
if ! pacman -Q antigravity >/dev/null 2>&1; then
	echo "Error: antigravity package not installed via pacman."
	exit 1
fi

PKG_VER=$(pacman -Q antigravity | awk '{print $2}')
echo "Installed antigravity package version: $PKG_VER"

CACHE_FILE="/var/cache/pacman/pkg/antigravity-${PKG_VER}-x86_64.pkg.tar.zst"

if [ ! -f "$CACHE_FILE" ]; then
	echo "Not found in pacman cache ($CACHE_FILE)."
	echo "Using yay to download PKGBUILD..."
	cd "$WORKDIR"
	yay -G antigravity
	if [ ! -d "antigravity" ]; then
		echo "Error: Failed to fetch PKGBUILD for antigravity."
		exit 1
	fi
	cd antigravity
	echo "Downloading source .deb via PKGBUILD..."
	makepkg -od
	DEB_FILE=$(ls *.deb | head -n 1)
	if [ -z "$DEB_FILE" ]; then
		echo "Error: Failed to download source .deb."
		exit 1
	fi
	echo "Extracting baseline files from deb..."
	bsdtar -xf "$DEB_FILE" data.tar.xz
	bsdtar -xf data.tar.xz ./usr/share/antigravity/resources/app/product.json ./usr/share/antigravity/resources/app/out/jetskiAgent/main.js

	cp usr/share/antigravity/resources/app/product.json "${ARCHIVE_APP}/product.json"
	cp usr/share/antigravity/resources/app/out/jetskiAgent/main.js "${ARCHIVE_MAIN}/main.js"
else
	echo "Found in cache: $CACHE_FILE"
	echo "Extracting baseline files from pacman cache..."
	cd "$WORKDIR"
	bsdtar -xf "$CACHE_FILE" opt/Antigravity/resources/app/product.json opt/Antigravity/resources/app/out/jetskiAgent/main.js

	cp opt/Antigravity/resources/app/product.json "${ARCHIVE_APP}/product.json"
	cp opt/Antigravity/resources/app/out/jetskiAgent/main.js "${ARCHIVE_MAIN}/main.js"
fi

echo "Successfully extracted baseline to archive/ag-${VERSION}/src"
