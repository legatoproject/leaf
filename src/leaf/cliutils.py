'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from abc import abstractmethod, ABC
from collections import OrderedDict
from leaf.core import Workspace
from leaf.utils import findWorkspaceRoot
import os
from pathlib import Path


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


class LeafCommand(ABC):
    '''
    Abstract class to define parser for leaf commands
    '''

    def __init__(self, cmdName, cmdHelp, cmdAliases=None, addVerboseQuiet=True):
        self.cmdName = cmdName
        self.cmdHelp = cmdHelp
        self.cmdAliases = [] if cmdAliases is None else cmdAliases
        self.addVerboseQuiet = addVerboseQuiet

    def isHandled(self, cmd):
        return cmd == self.cmdName or cmd in self.cmdAliases

    def create(self, subparsers):
        parser = subparsers.add_parser(self.cmdName,
                                       help=self.cmdHelp,
                                       aliases=self.cmdAliases)
        self._initArgs(parser)

    def _initArgs(self, subparser):
        if self.addVerboseQuiet:
            subparser.add_argument("-v", "--verbose",
                                   dest="verbose",
                                   action='store_true',
                                   help="increase output verbosity")
            subparser.add_argument("-q", "--quiet",
                                   dest="quiet",
                                   action='store_true',
                                   help="decrease output verbosity")
        self.internalInitArgs(subparser)

    def execute(self, app, logger, args):
        out = self.internalExecute(app, logger, args)
        return 0 if out is None else out

    @abstractmethod
    def internalInitArgs(self, subparser):
        pass

    @abstractmethod
    def internalExecute(self, app, logger, args):
        pass


class LeafWsCommand(LeafCommand):
    '''
    Abstract class to define parser for leaf commands
    '''

    def __init__(self, cmdName, cmdHelp, cmdAliases=None, autoFindWorkspace=True):
        LeafCommand.__init__(self,
                             cmdName,
                             cmdHelp,
                             cmdAliases=cmdAliases,
                             addVerboseQuiet=True)
        self.autoFindWorkspace = autoFindWorkspace

    def execute(self, app, logger, args):
        wspath = None
        if args.workspace is not None:
            wspath = args.workspace
        elif self.autoFindWorkspace:
            wspath = findWorkspaceRoot()
        else:
            wspath = Path(os.getcwd())
        ws = Workspace(wspath, app)
        out = self.internalExecute2(ws, app, logger, args)
        return 0 if out is None else out

    @abstractmethod
    def internalInitArgs(self, subparser):
        pass

    @abstractmethod
    def internalExecute2(self, ws, app, logger, args):
        pass

    def internalExecute(self, app, logger, args):
        raise ValueError("Internal Error")


class LeafCommandGenerator():

    def __init__(self):
        self.preVerbArgs = OrderedDict()
        self.postVerbArgs = OrderedDict()

    def initCommonArgs(self, args):
        # Alt config/ws
        if args.customConfig is not None:
            self.preVerbArgs["--config"] = args.customConfig
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
