"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from leaf.cli.base import LeafCommand
from leaf.cli.completion import complete_profiles


class SelectCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "select", "change current profile and install missing packages")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("profiles", nargs=1, metavar="PROFILE", help="the profile name").completer = complete_profiles

    def execute(self, args, uargs):
        wm = self.get_workspacemanager()

        name = args.profiles[0]
        profile = wm.get_profile(name)
        wm.switch_profile(profile)
        wm.provision_profile(profile)
