"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from pathlib import Path

from leaf.api import PackageManager
from leaf.cli.base import LeafCommand
from leaf.core.constants import LeafFiles


class ConfigCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "config", "update user configuration")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument(
            "--root",
            dest="install_folder",
            metavar="DIR",
            type=Path,
            help="set the root folder, default: {default}".format(default=LeafFiles.DEFAULT_LEAF_ROOT),
        )

    def execute(self, args, uargs):
        pm = PackageManager()
        if args.install_folder is not None:
            pm.set_install_folder(args.install_folder)
        config_file = pm.configuration_file
        if config_file is not None:
            pm.logger.print_default("Configuration file: {file}".format(file=config_file))
