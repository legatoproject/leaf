#!/bin/bash

if test "$1" = "--description"; then
	echo "Test command"
	exit
fi

echo "Hello World ;)"
python3 -m leaf --version
