"""
Renderer for search and package list commands

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from leaf.model.package import Entrypoint
from leaf.rendering.alignment import HAlign
from leaf.rendering.renderer.renderer import Renderer
from leaf.rendering.table import Table


class EntrypointListRenderer(Renderer):

    """
    Renderer for entrypoints
    """

    def __init__(self, scope):
        Renderer.__init__(self)
        self.scope = scope

    def _tostring_quiet(self):
        lines = []
        for ip in self:
            for ep in ip.binaries.values():
                lines.append("{pi}/{bin}: {desc}".format(pi=ip.identifier, bin=ep.name, desc=ep.description or ""))
        return "\n".join(lines)

    def _tostring_default(self):
        return self._tostring_verbose()

    def _tostring_verbose(self):
        """
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
        """
        count = 6
        table = Table(self.tm)

        # Header
        self._add_header_rows(table, count)

        if len(self) > 0:
            table.new_row().new_separator().new_cell(self.tm.LABEL("Package"), HAlign.CENTER).new_separator().new_cell(
                self.tm.LABEL("Binaries"), HAlign.CENTER
            ).new_hspan().new_separator()
            table.new_row().new_double_separator(count)

            # Body
            for ip in self:
                if len(ip.binaries) > 0:
                    labels, values = self._create_property_table(ip)

                    # Create table row
                    table.new_row().new_separator().new_cell(ip.identifier).new_separator().new_cell("\n".join(map(str, labels))).new_cell(
                        "\n".join(map(str, values))
                    ).new_separator()

                    # Footer for each manifest
                    table.new_row().new_separator(count)

        return table

    def _create_property_table(self, element: Entrypoint):
        labels = []
        values = []

        for _, entrypoint in element.binaries.items():
            labels.append(entrypoint.name)
            values.append(entrypoint.description or "")

        return map(self.tm.LABEL, labels), values

    def _add_header_rows(self, table, size):
        """
        Add header to the given Table like that:
        ┌────────────────────────────────────────────────────────────────────────────────┐
        │         List of declared binaries in workspace|installed packages|PKG_NAME     │
        ├────────────────────────────────────────────────────────────────────────────────┤
        """
        title = "List of declared binaries in {0}".format(self.scope)
        table.new_header(title, size)
