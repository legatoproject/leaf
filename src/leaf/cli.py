'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from abc import abstractmethod, ABC
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from leaf import __help_description__, __version__
from leaf.constants import LeafFiles
from leaf.core import LeafApp
from leaf.logger import createLogger
from leaf.utils import checkPythonVersion
from pathlib import Path
import sys
import traceback


class LeafCli():

    def __init__(self, *commands):
        checkPythonVersion()

        # Setup argument parser
        self.parser = ArgumentParser(description=__help_description__,
                                     formatter_class=RawDescriptionHelpFormatter)

        self.parser.add_argument('-V', '--version',
                                 action='version',
                                 version="v%s" % __version__)
        self.parser.add_argument("--config",
                                 metavar='CONFIG_FILE',
                                 dest="customConfig",
                                 type=Path,
                                 help="use custom configuration file")
        self.parser.add_argument("-y", "--non-interactive",
                                 dest="nonInteractive",
                                 action='store_true',
                                 help="assume yes if a confirmation is asked")

        subparsers = self.parser.add_subparsers(dest='command',
                                                description='supported commands',
                                                metavar="COMMAND",
                                                help='actions to execute')
        subparsers.required = True
        self.commands = commands
        for command in self.commands:
            command.create(subparsers)

    def run(self, customArgs=None):
        args = self.parser.parse_args(sys.argv[1:]
                                      if customArgs is None
                                      else customArgs)
        logger = createLogger(args.verbose, args.quiet, args.nonInteractive)

        configFile = LeafFiles.DEFAULT_CONFIG_FILE
        if args.customConfig is not None:
            configFile = args.customConfig

        app = LeafApp(logger, configFile)
        try:
            for cmd in self.commands:
                if cmd.isHandled(args.command):
                    return cmd.execute(app, logger, args)
            raise ValueError("Cannot find command for %s" % args.command)
        except Exception as e:
            logger.printError(e)
            if logger.isVerbose():
                traceback.print_exc()
            return 2


class LeafCommand(ABC):
    '''
    Abstract class to define parser for leaf commands
    '''

    def __init__(self, commandName, commandHelp, commandAlias=None):
        self.commandName = commandName
        self.commandHelp = commandHelp
        self.commandAlias = commandAlias

    def isHandled(self, cmd):
        return cmd == self.commandName or cmd == self.commandAlias

    def create(self, subparsers):
        parser = subparsers.add_parser(self.commandName,
                                       help=self.commandHelp,
                                       aliases=[] if self.commandAlias is None else [self.commandAlias])
        self.initArgs(parser)

    def initArgs(self, subparser):
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
