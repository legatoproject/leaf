'''
Renderer for status command

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from builtins import sorted

from leaf.format.alignment import HAlign
from leaf.format.renderer.profile import ProfileListRenderer
from leaf.format.renderer.renderer import Renderer
from leaf.format.table import Table


class StatusRenderer(ProfileListRenderer):
    '''
    Renderer for status command
    '''

    def __init__(self, workspaceRootFolder, currentProfile, sync, includedPackagesMap, dependenciesMap, otherProfiles):
        Renderer.__init__(self)
        self.workspaceRootFolder = workspaceRootFolder
        self.currentProfile = currentProfile
        self.sync = sync
        self.includedPackagesMap = includedPackagesMap
        self.dependenciesMap = dependenciesMap
        self.otherProfiles = otherProfiles

    def _toStringQuiet(self):
        return "Workspace %s" % self.workspaceRootFolder

    def _addPackagesRows(self, table, label, packMap):
        label = self.tm.LABEL(label)
        for pi, p in sorted(packMap.items()):
            table.newRow().newSep() \
                .newCell(label, hAlign=HAlign.CENTER).newSep() \
                .newCell(str(pi)).newSep() \
                .newCell(p.getDescription() if p is not None else "").newSep()
            label = ""

    def _toString(self, showEnv, showDependencies):
        nbElements = 7
        table = Table(self.tm)

        # Workspace header
        self._addHeader(table, nbElements)

        # Profile
        self._addProfile(table, showEnv, showDependencies, nbElements, self.currentProfile, self.sync,
                         self.includedPackagesMap, self.dependenciesMap)

        table.newRow().newSep(nbElements)
        out = str(table)

        otherCount = len(self.otherProfiles)
        if otherCount > 0:
            out += "\n{label_theme}{profile_label}:{reset_theme} {profiles_list}".format(
                label_theme=self.tm.LABEL,
                profile_label="Other profiles" if otherCount > 1 else "Other profile",
                reset_theme=self.tm.RESET,
                profiles_list=", ".join(map(str, self.otherProfiles)))

        return out

    def _toStringDefault(self):
        '''
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
        '''
        return self._toString(showEnv=False, showDependencies=False)

    def _toStringVerbose(self):
        '''
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
        '''
        return self._toString(showEnv=True, showDependencies=True)
