
# --------------------------------------------------------------------------------------------------
# Configuration file for a Bash sub-shell with Leaf integration.
#
# Copyright (C) Sierra Wireless Inc.
# --------------------------------------------------------------------------------------------------



# Name of the user's rc to load, and a message to display if the user's rc file can not be found.
LEAF_SHELL_USER_RC="$HOME/.bashrc"

LEAF_SHELL_NO_CONFIG_MESSAGE="Could not find a Bash shell configuration.
Run the following to create a new default one:

    cp /etc/skel/.bashrc ~/.bashrc"



# The user's base configuration and our common code.
source "$LEAF_SHARED_DIR/leafsh.common.sh"



# Called just before the Bash prompt is drawn.
function lsh_bash_PromptCmd
{
    # Check ot see if we had changed directories.  If we had, check to see if we have to reevaluate
    # things.
    if [ "$PWD" != "$LEAF_SHELL_OLDPWD" ]
    then
        lsh_HandleChangedDir

        LEAF_SHELL_OLDPWD="$PWD"
    fi

    # Generate the Leaf portion of the new prompt.
    local leafPrompt=''
    lsh_GeneratePromptString "leafPrompt"

    PS1="$leafPrompt $LEAF_SHELL_ORIGINAL_PROMPT"

    # Run the original prompt command, if there wasn't one this will evaluate to nothing.
    $LEAF_ORIGINAL_PROMPT_COMMAND
}



# Save the original prompt.
export LEAF_SHELL_ORIGINAL_PROMPT="$PS1"



# Start to keep track of the current working directory, and other Leaf variables.
export LEAF_SHELL_OLDPWD="$PWD"



# Save the current prompt command, if any, and install our own.
export LEAF_ORIGINAL_PROMPT_COMMAND="$PROMPT_COMMAND"
PROMPT_COMMAND=lsh_bash_PromptCmd



# Alias Leaf so that we know when the user tries to run Leaf and potentially change the
# environment.
alias leaf="lsh_HandleLeafExecution"



# Finally, check to see if we're to run interactively.  If not then run that command and then exit.
# If we are to be interactive, then show the welcome message and let the user run their commands.
lsh_FinishStartup
