"""
Renderer for status command

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from builtins import sorted

from leaf.rendering.alignment import HAlign
from leaf.rendering.renderer.profile import ProfileListRenderer
from leaf.rendering.renderer.renderer import Renderer
from leaf.rendering.table import Table


class StatusRenderer(ProfileListRenderer):

    """
    Renderer for status command
    """

    def __init__(self, ws_root_folder, current_profile, sync, included_packages_map, dependencies_map, other_profiles):
        Renderer.__init__(self)
        self.ws_root_folder = ws_root_folder
        self.current_profile = current_profile
        self.sync = sync
        self.included_packages_map = included_packages_map
        self.dependencies_map = dependencies_map
        self.other_profiles = other_profiles

    def _tostring_quiet(self):
        return "Workspace {folder}".format(folder=self.ws_root_folder)

    def _add_packages_rows(self, table, label, pkgmap):
        label = self.tm.LABEL(label)
        for pi, pkg in sorted(pkgmap.items()):
            description = ""
            if pkg is not None:
                description = pkg.description or ""
            table.new_row().new_separator().new_cell(label, halign=HAlign.CENTER).new_separator().new_cell(str(pi)).new_separator().new_cell(
                description
            ).new_separator()
            label = ""

    def _tostring(self, show_env, show_dependencies):
        count = 7
        table = Table(self.tm)

        # Workspace header
        self._add_header(table, count)

        # Profile
        self._add_profile(table, show_env, show_dependencies, count, self.current_profile, self.sync, self.included_packages_map, self.dependencies_map)

        table.new_row().new_separator(count)
        out = str(table)

        other_profiles_count = len(self.other_profiles)
        if other_profiles_count > 0:
            out += "\n{label_theme}{profile_label}:{reset_theme} {profiles_list}".format(
                label_theme=self.tm.LABEL,
                profile_label="Other profiles" if other_profiles_count > 1 else "Other profile",
                reset_theme=self.tm.RESET,
                profiles_list=", ".join(map(str, self.other_profiles)),
            )

        return out

    def _tostring_default(self):
        """
        ┌───────────────────────────────────────────────────────────────┐
        │                  Workspace: fake/root/folder                  │
        ╞═══════════════════════════════════════════════════════════════╡
        │               Profile: profile1 [current] (sync)              │
        ├──────────┬─────────────────┬──────────────────────────────────┤
        │ Packages │    Identifier   │           Description            │
        ├──────────┼─────────────────┼──────────────────────────────────┤
        │ Included │ container-A_1.0 │ Fake description for container A │
        │          │ container-B_1.0 │ Fake description for container B │
        └──────────┴─────────────────┴──────────────────────────────────┘
        Other profiles: profile2, profile3
        """
        return self._tostring(show_env=False, show_dependencies=False)

    def _tostring_verbose(self):
        """
        ┌──────────────────────────────────────────────────────────────────┐
        │                   Workspace: fake/root/folder                    │
        ╞══════════════════════════════════════════════════════════════════╡
        │                Profile: profile1 [current] (sync)                │
        ├─────────────┬────────────────────────────────────────────────────┤
        │ Environment │ Foo1=Bar1                                          │
        │             │ Foo2=Bar2                                          │
        │             │ Foo3=Bar3                                          │
        ├─────────────┼─────────────────┬──────────────────────────────────┤
        │   Packages  │    Identifier   │           Description            │
        ├─────────────┼─────────────────┼──────────────────────────────────┤
        │   Included  │ container-A_1.0 │ Fake description for container A │
        │             │ container-B_1.0 │ Fake description for container B │
        ├─────────────┼─────────────────┼──────────────────────────────────┤
        │  Dependency │ container-C_1.0 │ Fake description for container C │
        └─────────────┴─────────────────┴──────────────────────────────────┘
        Other profiles: profile2, profile3
        """
        return self._tostring(show_env=True, show_dependencies=True)
