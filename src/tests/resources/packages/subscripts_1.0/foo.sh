#!/bin/bash

RC=0
OUT=/dev/stdout

if test $# -eq 0; then
    RC=42
else
    OUT="$1"
fi

echo "Test LANG=$LANG" >> "$OUT"
echo "Test LEAF_VERSION=$LEAF_VERSION" >> "$OUT"
echo "Test MY_CUSTOM_VAR1=$MY_CUSTOM_VAR1" >> "$OUT"
echo "Test MY_CUSTOM_VAR2=$MY_CUSTOM_VAR2" >> "$OUT"
echo "Test MY_CUSTOM_VAR3=$MY_CUSTOM_VAR3" >> "$OUT"
echo "Test MY_EXPORTED_VAR=$MY_EXPORTED_VAR" >> "$OUT"
echo "Test STDERR" >> /dev/stderr
echo "Arguments counts: $#" >> "$OUT"
while test -n "$1"; do
    echo "  >$1<" >> "$OUT"
    shift
done

exit $RC
