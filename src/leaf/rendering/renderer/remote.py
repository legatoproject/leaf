"""
Renderer for remote list command

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from leaf.model.remote import Remote
from leaf.rendering.alignment import HAlign
from leaf.rendering.renderer.renderer import Renderer
from leaf.rendering.table import Table


class RemoteListRenderer(Renderer):

    """
    Renderer for remote list command
    """

    def __init__(self):
        Renderer.__init__(self)

    def _tostring_default(self):
        """
        Show a table like that:
        ┌───────────────────────────────────────────────────────────────────────────┐
        │                                  1 remote                                 │
        ├─────────┬───────────────────────────────────────────────────────┬─────────┤
        │  Alias  │                          URL                          │ Enabled │
        ╞═════════╪═══════════════════════════════════════════════════════╪═════════╡
        │ default │ {REMOTE_URL}                                          │ yes     │
        └─────────┴───────────────────────────────────────────────────────┴─────────┘
        """
        count = 7
        table = Table(self.tm)

        # Header
        self._add_header_rows(table, count)
        if len(self) > 0:
            table.new_row().new_separator().new_cell(self.tm.LABEL("Alias"), HAlign.CENTER).new_separator().new_cell(
                self.tm.LABEL("URL"), HAlign.CENTER
            ).new_separator().new_cell(self.tm.LABEL("Enabled"), HAlign.CENTER).new_separator()
            table.new_row().new_double_separator(count)

            # Body
            for element in self:
                theme = self.tm.VOID

                if not element.enabled:
                    theme = self.tm.REMOTE_DISABLED

                # Draw table
                table.new_row().new_separator().new_cell(theme(element.alias or "")).new_separator().new_cell(theme(element.url)).new_separator().new_cell(
                    theme(self._bool_to_text(element.enabled))
                ).new_separator()

            # Footer
            table.new_row().new_separator(count)

        return table

    def _bool_to_text(self, v):
        return "yes" if v else "no"

    def _tostring_verbose(self):
        """
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
        """
        count = 6
        table = Table(self.tm)

        # Header
        self._add_header_rows(table, count)

        if len(self) > 0:
            table.new_row().new_separator().new_cell(self.tm.LABEL("Alias"), HAlign.CENTER).new_separator().new_cell(
                self.tm.LABEL("Properties"), HAlign.CENTER
            ).new_hspan().new_separator()
            table.new_row().new_double_separator(count)

            for element in self:
                labels, values = self._create_property_table(element)

                alias = element.alias or "No alias"

                # Create table row
                table.new_row().new_separator().new_cell(alias).new_separator().new_cell("\n".join(map(str, labels)), HAlign.RIGHT).new_cell(
                    "\n".join(map(str, values))
                ).new_separator()

                # Footer for each manifest
                table.new_row().new_separator(count)

        return table

    def _create_property_table(self, element: Remote):
        labels = []
        values = []

        # URL
        labels.append(self.tm.LABEL("Url:"))
        values.append(element.url)

        if element.is_fetched:
            # Name
            if element.info_name is not None:
                labels.append("Name:")
                values.append(element.info_name)

            # Description
            if element.info_description is not None:
                labels.append("Description:")
                values.append(element.info_description)

            # Last update
            if element.info_date is not None:
                labels.append("Last update:")
                values.append(element.info_date)

            # Priority
            labels.append("Priority:")
            values.append(element.priority)

        labels.append("Enabled:")
        values.append(self._bool_to_text(element.enabled))

        if element.enabled:
            labels.append("Fetched:")
            values.append(self._bool_to_text(element.is_fetched))

        return map(self.tm.LABEL, labels), values

    def _add_header_rows(self, table, size):
        """
        Add header to the given Table like that:
        ┌──────────────────────────────────────────────────────────────────────────┐
        │                                 5 remote                                 │
        ├─────────┬────────────────────────────────────────────────────────────────┤
        """
        count = len(self)
        title = "{count} {labeltheme}{featureLabel}{resettheme}".format(
            count=count, labeltheme=self.tm.LABEL, featureLabel="remote" if count <= 1 else "remotes", resettheme=self.tm.RESET
        )
        table.new_header(title, size)
