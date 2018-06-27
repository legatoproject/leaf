'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafCommand


class SelectCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "select",
                             "change current profile and install missing packages")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('profiles', nargs=1,
                            metavar='PROFILE', help='the profile name'),

    def execute(self, args):
        ws = self.getWorkspace(args)
        name = args.profiles[0]
        profile = ws.getProfile(name)
        ws.switchProfile(profile)
        ws.provisionProfile(profile)
