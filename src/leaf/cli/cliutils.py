'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import argparse
import os
from abc import ABC, abstractmethod
from argparse import Action
from builtins import ValueError
from pathlib import Path

from leaf.api import LoggerManager, WorkspaceManager
from leaf.core.constants import LeafConstants, LeafSettings
from leaf.core.error import (LeafException, UnknownArgsException,
                             WorkspaceNotInitializedException)
from leaf.model.base import Scope


def stringToBoolean(value):
    if value.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif value.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ValueError('Boolean value expected.')


class EnvSetterAction(Action):
    def __init__(self, *args, **kwargs):
        if 'nargs' not in kwargs:
            kwargs['nargs'] = 0
        Action.__init__(self, *args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        value = None
        if self.nargs == 0:
            if self.const is None:
                raise ValueError()
            value = self.const
        elif self.nargs == 1:
            if values[0] is None:
                raise ValueError()
            value = values[0]
        else:
            raise ValueError()
        if value is None:
            raise ValueError("Cannot set null value for %s" % self.dest)
        os.environ[self.dest] = str(value)


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
                 allowUnknownArgs=False):
        self.name = name
        self.parent = None
        self.description = description
        self.allowUnknownArgs = allowUnknownArgs

    @property
    def path(self):
        '''
        Returns the command path, a tuple a the command/subcommands to invoke the command.
        '''
        if self.name is None:
            return ()
        if not isinstance(self.parent, LeafMetaCommand):
            return (self.name,)
        return self.parent.path + (self.name, )

    def _getExamples(self):
        '''
        Return a list of (text, command) to be printed in help epilog
        '''
        return ()

    def _getEpilogText(self):
        '''
        Create the epilog text
        '''
        out = None
        examples = self._getExamples()
        if examples is not None and len(examples) > 0:
            out = "example%s: " % ("s" if len(examples) > 1 else "")
            for command, text in examples:
                out += "\n  %s\n    $ %s" % (text, command)
        return out

    def _createParser(self, subparsers):
        '''
        This method should not be overiden.
        '''
        return subparsers.add_parser(self.name,
                                     help=self.description,
                                     epilog=self._getEpilogText(),
                                     formatter_class=argparse.RawTextHelpFormatter)

    def _configureParser(self, parser):
        '''
        By default, add --verbose/--quiet options
        This method should be overiden to add options and arguments.
        '''
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-v", "--verbose",
                           action=EnvSetterAction,
                           dest=LeafSettings.VERBOSITY.key,
                           const="verbose",
                           help="increase output verbosity")
        group.add_argument("-q", "--quiet",
                           action=EnvSetterAction,
                           dest=LeafSettings.VERBOSITY.key,
                           const="quiet",
                           help="decrease output verbosity")

    def setup(self, subparsers):
        p = self._createParser(subparsers)
        p.set_defaults(handler=self)
        self._configureParser(p)
        return p

    @abstractmethod
    def execute(self, args, uargs):
        pass

    def safeExecute(self, args, uargs):
        out = 0
        try:
            if uargs is not None and len(uargs) > 0 and not self.allowUnknownArgs:
                raise UnknownArgsException(uargs)
            out = self.execute(args, uargs)
        except Exception as e:
            lm = LoggerManager()
            if isinstance(e, LeafException):
                lm.printException(e)
                out = e.exitCode
            else:
                lm.logger.printError(e)
                out = LeafConstants.DEFAULT_ERROR_RC
        return out if out is not None else 0

    def getWorkspaceManager(self, autoFindWorkspace=True, checkInitialized=True):
        out = WorkspaceManager(WorkspaceManager.findRoot(
            checkParents=autoFindWorkspace))
        if checkInitialized and not out.isWorkspaceInitialized():
            raise WorkspaceNotInitializedException()
        return out


class LeafMetaCommand(LeafCommand):
    '''
    Generic class to represent commands that have subcommands
    '''

    def __init__(self, name, description, commands,
                 acceptDefaultCommand=False,
                 pluginManager=None):
        LeafCommand.__init__(self, name, description)
        self.commands = commands
        self.acceptDefaultCommand = acceptDefaultCommand
        self.pluginManager = pluginManager
        # Link subcommands to current Meta command
        for c in self.commands:
            c.parent = self

    def _configureParser(self, parser):
        # Add quiet/verbose
        super()._configureParser(parser)

        # Create sub parsers
        subparsers = parser.add_subparsers(description='supported subcommands',
                                           metavar="SUBCOMMAND",
                                           help='actions to execute')

        # Initialize all subcommand parsers
        for command in self.commands:
            command.setup(subparsers)
        # If external commands are enabled, initialize parsers
        if self.pluginManager is not None:
            for c in self.pluginManager.getCommands(self.path, [c.name for c in self.commands]):
                c.setup(subparsers)
        # If no default command, subparser is required
        subparsers.required = not self.acceptDefaultCommand
        # Register default handler
        if self.acceptDefaultCommand:
            parser.set_defaults(handler=self.commands[0])

    def execute(self, args, uargs):
        raise NotImplementedError()
