#!/bin/bash
#set -x


## Args
PARTIAL_MODE=0
if test "$1" = "--partial"; then
    PARTIAL_MODE=1
    shift
fi

## Prepare variables
COMP_LINE=leaf
COMP_WORDS=(leaf)
COMP_CWORD=0
for word in "$@"; do
    COMP_LINE="$COMP_LINE $word"
    COMP_WORDS=("${COMP_WORDS[@]}" $word)
    COMP_CWORD=$(($COMP_CWORD + 1))
done

if test $PARTIAL_MODE -eq 0; then
    COMP_LINE="$COMP_LINE "
    COMP_WORDS=("${COMP_WORDS[@]}" "")
    COMP_CWORD=$(($COMP_CWORD + 1))
fi

COMP_POINT=${#COMP_LINE}

## Source completion files
source /etc/bash_completion
source $(dirname "$0")/../../../resources/share/bash-completion/completions/leaf

## Debug
# echo "[DEBUG]  COMP_LINE=$COMP_LINE"
# echo "[DEBUG]  COMP_WORDS[${#COMP_WORDS[@]}]=${COMP_WORDS[@]}"
# echo "[DEBUG]  COMP_WORDS=$COMP_CWORD"
# echo "[DEBUG]  COMP_POINT=$COMP_POINT"

## Execute completion function
$(complete -p leaf | sed "s/.*-F \\([^ ]*\\) .*/\\1/")
printf '%s\n' "${COMPREPLY[@]}"