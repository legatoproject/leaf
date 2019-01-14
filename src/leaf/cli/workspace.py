'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafCommand
from leaf.core.error import LeafException


class WorkspaceInitCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            'init',
            "initialize workspace")

    def execute(self, args, uargs):
        wm = self.getWorkspaceManager(args,
                                      autoFindWorkspace=False,
                                      checkInitialized=False)
        if wm.workspaceConfigFile.exists():
            raise LeafException("Workspace is already initialized (file %s already exists)" %
                                wm.workspaceConfigFile)
        if wm.workspaceDataFolder.exists():
            raise LeafException("Workspace is already initialized (folder %s already exists" %
                                wm.workspaceDataFolder)
        wm.readWorkspaceConfiguration(initIfNeeded=True)
        wm.logger.printDefault("Workspace initialized", wm.workspaceRootFolder)
