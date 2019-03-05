"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from leaf.cli.base import LeafCommand
from leaf.cli.commands.profile import _compute_profile_info
from leaf.core.error import NoProfileSelected
from leaf.rendering.renderer.status import StatusRenderer


class StatusCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "status", "print leaf status")

    def execute(self, args, uargs):
        wm = self.get_workspacemanager(check_initialized=False)
        if not wm.is_initialized:
            wm.logger.print_default("Not in a workspace, use 'leaf init' to create one")
        else:
            profiles = wm.list_profiles().values()
            profile_count = len(profiles)
            if profile_count == 0:
                wm.print_hints("There is no profile yet. You should create a new profile xxx with 'leaf profile create xxx'")
                return

            # Current profile
            try:
                current_pfname = wm.current_profile_name
                current_profile = wm.get_profile(current_pfname)

                # Sync and dependencies
                profile_infos = _compute_profile_info(wm, current_profile)

                # Other profiles
                profile_infos["other_profiles"] = list(filter(lambda pf: pf.name != current_pfname, profiles))

                wm.print_renderer(StatusRenderer(ws_root_folder=wm.ws_root_folder, current_profile=current_profile, **profile_infos))
            except NoProfileSelected as nps:
                # Just print, return code is still 0
                wm.print_exception(nps)
