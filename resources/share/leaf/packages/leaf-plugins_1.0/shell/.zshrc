# --------------------------------------------------------------------------------------------------
# Configuration file for a Zsh sub-shell with Leaf integration.
#
# Copyright (C) Sierra Wireless Inc.
# --------------------------------------------------------------------------------------------------



# Name of the user's rc to load, and a message to display if the user's rc file can not be found.
LEAF_SHELL_USER_RC="$LEAF_SHELL_USER_ZDOTDIR/.zshrc"

# The user's base configuration and our common code.
source "$LEAF_SHARED_DIR/leafsh.common.sh"

# Function to update the prompt in Zsh.
function lsh_zsh_UpdatePrompt
{
    # Generate the Leaf portion of the new prompt.
    local leafPrompt=''
    lsh_GeneratePromptString "leafPrompt"

    # Figure out if the user wants the leaf info added to the left or the right prompt and update
    # the correct variable.
    if [ "$LEAF_SHELL_ZSH_PROMPT_SIDE" = "right" ]
    then
        if [ -z "$LEAF_SHELL_ORIGINAL_RPROMPT" ]
        then
            RPROMPT="$leafPrompt"
        else
            RPROMPT="$LEAF_SHELL_ORIGINAL_RPROMPT $leafPrompt"
        fi
    else
        PROMPT="$leafPrompt $LEAF_SHELL_ORIGINAL_PROMPT"
    fi
}



# Setup the side the Leaf portion of prompt will appear on.  If the user pre-defines:
#    $ export LEAF_SHELL_ZSH_PROMPT_SIDE='right'
# Then the prompt will be set as a r-prompt, otherwise we add our profile info to the left.
export LEAF_SHELL_ZSH_PROMPT_SIDE=${LEAF_SHELL_ZSH_PROMPT_SIDE:-left}



# Functions in the list chpwd_functions are called every time the user changes directory in the
# shell.
if [ -z "$chpwd_functions" ]
then
    typeset -a chpwd_functions
    export chpwd_functions
fi

chpwd_functions+=lsh_HandleChangedDir



# Allow any installed precommands to run first in order to capture the updated prompt string.  Then,
# save the original prompts for later use.
for cmd in $precmd_functions
do
    $cmd
done

export LEAF_SHELL_ORIGINAL_PROMPT="$PROMPT"
export LEAF_SHELL_ORIGINAL_RPROMPT="$RPROMPT"



# Hook into Zsh's precmd functions in order to play nicely with Zsh prompt themes.
precmd_functions+=lsh_zsh_UpdatePrompt



# Alias Leaf so that we know when the user tries to run Leaf and potentially change the
# environment.
alias leaf="lsh_HandleLeafExecution"



# Finally, check to see if we're to run interactively.  If not then run that command and then exit.
# If we are to be interactive, then show the welcome message and let the user run their commands.
lsh_FinishStartup
