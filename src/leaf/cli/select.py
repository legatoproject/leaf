'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafCommand


class SelectCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            'select',
            "change current profile and install missing packages")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('profiles', nargs=1,
                            metavar='PROFILE', help='the profile name'),

    def execute(self, args, uargs):
        wm = self.getWorkspaceManager()

        name = args.profiles[0]
        profile = wm.getProfile(name)
        wm.switchProfile(profile)
        wm.provisionProfile(profile)
