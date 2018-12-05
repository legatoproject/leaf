'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import os
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path
from signal import SIGINT, signal

from leaf import __help_description__, __version__
from leaf.cli.build import BuildMetaCommand
from leaf.cli.config import ConfigCommand
from leaf.cli.env import EnvMetaCommand
from leaf.cli.external import ExternalCommandUtils
from leaf.cli.feature import FeatureMetaCommand
from leaf.cli.package import PackageMetaCommand
from leaf.cli.profile import ProfileMetaCommand
from leaf.cli.remote import RemoteMetaCommand
from leaf.cli.search import SearchCommand
from leaf.cli.select import SelectCommand
from leaf.cli.status import StatusCommand
from leaf.cli.workspace import WorkspaceInitCommand
from leaf.constants import EnvConstants
from leaf.core.error import UserCancelException
from leaf.utils import checkPythonVersion


class LeafCli():

    def __init__(self):
        checkPythonVersion()

        self.commands = [
            # Common commands
            StatusCommand(),
            SearchCommand(),
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
            BuildMetaCommand()
        ]
        self.commands += ExternalCommandUtils.getCommands(
            prefix=(),
            ignoreList=[cmd.cmdName for cmd in self.commands])

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
        try:
            import argcomplete
            argcomplete.autocomplete(self.parser)
        except ImportError:
            pass

    def catchSigInt(self):
        # Catch CTRL-C
        def signal_handler(sig, frame):
            raise UserCancelException()
        signal(SIGINT, signal_handler)

    def run(self, argv):
        self.catchSigInt()
        args = self.parser.parse_args(argv)
        if args.workspace is not None:
            os.environ[EnvConstants.WORKSPACE_ROOT] = str(args.workspace)
        if args.nonInteractive:
            os.environ[EnvConstants.NON_INTERACTIVE] = "1"
        for cmd in self.commands:
            if cmd.isHandled(args.command):
                return cmd.doExecute(args)
        raise ValueError("Cannot find command for %s" % args.command)
