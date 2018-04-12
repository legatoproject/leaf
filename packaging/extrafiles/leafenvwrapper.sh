# Functions and alias to manage terminal environment auto-update when leaf profile changes
__leaf_load_env () {
	if test -f "$LEAF_DEACTIVATE"; then
		source "$LEAF_DEACTIVATE"
	fi
	rm -f "$LEAF_ACTIVATE" "$LEAF_DEACTIVATE"
	\leaf env -q \
		--activate-script "$LEAF_ACTIVATE" \
		--deactivate-script "$LEAF_DEACTIVATE" > /dev/null 2>&1
	if test $? -eq 0 -a -f "$LEAF_ACTIVATE"; then
		source "$LEAF_ACTIVATE"
		PS1="${LEAF_PS1:-{$LEAF_PROFILE\} $LEAF_OLDPS1}"
	fi
}

__leaf_refresh_env () {
	\leaf "$@"
	local RETURN_CODE=$?
	if test $RETURN_CODE -eq 0; then
		local CURRENT_ARG	
		for CURRENT_ARG in "$@"; do
		  if echo "$CURRENT_ARG" | grep -Eq "^(setup|select|sync|update|create|rename|delete|config:[uwp]|env:[uwp])"; then
				__leaf_load_env
				return $RETURN_CODE
			fi
		done
	fi
	return $RETURN_CODE
}

# Prevent multiple source
if test -z "$LEAF_OLDPS1"; then
	LEAF_OLDPS1="$PS1"
fi
LEAF_ACTIVATE=/tmp/leaf-$$-$RANDOM-activate.env
LEAF_DEACTIVATE=/tmp/leaf-$$-$RANDOM-deactivate.env
alias leaf=__leaf_refresh_env
