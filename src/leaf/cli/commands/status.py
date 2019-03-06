"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from leaf.cli.base import LeafCommand
from leaf.core.error import NoProfileSelected
from leaf.model.modelutils import find_manifest_list
from leaf.model.package import PackageIdentifier
from leaf.rendering.renderer.status import StatusRenderer


class StatusCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "status", "print leaf status")

    def execute(self, args, uargs):
        wm = self.get_workspacemanager(check_initialized=False)
        if not wm.is_initialized:
            wm.logger.print_default("Not in a workspace, use 'leaf init' to create one")
        else:
            ipmap = wm.list_installed_packages()
            profiles_map = wm.list_profiles()

            if len(profiles_map) == 0:
                wm.print_hints("There is no profile yet. You should create a new profile xxx with 'leaf profile create xxx'")
            else:
                # Current profile
                try:
                    renderer = StatusRenderer(wm.ws_root_folder, wm.build_ws_environment())

                    for profile in profiles_map.values():
                        sync = wm.is_profile_sync(profile)
                        iplist = []
                        if sync:
                            # if profile is sync, build the dependency list
                            iplist = wm.get_profile_dependencies(profile)
                        else:
                            # If profile is not sync, try to get installed packages for all included packages in profile
                            iplist = find_manifest_list(list(map(PackageIdentifier.parse, profile.packages)), ipmap, ignore_unknown=True)

                        renderer.append_profile(profile, sync, iplist)

                    wm.print_renderer(renderer)
                except NoProfileSelected as nps:
                    # Just print, return code is still 0
                    wm.print_exception(nps)
