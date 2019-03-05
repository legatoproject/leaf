import argparse
from abc import ABC, abstractmethod
from argparse import Namespace

from leaf.api import LoggerManager, WorkspaceManager
from leaf.cli.cliutils import EnvSetterAction
from leaf.core.constants import LeafConstants, LeafSettings
from leaf.core.error import LeafException, UnknownArgsException, WorkspaceNotInitializedException

"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""


class LeafCommand(ABC):

    """
    Generic command used by leaf
    """

    def __init__(self, name, description, allow_uargs=False):
        self.__name = name
        self.__parent = None
        self.__description = description
        self.__allow_uargs = allow_uargs

    @property
    def name(self):
        return self.__name

    @property
    def description(self):
        return self.__description

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, cmd):
        self.__parent = cmd

    @property
    def path(self):
        """
        Returns the command path, a tuple a the command/subcommands to invoke the command.
        """
        if isinstance(self.parent, LeafCommand):
            return self.parent.path + (self.name,)
        return (self.name,)

    def _get_examples(self):
        """
        Return a list of (text, command) to be printed in help epilog
        """
        return ()

    def _get_epilog_text(self):
        """
        Create the epilog text
        """
        out = None
        examples = self._get_examples()
        if examples is not None and len(examples) > 0:
            out = "example{s}: ".format(s=("s" if len(examples) > 1 else ""))
            for command, text in examples:
                out += "\n  {text}\n    $ {command}".format(text=text, command=command)
        return out

    def _create_parser(self, subparsers):
        """
        This method should not be overiden.
        """
        return subparsers.add_parser(self.name, help=self.description, epilog=self._get_epilog_text(), formatter_class=argparse.RawTextHelpFormatter)

    def _configure_parser(self, parser):
        """
        By default, add --verbose/--quiet options
        This method should be overiden to add options and arguments.
        """
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-v", "--verbose", action=EnvSetterAction, dest=LeafSettings.VERBOSITY.key, const="verbose", help="increase output verbosity")
        group.add_argument("-q", "--quiet", action=EnvSetterAction, dest=LeafSettings.VERBOSITY.key, const="quiet", help="decrease output verbosity")

    def setup(self, subparsers):
        p = self._create_parser(subparsers)
        p.set_defaults(handler=self)
        self._configure_parser(p)
        return p

    @abstractmethod
    def execute(self, args: Namespace, uargs: list):
        pass

    def safe_execute(self, args: Namespace, uargs: list):
        out = 0
        try:
            if uargs is not None and len(uargs) > 0 and not self.__allow_uargs:
                raise UnknownArgsException(uargs)
            out = self.execute(args, uargs)
        except Exception as e:
            lm = LoggerManager()
            if isinstance(e, LeafException):
                lm.print_exception(e)
                out = e.exit_code
            else:
                lm.logger.print_error(e)
                out = LeafConstants.DEFAULT_ERROR_RC
        return out if out is not None else 0

    def get_workspacemanager(self, check_parents=True, check_initialized=True):
        out = WorkspaceManager(WorkspaceManager.find_root(check_parents=check_parents))
        if check_initialized and not out.is_initialized:
            raise WorkspaceNotInitializedException()
        return out
