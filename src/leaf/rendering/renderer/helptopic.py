"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from leaf.model.package import Entrypoint
from leaf.rendering.alignment import HAlign
from leaf.rendering.renderer.renderer import Renderer
from leaf.rendering.table import Table


class HelpTopicListRenderer(Renderer):
    def __init__(self, scope, filter_format: str = None):
        Renderer.__init__(self)
        self.scope = scope
        self.filter_format = filter_format

    def _tostring_quiet(self):
        lines = []
        for ip in self:
            for ht in ip.help_topics.values():
                if self.filter_format is None or self.filter_format in ht.resources.keys():
                    lines.append("{pi.name}/{t.name}: {fmt}".format(pi=ip.identifier, t=ht, fmt="|".join(ht.resources.keys())))
        return "\n".join(lines)

    def _tostring_default(self):
        return self._tostring_verbose()

    def _tostring_verbose(self):
        """
        Show a table like that:
        ┌──────────────────────────────────────────────────┐
        │     Topic     │     Package     │     Format     │
        ╞═══════════════╪═════════════════╪════════════════╡
        """
        count = 7
        table = Table(self.tm)

        # Header
        self._add_header_rows(table, count)

        if len(self) > 0:
            table.new_row().new_separator().new_cell(self.tm.LABEL("Topic"), HAlign.CENTER).new_separator().new_cell(
                self.tm.LABEL("Version"), HAlign.CENTER
            ).new_separator().new_cell(self.tm.LABEL("Formats"), HAlign.CENTER).new_separator()

            topics = []
            for ip in self:
                for topic in ip.help_topics.values():
                    if self.filter_format is None or self.filter_format in topic.resources.keys():
                        topics.append(topic)

            if len(topics) > 0:
                table.new_row().new_double_separator(count)
                for topic in topics:
                    # Create table row
                    table.new_row().new_separator().new_cell(topic.full_name).new_separator().new_cell(
                        topic.installed_package.version
                    ).new_separator().new_cell("|".join(topic.resources.keys())).new_separator()
            table.new_row().new_separator(count)

        return table

    def _create_property_table(self, element: Entrypoint):
        labels = []
        values = []

        for topic in element.help_topics.values():
            labels.append(topic.name)
            values.append(", ".join(topic.resources.keys()))

        return map(self.tm.LABEL, labels), values

    def _add_header_rows(self, table, size):
        """
        Add header to the given Table like that:
        ┌────────────────────────────────────────────────────────────────────────────────┐
        │         List of help topics in workspace|installed packages|PKG_NAME           │
        ├────────────────────────────────────────────────────────────────────────────────┤
        """
        title = "List of help topics in {0}".format(self.scope)
        table.new_header(title, size)
