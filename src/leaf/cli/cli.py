'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argcomplete
from argparse import RawDescriptionHelpFormatter, ArgumentParser
from pathlib import Path
import sys

from leaf import __help_description__, __version__
from leaf.cli.config import ConfigCommand
from leaf.cli.env import EnvMetaCommand
from leaf.cli.external import findLeafExternalCommands
from leaf.cli.feature import FeatureMetaCommand
from leaf.cli.package import PackageMetaCommand
from leaf.cli.profile import ProfileMetaCommand
from leaf.cli.remote import RemoteMetaCommand
from leaf.cli.repository import RepositoryMetaCommand
from leaf.cli.search import SearchCommand
from leaf.cli.select import SelectCommand
from leaf.cli.setup import SetupCommand
from leaf.cli.status import StatusCommand
from leaf.cli.workspace import WorkspaceInitCommand
from leaf.utils import checkPythonVersion


class LeafCli():

    def __init__(self):
        checkPythonVersion()

        self.commands = [
            # Common commands
            StatusCommand(),
            SearchCommand(),
            SetupCommand(),
            SelectCommand(),
            # Env
            EnvMetaCommand(),
            # Features
            FeatureMetaCommand(),
            # Workspace common operations
            WorkspaceInitCommand(),
            ProfileMetaCommand(),
            # Config & remotes
            ConfigCommand(),
            RemoteMetaCommand(),
            # Packages
            PackageMetaCommand(),
            # Releng
            RepositoryMetaCommand()
        ]
        self.commands += findLeafExternalCommands(
            blacklistCommands=[cmd.cmdName for cmd in self.commands])

        # Setup argument parser
        apkw = {'description': __help_description__,
                'formatter_class': RawDescriptionHelpFormatter}
        # Disable args abbreviation, only supported in 3.5+
        if sys.version_info > (3, 5):
            apkw['allow_abbrev'] = False

        self.parser = ArgumentParser(**apkw)

        self.parser.add_argument('-V', '--version',
                                 action='version',
                                 version="leaf version %s" % __version__)
        self.parser.add_argument("--non-interactive",
                                 dest="nonInteractive",
                                 action='store_true',
                                 help="assume yes if a confirmation is asked")
        self.parser.add_argument("-w", "--workspace",
                                 dest="workspace",
                                 type=Path,
                                 help="use given workspace")

        subparsers = self.parser.add_subparsers(dest='command',
                                                description='supported commands',
                                                metavar="COMMAND",
                                                help='actions to execute')
        subparsers.required = True
        for command in self.commands:
            command.create(subparsers)
        argcomplete.autocomplete(self.parser)

    def run(self, argv, handleExceptions=True):
        args = self.parser.parse_args(argv)
        for cmd in self.commands:
            if cmd.isHandled(args.command):
                return cmd.doExecute(args, catchException=handleExceptions)
        raise ValueError("Cannot find command for %s" % args.command)
