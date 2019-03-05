"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from leaf.cli.base import LeafCommand
from leaf.core.error import LeafException


class WorkspaceInitCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "init", "initialize workspace")

    def execute(self, args, uargs):
        wm = self.get_workspacemanager(check_parents=False, check_initialized=False)
        if wm.ws_config_file.exists():
            raise LeafException("Workspace is already initialized (file {ws.ws_config_file} already exists)".format(ws=wm))
        wm.read_ws_configuration(init_if_needed=True)
        wm.logger.print_default("Workspace initialized", wm.ws_root_folder)
