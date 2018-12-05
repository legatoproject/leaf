'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from abc import ABC, abstractmethod
from argparse import RawTextHelpFormatter
from builtins import ValueError
from pathlib import Path

from leaf.core.error import LeafException
from leaf.core.packagemanager import LoggerManager, PackageManager
from leaf.core.workspacemanager import WorkspaceManager
from leaf.format.logger import Verbosity
from leaf.model.base import Scope


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


class GenericCommand(ABC):
    '''
    Generic command used by leaf
    '''

    def __init__(self, cmdName, cmdHelp, cmdExamples=None):
        self.cmdName = cmdName
        self.cmdHelp = cmdHelp
        self.cmdExamples = cmdExamples

    def isHandled(self, cmd):
        return cmd == self.cmdName

    def _buildExampleText(self):
        out = None
        if self.cmdExamples is not None:
            out = "example%s: " % ("s" if len(self.cmdExamples) > 1 else "")
            for command, text in self.cmdExamples:
                out += "\n  %s\n    $ %s" % (text, command)
        return out

    def create(self, subparsers):
        parser = subparsers.add_parser(self.cmdName,
                                       help=self.cmdHelp,
                                       epilog=self._buildExampleText(),
                                       formatter_class=RawTextHelpFormatter)
        self.initArgs(parser)

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

    @abstractmethod
    def initArgs(self, parser):
        pass

    @abstractmethod
    def execute(self, args):
        pass

    def doExecute(self, args):
        try:
            out = self.execute(args)
            return 0 if out is None else out
        except Exception as e:
            exitCode = 2
            lm = self.getLoggerManager(args)
            if isinstance(e, LeafException):
                lm.printException(e)
                exitCode = e.exitCode
            else:
                lm.logger.printError(e)
            return exitCode


class LeafMetaCommand(GenericCommand):
    '''
    Generic class to represent commands that have subcommands
    '''

    def __init__(self, cmdName, cmdHelp, cmdExamples=None, externalCommandsPrefix=None):
        GenericCommand.__init__(self, cmdName, cmdHelp,
                                cmdExamples=cmdExamples)
        self.externalCommandsPrefix = externalCommandsPrefix

    def initArgs(self, parser):
        super().initArgs(parser)
        subparsers = parser.add_subparsers(dest='subCommand',
                                           description='supported subcommands',
                                           metavar="SUBCOMMAND",
                                           help='actions to execute')

        self.subCommands = []
        self.defaultSubCommand = self.getDefaultSubCommand()
        if self.defaultSubCommand is None:
            subparsers.required = True
        else:
            subparsers.required = False
            self.subCommands.append(self.defaultSubCommand)

        self.subCommands += self.getSubCommands()
        if self.externalCommandsPrefix is not None:
            from leaf.cli.external import ExternalCommandUtils
            self.subCommands += ExternalCommandUtils.getCommands(
                prefix=self.externalCommandsPrefix,
                ignoreList=[cmd.cmdName for cmd in self.subCommands])

        for lc in self.subCommands:
            lc.create(subparsers)

    def execute(self, args):
        if args.subCommand is None:
            if self.defaultSubCommand is not None:
                return self.defaultSubCommand.execute(args)
        else:
            for subCommand in self.subCommands:
                if subCommand.isHandled(args.subCommand):
                    return subCommand.execute(args)
        # Should not happen, handled by argparse
        raise ValueError()

    @abstractmethod
    def getSubCommands(self):
        return []

    def getDefaultSubCommand(self):
        return None


class LeafCommand(GenericCommand):
    '''
    Define a leaf commands which uses -v/-q to set the logger verbosity
    '''

    def __init__(self, cmdName, cmdHelp, cmdExamples=None):
        GenericCommand.__init__(self, cmdName, cmdHelp,
                                cmdExamples=cmdExamples)

    def initArgs(self, parser):
        super().initArgs(parser)
        addVerboseQuietArgs(parser)


def stringToBoolean(value):
    if value.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif value.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ValueError('Boolean value expected.')
