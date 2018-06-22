'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafCommand
from leaf.constants import LeafFiles
from pathlib import Path


class ConfigCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "config",
                             "update user configuration")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('--root',
                            dest='rootFolder',
                            metavar='DIR',
                            type=Path,
                            help="set the root folder, default: %s" % LeafFiles.DEFAULT_LEAF_ROOT)

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getApp(args, logger)
        app.updateUserConfiguration(rootFolder=args.rootFolder)
        logger.printDefault("Configuration file: %s" % app.configurationFile)
