'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from abc import abstractmethod, ABC
from collections import OrderedDict
from leaf.core import Workspace, LeafApp
from leaf.logger import createLogger
from leaf.utils import findWorkspaceRoot
import os
from pathlib import Path
import traceback


def initCommonArgs(subparser, withEnv=False, withRemotes=False, withPackages=False, profileNargs=None):
    if withEnv:
        subparser.add_argument('--set',
                               dest='setEnvList',
                               action='append',
                               metavar='KEY=VALUE',
                               help='add given environment variable')
        subparser.add_argument('--unset',
                               dest='unsetEnvList',
                               action='append',
                               metavar='KEY',
                               help='remote given environment variable')
    if withRemotes:
        subparser.add_argument('--add-remote',
                               dest='addRemoteList',
                               action='append',
                               metavar='URL',
                               help='add given remote url')
        subparser.add_argument('--rm-remote',
                               dest='rmRemoteList',
                               action='append',
                               metavar='URL',
                               help='remove given remote url')
    if withPackages:
        subparser.add_argument('-p', '--package',
                               dest='motifList',
                               action='append',
                               metavar='PACKAGE',
                               help="add given packages to the current profile")
    if profileNargs is not None:
        subparser.add_argument('profiles',
                               metavar='PROFILE_NAME',
                               nargs=profileNargs,
                               help='the profile name')


class GenericCommand(ABC):
    '''
    Generic command used by leaf
    '''

    def __init__(self, cmdName, cmdHelp, cmdAliases=None):
        self.cmdName = cmdName
        self.cmdHelp = cmdHelp
        self.cmdAliases = [] if cmdAliases is None else cmdAliases

    def isHandled(self, cmd):
        return cmd == self.cmdName or cmd in self.cmdAliases

    def create(self, subparsers):
        parser = subparsers.add_parser(self.cmdName,
                                       help=self.cmdHelp,
                                       aliases=self.cmdAliases)
        self.initArgs(parser)

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
            traceback.print_exc()
            return 2


class LeafCommand(GenericCommand):
    '''
    Define a leaf commands which uses -v/-q to set the logger verbosity
    '''

    def __init__(self, cmdName, cmdHelp, cmdAliases=None):
        GenericCommand.__init__(self, cmdName, cmdHelp, cmdAliases)

    def initArgs(self, parser):
        GenericCommand.initArgs(self, parser)
        parser.add_argument("-v", "--verbose",
                            dest="verbose",
                            action='store_true',
                            help="increase output verbosity")
        parser.add_argument("-q", "--quiet",
                            dest="quiet",
                            action='store_true',
                            help="decrease output verbosity")

    def getLogger(self, args):
        return createLogger(args.verbose, args.quiet, args.nonInteractive)

    def getApp(self, args, logger=None):
        if logger is None:
            logger = self.getLogger(args)
        return LeafApp(logger, nonInteractive=args.nonInteractive)

    def getWorkspace(self, args, autoFindWorkspace=True, app=None):
        wspath = None
        if args is not None and args.workspace is not None:
            wspath = args.workspace
        elif autoFindWorkspace:
            wspath = findWorkspaceRoot()
        else:
            wspath = Path(os.getcwd())

        if app is None:
            app = self.getApp(args)
        return Workspace(wspath, app)

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
        if args.verbose:
            self.postVerbArgs["--verbose"] = None
        if args.quiet:
            self.postVerbArgs["--quiet"] = None

    def genCommand(self, verb, arguments=None):
        command = []

        for k, v in self.preVerbArgs.items():
            if v is None:
                command.append(k)
            else:
                command += [k, str(v)]

        if isinstance(verb, list):
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
