'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafCommand
from leaf.core.workspacemanager import WorkspaceManager
from leaf.utils import findWorkspaceRoot


class StatusCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "status",
                             "print leaf status")

    def execute(self, args):
        wspath = findWorkspaceRoot(currentFolder=args.workspace,
                                   failIfNoWs=False)
        if wspath is not None:
            ws = WorkspaceManager(wspath, self.getPackageManager(args))
            self.getLogger(args).displayItem(ws)
        else:
            self.getLogger(args).printDefault(
                "Not in a workspace, use 'leaf init' to create one")
