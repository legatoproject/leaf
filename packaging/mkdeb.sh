#!/bin/sh
set -e
set -u

__usage () {
	echo "Usage: $0 <LEAF_SDIST_FILE> <TARGET_FOLDER>"
	echo "LEAF_SDIST_FILE: source archive generated with ./setup.py sdist"
	echo "TARGET_FOLDER: whare deb will be generated"
}

if ! test $# -eq 2; then
	__usage
	exit 1
fi

SDIST_FILE="$1"
TARGET_FOLDER="$2"
echo "Using Leaf sdist file: $SDIST_FILE"
echo "Target folder: $TARGET_FOLDER"

ROOT_FOLDER=$(dirname "$0")
SKEL_FOLDER="$ROOT_FOLDER/skel"
test -d "$SKEL_FOLDER"

test -f "$SDIST_FILE"
mkdir -p "$TARGET_FOLDER"

# Extract source
WORKING_FOLDER="$TARGET_FOLDER/leaf"
if test -d "$WORKING_FOLDER"; then
	rm -rf "$WORKING_FOLDER"
fi
mkdir "$WORKING_FOLDER"
tar -xaf "$SDIST_FILE" -C "$WORKING_FOLDER" --strip-components=1

# Get verison
test -f "$WORKING_FOLDER/PKG-INFO"
VERSION=$(awk '/^Version:/ {print $2}' "$WORKING_FOLDER/PKG-INFO")
test -n "$VERSION"

# Copy debian skel
rsync -Pra \
	"$SKEL_FOLDER/" \
	"$WORKING_FOLDER/"

# Create deb
(
	cd "$WORKING_FOLDER" \
	&& dch --create --package leaf --newversion "$VERSION" -u low -D release --force-distribution -M "Leaf Package Manager" \
	&& debuild -b
)

# Create _latest artifacts & clean dist folder
rm -rf "$WORKING_FOLDER"
cp -an "$SDIST_FILE" "$TARGET_FOLDER"
cp -an "$TARGET_FOLDER/leaf_${VERSION}_all.deb" "$TARGET_FOLDER/leaf_latest.deb"
