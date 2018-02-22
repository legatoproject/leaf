#!/bin/sh
set -x
set -e

# Init
ROOT="$(dirname "$0")/.."
SRC_DIR="$ROOT/src"
DIST_DIR="$SRC_DIR/dist"
VERSION=$(git describe --tags)

# Build source distribution
(cd "$SRC_DIR" && python3 setup.py sdist)
DIST_FILE="$DIST_DIR/leaf-0.0.0.tar.gz"
test -f "$DIST_FILE"

# Extract source
tar -C "$DIST_DIR" -xvzf "$DIST_FILE"
rm "$DIST_FILE"
WORKING_DIR=${DIST_FILE%.tar.gz}
test -d "$WORKING_DIR"

# Init version 
sed -i -e "s/0.0.0/$VERSION/" "$WORKING_DIR/leaf/__init__.py"
tar -C "$WORKING_DIR" -cvzf "$DIST_DIR/leaf_$VERSION.tar.gz" .

# Copy debian skel
cp -r "$ROOT/packaging/debian/" "$WORKING_DIR"

# Create deb
cd "$WORKING_DIR"
dch --create --package leaf --newversion $VERSION -u low -D release --force-distribution -M "Leaf Package Manager"
debuild -b
