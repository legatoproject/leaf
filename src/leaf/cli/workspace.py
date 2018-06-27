'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafCommand


class WorkspaceInitCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "init",
                             "initialize workspace")

    def execute(self, args):
        logger = self.getLogger(args)
        ws = self.getWorkspace(
            args, autoFindWorkspace=False, checkInitialized=False)

        if ws.configFile.exists():
            raise ValueError("File %s already exist" % str(ws.configFile))
        if ws.dataFolder.exists():
            raise ValueError("Folder %s already exist" % str(ws.dataFolder))
        ws.readConfiguration(initIfNeeded=True)
        logger.printDefault("Workspace initialized", ws.rootFolder)
