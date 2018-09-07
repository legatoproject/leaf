'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from pathlib import Path

from leaf.cli.cliutils import LeafCommand
from leaf.constants import LeafFiles


class ConfigCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            "config",
            "update user configuration")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument(
            '--root',
            dest='rootFolder',
            metavar='DIR',
            type=Path,
            help="set the root folder, default: %s" % LeafFiles.DEFAULT_LEAF_ROOT)

    def execute(self, args):
        pm = self.getPackageManager(args)
        if args.rootFolder is not None:
            pm.setInstallFolder(args.rootFolder)
        configurationFile = pm.getConfigurationFile(
            LeafFiles.CONFIG_FILENAME, checkExists=True)
        if configurationFile is not None:
            pm.logger.printDefault(
                "Configuration file: %s" % configurationFile)
