"""
Renderer for status command

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from pathlib import Path

from leaf.model.environment import Environment
from leaf.rendering.renderer.profile import ProfileListRenderer
from leaf.rendering.table import Table


class StatusRenderer(ProfileListRenderer):

    """
    Renderer for status command
    """

    def __init__(self, ws_root_folder: Path, ws_env: Environment):
        ProfileListRenderer.__init__(self, ws_root_folder, ws_env)

    def _tostring_quiet(self):
        return "Workspace {folder}".format(folder=self.ws_root_folder)

    def _tostring(self, show_env, show_dependencies):
        count = 7
        table = Table(self.tm)

        # Workspace header
        self._add_header(table, count)

        other_profiles_names = []
        # Profile
        for profile, sync, dependencies_iplist in self:
            if profile.is_current:
                self._add_profile(table, show_env, show_dependencies, count, profile, sync, dependencies_iplist)
            else:
                other_profiles_names.append(profile.name)

        table.new_row().new_separator(count)
        out = str(table)

        if len(other_profiles_names) > 0:
            out += "\n{label_theme}{profile_label}:{reset_theme} {profiles_list}".format(
                label_theme=self.tm.LABEL,
                profile_label="Other profiles" if len(other_profiles_names) > 1 else "Other profile",
                reset_theme=self.tm.RESET,
                profiles_list=", ".join(other_profiles_names),
            )
        return out
