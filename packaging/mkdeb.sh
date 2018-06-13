#!/bin/sh
set -x
set -e
set -u

# Init
ROOT="$(dirname "$0")/.."
TARGET="$ROOT/target"
WORKING_DIR="$TARGET/src"

# Clean target folder
rm -fr "$TARGET"
mkdir "$TARGET"

# Build source distribution
(
	cd "$ROOT/src/" \
	&& python3 setup.py sdist
)
DIST_FILE="$ROOT/src/dist/leaf-0.0.0.tar.gz"
test -f "$DIST_FILE"

# Extract source
mkdir "$WORKING_DIR"
tar -xzf "$DIST_FILE" -C "$WORKING_DIR" --strip-components=1

# Init version
sed -i -e "s/0.0.0/$VERSION/" "$WORKING_DIR/leaf/__init__.py"
tar -czf "$TARGET/leaf_$VERSION.tar.gz" -C "$WORKING_DIR" .

# Copy debian skel
rsync -Pra \
	"$ROOT/packaging/extrafiles/" \
	"$WORKING_DIR/"

# Create deb
(
	cd "$WORKING_DIR" \
	&& dch --create --package leaf --newversion $VERSION -u low -D release --force-distribution -M "Leaf Package Manager" \
	&& debuild -b
)

# Create _latest artifacts & clean dist folder
(
	rm -rf "$WORKING_DIR" \
	&& cd "$TARGET" \
	&& cp "leaf_$VERSION.tar.gz"	"leaf_latest.tar.gz" \
	&& cp "leaf_${VERSION}_all.deb"	"leaf_latest.deb"
)
