#!/bin/bash
# Some comment here
# And then LEAF_DESCRIPTION The description of my command
# And another line
#

echo "Hello World ;)"
if test -n "$1"; then
    exit $1
fi

python3 -m leaf --version

