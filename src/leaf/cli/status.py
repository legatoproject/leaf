'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafCommand
from leaf.cli.profile import computeProfileInfo
from leaf.core.workspacemanager import WorkspaceManager

from leaf.core.error import NoProfileSelected
from leaf.format.renderer.status import StatusRenderer


class StatusCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "status",
                             "print leaf status")

    def execute(self, args):
        wsRoot = WorkspaceManager.findRoot()
        if not WorkspaceManager.isWorkspaceRoot(wsRoot):
            self.getLoggerManager(args).logger.printDefault(
                "Not in a workspace, use 'leaf init' to create one")
        else:
            wm = WorkspaceManager(wsRoot, self.getVerbosity(args))

            pfs = wm.listProfiles().values()
            pfsCount = len(pfs)
            if pfsCount == 0:
                wm.printHints(
                    "There is no profile yet. You should create a new profile xxx with 'leaf profile create xxx'")
                return

            # Current profile
            try:
                currentPfName = wm.getCurrentProfileName()
                currentProfile = wm.getProfile(currentPfName)

                # Sync and dependencies
                profileInfos = computeProfileInfo(wm, currentProfile)

                # Other profiles
                profileInfos["otherProfiles"] = [
                    prof for prof in pfs if prof.name != currentProfile.name]

                wm.printRenderer(StatusRenderer(workspaceRootFolder=wsRoot,
                                                currentProfile=currentProfile,
                                                **profileInfos))
            except NoProfileSelected as nps:
                # Just print, return code is still 0
                wm.printException(nps)
