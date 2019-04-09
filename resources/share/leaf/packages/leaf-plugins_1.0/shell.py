# --------------------------------------------------------------------------------------------------
# External command for invoking a shell from Leaf.
#
# This command actually invokes a script written in the language for each supported shell.  This way
# this script doesn't need to know all of the details on how to support each shell.  It just needs
# to know how to find the script.  This way new support can just be dropped in without having to
# modify this script.
#
# Copyright (C) Sierra Wireless Inc.
# --------------------------------------------------------------------------------------------------

import argparse
import os

from leaf.cli.plugins import LeafPluginCommand
from leaf.core.constants import CommonSettings
from leaf.core.error import LeafException


class ShellPlugin(LeafPluginCommand):

    SHELL_DIRNAME = "shell"

    def _configure_parser(self, parser):
        parser.add_argument("-n", "--name", dest="shell", help="run the named shell instead of the default")
        parser.add_argument("-c", "--command", dest="command", nargs=argparse.REMAINDER, default=[], help="run a command in the given shell and exit")

    def execute(self, args, uargs):
        shell_folder = self.installed_package.folder / ShellPlugin.SHELL_DIRNAME

        if shell_folder is None:
            raise LeafException("Cannot find leaf shell configuration files")
        shell_name = None
        # Was the shell name specified by the user directly?
        if args.shell is not None:
            shell_name = args.shell
        elif CommonSettings.SHELL.is_set():
            # No, so see if the parent shell advertised it's name.
            shell_name = CommonSettings.SHELL.as_path().name
        else:
            # If nothing else was found, assume Bash.
            shell_name = "bash"
        # Now run our shell.
        self.__run_sub_shell(shell_folder, shell_name, args.command)

    def __try_exec_shell(self, script_dir, shell_name, command, raise_exception=False):
        """
        Try to execute the given shell.
        If successful, this function will not return.
        """
        # Name of the support script to run.
        script_name = "leafsh.{shell}.sh".format(shell=shell_name)
        # Path to this support script.
        script_path = script_dir / script_name

        # If the support script exists, run it now.
        if script_path.is_file():
            os.execv(str(script_path), [str(script_path), str(script_dir)] + command)

        # Looks like we failed to run the shell, so if requeststed, throw an exception here.
        if raise_exception:
            raise RuntimeError("Shell startup script {file} was not found.".format(file=script_path))

    def __run_sub_shell(self, script_path, shell_name, command):
        """
        Try to fire up a support script.
        If __try_exec_shell is successful it will not return
        """
        self.__try_exec_shell(script_path, shell_name, command)

        # Looks like the shell they were looking for was not found.
        # Try again# with a default.
        print("The shell {shell} is not supported, defaulting to Bash.".format(shell=shell_name))

        self.__try_exec_shell(script_path, "bash", command, raise_exception=True)
