#!/bin/sh
VERSION=1.1
OUTPUT="/dev/null"

if test -n "$1"; then
    OUTPUT="$1"
fi

echo "my special binary v$VERSION" | tee "$OUTPUT"
