# Functions and alias to manage terminal environment auto-update when leaf profile changes
__leaf_load_env () {
	\leaf env 2> /dev/null > ${LEAF_ADDENV}
	if test -s ${LEAF_ADDENV}; then
		__leaf_unload_env
		source ${LEAF_ADDENV}
		PS1="${LEAF_PS1:-{$LEAF_PROFILE\} $LEAF_OLDPS1}"
	fi
}

__leaf_unload_env () {
	if test -s ${LEAF_RMENV}; then
		source ${LEAF_RMENV}
	fi
	
	# Compute unload script
	rm -f ${LEAF_RMENV}
	touch ${LEAF_RMENV}
	local unsetvar
	for unsetvar in `cat ${LEAF_ADDENV} | sed -e "s/export \([^=]*\)=.*;/\1/"`; do
		local oldValue="${!unsetvar}"
		if test -n "$oldValue"; then
			# Restore value
			echo "export ${unsetvar}=\"${oldValue}\";" >> ${LEAF_RMENV}
		else
			# Simply unset
			echo "unset ${unsetvar};" >> ${LEAF_RMENV}
		fi
		cat ${LEAF_RMENV} | sort -u > ${LEAF_RMENV}.new
		cp ${LEAF_RMENV}.new ${LEAF_RMENV} && rm ${LEAF_RMENV}.new
	done
}

__leaf_refresh_env () {
	\leaf "$@"
	local rc=$?
	if test $rc -eq 0; then
		local trigger
		local arg
		for arg in $@; do
			for trigger in init create update sync workspace ws rename mv; do
				if test "$arg" = "$trigger"; then
					__leaf_load_env
					return $rc
				fi
			done
		done
	fi
	return $rc
}

LEAF_OLDPS1="$PS1"
LEAF_ADDENV=/tmp/leaf-$$-$RANDOM-addenv.sh
LEAF_RMENV=/tmp/leaf-$$-$RANDOM-rmenv.sh
alias leaf=__leaf_refresh_env
