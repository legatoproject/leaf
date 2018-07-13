'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafCommand
from leaf.core.workspacemanager import WorkspaceManager


class StatusCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "status",
                             "print leaf status")

    def execute(self, args):
        wsRoot = WorkspaceManager.findRoot(customPath=args.workspace)
        if not WorkspaceManager.isWorkspaceRoot(wsRoot):
            self.getLogger(args).printDefault(
                "Not in a workspace, use 'leaf init' to create one")
        else:
            ws = WorkspaceManager(wsRoot, self.getPackageManager(args))
            self.getLogger(args).displayItem(ws)