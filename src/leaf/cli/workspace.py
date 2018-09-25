'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafCommand


class WorkspaceInitCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "init",
                             "initialize workspace")

    def execute(self, args):
        wm = self.getWorkspaceManager(args,
                                      autoFindWorkspace=False,
                                      checkInitialized=False)

        if wm.workspaceConfigFile.exists():
            raise ValueError("File %s already exist" %
                             str(wm.workspaceConfigFile))
        if wm.workspaceDataFolder.exists():
            raise ValueError("Folder %s already exist" %
                             str(wm.workspaceDataFolder))
        wm.readWorkspaceConfiguration(initIfNeeded=True)
        wm.logger.printDefault("Workspace initialized", wm.workspaceRootFolder)
