'''
Renderer for status command

@author:    Nicolas Lambert <nlambert@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.format.alignment import HAlign
from leaf.format.renderer.renderer import Renderer
from leaf.format.table import Table


class WorkspaceRenderer(Renderer):
    '''
    Renderer for status command
    '''

    def __init__(self, ws):
        self.append(ws)

    def _toStringQuiet(self):
        return "Workspace %s" % self[0].workspaceRootFolder

    def _toDecoratedName(self, pf):
        out = pf.name
        if pf.isCurrentProfile:
            out += ' ' + self.tm.PROFILE_CURRENT("[current]")
        return out

    def _toStringDefault(self):
        '''
        ┌─────────────────────────────────────────────┐
        │        Current Workspace - 1 profile        │
        │      {ROOT_FOLDER}/volatile/workspace       │
        ├─────────┬───────────────────────────────────┤
        │ Profile │                Sync               │
        ╞═════════╪═══════════════════════════════════╡
        │   foo   │                yes                │
        └─────────┴───────────────────────────────────┘
        '''
        item = self[0]
        nbElements = 5
        table = Table(self.tm)

        # Header
        pfs = item.listProfiles().values()
        nbPfs = len(pfs)
        self._addHeaderRows(table, nbPfs, nbElements)
        if nbPfs > 0:
            table.newRow().newSep() \
                .newCell(self.tm.LABEL("Profile"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Sync"), HAlign.CENTER).newSep()
            table.newRow().newDblSep(nbElements)

            # Body
            for pf in pfs:
                table.newRow().newSep() \
                    .newCell(self._toDecoratedName(pf), HAlign.CENTER).newSep() \
                    .newCell("yes" if item.isProfileSync(pf) else "no", HAlign.CENTER).newSep()

                # Footer for each manifest
                table.newRow().newSep(nbElements)

        return table

    def _boolToText(self, boole):
        return "yes" if boole else "no"

    def _toStringVerbose(self):
        '''
        ┌────────────────────────────────────────────────────────┐
        │            Current Workspace - 1 profile               │
        │        {ROOT_FOLDER}/volatile/workspace                │
        ├─────────┬──────┬───────────┬───────────────────────────┤
        │ Profile │ Sync │  Env vars │          Packages         │
        ╞═════════╪══════╪═══════════╪═══════════════════════════╡
        │ foo     │ yes  |           │ container-A_2.1           │
        └─────────┴──────┴───────────┴───────────────────────────┘
        '''
        item = self[0]

        nbElements = 9
        table = Table(self.tm)

        # Header
        pfs = item.listProfiles().values()
        nbPfs = len(pfs)
        self._addHeaderRows(table, nbPfs, nbElements)
        if nbPfs > 0:
            table.newRow().newSep() \
                .newCell(self.tm.LABEL("Profile"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Sync"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Env vars"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Packages"), HAlign.CENTER).newSep()
            table.newRow().newDblSep(nbElements)

            # Body
            for pf in pfs:

                # first column
                profile = self._toDecoratedName(pf)

                # second column
                env = ["%s=%s" % (k, v) for (k, v) in pf.getEnvMap().items()]

                # third column
                synced = self._boolToText(item.isProfileSync(pf))

                # fourth column
                packages = map(str, pf.getPackages())

                # Create table row
                table.newRow().newSep() \
                    .newCell(profile).newSep() \
                    .newCell(synced).newSep() \
                    .newCell('\n'.join(env)).newSep() \
                    .newCell('\n'.join(packages)).newSep()

                # Footer
                table.newRow().newSep(nbElements)

        return table

    def _addHeaderRows(self, table, nbPf, nbElements):
        '''
        Add header to the given Table like that:
        ┌───────────────────────────────┐
        │ Current Workspace - 1 profile │
        │      {WORKSPACE_FOLDER}       │
        ├───────────────────────────────┤
        '''
        header = []
        header.append("Workspace: {workspace_folder}".format(
            workspace_folder=self[0].workspaceRootFolder))
        header.append("{count} {labeltheme}{profileLabel}{resettheme}".format(
            count=nbPf,
            labeltheme=self.tm.LABEL,
            profileLabel="profile" if nbPf <= 1 else "profiles",
            resettheme=self.tm.RESET))
        table.newHeader('\n'.join(header), nbElements)
