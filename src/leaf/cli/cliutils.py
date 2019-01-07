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
from abc import ABC, abstractmethod
from builtins import ValueError
from collections import OrderedDict
from os.path import pathsep
from pathlib import Path

from leaf.constants import LeafConstants
from leaf.core.error import LeafException, UnknownArgsException
from leaf.core.packagemanager import LoggerManager, PackageManager
from leaf.core.workspacemanager import WorkspaceManager
from leaf.format.logger import Verbosity
from leaf.model.base import Scope


def stringToBoolean(value):
    if value.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif value.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ValueError('Boolean value expected.')


def addVerboseQuietArgs(parser):
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose",
                       dest="verbosity",
                       action='store_const',
                       const=Verbosity.VERBOSE,
                       default=Verbosity.DEFAULT,
                       help="increase output verbosity")
    group.add_argument("-q", "--quiet",
                       dest="verbosity",
                       action='store_const',
                       const=Verbosity.QUIET,
                       help="decrease output verbosity")


def initCommonArgs(parser,
                   addRemoveEnv=False,
                   withEnvScripts=False,
                   addRemovePackages=False,
                   withScope=False):
    if addRemoveEnv:
        parser.add_argument('--set',
                            dest='envAddList',
                            action='append',
                            metavar='KEY=VALUE',
                            help='add given environment variable')
        parser.add_argument('--unset',
                            dest='envRmList',
                            action='append',
                            metavar='KEY',
                            help='remote given environment variable')
    if withEnvScripts:
        parser.add_argument('--activate-script',
                            dest='activateScript',
                            metavar='FILE',
                            type=Path,
                            help="create a script to activate the env variables")
        parser.add_argument('--deactivate-script',
                            dest='deactivateScript',
                            metavar='FILE',
                            type=Path,
                            help="create a script to deactivate the env variables")
    if addRemovePackages:
        parser.add_argument('-p', '--add-package',
                            dest='pkgAddList',
                            action='append',
                            metavar='PKGNAME',
                            help="add given package")
        parser.add_argument('--rm-package',
                            dest='pkgRmList',
                            action='append',
                            metavar='PKGNAME',
                            help="remove given package")
    if withScope:
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--user",
                           dest="envScope",
                           action="store_const",
                           const=Scope.USER,
                           default=Scope.PROFILE,
                           help="use user configuration environment")
        group.add_argument("--workspace",
                           dest="envScope",
                           action="store_const",
                           const=Scope.WORKSPACE,
                           help="use workspace environment")
        group.add_argument("--profile",
                           dest="envScope",
                           action="store_const",
                           const=Scope.PROFILE,
                           help="use profile environment")


class LeafCommand(ABC):
    '''
    Generic command used by leaf
    '''

    def __init__(self, name, description,
                 addVerboseQuietArgs=True,
                 allowUnknownArgs=False):
        self.name = name
        self.parent = None
        self.description = description
        self.addVerboseQuietArgs = addVerboseQuietArgs
        self.allowUnknownArgs = allowUnknownArgs

    def _getCommandPath(self):
        if self.name is None:
            return ()
        if not isinstance(self.parent, LeafMetaCommand):
            return (self.name,)
        return self.parent._getCommandPath() + (self.name, )

    def _getExamples(self):
        '''
        Return a list of (text, command) to be printed in help epilog
        '''
        return None

    def _getEpilogText(self):
        '''
        Create the epilog text
        '''
        out = None
        examples = self._getExamples()
        if examples is not None:
            out = "example%s: " % ("s" if len(examples) > 1 else "")
            for command, text in examples:
                out += "\n  %s\n    $ %s" % (text, command)
        return out

    def _createParser(self, subparsers):
        return subparsers.add_parser(self.name,
                                     help=self.description,
                                     epilog=self._getEpilogText(),
                                     formatter_class=argparse.RawTextHelpFormatter)

    def _configureParser(self, parser):
        pass

    def setup(self, subparsers):
        p = self._createParser(subparsers)
        p.set_defaults(handler=self)
        if self.addVerboseQuietArgs:
            addVerboseQuietArgs(p)
        self._configureParser(p)
        return p

    @abstractmethod
    def execute(self, args, uargs):
        pass

    def safeExecute(self, args, uargs):
        out = 0
        try:
            if uargs is not None and len(uargs) > 0 and not self.allowUnknownArgs:
                raise UnknownArgsException(self._getCommandPath(), uargs)
            out = self.execute(args, uargs)
        except Exception as e:
            lm = self.getLoggerManager(args)
            if isinstance(e, LeafException):
                lm.printException(e)
                out = e.exitCode
            else:
                lm.logger.printError(e)
                out = LeafConstants.DEFAULT_ERROR_RC
        return out if out is not None else 0

    def getVerbosity(self, args, default=Verbosity.DEFAULT):
        if hasattr(args, 'verbosity'):
            return getattr(args, 'verbosity')
        return default

    def getLoggerManager(self, args):
        return LoggerManager(self.getVerbosity(args))

    def getPackageManager(self, args):
        return PackageManager(self.getVerbosity(args))

    def getWorkspaceManager(self, args, autoFindWorkspace=True, checkInitialized=True):
        wsRoot = WorkspaceManager.findRoot(checkParents=autoFindWorkspace)
        out = WorkspaceManager(wsRoot, self.getVerbosity(args))
        if checkInitialized and not out.isWorkspaceInitialized():
            raise ValueError("Workspace is not initialized")
        return out


class LeafMetaCommand(LeafCommand):
    '''
    Generic class to represent commands that have subcommands
    '''

    def __init__(self, name, description, commands,
                 acceptDefaultCommand=False,
                 enableExternalCommands=True):
        LeafCommand.__init__(self, name, description,
                             addVerboseQuietArgs=False)
        self.commands = commands
        self.acceptDefaultCommand = acceptDefaultCommand
        self.enableExternalCommands = enableExternalCommands
        # Link subcommands to current Meta command
        for c in self.commands:
            c.parent = self

    def _configureParser(self, parser):
        subparsers2 = parser.add_subparsers(description='supported subcommands',
                                            metavar="SUBCOMMAND",
                                            help='actions to execute')
        # Initialize all subcommand parsers
        for command in self.commands:
            command.setup(subparsers2)
        # If external commands are enabled, initialize parsers
        if self.enableExternalCommands:
            for c in ExternalCommandUtils.getCommands(prefix=self._getCommandPath(),
                                                      ignoreList=[c.name for c in self.commands]):
                c.setup(subparsers2)
        # If no default command, subparser is required
        subparsers2.required = not self.acceptDefaultCommand
        # Register default handler
        if self.acceptDefaultCommand:
            parser.set_defaults(handler=self.commands[0])

    def execute(self, args, uargs):
        raise NotImplementedError()


class ExternalCommand(LeafCommand):
    '''
    Wrapper to run external binaries as leaf subcommand.
    '''

    def __init__(self, name, description, executable):
        LeafCommand.__init__(self,
                             name,
                             description,
                             addVerboseQuietArgs=False)
        self.executable = executable

    def _createParser(self, subparsers):
        return subparsers.add_parser(self.name,
                                     help=self.description,
                                     prefix_chars='+',
                                     add_help=False)

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('ARGS',
                            nargs=argparse.REMAINDER)

    def execute(self, args, uargs):
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
