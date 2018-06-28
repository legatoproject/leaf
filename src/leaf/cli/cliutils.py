'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from abc import abstractmethod, ABC
from collections import OrderedDict
import os
from pathlib import Path
import traceback

from leaf.format.logger import Verbosity, TextLogger
from leaf.core.packagemanager import PackageManager
from leaf.core.workspacemanager import WorkspaceManager
from leaf.model.base import Scope
from leaf.utils import findWorkspaceRoot


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

    def __init__(self, cmdName, cmdHelp):
        self.cmdName = cmdName
        self.cmdHelp = cmdHelp

    def isHandled(self, cmd):
        return cmd == self.cmdName

    def create(self, subparsers):
        parser = subparsers.add_parser(self.cmdName,
                                       help=self.cmdHelp)
        self.initArgs(parser)

    def getLoggerAttr(self, args):
        nonInteractive = False
        verbosity = Verbosity.DEFAULT
        if hasattr(args, 'verbosity'):
            verbosity = getattr(args, 'verbosity')
        if hasattr(args, 'nonInteractive'):
            nonInteractive = getattr(args, 'nonInteractive')
        return (verbosity, nonInteractive)

    def getLogger(self, args):
        loggerAttr = self.getLoggerAttr(args)
        return TextLogger(loggerAttr[0], loggerAttr[1])

    def getPackageManager(self, args):
        loggerAttr = self.getLoggerAttr(args)
        return PackageManager(self.getLogger(args), loggerAttr[1])

    def getWorkspace(self, args, autoFindWorkspace=True, checkInitialized=True):
        wspath = None
        if args is not None and args.workspace is not None:
            wspath = args.workspace
        elif autoFindWorkspace:
            wspath = findWorkspaceRoot(failIfNoWs=checkInitialized)
        if wspath is None:
            wspath = Path(os.getcwd())
        out = WorkspaceManager(wspath, self.getPackageManager(args))
        if checkInitialized and not out.isInitialized():
            raise ValueError("Workspace is not initialized")
        return out

    @abstractmethod
    def initArgs(self, parser):
        pass

    @abstractmethod
    def execute(self, args):
        pass

    def doExecute(self, args, catchException=False):
        try:
            out = self.execute(args)
            return 0 if out is None else out
        except Exception as e:
            if not catchException:
                raise e
            logger = self.getLogger(args)
            logger.printError(e)
            if logger.isVerbose():
                traceback.print_exc()
            return 2


class LeafMetaCommand(GenericCommand):
    '''
    Generic class to represent commands that have subcommands
    '''

    def __init__(self, cmdName, cmdHelp):
        GenericCommand.__init__(self, cmdName, cmdHelp)

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

    def __init__(self, cmdName, cmdHelp):
        GenericCommand.__init__(self, cmdName, cmdHelp)

    def initArgs(self, parser):
        super().initArgs(parser)
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


class LeafCommandGenerator():

    def __init__(self):
        self.preVerbArgs = OrderedDict()
        self.postVerbArgs = OrderedDict()

    def initCommonArgs(self, args):
        # Alt config/ws
        if args.workspace is not None:
            self.preVerbArgs["--workspace"] = args.workspace
        if args.nonInteractive:
            self.preVerbArgs["--non-interactive"] = None
        # Verbose, Quiet
        if args.verbosity == Verbosity.VERBOSE:
            self.postVerbArgs["--verbose"] = None
        elif args.verbosity == Verbosity.QUIET:
            self.postVerbArgs["--quiet"] = None

    def genCommand(self, verb, arguments=None):
        command = []

        for k, v in self.preVerbArgs.items():
            if v is None:
                command.append(k)
            else:
                command += [k, str(v)]

        if isinstance(verb, (list, tuple)):
            command += verb
        else:
            command.append(verb)

        for k, v in self.postVerbArgs.items():
            if v is None:
                command.append(k)
            else:
                command += [k, str(v)]

        if arguments is not None:
            command += list(map(str, arguments))

        return command
