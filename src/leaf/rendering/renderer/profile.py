"""
Renderer for profile list command

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from leaf.rendering.alignment import HAlign
from leaf.rendering.renderer.renderer import Renderer
from leaf.rendering.table import Table


class ProfileListRenderer(Renderer):

    """
    Renderer for profile list command
    profiles_infomap is a dict with profiles as key and the dict returned by WorkspaceManager#_compute_profile_info as values
    """

    def __init__(self, ws_root_folder, profile_infomap):
        Renderer.__init__(self)
        self.ws_root_folder = ws_root_folder
        self.extend(profile_infomap.keys())
        self.sort(key=str)
        self.profile_infomap = profile_infomap

    def _add_packages_rows(self, table, label, package_map):
        label = self.tm.LABEL(label)
        for pi, pkg in sorted(package_map.items()):
            description = ""
            if pkg is not None:
                description = pkg.description or ""
            table.new_row().new_separator().new_cell(label, halign=HAlign.CENTER).new_separator().new_cell(str(pi)).new_separator().new_cell(
                description
            ).new_separator()
            label = ""

    def _add_header(self, table, nb_elements):
        # Header
        table.new_row().new_separator(nb_elements)
        text = ("{label_theme}Workspace:{reset_theme} {workspace_folder}").format(
            label_theme=self.tm.LABEL, reset_theme=self.tm.RESET, workspace_folder=self.ws_root_folder
        )
        table.new_row().new_separator().new_cell(text, halign=HAlign.CENTER).new_hspan(nb_elements - 3).new_separator()

    def _add_profile(self, table, show_env, show_dependencies, element_count, profile, sync, included_packages_map, dependencies_map):
        # Profile header
        table.new_row().new_double_separator(element_count)
        pfname = profile.name
        if profile.is_current:
            pfname += " " + self.tm.PROFILE_CURRENT("[current]")
        header_text = ("{label_theme}Profile:{reset_theme} {profile_name} ({sync_state})").format(
            label_theme=self.tm.LABEL, reset_theme=self.tm.RESET, profile_name=pfname, sync_state="sync" if sync else "not sync"
        )
        table.new_row().new_separator().new_cell(header_text, halign=HAlign.CENTER).new_hspan(element_count - 3).new_separator()

        # Environment
        if show_env:
            env = []
            profile.build_environment().print_env(kv_consumer=lambda k, v: env.append("{0}={1}".format(k, v)))
            if len(env) > 0:
                table.new_row().new_separator(element_count)
                table.new_row().new_separator().new_cell(self.tm.LABEL("Environment"), halign=HAlign.CENTER).new_separator().new_cell("\n".join(env)).new_hspan(
                    2
                ).new_separator()

        # Included packages
        included_packages_count = len(included_packages_map)

        if show_dependencies:
            # Dependencies
            dependencies_count = len(dependencies_map)
        else:
            dependencies_count = 0

        # Packages header
        if included_packages_count > 0 or dependencies_count > 0:
            table.new_row().new_separator(element_count)
            table.new_row().new_separator().new_cell(self.tm.LABEL("Packages"), halign=HAlign.CENTER).new_separator().new_cell(
                self.tm.LABEL("Identifier"), halign=HAlign.CENTER
            ).new_separator().new_cell(self.tm.LABEL("Description"), halign=HAlign.CENTER).new_separator()

            # Included packages
            if included_packages_count > 0:
                table.new_row().new_separator(element_count)
                self._add_packages_rows(table, "Included", included_packages_map)

            if dependencies_count > 0:
                # Dependencies
                table.new_row().new_separator(element_count)
                self._add_packages_rows(table, "Dependencies" if dependencies_count > 1 else "Dependency", dependencies_map)

    def _tostring(self, show_env, show_dependencies):
        count = 7
        table = Table(self.tm)

        # Workspace header
        self._add_header(table, count)

        # Profile
        for profile in self:
            info = self.profile_infomap[profile]
            self._add_profile(table, show_env, show_dependencies, count, profile, **info)

        table.new_row().new_separator(count)
        return table

    def _tostring_default(self):
        """
        ┌───────────────────────────────────────────────────────────────┐
        │                  Workspace: fake/root/folder                  │
        ╞═══════════════════════════════════════════════════════════════╡
        │                    Profile: profile1 (sync)                   │
        ├──────────┬─────────────────┬──────────────────────────────────┤
        │ Packages │    Identifier   │           Description            │
        ├──────────┼─────────────────┼──────────────────────────────────┤
        │ Included │ container-A_1.0 │ Fake description for container A │
        ╞══════════╧═════════════════╧══════════════════════════════════╡
        │             Profile: profile2 [current] (not sync)            │
        ├──────────┬─────────────────┬──────────────────────────────────┤
        │ Packages │    Identifier   │           Description            │
        ├──────────┼─────────────────┼──────────────────────────────────┤
        │ Included │ container-B_1.0 │ Fake description for container B │
        ╞══════════╧═════════════════╧══════════════════════════════════╡
        │                    Profile: profile3 (sync)                   │
        ╞═══════════════════════════════════════════════════════════════╡
        │                  Profile: profile4 (not sync)                 │
        └───────────────────────────────────────────────────────────────┘
        """
        return self._tostring(show_env=False, show_dependencies=False)

    def _tostring_verbose(self):
        """
        ┌───────────────────────────────────────────────────────────────────┐
        │                    Workspace: fake/root/folder                    │
        ╞═══════════════════════════════════════════════════════════════════╡
        │                      Profile: profile1 (sync)                     │
        ├──────────────┬────────────────────────────────────────────────────┤
        │ Environment  │ Foo1=Bar1                                          │
        │              │ Foo2=Bar2                                          │
        │              │ Foo3=Bar3                                          │
        ├──────────────┼─────────────────┬──────────────────────────────────┤
        │   Packages   │    Identifier   │           Description            │
        ├──────────────┼─────────────────┼──────────────────────────────────┤
        │   Included   │ container-A_1.0 │ Fake description for container A │
        ├──────────────┼─────────────────┼──────────────────────────────────┤
        │ Dependencies │ container-B_1.0 │ Fake description for container B │
        │              │ container-C_1.0 │ Fake description for container C │
        ╞══════════════╧═════════════════╧══════════════════════════════════╡
        │               Profile: profile2 [current] (not sync)              │
        ├──────────────┬─────────────────┬──────────────────────────────────┤
        │   Packages   │    Identifier   │           Description            │
        ├──────────────┼─────────────────┼──────────────────────────────────┤
        │   Included   │ container-B_1.0 │ Fake description for container B │
        ╞══════════════╧═════════════════╧══════════════════════════════════╡
        │                      Profile: profile3 (sync)                     │
        ├──────────────┬────────────────────────────────────────────────────┤
        │ Environment  │ Foo2=Bar2                                          │
        │              │ Foo3=Bar3                                          │
        ├──────────────┼─────────────────┬──────────────────────────────────┤
        │   Packages   │    Identifier   │           Description            │
        ├──────────────┼─────────────────┼──────────────────────────────────┤
        │  Dependency  │ container-B_1.0 │ Fake description for container B │
        ╞══════════════╧═════════════════╧══════════════════════════════════╡
        │                    Profile: profile4 (not sync)                   │
        └───────────────────────────────────────────────────────────────────┘
        """
        return self._tostring(show_env=True, show_dependencies=True)
