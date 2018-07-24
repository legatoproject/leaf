'''
Renderer for profile list command

@author:    Nicolas Lambert <nlambert@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.format.alignment import HAlign
from leaf.format.renderer.renderer import Renderer
from leaf.format.table import Table


class ProfileListRenderer(Renderer):
    '''
    Renderer for profile list command
    '''

    def _toDecoratedName(self, pf):
        out = pf.name
        if pf.isCurrentProfile:
            out += ' ' + self.tm.PROFILE_CURRENT("[current]")
        return out

    def _toStringDefault(self):
        '''
        ┌───────────────┐
        │   2 profiles  │
        ├───────────────┤
        │ foo [current] │
        │ bar           │
        └───────────────┘
        '''
        table = Table(self.tm)
        nbElements = 3

        # Header
        self._addHeaderRows(table, nbElements)

        # Body
        for pf in self:
            line = self._toDecoratedName(pf)
            table.newRow().newSep().newCell(line).newSep()

        # Footer
        table.newRow().newSep(nbElements)

        return table

    def _toStringVerbose(self):
        '''
        ┌─────────────────────────────────────┐
        │              1 profile              │
        ├─────────┬─────────┬─────────────────┤
        │ Profile │   Env   │     Packages    │
        ╞═════════╪═════════╪═════════════════╡
        │ foo     │ FOO=BAR │ container-A_1.0 │
        └─────────┴─────────┴─────────────────┘
        '''
        nbElements = 7
        table = Table(self.tm)

        # Header
        self._addHeaderRows(table, nbElements)
        table.newRow().newSep() \
            .newCell(self.tm.LABEL("Profile"), HAlign.CENTER).newSep() \
            .newCell(self.tm.LABEL("Env vars"), HAlign.CENTER).newSep() \
            .newCell(self.tm.LABEL("Packages"), HAlign.CENTER).newSep()
        table.newRow().newDblSep(nbElements)

        # Body
        for pf in self:
            profileName = self._toDecoratedName(pf)
            env = ["%s=%s" % (k, v) for (k, v) in pf.getEnvMap().items()]
            packages = map(str, pf.getPackages())

            # Create table row
            table.newRow().newSep() \
                .newCell(profileName).newSep() \
                .newCell('\n'.join(env)).newSep() \
                .newCell('\n'.join(packages)).newSep()

            # Footer
            table.newRow().newSep(nbElements)

        return table

    def _addHeaderRows(self, table, nbElements):
        '''
        Add header to the given Table like that:
        ┌────────────┐
        │ 5 profiles │
        ├────────────┤
        '''
        count = len(self)
        header = "{count} {labeltheme}{profileLabel}{resettheme}".format(
            count=count,
            labeltheme=self.tm.LABEL,
            profileLabel="profile" if count <= 1 else "profiles",
            resettheme=self.tm.RESET)
        table.newHeader(header, nbElements)
