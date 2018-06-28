'''
Renderer for search command

@author:    Nicolas Lambert <nlambert@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.model.package import AvailablePackage, InstalledPackage, ConditionalPackageIdentifier
from leaf.format.table import Table
from leaf.format.renderers import Renderer
from leaf.format.alignment import HAlign


class SearchRenderer(Renderer):
    '''
    Renderer for search command
    '''

    def __init__(self, pkgFilter=None):
        '''
        Store the pkgFilter to show it in the table header
        '''
        self.pkgFilter = pkgFilter

    def _toStringDefault(self):
        '''
        Show a table like that:
        ┌──────────────────────────────────────────────────┐
        │         4 packages - Filter: only master         │
        ├──────────────────────────┬─────────────┬─────────┤
        │        Identifier        │ Description │   Tags  │
        ╞══════════════════════════╪═════════════╪═════════╡
        │ condition_1.0            │             │ latest  │
        │ container-A_1.0          │ Desc1       │ foo     │
        │ container-A_2.0          │             │ foo,bar │
        │ featured-with-source_1.0 │ Desc2       │ latest  │
        └──────────────────────────┴─────────────┴─────────┘
        '''
        nbElements = 7
        table = Table()

        # Header
        self._addHeaderRows(table, nbElements)
        if len(self) > 0:
            table.newRow().newSep() \
                .newCell("Identifier", HAlign.CENTER).newSep() \
                .newCell("Description", HAlign.CENTER).newSep() \
                .newCell("Tags", HAlign.CENTER).newSep()
            table.newRow().newDblSep(nbElements)

            # Body
            for inputElt in self:
                descValue = ""
                if inputElt.getDescription() is not None:
                    descValue = inputElt.getDescription()

                # Draw table
                table.newRow().newSep() \
                    .newCell(inputElt.getIdentifier()).newSep() \
                    .newCell(descValue).newSep() \
                    .newCell(",".join(inputElt.getAllTags())).newSep()

            # Footer
            table.newRow().newSep(nbElements)

        return table

    def _toStringVerbose(self):
        '''
        Show a table like that:
        ┌────────────────────────────────────────────────────────────────────────────────┐
        │  47 packages - Filter: only master and (+tag1 or +tag2keyword1 or +keyword2)   │
        ├─────────────────────────────────────┬──────────────────────────────────────────┤
        │              Identifier             │                Properties                │
        ╞═════════════════════════════════════╪══════════════════════════════════════════╡
        │                                     │       Description: None                  │
        │                                     │              Tags: latest                │
        │                                     │              Size: 528 bytes             │
        │                                     │ Included Packages: condition-A_1.0       │
        │                                     │                    condition-B_1.0       │
        │ condition_1.0                       │                    condition-C_1.0       │
        │                                     │                    condition-D_1.0       │
        │                                     │                    condition-E_1.0       │
        │                                     │                    condition-F_1.0       │
        │                                     │                    condition-G_1.0       │
        │                                     │                    condition-H_1.0       │
        ├─────────────────────────────────────┼──────────────────────────────────────────┤
        │ ...                                 │                ... ...                   │
        '''
        nbElements = 6
        table = Table()

        # Header
        self._addHeaderRows(table, nbElements)

        if len(self) > 0:
            table.newRow().newSep() \
                .newCell("Identifier", HAlign.CENTER).newSep() \
                .newCell("Properties", HAlign.CENTER).newHSpan().newSep()
            table.newRow().newDblSep(nbElements)

            for inputElt in self:
                labels, values = self._createPropertyTable(inputElt)

                # Create table row
                table.newRow().newSep().newCell(inputElt.getIdentifier()).newSep() \
                    .newCell("\n".join(labels), HAlign.RIGHT) \
                    .newCell("\n".join(values)).newSep()

                # Footer for each manifest
                table.newRow().newSep(nbElements)

        return table

    def _createPropertyTable(self, inputElt):
        labels = []
        values = []

        # Description
        if inputElt.getDescription() is not None:
            labels.append("Description:")
            values.append(inputElt.getDescription())

        # Tags
        tagCount = len(inputElt.getAllTags())
        if tagCount > 0:
            labels.append("Tags:" if tagCount > 1 else "Tag:")
            values.append(",".join(inputElt.getAllTags()))

        depCount = len(inputElt.getLeafDepends())
        if isinstance(inputElt, AvailablePackage) and depCount == 0:
            # Size
            labels.append("Size:")
            values.append(str(inputElt.getSize()) + ' bytes')
        elif isinstance(inputElt, InstalledPackage):
            #Folder
            labels.append("Folder:")
            values.append(inputElt.folder)

        # Included packages
        if depCount > 0:
            labels.append("Included Packages:" if depCount > 1
                          else "Included Package:")
            values.append("\n".join(self._getCpis(inclPack)
                                    for inclPack in inputElt.getLeafDepends()))

        return labels, values

    def _addHeaderRows(self, table, tableSize):
        '''
        Add header to the given Table like that:
        ┌──────────────────────────────────────────────────────────────────┐
        │                36 packages - Filter: only master                 │
        ├──────────────────────────────────────────────────────────────────┤
        '''
        inputCount = len(self)
        title = "%d %s - Filter: %s" % (
            inputCount, "package" if inputCount <= 1 else "packages", self.pkgFilter)
        table.newRow().newSep(tableSize)
        table.newRow().newSep() \
            .newCell(title, HAlign.CENTER).newHSpan(tableSize - 3).newSep()
        table.newRow().newSep(tableSize)

    def _getCpis(self, cpis):
        try:
            return str(ConditionalPackageIdentifier.fromString(cpis))
        except:
            return cpis
