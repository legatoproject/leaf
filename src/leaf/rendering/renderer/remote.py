'''
Renderer for remote list command

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.rendering.alignment import HAlign
from leaf.rendering.renderer.renderer import Renderer
from leaf.rendering.table import Table


class RemoteListRenderer(Renderer):
    '''
    Renderer for remote list command
    '''
    def __init__(self):
        Renderer.__init__(self)

    def _toStringDefault(self):
        '''
        Show a table like that:
        ┌───────────────────────────────────────────────────────────────────────────┐
        │                                  1 remote                                 │
        ├─────────┬───────────────────────────────────────────────────────┬─────────┤
        │  Alias  │                          URL                          │ Enabled │
        ╞═════════╪═══════════════════════════════════════════════════════╪═════════╡
        │ default │ {REMOTE_URL}                                          │ yes     │
        └─────────┴───────────────────────────────────────────────────────┴─────────┘
        '''
        nbElements = 7
        table = Table(self.tm)

        # Header
        self._addHeaderRows(table, nbElements)
        if len(self) > 0:
            table.newRow().newSep() \
                .newCell(self.tm.LABEL("Alias"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("URL"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Enabled"), HAlign.CENTER).newSep()
            table.newRow().newDblSep(nbElements)

            # Body
            for inputElt in self:
                aliasValue = ""
                if inputElt.alias is not None:
                    aliasValue = inputElt.alias

                theme = self.tm.VOID
                if not inputElt.isEnabled():
                    theme = self.tm.REMOTE_DISABLED

                # Draw table
                table.newRow().newSep() \
                    .newCell(theme(aliasValue)).newSep() \
                    .newCell(theme(inputElt.getUrl())).newSep() \
                    .newCell(theme(self._boolToText(inputElt.isEnabled()))).newSep()

            # Footer
            table.newRow().newSep(nbElements)

        return table

    def _boolToText(self, boole):
        return "yes" if boole else "no"

    def _toStringVerbose(self):
        '''
        Show a table like that:
        ┌──────────────────────────────────────────────────────────────────────────┐
        │                                 1 remote                                 │
        ├─────────┬────────────────────────────────────────────────────────────────┤
        │  Alias  │                           Properties                           │
        ╞═════════╪════════════════════════════════════════════════════════════════╡
        │ default │     Url: {REMOTE_URL}                                          │
        │         │ Enabled: yes                                                   │
        │         │ Fetched: no                                                    │
        └─────────┴────────────────────────────────────────────────────────────────┘
        '''
        nbElements = 6
        table = Table(self.tm)

        # Header
        self._addHeaderRows(table, nbElements)

        if len(self) > 0:
            table.newRow().newSep() \
                .newCell(self.tm.LABEL("Alias"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Properties"), HAlign.CENTER).newHSpan().newSep()
            table.newRow().newDblSep(nbElements)

            for inputElt in self:
                labels, values = self._createPropertyTable(inputElt)

                aliasValue = "No alias"
                if inputElt.alias is not None:
                    aliasValue = inputElt.alias

                # Create table row
                table.newRow().newSep().newCell(aliasValue).newSep() \
                    .newCell("\n".join(map(str, labels)), HAlign.RIGHT) \
                    .newCell("\n".join(map(str, values))).newSep()

                # Footer for each manifest
                table.newRow().newSep(nbElements)

        return table

    def _createPropertyTable(self, inputElt):
        labels = []
        values = []

        # URL
        labels.append(self.tm.LABEL("Url:"))
        values.append(inputElt.getUrl())

        if inputElt.isFetched():
            # Name
            name = inputElt.getInfoName()
            if name is not None:
                labels.append("Name:")
                values.append(inputElt.getInfoName())

            # Description
            desc = inputElt.getInfoDescription()
            if desc is not None:
                labels.append("Description:")
                values.append(desc)

            # Last update
            lastUpdate = inputElt.getInfoDate()
            if lastUpdate is not None:
                labels.append("Last update:")
                values.append(lastUpdate)

        labels.append("Enabled:")
        enabled = inputElt.isEnabled()
        values.append(self._boolToText(enabled))

        if enabled:
            labels.append("Fetched:")
            values.append(self._boolToText(inputElt.isFetched()))

        return map(self.tm.LABEL, labels), values

    def _addHeaderRows(self, table, tableSize):
        '''
        Add header to the given Table like that:
        ┌──────────────────────────────────────────────────────────────────────────┐
        │                                 5 remote                                 │
        ├─────────┬────────────────────────────────────────────────────────────────┤
        '''
        inputCount = len(self)
        title = "{count} {labeltheme}{featureLabel}{resettheme}".format(
            count=inputCount,
            labeltheme=self.tm.LABEL,
            featureLabel="remote" if inputCount <= 1 else "remotes",
            resettheme=self.tm.RESET)
        table.newHeader(title, tableSize)
