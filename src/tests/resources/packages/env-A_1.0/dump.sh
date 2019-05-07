#!/bin/sh
set -x
echo "Hello install"
echo "LEAF_ENV_A2 = $LEAF_ENV_A2" > "$(dirname "$0")/dump.out"