'''
Renderer for feature list command

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import operator

from leaf.format.alignment import HAlign
from leaf.format.renderer.renderer import Renderer
from leaf.format.table import Table


class FeatureListRenderer(Renderer):
    '''
    Renderer for feature list command
    '''

    def _toStringDefault(self):
        '''
        Show a table like that:
        ┌─────────────────────────────────────────────────────────────────┐
        │                            6 features                           │
        ├─────────────────────────┬───────────────────────┬───────────────┤
        │         Feature         │      Description      │     Values    │
        ╞═════════════════════════╪═══════════════════════╪═══════════════╡
        │ broken-src              │                       │ binary|source │
        │ featureWithDups         │                       │ enum1|enum2   │
        │ featureWithMultipleKeys │                       │ enum1         │
        │ myFeatureFoo            │ Some description here │ bar|notbar    │
        │ myFeatureHello          │ Some description here │ default|world │
        │ test-src                │                       │ binary|source │
        └─────────────────────────┴───────────────────────┴───────────────┘
        '''
        nbElements = 7
        table = Table(self.tm)

        # Header
        self._addHeaderRows(table, nbElements)
        if len(self) > 0:
            table.newRow().newSep() \
                .newCell(self.tm.LABEL("Feature"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Description"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Values"), HAlign.CENTER).newSep()
            table.newRow().newDblSep(nbElements)

            # Body
            for inputElt in self:
                descValue = ""
                if inputElt.getDescription() is not None:
                    descValue = inputElt.getDescription()

                # Draw table
                table.newRow().newSep() \
                    .newCell(inputElt.name).newSep() \
                    .newCell(descValue).newSep() \
                    .newCell("|".join(sorted(inputElt.getValues().keys()))).newSep()

            # Footer
            table.newRow().newSep(nbElements)

        return table

    def _toStringVerbose(self):
        '''
        Show a table like that:
        ┌────────────────────────────────────────────────────────────────┐
        │                           6 features                           │
        ├─────────────────────────┬──────────────────────────────────────┤
        │         Feature         │              Properties              │
        ╞═════════════════════════╪══════════════════════════════════════╡
        │ broken-src              │         Key: LEAF_FTR_BROKEN_SRC     │
        │                         │      Values: binary()                │
        │                         │              source(1)               │
        ├─────────────────────────┼──────────────────────────────────────┤
        │ featureWithDups         │         Key: featureWithDups         │
        │                         │      Values: enum1(VALUE1)           │
        │                         │              enum2(VALUE2)           │
        ├─────────────────────────┼──────────────────────────────────────┤
        │ featureWithMultipleKeys │         Key: featureWithMultipleKeys │
        │                         │       Value: enum1(VALUE1)           │
        ├─────────────────────────┼──────────────────────────────────────┤
        │ myFeatureFoo            │ Description: Some description here   │
        │                         │         Key: FOO                     │
        │                         │      Values: bar(BAR)                │
        │                         │              notbar(OTHER_VALUE)     │
        ├─────────────────────────┼──────────────────────────────────────┤
        │ myFeatureHello          │ Description: Some description here   │
        │                         │         Key: HELLO                   │
        │                         │      Values: default()               │
        │                         │              world(WoRlD)            │
        ├─────────────────────────┼──────────────────────────────────────┤
        │ test-src                │         Key: LEAF_FTR_TEST_SRC       │
        │                         │      Values: binary()                │
        │                         │              source(1)               │
        └─────────────────────────┴──────────────────────────────────────┘
        '''
        nbElements = 6
        table = Table(self.tm)

        # Header
        self._addHeaderRows(table, nbElements)

        if len(self) > 0:
            table.newRow().newSep() \
                .newCell(self.tm.LABEL("Feature"), HAlign.CENTER).newSep() \
                .newCell(self.tm.LABEL("Properties"), HAlign.CENTER).newHSpan().newSep()
            table.newRow().newDblSep(nbElements)

            # Body
            for inputElt in self:
                labels, values = self._createPropertyTable(inputElt)

                # Create table row
                table.newRow().newSep() \
                    .newCell(inputElt.name).newSep() \
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

        # Key
        if inputElt.getKey() is not None:
            labels.append("Key:")
            values.append(inputElt.getKey())

        # Values
        tagCount = len(inputElt.getValues().items())
        if tagCount > 0:
            labels.append("Values:" if tagCount > 1 else "Value:")

            values.extend(["%s(%s)" % (k, "" if v is None else v)
                           for k, v in sorted(inputElt.getValues().items(),
                                              key=operator.itemgetter(0))])

        return map(self.tm.LABEL, labels), values

    def _addHeaderRows(self, table, tableSize):
        '''
        Add header to the given Table like that:
        ┌─────────────────────────────────────────────────────────────────┐
        │                            6 features                           │
        ├─────────────────────────┬───────────────────────────────────────┤
        '''
        inputCount = len(self)
        title = "{count} {labeltheme}{featureLabel}{resettheme}".format(
            count=inputCount,
            labeltheme=self.tm.LABEL,
            featureLabel="feature" if inputCount <= 1 else "features",
            resettheme=self.tm.RESET)
        table.newHeader(title, tableSize)
