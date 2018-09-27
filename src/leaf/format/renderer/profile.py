'''
Renderer for profile list command

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.format.alignment import HAlign
from leaf.format.renderer.renderer import Renderer
from leaf.format.table import Table


class ProfileListRenderer(Renderer):
    '''
    Renderer for profile list command
    profilesInfoMap is a dict with profiles as key and the dict returned by WorkspaceManager#computeProfileInfo as values
    '''

    def __init__(self, workspaceRootFolder, profilesInfoMap):
        Renderer.__init__(self)
        self.workspaceRootFolder = workspaceRootFolder
        self.extend(profilesInfoMap.keys())
        self.sort(key=str)
        self.profilesInfoMap = profilesInfoMap

    def _addPackagesRows(self, table, label, packMap):
        label = self.tm.LABEL(label)
        for pi, p in sorted(packMap.items()):
            table.newRow().newSep() \
                .newCell(label, hAlign=HAlign.CENTER).newSep() \
                .newCell(str(pi)).newSep() \
                .newCell(p.getDescription() if p is not None else "").newSep()
            label = ""

    def _addHeader(self, table, nbElements):
        # Header
        table.newRow().newSep(nbElements)
        headerText = ("{label_theme}Workspace:{reset_theme} {workspace_folder}") \
            .format(
                label_theme=self.tm.LABEL,
                reset_theme=self.tm.RESET,
                workspace_folder=self.workspaceRootFolder)
        table.newRow().newSep().newCell(
            headerText, hAlign=HAlign.CENTER).newHSpan(nbElements - 3).newSep()

    def _addProfile(self, table, showEnv, showDependencies, nbElements, profile, sync, includedPackagesMap, dependenciesMap):
        # Profile header
        table.newRow().newDblSep(nbElements)
        profileName = profile.name
        if profile.isCurrentProfile:
            profileName += " " + self.tm.PROFILE_CURRENT("[current]")
        headerText = ("{label_theme}Profile:{reset_theme} {profile_name} ({sync_state})") \
            .format(
                label_theme=self.tm.LABEL,
                reset_theme=self.tm.RESET,
                profile_name=profileName,
                sync_state="sync" if sync else "not sync")
        table.newRow().newSep().newCell(
            headerText, hAlign=HAlign.CENTER).newHSpan(nbElements - 3).newSep()

        # Environment
        if showEnv:
            env = sorted(["%s=%s" % (k, v)
                          for (k, v) in profile.getEnvMap().items()])
            if len(env) > 0:
                table.newRow().newSep(nbElements)
                table.newRow().newSep() \
                    .newCell(self.tm.LABEL("Environment"), hAlign=HAlign.CENTER).newSep() \
                    .newCell("\n".join(env)).newHSpan(2).newSep()

        # Included packages
        inclPkgCount = len(includedPackagesMap)

        if showDependencies:
            # Dependencies
            depsCount = len(dependenciesMap)
        else:
            depsCount = 0

        # Packages header
        if inclPkgCount > 0 or depsCount > 0:
            table.newRow().newSep(nbElements)
            table.newRow().newSep() \
                .newCell(self.tm.LABEL("Packages"), hAlign=HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Identifier"), hAlign=HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Description"), hAlign=HAlign.CENTER).newSep()

            # Included packages
            if inclPkgCount > 0:
                table.newRow().newSep(nbElements)
                self._addPackagesRows(table, "Included", includedPackagesMap)

            if depsCount > 0:
                # Dependencies
                table.newRow().newSep(nbElements)
                self._addPackagesRows(
                    table, "Dependencies" if depsCount > 1 else "Dependency", dependenciesMap)

    def _toString(self, showEnv, showDependencies):
        nbElements = 7
        table = Table(self.tm)

        # Workspace header
        self._addHeader(table, nbElements)

        # Profile
        for profile in self:
            profileInfos = self.profilesInfoMap[profile]
            self._addProfile(table, showEnv, showDependencies,
                             nbElements, profile, **profileInfos)

        table.newRow().newSep(nbElements)
        return table

    def _toStringDefault(self):
        '''
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
        '''
        return self._toString(showEnv=False, showDependencies=False)

    def _toStringVerbose(self):
        '''
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
        '''
        return self._toString(showEnv=True, showDependencies=True)
