'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from pathlib import Path

from leaf.api import PackageManager
from leaf.cli.cliutils import LeafCommand
from leaf.core.constants import LeafFiles


class ConfigCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'config',
            "update user configuration")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('--root',
                            dest='rootFolder',
                            metavar='DIR',
                            type=Path,
                            help="set the root folder, default: %s" % LeafFiles.DEFAULT_LEAF_ROOT)

    def execute(self, args, uargs):
        pm = PackageManager()
        if args.rootFolder is not None:
            pm.setInstallFolder(args.rootFolder)
        configurationFile = pm.getConfigurationFile(
            LeafFiles.CONFIG_FILENAME, checkExists=True)
        if configurationFile is not None:
            pm.logger.printDefault(
                "Configuration file: %s" % configurationFile)
