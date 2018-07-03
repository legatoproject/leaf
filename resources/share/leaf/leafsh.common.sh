
# --------------------------------------------------------------------------------------------------
# This code is shared between Bash and Zsh support.  This file holds all of the common code for
# managing a Leaf environment in the user's shell.
#
# Copyright (C) Sierra Wireless Inc.
# --------------------------------------------------------------------------------------------------



# This function is called to store the current leaf profile activate and deactivate scripts.
function lsh_StoreEnvironment
{
    python3 -m leaf env print -q --activate-script "$LEAF_SHELL_ACTIVATE_FILE" \
                                 --deactivate-script "$LEAF_SHELL_DEACTIVATE_FILE" > /dev/null 2>&1
}



# Call this function to unload any active Leaf config from your shell environment.
function lsh_UnloadEnvironment
{
    # If we're not actively in a workspace, then there's not much to unload.
    if [ -z "$LEAF_SHELL_WORKSPACE" ]
    then
        return
    fi

    # Looks like we at least were in a workspace, so unload Leaf and our variables.
    if [ -e "$LEAF_SHELL_DEACTIVATE_FILE" ]
    then
        source "$LEAF_SHELL_DEACTIVATE_FILE"
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
    if [ -e "$LEAF_SHELL_ACTIVATE_FILE" ]
    then
        source "$LEAF_SHELL_ACTIVATE_FILE"

        LEAF_SHELL_WORKSPACE="$LEAF_WORKSPACE"
        LEAF_SHELL_PROFILE="$LEAF_PROFILE"
    fi
}



# Either display a welcome message to the user, or execute a supplied command and then exit.
function lsh_FinishStartup
{
    if [ -z "$LEAF_SHELL_EXEC_COMMAND" ]
    then
        # We're running an interactive shell, so check the running shell...  Is this the user's
        # default shell?
        if [ "$LEAF_SHELL" != "$SHELL" ]
        then
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



# Check the given directory and see if it is inside of the parent directory.
function lsh_IsInDir
{
    local givenDir="$1"
    local parentDir='$2'

    case "$givenDir" in
        # We are either in the given directory's root, or we are in a
        # sub-directory of the given directory.
        "$parentDir")            ;&
        "$parentDir/*") return 0 ;;

        # We are somewhere outside of the given directory.
        *)              return 1 ;;
    esac
}



# Is the given directory path inside of a Leaf workspace directory?
function lsh_IsInWorkspace
{
    local givenDir="$1"
    local workspaceFile="leaf-workspace.json"

    # Search up the directory hierarchy and look for a Leaf workspace file.
    while [ "$givenDir" != "/" ]
    do
        if [ -e "$givenDir/$workspaceFile" ]
        then
            # We are in a workspace, success!
            return 0
        fi

        givenDir="$(readlink -f "$givenDir"/..)"
    done

    # We searched all the way up to root, we are not in a workspace.
    return 1
}



# Called when the user changes their working directory.  We detect if we need to reaload our LeaF
# environment based on the new working directory.
function lsh_HandleChangedDir
{
    # Were we last in a Leaf environment?
    if [ -n "$LEAF_WORKSPACE" ]
    then
        lsh_IsInDir "$PWD" "$LEAF_WORKSPACE"

        if [ ! $? -eq 0 ]
        then
            lsh_IsInWorkspace "$PWD"

            if [ $? -eq 0 ]
            then
                lsh_LoadEnvironment
            else
                lsh_UnloadEnvironment
            fi
        fi
    else
        # We were not in a Leaf workspace.  So, just check if the new directory is a workspace
        # directory.  If it is, then load the info for it.
        lsh_IsInWorkspace "$PWD"

        if [ $? -eq 0 ]
        then
            lsh_LoadEnvironment
        fi
    fi
}



# Run the original Leaf command, and then reload the environment in case if anything had changed.
function lsh_HandleLeafExecution
{
    \leaf $@
    lsh_LoadEnvironment
}



# Generate the string to append to the user's prompt.
function lsh_GeneratePromptString
{
    local outputVar=$1
    local profileName=""

    if [ -n "$LEAF_PROFILE" ]
    then
        profileName=":$LEAF_PROFILE"
    fi

    newString="(${LEAF_SHELL_PROMPT_PREFIX}${profileName})"
    eval "$outputVar=\"$newString\""
}



# Look for the user's shell rc file and load it.  If it can't be found, bail out now.
if [ ! -e "$LEAF_SHELL_USER_RC" ]
then
    echo "$LEAF_SHELL_NO_CONFIG_MESSAGE"
    exit 1
fi

source "$LEAF_SHELL_USER_RC" || exit 1



# Figure out the name of the shell that is actually running.  $SHELL seems to just be set to what
# the user's default shell is set to.  If this variable is already set, then we're running within a
# Leaf shell already, so we should exit with an error now.
if [ ! -z "$LEAF_SHELL" ]
then
    echo "You appear to be currently running within a Leaf enabled shell."
    echo "Not starting a new shell."

    exit 1
fi

export LEAF_SHELL=`readlink -f "/proc/$$/exe"`



# Work out where to store the load and unload scripts.
export LEAF_SHELL_ACTIVATE_FILE=`mktemp --tmpdir leaf-XXXXXXXXXX-activate.env`
export LEAF_SHELL_DEACTIVATE_FILE=`mktemp --tmpdir leaf-XXXXXXXXXX-deactivate.env`



# If we are in a workspace and profile, record this now.
export LEAF_SHELL_WORKSPACE=""
export LEAF_SHELL_PROFILE=""



# If the user specifies a custom prefix, use that.  Otherwise use a default.
export LEAF_SHELL_PROMPT_PREFIX=${LEAF_SHELL_PROMPT_PREFIX:-lsh}



# Check to see if we're currently in a leaf workspace, and if we are, set up our environment.
lsh_IsInWorkspace "$PWD"

if [ $? -eq 0 ]
then
    lsh_LoadEnvironment
fi
