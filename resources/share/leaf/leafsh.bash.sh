#!/bin/bash

# --------------------------------------------------------------------------------------------------
# Shell Launcher
#
# This script takes care of making sure that a bash shell is started with both the user's
# configuration and support for Leaf is enabled.
#
# This script isn't intended to be run directly, but instead run through leaf shell.
#
# Copyright (C) Sierra Wireless Inc.
# --------------------------------------------------------------------------------------------------



# Get the location for where find support files from Leaf.
export LEAF_SHARED_DIR="$1"
shift

# Any remaining arguments past are interpreted as a command to execute.
export LEAF_SHELL_EXEC_COMMAND="$@"



if [ -n "$LEAF_SHELL_EXEC_COMMAND" ]
then
    # Exec the sub-shell to run a custom command, then exit
    exec bash -c "source $LEAF_SHARED_DIR/.bashrc"
fi

# Spawn the sub-shell with our custom, enhanced configuration.
exec bash --rcfile "$LEAF_SHARED_DIR/.bashrc"
