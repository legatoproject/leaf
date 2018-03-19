'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from leaf import __help_description__, __version__
from leaf.cli_packagemanager import ConfigCommand, CleanCommand, RemoteCommand,\
    FetchCommand, ListCommand, SearchCommand, DependsCommand, DownloadCommand,\
    ExtractCommand, InstallCommand, RemoveCommand, EnvCommand
from leaf.cli_profile import ProfileCommand
from leaf.cli_releng import PackCommand, IndexCommand
from leaf.constants import LeafFiles
from leaf.core import LeafApp
from leaf.logger import createLogger
from leaf.utils import checkPythonVersion
from pathlib import Path
import sys
import traceback


class LeafCli():

    def __init__(self):
        # Setup argument parser
        self.parser = ArgumentParser(description=__help_description__,
                                     formatter_class=RawDescriptionHelpFormatter)

        self.parser.add_argument("--json",
                                 dest="json",
                                 action="store_true",
                                 help="output json format")
        self.parser.add_argument('-V', '--version',
                                 action='version',
                                 version="v%s" % __version__)
        self.parser.add_argument("--config",
                                 metavar='CONFIG_FILE',
                                 dest="customConfig",
                                 type=Path,
                                 help="use custom configuration file")

        subparsers = self.parser.add_subparsers(dest='command',
                                                description='supported commands',
                                                metavar="COMMAND",
                                                help='actions to execute')
        subparsers.required = True

        self.commands = [
            # Package manader
            ConfigCommand(),
            CleanCommand(),
            RemoteCommand(),
            FetchCommand(),
            ListCommand(),
            SearchCommand(),
            DependsCommand(),
            DownloadCommand(),
            ExtractCommand(),
            InstallCommand(),
            RemoveCommand(),
            EnvCommand(),
            # Releng
            PackCommand(),
            IndexCommand(),
            # Profile
            ProfileCommand()]

        for command in self.commands:
            command.create(subparsers)

    def execute(self, args0):
        args = self.parser.parse_args(args0)
        logger = createLogger(args.verbose, args.quiet, args.json)

        configFile = LeafFiles.DEFAULT_CONFIG_FILE
        if args.customConfig is not None:
            configFile = args.customConfig

        app = LeafApp(logger, configFile)
        try:
            for cmd in self.commands:
                if cmd.isHandled(args.command):
                    return cmd.execute(app, logger, args)
            raise ValueError("Cannot find command for " + args.command)
        except Exception as e:
            logger.printError(e)
            if logger.isVerbose():
                traceback.print_exc()
            return 2


def main():
    checkPythonVersion()
    return LeafCli().execute(sys.argv[1:])
