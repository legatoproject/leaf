'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from collections import OrderedDict
from os.path import pathsep
from pathlib import Path
import argparse
import os
import subprocess

from leaf.cli.cliutils import GenericCommand


MOTIF = 'LEAF_DESCRIPTION'
HEADER_SIZE = 2048


class ExternalCommand(GenericCommand):
    '''
    Wrapper to run external binaries as leaf subcommand.
    '''

    def __init__(self, name, description, executable):
        GenericCommand.__init__(self,
                                name,
                                description)
        self.executable = executable
        self.cmdHelp = description

    def create(self, subparsers):
        parser = subparsers.add_parser(self.cmdName,
                                       help=self.cmdHelp,
                                       prefix_chars='+',
                                       add_help=False)
        self.initArgs(parser)

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('ARGS',
                            nargs=argparse.REMAINDER)

    def execute(self, args):
        wm = self.getWorkspaceManager(args, checkInitialized=False)

        env = dict(os.environ)
        env.update(wm.getLeafEnvironment().toMap())
        env.update(wm.getUserEnvironment().toMap())
        if wm.isWorkspaceInitialized():
            env.update(wm.getWorkspaceEnvironment().toMap())

        # Use args to run the external command
        command = [str(self.executable)]
        command += args.ARGS

        return subprocess.call(command, env=env)


def grepDescription(file):
    try:
        with open(str(file), 'rb') as fp:
            header = fp.read(HEADER_SIZE)
            if MOTIF.encode() in header:
                for line in header.decode().splitlines():
                    if MOTIF in line:
                        return line.split(MOTIF, 1)[1].strip()
    except Exception:
        pass


def findLeafExternalCommands(blacklistCommands=None):
    '''
    Find leaf-XXX binaries in $PATH to build external commands
    @param blacklistCommands: do not use commands with name in list
    @return: ExternalCommands list
    '''
    out = OrderedDict()
    pathFolderList = os.environ["PATH"].split(pathsep)
    for pathFolder in map(Path, pathFolderList):
        if pathFolder.is_dir():
            for candidate in pathFolder.iterdir():
                if candidate.is_file() \
                        and candidate.name.startswith("leaf-") \
                        and os.access(str(candidate), os.X_OK):
                    name = candidate.name[5:]
                    if name in out:
                        # Command already found
                        continue
                    if blacklistCommands is not None and name in blacklistCommands:
                        # Command is blacklisted
                        continue
                    description = grepDescription(candidate)
                    if description is not None:
                        out[name] = ExternalCommand(
                            name, description, candidate)
    return out.values()
