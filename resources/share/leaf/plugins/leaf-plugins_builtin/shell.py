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
from pathlib import Path

from leaf.cli.plugins import LeafPluginCommand
from leaf.constants import LeafFiles
from leaf.core.error import LeafException


class ShellPlugin(LeafPluginCommand):

    def _configureParser(self, parser):
        parser.add_argument('-n', '--name',
                            dest='shell',
                            help='run the named shell instead of the default')
        parser.add_argument('-c', '--command',
                            dest='command',
                            nargs=argparse.REMAINDER,
                            default=[],
                            help='run a command in the given shell and exit')

    def execute(self, args, uargs):
        shellFolder = LeafFiles.getResource(LeafFiles.SHELL_DIRNAME)
        if shellFolder is None:
            raise LeafException("Cannot find leaf shell configuration files")
        shellName = None
        # Was the shell name specified by the user directly?
        if args.shell is not None:
            shellName = args.shell
        elif 'SHELL' in os.environ:
            # No, so see if the parent shell advertised it's name.
            shellPath = Path(os.environ['SHELL'])
            shellName = shellPath.name
        else:
            # If nothing else was found, assume Bash.
            shellName = 'bash'
        # Now run our shell.
        self.runSubShell(shellFolder, shellName, args.command)

    def tryExecShell(self, scriptDir, shellName, command, raiseException=False):
        '''
        Try to execute the given shell.
        If successful, this function will not return.
        '''
        # Name of the support script to run.
        scriptName = 'leafsh.%s.sh' % shellName
        # Path to this support script.
        scriptPath = scriptDir / scriptName

        # If the support script exists, run it now.
        if scriptPath.is_file():
            os.execv(str(scriptPath), [
                     str(scriptPath), str(scriptDir)] + command)

        # Looks like we failed to run the shell, so if requeststed, throw an exception here.
        if raiseException:
            raise RuntimeError(
                'Shell startup script %s was not found.' % scriptPath)

    def runSubShell(self, scriptPath, shellName, command):
        '''
        Try to fire up a support script.
        If TryExecShell is successful it will not return
        '''
        self.tryExecShell(scriptPath, shellName, command)

        # Looks like the shell they were looking for was not found.
        # Try again# with a default.
        print('The shell %s is not supported, defaulting to Bash.' % shellName)

        self.tryExecShell(scriptPath, 'bash', command, raiseException=True)
