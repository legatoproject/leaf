#!/bin/bash

set -x 
set -e
set -u

VERSION=$1
INSTALL=${2:-install}
CONFIGURE_ARGS=""
MAKE_ARGS="-j4"
ARCHIVE_FILE=Python-$VERSION.tar.xz
SRC_FOLDER=`mktemp -d`

if ! test -f "$ARCHIVE_FILE"; then
	URL=https://www.python.org/ftp/python/$VERSION/Python-$VERSION.tar.xz
	wget "$URL" -O "$ARCHIVE_FILE"
fi
tar -xJC "$SRC_FOLDER" --strip-components=1 -f "$ARCHIVE_FILE"
rm "$ARCHIVE_FILE"

cd "$SRC_FOLDER"
./configure $CONFIGURE_ARGS
make $MAKE_ARGS
make $INSTALL
rm -rf "$SRC_FOLDER"
