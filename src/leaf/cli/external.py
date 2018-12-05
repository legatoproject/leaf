'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse
import os
import subprocess
from collections import OrderedDict
from os.path import pathsep
from pathlib import Path

from leaf.cli.cliutils import GenericCommand


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

        # Use args to run the external command
        command = [str(self.executable)]
        command += args.ARGS

        return subprocess.call(command, env=env)


class ExternalCommandUtils():
    '''
    Find leaf-XXX binaries in $PATH to build external commands
    '''

    COMMANDS = None
    MOTIF = 'LEAF_DESCRIPTION'
    HEADER_SIZE = 2048

    @staticmethod
    def grepDescription(file):
        try:
            with open(str(file), 'rb') as fp:
                header = fp.read(ExternalCommandUtils.HEADER_SIZE)
                if ExternalCommandUtils.MOTIF.encode() in header:
                    for line in header.decode().splitlines():
                        if ExternalCommandUtils.MOTIF in line:
                            return line.split(ExternalCommandUtils.MOTIF, 1)[1].strip()
        except Exception:
            pass

    @staticmethod
    def scanPath():
        out = []
        folderList = os.environ["PATH"].split(pathsep)
        for folder in map(Path, folderList):
            out += ExternalCommandUtils.scanFolder(folder)
        return out

    @staticmethod
    def scanFolder(folder):
        out = []
        if isinstance(folder, Path) and folder.is_dir():
            for candidate in folder.iterdir():
                if candidate.is_file() and candidate.name.startswith("leaf-") and os.access(str(candidate), os.X_OK):
                    segments = candidate.name.split('-')[1:]
                    description = ExternalCommandUtils.grepDescription(
                        candidate)
                    if description is not None:
                        out.append((segments, description, candidate))
        return out

    @staticmethod
    def getCommands(prefix=(), ignoreList=None):
        if ExternalCommandUtils.COMMANDS is None:
            ExternalCommandUtils.COMMANDS = ExternalCommandUtils.scanPath()

        out = OrderedDict()
        for segments, description, binary in ExternalCommandUtils.COMMANDS:
            # Filter leaf-PREFIX1-PREFIX2-XXX only, where XXX will be the name
            if len(segments) == len(prefix) + 1 and segments[:len(prefix)] == list(prefix):
                name = segments[-1]
                if ignoreList is not None and name in ignoreList:
                    # Ignore command
                    continue
                if name in out:
                    # Command already found
                    continue
                out[name] = ExternalCommand(name, description, binary)
        return out.values()
