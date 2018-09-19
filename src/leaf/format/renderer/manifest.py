'''
Renderer for search and package list commands

@author:    Nicolas Lambert <nlambert@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.format.alignment import HAlign
from leaf.format.formatutils import sizeof_fmt
from leaf.format.renderer.renderer import Renderer
from leaf.format.table import Table
from leaf.model.package import AvailablePackage, InstalledPackage, ConditionalPackageIdentifier


class ManifestListRenderer(Renderer):
    '''
    Renderer for search and package list commands
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
        table = Table(self.tm)

        # Header
        self._addHeaderRows(table, nbElements)
        if len(self) > 0:
            table.newRow().newSep() \
                .newCell(self.tm.LABEL("Identifier"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Description"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Tags"), HAlign.CENTER).newSep()
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
                    .newCell(self._getTagList(inputElt)).newSep()

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
                .newCell(self.tm.LABEL("Identifier"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Properties"), HAlign.CENTER).newHSpan().newSep()
            table.newRow().newDblSep(nbElements)

            # Body
            for inputElt in self:
                labels, values = self._createPropertyTable(inputElt)

                # Create table row
                table.newRow().newSep() \
                    .newCell(inputElt.getIdentifier()).newSep() \
                    .newCell("\n".join(map(str, labels)), HAlign.RIGHT) \
                    .newCell("\n".join(map(str, values))).newSep()

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
            values.append(self._getTagList(inputElt))

        # Release date
        relDate = inputElt.getDate()
        if relDate is not None:
            labels.append("Release date:")
            values.append(relDate)

        # Count included packages
        depCount = len(inputElt.getLeafDepends())

        # For Availables Packages
        if isinstance(inputElt, AvailablePackage):
            # Sources
            remoteCount = len(inputElt.sourceRemotes)
            if remoteCount > 0:
                labels.append("Source:" if remoteCount <= 1 else "Sources:")
                values.append(",".join(remote.alias
                                       for remote in inputElt.sourceRemotes))

            if depCount == 0:
                # Size
                labels.append("Size:")
                values.append(sizeof_fmt(inputElt.getSize()))
        # For Installed Packages
        elif isinstance(inputElt, InstalledPackage):
            # Folder
            labels.append("Folder:")
            values.append(inputElt.folder)

        # Included packages
        if depCount > 0:
            labels.append("Included Packages:" if depCount >
                          1 else "Included Package:")
            values.append("\n".join(self._getCpis(inclPack)
                                    for inclPack in inputElt.getLeafDepends()))

        return map(self.tm.LABEL, labels), values

    def _addHeaderRows(self, table, tableSize):
        '''
        Add header to the given Table like that:
        ┌──────────────────────────────────────────────────────────────────┐
        │                36 packages - Filter: only master                 │
        ├──────────────────────────────────────────────────────────────────┤
        '''
        inputCount = len(self)
        title = "{count} {labeltheme}{featureLabel} - Filter:{resettheme} {filter}".format(
            count=inputCount,
            labeltheme=self.tm.LABEL,
            featureLabel="package" if inputCount <= 1 else "packages",
            resettheme=self.tm.RESET,
            filter=self.pkgFilter)
        table.newHeader(title, tableSize)

    def _getCpis(self, cpis):
        try:
            return str(ConditionalPackageIdentifier.fromString(cpis))
        except Exception:
            return cpis

    def _getTagList(self, inputElt):
        return ",".join(map(self.tm.colorizeTag, inputElt.getAllTags()))
