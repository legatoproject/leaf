"""
Renderer for feature list command

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import operator

from leaf.rendering.alignment import HAlign
from leaf.rendering.renderer.renderer import Renderer
from leaf.rendering.table import Table


class FeatureListRenderer(Renderer):

    """
    Renderer for feature list command
    """

    def __init__(self):
        Renderer.__init__(self)

    def _tostring_default(self):
        """
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
        """
        count = 7
        table = Table(self.tm)

        # Header
        self._add_header_rows(table, count)
        if len(self) > 0:
            table.new_row().new_separator().new_cell(self.tm.LABEL("Feature"), HAlign.CENTER).new_separator().new_cell(
                self.tm.LABEL("Description"), HAlign.CENTER
            ).new_separator().new_cell(self.tm.LABEL("Values"), HAlign.CENTER).new_separator()
            table.new_row().new_double_separator(count)

            # Body
            for element in self:
                # Draw table
                table.new_row().new_separator().new_cell(element.name).new_separator().new_cell(element.description or "").new_separator().new_cell(
                    "|".join(sorted(element.values.keys()))
                ).new_separator()

            # Footer
            table.new_row().new_separator(count)

        return table

    def _tostring_verbose(self):
        """
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
        """
        count = 6
        table = Table(self.tm)

        # Header
        self._add_header_rows(table, count)

        if len(self) > 0:
            table.new_row().new_separator().new_cell(self.tm.LABEL("Feature"), HAlign.CENTER).new_separator().new_cell(
                self.tm.LABEL("Properties"), HAlign.CENTER
            ).new_hspan().new_separator()
            table.new_row().new_double_separator(count)

            # Body
            for element in self:
                labels, values = self._create_property_table(element)

                # Create table row
                table.new_row().new_separator().new_cell(element.name).new_separator().new_cell("\n".join(map(str, labels)), HAlign.RIGHT).new_cell(
                    "\n".join(map(str, values))
                ).new_separator()

                # Footer for each manifest
                table.new_row().new_separator(count)

        return table

    def _create_property_table(self, element):
        labels = []
        values = []

        # Description
        if element.description is not None:
            labels.append("Description:")
            values.append(element.description)

        # Key
        if element.key is not None:
            labels.append("Key:")
            values.append(element.key)

        # Values
        tag_count = len(element.values.items())
        if tag_count > 0:
            labels.append("Values:" if tag_count > 1 else "Value:")
            values.extend(["{enum}({value})".format(enum=k, value=v or "") for k, v in sorted(element.values.items(), key=operator.itemgetter(0))])

        return map(self.tm.LABEL, labels), values

    def _add_header_rows(self, table, size):
        """
        Add header to the given Table like that:
        ┌─────────────────────────────────────────────────────────────────┐
        │                            6 features                           │
        ├─────────────────────────┬───────────────────────────────────────┤
        """
        count = len(self)
        title = "{count} {labeltheme}{featurelabel}{resettheme}".format(
            count=count, labeltheme=self.tm.LABEL, featurelabel="feature" if count <= 1 else "features", resettheme=self.tm.RESET
        )
        table.new_header(title, size)
