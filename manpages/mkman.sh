#!/bin/sh
set -x
set -e

# Init
ROOT="$(dirname "$0")"

# Check we're ready
which a2x || (echo "Missing system dependencies to build man pages; see README.md"; exit 1)

# Prepare directories
MANTARGET=$ROOT/../src/man
rm -rf $MANTARGET
mkdir -p $MANTARGET/man1/
MANTMP=$(mktemp -d)

# Look for man pages
for PAGE in $(cd $ROOT; ls leaf*.adoc); do
	cat $ROOT/header.adoc $ROOT/$PAGE $ROOT/footer.adoc > $MANTMP/$PAGE
	sed -i $MANTMP/$PAGE -e "s/{VERSION}/${VERSION}/"
	a2x -f manpage $MANTMP/$PAGE -D $MANTARGET/man1/ -v
done
