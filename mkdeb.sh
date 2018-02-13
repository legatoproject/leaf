#!/bin/sh
set -x
set -e

# Init
ROOT=$(dirname "$0")
DIST_DIR="dist"
cd "$ROOT"

# Build source distribution
python3 setup.py sdist
DIST_FILE=$(ls -1 "$DIST_DIR"/*.tar.gz | head -1)
test -f "$DIST_FILE"

# Extract source
tar -C "$DIST_DIR" -xvzf "$DIST_FILE"
WORKING_DIR=${DIST_FILE%.tar.gz}
test -d "$WORKING_DIR"

# Copy debian skel
cp -r packaging/debian/ "$WORKING_DIR"

# Create debian package
cd "$WORKING_DIR"
debuild -b
