#!/usr/bin/zsh

# --------------------------------------------------------------------------------------------------
# Shell Launcher
#
# This script takes care of making sure that a Zsh shell is started with both the user's
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



# Keep track of the original .zshrc directory, then setup our custom one.
export LEAF_SHELL_USER_ZDOTDIR=${ZDOTDIR:-$HOME}
export ZDOTDIR="$LEAF_SHARED_DIR"



# Exec the sub-shell with our custom, enhanced configuration.
exec zsh
