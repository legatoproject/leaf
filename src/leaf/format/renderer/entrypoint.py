'''
Renderer for search and package list commands

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.format.alignment import HAlign
from leaf.format.renderer.renderer import Renderer
from leaf.format.table import Table


class EntrypointListRenderer(Renderer):
    '''
    Renderer for entrypoints
    '''

    def __init__(self, scope):
        Renderer.__init__(self)
        self.scope = scope

    def _toStringQuiet(self):
        lines = []
        for ip in self:
            for ep in ip.getBinMap().values():
                lines.append("{pi}/{bin}: {desc}".format(pi=ip.getIdentifier(),
                                                         bin=ep.name,
                                                         desc=ep.getDescription() or ''))
        return '\n'.join(lines)

    def _toStringDefault(self):
        return self._toStringVerbose()

    def _toStringVerbose(self):
        '''
        Show a table like that:
        ┌────────────────────────────────────────────────────────────────────────────────┐
        │              Package                │                Binaries                  │
        ╞═════════════════════════════════════╪══════════════════════════════════════════╡
        │ condition_1.0                       │       Description: None                  │
        │                                     │              Tags: latest                │
        │                                     │              Size: 528 bytes             │
        │                                     │      Release date: 29/12/2015            │
        │                                     │            Source: remote2               │
        │                                     │ Included Packages: condition-A_1.0       │
        │                                     │                    condition-B_1.0       │
        │                                     │                    condition-C_1.0       │
        │                                     │                    condition-D_1.0       │
        │                                     │                    condition-E_1.0       │
        │                                     │                    condition-F_1.0       │
        │                                     │                    condition-G_1.0       │
        │                                     │                    condition-H_1.0       │
        ├─────────────────────────────────────┼──────────────────────────────────────────┤
        │ ...                                 │                ... ...                   │
        '''
        nbElements = 6
        table = Table(self.tm)

        # Header
        self._addHeaderRows(table, nbElements)

        if len(self) > 0:
            table.newRow().newSep() \
                .newCell(self.tm.LABEL("Package"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Binaries"), HAlign.CENTER).newHSpan().newSep()
            table.newRow().newDblSep(nbElements)

            # Body
            for ip in self:
                if len(ip.getBinMap()) > 0:
                    labels, values = self._createPropertyTable(ip)

                    # Create table row
                    table.newRow().newSep() \
                        .newCell(ip.getIdentifier()).newSep() \
                        .newCell("\n".join(map(str, labels))) \
                        .newCell("\n".join(map(str, values))).newSep()

                    # Footer for each manifest
                    table.newRow().newSep(nbElements)

        return table

    def _createPropertyTable(self, inputElt):
        labels = []
        values = []

        for binname, entrypoint in inputElt.getBinMap().items():
            labels.append(binname)
            values.append(entrypoint.getDescription() or "")

        return map(self.tm.LABEL, labels), values

    def _addHeaderRows(self, table, tableSize):
        '''
        Add header to the given Table like that:
        ┌────────────────────────────────────────────────────────────────────────────────┐
        │         List of declared binaries in workspace|installed packages|PKG_NAME     │
        ├────────────────────────────────────────────────────────────────────────────────┤
        '''
        title = "List of declared binaries in {}".format(self.scope)
        table.newHeader(title, tableSize)
