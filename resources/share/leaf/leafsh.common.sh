
# --------------------------------------------------------------------------------------------------
# This code is shared between Bash and Zsh support.  This file holds all of the common code for
# managing a Leaf environment in the user's shell.
#
# Copyright (C) Sierra Wireless Inc.
# --------------------------------------------------------------------------------------------------

# This function is called to store the current leaf profile activate and deactivate scripts.
function lsh_StoreEnvironment
{
    unset LEAF_WORKSPACE
    python3 -m leaf env print -q --activate-script "$LEAF_SHELL_ACTIVATE_FILE" \
                                 --deactivate-script "$LEAF_SHELL_DEACTIVATE_FILE" > /dev/null 2>&1
    export LEAF_WORKSPACE="$LEAF_SHELL_WORKSPACE"
}

# Call this function to unload any active Leaf config from your shell environment.
function lsh_UnloadEnvironment
{
    # If we're not actively in a workspace, then there's not much to unload.
    if test -z "$LEAF_SHELL_WORKSPACE"; then
        return
    fi

    # Looks like we at least were in a workspace, so unload Leaf and our variables.
    if test -r "$LEAF_SHELL_DEACTIVATE_FILE"; then
        source "$LEAF_SHELL_DEACTIVATE_FILE"
        rm "$LEAF_SHELL_DEACTIVATE_FILE"
    fi

    LEAF_SHELL_WORKSPACE=""
    LEAF_SHELL_PROFILE=""
}

# This function handles loading the Leaf environment variables for the current profile.
function lsh_LoadEnvironment
{
    # First, make sure that the old values are cleared out.  We can't just depend on values being
    # overwritten by the new profile.  The old profile may have variables that are not in the
    # current one.
    lsh_UnloadEnvironment

    # Ok, make sure we have the environment scripts setup for this newly current profile.
    lsh_StoreEnvironment

    # Load the new environment variables, and keep track of the now current workspace/profile.
    if test -r "$LEAF_SHELL_ACTIVATE_FILE"; then
        source "$LEAF_SHELL_ACTIVATE_FILE"
        rm "$LEAF_SHELL_ACTIVATE_FILE"
        LEAF_SHELL_WORKSPACE="$LEAF_WORKSPACE"
        LEAF_SHELL_PROFILE="$LEAF_PROFILE"
    fi
}

# Either display a welcome message to the user, or execute a supplied command and then exit.
function lsh_FinishStartup
{
    if test -z "$LEAF_SHELL_EXEC_COMMAND"; then
        # We're running an interactive shell, so check the running shell...  Is this the user's
        # default shell?
        if test "$LEAF_SHELL" != "$SHELL"; then
            echo "Leaf Shell $LEAF_SHELL, (instead of $SHELL,) started."
        else
            echo "Leaf Shell $LEAF_SHELL started in Leaf environment."
        fi
        echo
    else
        # We're not running interactively, so evaluate the user specified command and then exit.
        eval "$LEAF_SHELL_EXEC_COMMAND"
        exit $?
    fi
}

# Is the given directory path inside of a Leaf workspace directory?
function lsh_IsInWorkspace
{
    unset LEAF_WORKSPACE
    WSROOT=`python3 -m leaf status -q`
    export LEAF_WORKSPACE="$LEAF_SHELL_WORKSPACE"
    test -n "$WSROOT"
}

# Called when the user changes their working directory.  We detect if we need to reaload our LeaF
# environment based on the new working directory.
function lsh_HandleChangedDir
{
    if lsh_IsInWorkspace; then
        # If we are in a workspace, load its environment
        lsh_LoadEnvironment
    else
        # If we are not in a workspace, unload env if needed
        lsh_UnloadEnvironment
    fi
}

# Run the original Leaf command, and then reload the environment in case if anything had changed.
function lsh_HandleLeafExecution
{
    \leaf "$@"
    OUT=$?
    lsh_LoadEnvironment
    return $OUT
}

# Generate the string to append to the user's prompt.
function lsh_GeneratePromptString
{
    local outputVar=$1
    local profileName=""

    if test -n "$LEAF_PROFILE"; then
        profileName=":$LEAF_PROFILE"
    fi

    newString="(${LEAF_SHELL_PROMPT_PREFIX}${profileName})"
    eval "$outputVar=\"$newString\""
}

if test -r "$LEAF_SHELL_USER_RC"; then
    source "$LEAF_SHELL_USER_RC"
fi

# Figure out the name of the shell that is actually running.  $SHELL seems to just be set to what
# the user's default shell is set to.  If this variable is already set, then we're running within a
# Leaf shell already, so we should exit with an error now.
if test -n "$LEAF_SHELL"; then
    echo "You appear to be currently running within a Leaf enabled shell."
    echo "Not starting a new shell."
    exit 1
fi

export LEAF_SHELL=`readlink -f "/proc/$$/exe"`

# Work out where to store the load and unload scripts.
LEAF_SHELL_ACTIVATE_FILE=`mktemp --tmpdir leaf-XXXXXXXXXX-activate.env`
LEAF_SHELL_DEACTIVATE_FILE=`mktemp --tmpdir leaf-XXXXXXXXXX-deactivate.env`

# If we are in a workspace and profile, record this now.
LEAF_SHELL_WORKSPACE=""
LEAF_SHELL_PROFILE=""

# If the user specifies a custom prefix, use that.  Otherwise use a default.
LEAF_SHELL_PROMPT_PREFIX=${LEAF_SHELL_PROMPT_PREFIX:-lsh}

# Check to see if we're currently in a leaf workspace, and if we are, set up our environment.
if lsh_IsInWorkspace; then
    lsh_LoadEnvironment
fi
